"""Parallel execution support for CPU scaling.

Provides safe multi-core execution for agent processing.

Key constraints:
- No shared mutable state across processes
- Deterministic partitioning based on seed
- RNG state must be consistent
- Optional and auto-scaled based on CPU count
"""

import os
import random
from typing import Dict, List, Tuple, Callable, Any, Optional, TypeVar
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from living_matrix.constants.performance_constants import (
    ENABLE_PARALLEL,
    get_worker_count,
    should_use_parallel,
    AGENT_BATCH_SIZE
)
from living_matrix.utils.observability import get_observer

T = TypeVar('T')


@dataclass
class AgentBatch:
    """A batch of agents for parallel processing."""
    batch_id: int
    agent_ids: List[str]
    seed_offset: int  # For deterministic RNG in each batch


@dataclass
class BatchResult:
    """Result from processing a batch."""
    batch_id: int
    events: List[Tuple[str, str, Optional[str]]]
    agent_updates: Dict[str, Dict[str, Any]]  # agent_id -> field updates
    metrics: Dict[str, Any]


def partition_agents_deterministic(
    agent_ids: List[str],
    num_batches: int,
    seed: int
) -> List[AgentBatch]:
    """
    Partition agents into deterministic batches.
    
    The partitioning is stable: same agents, seed, and batch count
    always produces the same batches.
    
    Args:
        agent_ids: List of agent IDs to partition
        num_batches: Number of batches to create
        seed: Random seed for deterministic partitioning
    
    Returns:
        List of AgentBatch objects
    """
    if num_batches <= 0:
        num_batches = 1
    
    # Sort for determinism
    sorted_ids = sorted(agent_ids)
    
    # Create batches
    batches = []
    batch_size = max(1, len(sorted_ids) // num_batches)
    
    for i in range(num_batches):
        start = i * batch_size
        if i == num_batches - 1:
            # Last batch gets any remainder
            end = len(sorted_ids)
        else:
            end = start + batch_size
        
        if start >= len(sorted_ids):
            break
        
        batch_ids = sorted_ids[start:end]
        if batch_ids:
            batches.append(AgentBatch(
                batch_id=i,
                agent_ids=batch_ids,
                seed_offset=seed + i * 1000  # Unique but deterministic seed
            ))
    
    return batches


def _process_agent_batch_worker(
    batch: AgentBatch,
    agent_data: Dict[str, Dict],  # Serialized agent data
    context_data: Dict[str, Any],  # Serialized context
    processor_func_name: str  # Name of processor to use
) -> BatchResult:
    """
    Worker function for processing an agent batch.
    
    This runs in a separate process. All data must be serializable.
    
    Args:
        batch: The batch to process
        agent_data: Dictionary of agent_id -> serialized agent dict
        context_data: Shared context data (read-only)
        processor_func_name: Name of the processing function to use
    
    Returns:
        BatchResult with events and updates
    """
    # Initialize RNG with batch-specific seed
    random.seed(batch.seed_offset)
    
    events = []
    agent_updates = {}
    metrics = {"processed": 0}
    
    # Process each agent
    for agent_id in batch.agent_ids:
        if agent_id not in agent_data:
            continue
        
        agent = agent_data[agent_id]
        
        # Apply basic processing (needs update, mood update)
        updates = _process_single_agent(agent, context_data)
        
        if updates:
            agent_updates[agent_id] = updates
        
        metrics["processed"] = metrics.get("processed", 0) + 1
    
    return BatchResult(
        batch_id=batch.batch_id,
        events=events,
        agent_updates=agent_updates,
        metrics=metrics
    )


def _process_single_agent(
    agent: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a single agent (needs decay, mood update).
    
    Returns dict of field updates to apply.
    """
    updates = {}
    
    # Needs decay (basic version for parallel processing)
    if "needs" in agent:
        needs = agent["needs"]
        new_hunger = min(100, needs.get("hunger", 30) + 1)
        updates["needs.hunger"] = new_hunger
        
        if agent.get("current_action") not in ["rest", "idle"]:
            new_rest = min(100, needs.get("rest", 40) + 2)
            updates["needs.rest"] = new_rest
        
        # Belonging decay
        new_belonging = max(0, needs.get("belonging", 50) - 0.5)
        updates["needs.belonging"] = new_belonging
    
    return updates


class ParallelExecutor:
    """
    Manages parallel execution of agent processing.
    
    Usage:
        executor = ParallelExecutor(seed=42)
        if executor.should_parallelize(agent_count):
            results = executor.process_agents_parallel(agents, context, processor)
        else:
            results = executor.process_agents_sequential(agents, context, processor)
    """
    
    __slots__ = ('_seed', '_executor', '_worker_count', '_enabled')
    
    def __init__(self, seed: int = 42):
        self._seed = seed
        self._worker_count = get_worker_count()
        self._enabled = ENABLE_PARALLEL
        self._executor: Optional[ProcessPoolExecutor] = None
    
    def should_parallelize(self, agent_count: int) -> bool:
        """Check if parallelization should be used."""
        return self._enabled and should_use_parallel(agent_count)
    
    def get_batches(self, agent_ids: List[str]) -> List[AgentBatch]:
        """Get deterministic batches for agents."""
        num_batches = min(self._worker_count, len(agent_ids) // AGENT_BATCH_SIZE + 1)
        return partition_agents_deterministic(agent_ids, num_batches, self._seed)
    
    def process_agents_parallel(
        self,
        agents: Dict[str, Any],
        context: Dict[str, Any],
        processor: Callable[[Dict, Dict], Dict]
    ) -> Tuple[List[Tuple[str, str, Optional[str]]], Dict[str, Dict]]:
        """
        Process agents in parallel using ProcessPoolExecutor.
        
        Args:
            agents: Dictionary of agent_id -> agent object
            context: Context data for processing
            processor: Function to process each agent
        
        Returns:
            Tuple of (all_events, all_updates)
        """
        observer = get_observer()
        
        # Serialize agents for inter-process transfer
        agent_data = {}
        for agent_id, agent in agents.items():
            agent_data[agent_id] = self._serialize_agent(agent)
        
        # Create batches
        agent_ids = list(agents.keys())
        batches = self.get_batches(agent_ids)
        
        if not batches:
            return ([], {})
        
        # Process batches in parallel
        all_events = []
        all_updates = {}
        completed_batches = 0
        
        try:
            if self._executor is None:
                self._executor = ProcessPoolExecutor(max_workers=self._worker_count)
            
            futures = []
            for batch in batches:
                # Get agent data for this batch
                batch_agent_data = {
                    aid: agent_data[aid] for aid in batch.agent_ids if aid in agent_data
                }
                future = self._executor.submit(
                    _process_agent_batch_worker,
                    batch,
                    batch_agent_data,
                    context,
                    "default"
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    all_events.extend(result.events)
                    all_updates.update(result.agent_updates)
                    completed_batches += 1
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"Batch processing failed: {e}",
                        exc_info=True
                    )
            
            # Record utilization
            if len(batches) > 0:
                utilization = completed_batches / len(batches)
                observer.record_worker_utilization(utilization)
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Parallel execution failed: {e}",
                exc_info=True
            )
            # Fallback to sequential
            return self.process_agents_sequential(agents, context, processor)
        
        return (all_events, all_updates)
    
    def process_agents_sequential(
        self,
        agents: Dict[str, Any],
        context: Dict[str, Any],
        processor: Callable[[Any, Dict], Tuple[List, Dict]]
    ) -> Tuple[List[Tuple[str, str, Optional[str]]], Dict[str, Dict]]:
        """
        Process agents sequentially (fallback or small population).
        
        Args:
            agents: Dictionary of agent_id -> agent object
            context: Context data for processing
            processor: Function to process each agent
        
        Returns:
            Tuple of (all_events, all_updates)
        """
        all_events = []
        all_updates = {}
        
        for agent_id, agent in agents.items():
            events, updates = processor(agent, context)
            all_events.extend(events)
            if updates:
                all_updates[agent_id] = updates
        
        return (all_events, all_updates)
    
    def _serialize_agent(self, agent: Any) -> Dict[str, Any]:
        """Serialize an agent for inter-process transfer."""
        # Handle both dict and object agents
        if isinstance(agent, dict):
            return agent
        
        # Serialize object
        data = {
            "id": getattr(agent, "id", ""),
            "name": getattr(agent, "name", ""),
            "district": getattr(agent, "district", ""),
            "location": getattr(agent, "location", ""),
            "role": getattr(agent, "role", ""),
            "mood": getattr(agent, "mood", 0.0),
            "current_action": getattr(agent, "current_action", "idle"),
            "age": getattr(agent, "age", 0),
            "is_alive": getattr(agent, "is_alive", True),
        }
        
        # Serialize needs
        if hasattr(agent, "needs"):
            needs = agent.needs
            data["needs"] = {
                "hunger": getattr(needs, "hunger", 30),
                "rest": getattr(needs, "rest", 40),
                "safety": getattr(needs, "safety", 70),
                "belonging": getattr(needs, "belonging", 50),
                "purpose": getattr(needs, "purpose", 60),
            }
        
        # Serialize traits
        if hasattr(agent, "traits"):
            traits = agent.traits
            data["traits"] = {
                "risk": getattr(traits, "risk", 0.5),
                "empathy": getattr(traits, "empathy", 0.5),
                "ambition": getattr(traits, "ambition", 0.5),
                "patience": getattr(traits, "patience", 0.5),
            }
        
        return data
    
    def apply_updates(self, agents: Dict[str, Any], updates: Dict[str, Dict]) -> None:
        """
        Apply updates from parallel processing back to agents.
        
        Args:
            agents: The agent dictionary to update
            updates: Dictionary of agent_id -> field updates
        """
        for agent_id, agent_updates in updates.items():
            if agent_id not in agents:
                continue
            
            agent = agents[agent_id]
            
            for field_path, value in agent_updates.items():
                # Handle nested paths like "needs.hunger"
                parts = field_path.split(".")
                obj = agent
                
                for part in parts[:-1]:
                    if hasattr(obj, part):
                        obj = getattr(obj, part)
                    elif isinstance(obj, dict) and part in obj:
                        obj = obj[part]
                    else:
                        break
                
                # Set final value
                final_part = parts[-1]
                if hasattr(obj, final_part):
                    setattr(obj, final_part, value)
                elif isinstance(obj, dict):
                    obj[final_part] = value
    
    def shutdown(self) -> None:
        """Shutdown the executor pool."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None


# Global executor instance (lazy initialized)
_executor: Optional[ParallelExecutor] = None


def get_parallel_executor(seed: int = 42) -> ParallelExecutor:
    """Get or create the global parallel executor."""
    global _executor
    if _executor is None:
        _executor = ParallelExecutor(seed=seed)
    return _executor
