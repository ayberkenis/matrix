"""Agent tier management for performance-optimized simulation.

Agents are divided into tiers to reduce per-tick workload:
- ACTIVE: Fully simulated each tick (decision making, actions, etc.)
- INACTIVE: Statistically updated (needs decay, relationship decay) every N ticks
- CHILD_POOL: Aggregated counters, no individual simulation

This is the "Active Set" mechanism - analogous to an LLM's context window.
Only ACTIVE agents get full simulation; others get compressed updates.

Safety Guarantee: When ACTIVE_SET_ENABLED is False, ALL agents are active
and behavior is identical to baseline.
"""

import random
from typing import Dict, List, Set, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from living_matrix.constants.performance_constants import (
    TIER_POPULATION_THRESHOLD,
    FULL_SIMULATION_FRACTION,
    MIN_FULL_SIMULATION_COUNT,
    MAX_ACTIVE_SIMULATION_COUNT,
    INACTIVE_AGENT_UPDATE_INTERVAL,
    VERY_LARGE_POP_THRESHOLD,
    VERY_LARGE_POP_SIMULATION_FRACTION,
    VERY_LARGE_MAX_ACTIVE
)

# Import learning config for ACTIVE_SET_ENABLED
try:
    from living_matrix.config import get_config as get_learning_config
    _HAS_LEARNING_CONFIG = True
except ImportError:
    _HAS_LEARNING_CONFIG = False
    def get_learning_config():
        return None

if TYPE_CHECKING:
    from living_matrix.dataclasses import HumanAgent


class AgentTier(Enum):
    """Agent simulation tiers."""
    ACTIVE = "active"      # Fully simulated each tick
    INACTIVE = "inactive"  # Statistically updated periodically
    # Children are not agents - they exist in cohort pools


@dataclass
class TierAssignment:
    """Tracks which tier each agent belongs to."""
    agent_id: str
    tier: AgentTier
    last_full_update: int = 0  # Turn of last full simulation
    priority_score: float = 0.0  # Higher = more likely to be active


@dataclass
class TierState:
    """State for the tier management system."""
    assignments: Dict[str, TierAssignment] = field(default_factory=dict)
    active_ids: Set[str] = field(default_factory=set)
    inactive_ids: Set[str] = field(default_factory=set)
    last_rotation_turn: int = 0
    rotation_interval: int = 10  # Rotate active set every N turns


