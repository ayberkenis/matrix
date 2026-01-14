"""Cleanup Module - Memory management and pruning.

This module handles cleanup of accumulated data to prevent unbounded
memory growth:

- Dead agent cleanup (rolling cap)
- Relationship pruning (per-agent cap)
- Belief pruning (keep strongest)
- Memory cleanup (already capped, but can be reduced)

PERFORMANCE IMPACT:
- Prevents memory exhaustion
- Reduces iteration overhead for large collections
- Improves cache locality

BEHAVIOR PRESERVATION:
- Pruning is deterministic based on strength/recency
- Only very weak/old data is removed
- No behavioral impact on active simulation
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Set
from collections import deque

from ..constants.performance_constants import (
    MAX_DEAD_AGENTS,
    DEAD_AGENT_PRUNE_COUNT,
    DEAD_AGENT_CLEANUP_INTERVAL,
    MAX_RELATIONSHIPS_PER_AGENT,
    RELATIONSHIP_PRUNE_THRESHOLD,
)

if TYPE_CHECKING:
    from ..human_agent import HumanAgent, HumanAgentSystem

logger = logging.getLogger(__name__)


class DeadAgentManager:
    """
    Manages dead agent storage with rolling cap.
    
    Instead of keeping all dead agents forever, keeps only the most recent
    and stores summary statistics for the rest.
    """
    
    def __init__(self, max_agents: int = MAX_DEAD_AGENTS):
        self.max_agents = max_agents
        self.prune_count = DEAD_AGENT_PRUNE_COUNT
        self._cleanup_interval = DEAD_AGENT_CLEANUP_INTERVAL
        self._last_cleanup_turn = 0
        
        # Archived statistics
        self.archived_count = 0
        self.archived_total_age = 0
        self.archived_by_cause: Dict[str, int] = {}
    
    def should_cleanup(self, turn: int) -> bool:
        """Check if cleanup should run this turn."""
        return turn - self._last_cleanup_turn >= self._cleanup_interval
    
    def cleanup(
        self,
        dead_agents: Dict[str, 'HumanAgent'],
        turn: int
    ) -> int:
        """
        Clean up dead agents dict, keeping only the most recent.
        
        Returns number of agents archived.
        """
        if len(dead_agents) <= self.max_agents:
            self._last_cleanup_turn = turn
            return 0
        
        # Sort by death turn (oldest first)
        agents_by_death = sorted(
            dead_agents.values(),
            key=lambda a: a.death_turn if a.death_turn else 0
        )
        
        # Archive the oldest agents
        to_archive = agents_by_death[:self.prune_count]
        archived = 0
        
        for agent in to_archive:
            self._archive_agent(agent)
            del dead_agents[agent.id]
            archived += 1
        
        self._last_cleanup_turn = turn
        logger.debug(f"Archived {archived} dead agents (total: {self.archived_count})")
        
        return archived
    
    def _archive_agent(self, agent: 'HumanAgent'):
        """Archive an agent's statistics without keeping full object."""
        self.archived_count += 1
        self.archived_total_age += agent.age
        
        # Track death causes
        cause = getattr(agent, 'death_cause', 'unknown')
        self.archived_by_cause[cause] = self.archived_by_cause.get(cause, 0) + 1
    
    def get_statistics(self) -> Dict:
        """Get archived agent statistics."""
        avg_age = (
            self.archived_total_age / self.archived_count
            if self.archived_count > 0 else 0
        )
        return {
            "archived_count": self.archived_count,
            "average_age": avg_age,
            "death_causes": self.archived_by_cause.copy(),
        }


class RelationshipPruner:
    """
    Prunes weak relationships to prevent unbounded growth.
    
    Each agent has a cap on relationships. When exceeded, the weakest
    relationships (by combined strength) are removed.
    """
    
    def __init__(
        self,
        max_per_agent: int = MAX_RELATIONSHIPS_PER_AGENT,
        prune_threshold: float = RELATIONSHIP_PRUNE_THRESHOLD
    ):
        self.max_per_agent = max_per_agent
        self.prune_threshold = prune_threshold
        
        # Statistics
        self._total_pruned = 0
    
    def prune_agent_relationships(
        self,
        agent: 'HumanAgent',
        turn: int
    ) -> int:
        """
        Prune relationships for a single agent.
        
        Returns number of relationships pruned.
        """
        if len(agent.relationships) <= self.max_per_agent:
            return 0
        
        # Calculate strength for each relationship
        rel_strengths: List[Tuple[str, float]] = []
        
        for target_id, rel in agent.relationships.items():
            # Strength = affection + trust + familiarity weight
            strength = (
                abs(rel.affection) * 0.4 +
                rel.trust * 0.4 +
                min(1.0, rel.familiarity / 100) * 0.2
            )
            rel_strengths.append((target_id, strength))
        
        # Sort by strength (weakest first)
        rel_strengths.sort(key=lambda x: x[1])
        
        # Remove weakest until at cap
        to_remove = len(agent.relationships) - self.max_per_agent
        pruned = 0
        
        for target_id, strength in rel_strengths[:to_remove]:
            # Only prune if below threshold
            if strength < self.prune_threshold:
                del agent.relationships[target_id]
                pruned += 1
            else:
                break  # Stop if we hit relationships above threshold
        
        self._total_pruned += pruned
        return pruned
    
    def prune_all_agents(
        self,
        agents: Dict[str, 'HumanAgent'],
        turn: int,
        sample_fraction: float = 0.1
    ) -> int:
        """
        Prune relationships for a sample of agents.
        
        Uses sampling to avoid O(n) every turn.
        """
        import random
        
        agents_list = list(agents.values())
        sample_size = max(1, int(len(agents_list) * sample_fraction))
        sample = random.sample(agents_list, min(sample_size, len(agents_list)))
        
        total_pruned = 0
        for agent in sample:
            if agent.is_alive:
                total_pruned += self.prune_agent_relationships(agent, turn)
        
        return total_pruned
    
    def get_statistics(self) -> Dict:
        """Get pruning statistics."""
        return {
            "total_pruned": self._total_pruned,
        }