class AgentTierManager:
    """
    Manages agent tier assignments for optimized simulation.
    
    Key principles:
    - Deterministic tier assignment when seed is fixed
    - Preserves simulation behavior over time (all agents get updates)
    - Rotates active set to ensure fair simulation coverage
    """
    
    __slots__ = ('_state', '_rng', '_seed')
    
    def __init__(self, seed: int = 42):
        self._seed = seed
        self._rng = random.Random(seed)
        self._state = TierState()
    
    def should_use_tiers(self, agent_count: int) -> bool:
        """
        Check if tier system should be active.
        
        Conditions:
        - Population exceeds threshold, OR
        - ACTIVE_SET_ENABLED is True in config
        
        When tier system is disabled, ALL agents are active.
        """
        # Check config flag first
        if _HAS_LEARNING_CONFIG:
            cfg = get_learning_config()
            if cfg and cfg.ACTIVE_SET_ENABLED:
                return True  # Always use tiers when explicitly enabled
        
        return agent_count >= TIER_POPULATION_THRESHOLD
    
    def update_assignments(
        self,
        agents: Dict[str, 'HumanAgent'],
        turn: int,
        force_active_ids: Optional[Set[str]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Update tier assignments based on current population.
        
        Args:
            agents: Dictionary of all active agents
            turn: Current simulation turn
            force_active_ids: Optional set of agent IDs that must be active
                             (e.g., followed agent, recently interacted)
        
        Returns:
            Tuple of (active_agent_ids, inactive_agent_ids)
        """
        agent_count = len(agents)
        
        # Below threshold: all agents are active
        if not self.should_use_tiers(agent_count):
            all_ids = list(agents.keys())
            self._state.active_ids = set(all_ids)
            self._state.inactive_ids = set()
            return (all_ids, [])
        
        # Calculate target counts - use more aggressive reduction for very large populations
        if agent_count >= VERY_LARGE_POP_THRESHOLD:
            # Very large population: only simulate 5%, with hard cap
            target_active = min(
                VERY_LARGE_MAX_ACTIVE,
                max(
                    MIN_FULL_SIMULATION_COUNT,
                    int(agent_count * VERY_LARGE_POP_SIMULATION_FRACTION)
                )
            )
        else:
            # Normal population: simulate 10%, with hard cap
            target_active = min(
                MAX_ACTIVE_SIMULATION_COUNT,
                max(
                    MIN_FULL_SIMULATION_COUNT,
                    int(agent_count * FULL_SIMULATION_FRACTION)
                )
            )
        
        # Score agents for priority
        scored_agents = self._score_agents(agents, turn)
        
        # Sort by priority (highest first)
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Assign to active tier
        active_ids = set()
        
        # First, include forced active agents
        if force_active_ids:
            for agent_id in force_active_ids:
                if agent_id in agents:
                    active_ids.add(agent_id)
        
        # Then fill remaining slots by priority
        for agent_id, score in scored_agents:
            if len(active_ids) >= target_active:
                break
            if agent_id not in active_ids:
                active_ids.add(agent_id)
        
        # Everyone else is inactive
        all_ids = set(agents.keys())
        inactive_ids = all_ids - active_ids
        
        # Update state
        self._state.active_ids = active_ids
        self._state.inactive_ids = inactive_ids
        
        # Update assignments
        for agent_id in active_ids:
            if agent_id not in self._state.assignments:
                self._state.assignments[agent_id] = TierAssignment(
                    agent_id=agent_id,
                    tier=AgentTier.ACTIVE
                )
            else:
                self._state.assignments[agent_id].tier = AgentTier.ACTIVE
            self._state.assignments[agent_id].last_full_update = turn
        
        for agent_id in inactive_ids:
            if agent_id not in self._state.assignments:
                self._state.assignments[agent_id] = TierAssignment(
                    agent_id=agent_id,
                    tier=AgentTier.INACTIVE
                )
            else:
                self._state.assignments[agent_id].tier = AgentTier.INACTIVE
        
        # Check for rotation
        if turn - self._state.last_rotation_turn >= self._state.rotation_interval:
            self._rotate_active_set(agents, turn)
        
        return (list(active_ids), list(inactive_ids))
    
    def _score_agents(
        self,
        agents: Dict[str, 'HumanAgent'],
        turn: int
    ) -> List[Tuple[str, float]]:
        """
        Score agents for active tier priority.
        
        Higher scores = more likely to be fully simulated.
        
        Scoring factors (preserves simulation fairness):
        - Time since last full update (longer = higher priority)
        - Agent activity level (more active = higher priority)
        - Random jitter (ensures fairness with fixed seed)
        
        OPTIMIZATION: For very large populations, use a simpler scoring
        method that samples agents instead of scoring all of them.
        """
        scores = []
        agent_count = len(agents)
        
        # OPTIMIZATION: For very large populations, use simplified scoring
        # Instead of scoring all agents, we prioritize based on simple criteria
        if agent_count > 3000:
            # First, add agents that haven't been updated recently
            never_updated = []
            recently_updated = []
            
            for agent_id, agent in agents.items():
                if agent_id in self._state.assignments:
                    turns_since = turn - self._state.assignments[agent_id].last_full_update
                    if turns_since >= 5:  # Haven't been updated in 5+ turns
                        # Simple score based on turns since update + random jitter
                        score = turns_since * 10.0 + self._rng.random() * 5.0
                        never_updated.append((agent_id, score))
                    else:
                        recently_updated.append((agent_id, agent))
                else:
                    # New agent - high priority
                    never_updated.append((agent_id, 100.0 + self._rng.random() * 5.0))
            
            # Sort never_updated by score and take enough for active slots
            never_updated.sort(key=lambda x: x[1], reverse=True)
            
            # If we don't have enough from never_updated, sample from recently_updated
            target_count = min(MAX_ACTIVE_SIMULATION_COUNT, agent_count)
            if len(never_updated) < target_count and recently_updated:
                # Sample from recently updated with random jitter
                sample_needed = target_count - len(never_updated)
                sample_size = min(sample_needed * 2, len(recently_updated))  # Oversample then pick top
                sampled = self._rng.sample(recently_updated, sample_size)
                for agent_id, agent in sampled:
                    score = self._rng.random() * 20.0  # Pure random for recently updated
                    never_updated.append((agent_id, score))
            
            return never_updated
        
        # Standard scoring for smaller populations
        for agent_id, agent in agents.items():
            score = 0.0
            
            # Time since last full update (most important for fairness)
            if agent_id in self._state.assignments:
                turns_since_update = turn - self._state.assignments[agent_id].last_full_update
                score += turns_since_update * 10.0  # Strong weight for fairness
            else:
                score += 100.0  # New agents get high priority
            
            # Activity level (higher needs = more important to simulate)
            if hasattr(agent, 'needs'):
                # Urgent needs increase priority
                hunger_urgency = max(0, agent.needs.hunger - 50) / 50.0
                rest_urgency = max(0, agent.needs.rest - 50) / 50.0
                score += (hunger_urgency + rest_urgency) * 5.0
            
            # Reproduction drive (important for population dynamics)
            if hasattr(agent, 'reproduction_drive'):
                score += agent.reproduction_drive * 3.0
            
            # Mood extremes (interesting agents)
            if hasattr(agent, 'mood'):
                mood_extreme = abs(agent.mood)
                score += mood_extreme * 2.0
            
            # Random jitter for fairness (deterministic with seed)
            score += self._rng.random() * 5.0
            
            scores.append((agent_id, score))
        
        return scores
    
    def _rotate_active_set(self, agents: Dict[str, 'HumanAgent'], turn: int) -> None:
        """
        Rotate a portion of active/inactive agents.
        
        This ensures all agents get simulated over time.
        """
        self._state.last_rotation_turn = turn
        
        # Swap 10% of active/inactive
        swap_count = max(1, len(self._state.active_ids) // 10)
        
        # Select agents to demote (lowest priority from active)
        active_list = list(self._state.active_ids)
        if len(active_list) > swap_count:
            # Use RNG for deterministic selection
            demote_candidates = self._rng.sample(active_list, swap_count)
        else:
            demote_candidates = []
        
        # Select agents to promote (highest priority from inactive)
        inactive_list = list(self._state.inactive_ids)
        if len(inactive_list) > swap_count:
            promote_candidates = self._rng.sample(inactive_list, swap_count)
        else:
            promote_candidates = inactive_list[:swap_count]
        
        # Swap
        for agent_id in demote_candidates:
            self._state.active_ids.discard(agent_id)
            self._state.inactive_ids.add(agent_id)
            if agent_id in self._state.assignments:
                self._state.assignments[agent_id].tier = AgentTier.INACTIVE
        
        for agent_id in promote_candidates:
            self._state.inactive_ids.discard(agent_id)
            self._state.active_ids.add(agent_id)
            if agent_id in self._state.assignments:
                self._state.assignments[agent_id].tier = AgentTier.ACTIVE
                self._state.assignments[agent_id].last_full_update = turn
    
    def should_update_inactive(self, agent_id: str, turn: int) -> bool:
        """Check if an inactive agent should get a statistical update this turn."""
        if agent_id not in self._state.assignments:
            return True
        
        assignment = self._state.assignments[agent_id]
        turns_since = turn - assignment.last_full_update
        return turns_since >= INACTIVE_AGENT_UPDATE_INTERVAL
    
    def get_tier(self, agent_id: str) -> AgentTier:
        """Get the tier for an agent."""
        if agent_id in self._state.assignments:
            return self._state.assignments[agent_id].tier
        return AgentTier.ACTIVE  # Default to active for unknown agents
    
    def is_active(self, agent_id: str) -> bool:
        """Check if agent is in active tier."""
        return agent_id in self._state.active_ids
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove agent from tier tracking (when agent dies)."""
        self._state.active_ids.discard(agent_id)
        self._state.inactive_ids.discard(agent_id)
        self._state.assignments.pop(agent_id, None)
    
    def add_agent(self, agent_id: str, turn: int) -> None:
        """Add new agent to tier tracking (when promoted from child pool)."""
        # New agents start in active tier for immediate simulation
        self._state.active_ids.add(agent_id)
        self._state.assignments[agent_id] = TierAssignment(
            agent_id=agent_id,
            tier=AgentTier.ACTIVE,
            last_full_update=turn,
            priority_score=100.0  # High priority for new agents
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get tier statistics."""
        return {
            "active_count": len(self._state.active_ids),
            "inactive_count": len(self._state.inactive_ids),
            "total_tracked": len(self._state.assignments)
        }