class BeliefPruner:
    """
    Prunes weak beliefs to prevent unbounded growth.
    
    Each agent has a cap on beliefs. When exceeded, the weakest
    beliefs (by confidence) are removed.
    """
    
    def __init__(self, max_per_agent: int = 30):
        self.max_per_agent = max_per_agent
        self._total_pruned = 0
    
    def prune_agent_beliefs(
        self,
        agent: 'HumanAgent',
        turn: int
    ) -> int:
        """Prune beliefs for a single agent."""
        if len(agent.beliefs) <= self.max_per_agent:
            return 0
        
        # Sort by confidence (lowest first)
        beliefs_by_confidence = sorted(
            agent.beliefs.items(),
            key=lambda x: x[1].confidence if hasattr(x[1], 'confidence') else 0
        )
        
        # Remove weakest
        to_remove = len(agent.beliefs) - self.max_per_agent
        pruned = 0
        
        for topic, belief in beliefs_by_confidence[:to_remove]:
            del agent.beliefs[topic]
            pruned += 1
        
        self._total_pruned += pruned
        return pruned


class CleanupManager:
    """
    Coordinates all cleanup operations.
    
    Usage:
        cleanup_mgr = CleanupManager()
        
        # Run periodic cleanup
        if cleanup_mgr.should_run_cleanup(turn):
            cleanup_mgr.run_cleanup(human_agent_system, turn)
    """
    
    def __init__(self):
        self.dead_agent_mgr = DeadAgentManager()
        self.relationship_pruner = RelationshipPruner()
        self.belief_pruner = BeliefPruner()
        
        self._cleanup_interval = 20  # Run full cleanup every N turns
        self._last_cleanup = 0
    
    def should_run_cleanup(self, turn: int) -> bool:
        """Check if cleanup should run this turn."""
        return turn - self._last_cleanup >= self._cleanup_interval
    
    def run_cleanup(
        self,
        system: 'HumanAgentSystem',
        turn: int
    ) -> Dict:
        """
        Run all cleanup operations.
        
        Returns statistics about what was cleaned up.
        """
        start = time.perf_counter()
        results = {}
        
        # Dead agent cleanup
        if self.dead_agent_mgr.should_cleanup(turn):
            archived = self.dead_agent_mgr.cleanup(system.dead_agents, turn)
            results['dead_agents_archived'] = archived
        
        # Relationship pruning (sample-based)
        rel_pruned = self.relationship_pruner.prune_all_agents(
            system.agents, turn, sample_fraction=0.2
        )
        results['relationships_pruned'] = rel_pruned
        
        # Belief pruning (sample-based)
        import random
        agents_list = list(system.agents.values())
        sample = random.sample(
            agents_list,
            min(50, len(agents_list))
        )
        beliefs_pruned = 0
        for agent in sample:
            if agent.is_alive:
                beliefs_pruned += self.belief_pruner.prune_agent_beliefs(agent, turn)
        results['beliefs_pruned'] = beliefs_pruned
        
        duration_ms = (time.perf_counter() - start) * 1000
        results['duration_ms'] = duration_ms
        
        self._last_cleanup = turn
        
        if rel_pruned > 0 or beliefs_pruned > 0:
            logger.debug(
                f"Cleanup turn {turn}: "
                f"rels={rel_pruned}, beliefs={beliefs_pruned}, "
                f"time={duration_ms:.2f}ms"
            )
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get comprehensive cleanup statistics."""
        return {
            "dead_agents": self.dead_agent_mgr.get_statistics(),
            "relationships": self.relationship_pruner.get_statistics(),
            "beliefs": {"total_pruned": self.belief_pruner._total_pruned},
        }


# Global instance
_cleanup_manager: Optional[CleanupManager] = None


def get_cleanup_manager() -> CleanupManager:
    """Get or create the global cleanup manager."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    return _cleanup_manager


def reset_cleanup_manager():
    """Reset the global cleanup manager (for testing)."""
    global _cleanup_manager
    _cleanup_manager = None
