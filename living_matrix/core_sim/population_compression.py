"""Population Compression - Statistical Agent Representation.

This module implements a compression system that replaces excess agents
with statistical cohorts when population exceeds thresholds. This allows
the simulation to scale to 10,000+ effective population without O(n)
processing overhead.

ARCHITECTURE:

1. **Active Agents**: Full simulation with decisions, actions, relationships
2. **Statistical Cohorts**: Aggregated groups per district with:
   - Age distribution
   - Average mood/needs
   - Reproduction rate
   - Death rate
   - Economic contribution

Cohorts:
- Participate statistically in economy (production, consumption)
- Influence district tension
- Generate births/deaths probabilistically
- DO NOT run decision loops

Promotion/Demotion:
- When active count drops, promote from cohort
- When active count exceeds cap, demote to cohort
- Promotion reconstructs plausible agent state from cohort distribution

BEHAVIOR PRESERVATION:
- Same population dynamics (birth/death rates)
- Same economic contribution
- Same tension effects
- Only granularity of individual behavior is reduced
"""

import random
import logging
import math
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Set
from dataclasses import dataclass, field
from collections import defaultdict

from ..constants.performance_constants import (
    MAX_ACTIVE_AGENTS,
    COMPRESSION_THRESHOLD,
    MIN_ACTIVE_AGENTS,
)

if TYPE_CHECKING:
    from ..human_agent import HumanAgent, HumanAgentSystem

logger = logging.getLogger(__name__)


@dataclass
class CohortStats:
    """Statistical representation of a compressed population segment."""
    district_id: str
    count: int = 0
    
    # Demographics
    avg_age: float = 200.0  # Average age in ticks
    age_std: float = 100.0  # Standard deviation
    male_fraction: float = 0.5
    
    # Needs and mood
    avg_hunger: float = 0.3
    avg_energy: float = 0.6
    avg_mood: float = 0.5
    avg_health: float = 0.8
    
    # Reproduction
    reproductive_fraction: float = 0.3  # Fraction in reproductive age
    avg_reproduction_drive: float = 0.5
    
    # Economic
    avg_wealth: float = 50.0
    employment_rate: float = 0.7
    productivity: float = 1.0
    
    # Birth/death rates (per 100 population per turn)
    birth_rate: float = 0.1
    death_rate: float = 0.05
    
    # Tension contribution
    tension_contribution: float = 0.0
    
    def get_economic_contribution(self) -> float:
        """Calculate total economic contribution of cohort."""
        employed = int(self.count * self.employment_rate)
        return employed * self.productivity
    
    def get_food_consumption(self) -> float:
        """Calculate food consumption per turn."""
        return self.count * (0.5 + self.avg_hunger * 0.5)
    
    def get_tension_contribution(self) -> float:
        """Calculate tension contribution from cohort."""
        # Tension from unmet needs
        hunger_tension = self.avg_hunger * 0.3
        # Tension from low mood
        mood_tension = (1.0 - self.avg_mood) * 0.2
        # Tension from unemployment
        unemployment_tension = (1.0 - self.employment_rate) * 0.3
        
        return self.count * (hunger_tension + mood_tension + unemployment_tension) * 0.01
    
    def advance(self, turn: int, resources: Dict) -> Tuple[int, int]:
        """
        Advance cohort by one turn.
        
        Returns (births, deaths).
        """
        births = 0
        deaths = 0
        
        if self.count <= 0:
            return 0, 0
        
        # Adjust rates based on resources
        food_abundance = resources.get('food_stock', 50) / 100.0
        
        # Death rate increases with low food
        effective_death_rate = self.death_rate * (1.0 + (1.0 - food_abundance) * 0.5)
        
        # Birth rate decreases with low food
        effective_birth_rate = self.birth_rate * food_abundance
        
        # Calculate births and deaths (stochastic)
        expected_deaths = self.count * effective_death_rate / 100.0
        expected_births = self.count * self.reproductive_fraction * effective_birth_rate / 100.0
        
        # Poisson-distributed events
        deaths = self._poisson(expected_deaths)
        births = self._poisson(expected_births)
        
        # Age the cohort
        self.avg_age += 1
        
        # Needs decay
        self.avg_hunger = min(1.0, self.avg_hunger + 0.01)
        self.avg_energy = max(0.0, self.avg_energy - 0.005)
        
        # Resource-based recovery
        if food_abundance > 0.5:
            self.avg_hunger = max(0.0, self.avg_hunger - food_abundance * 0.02)
            self.avg_mood = min(1.0, self.avg_mood + 0.01)
        else:
            self.avg_mood = max(0.0, self.avg_mood - 0.02)
        
        # Update count
        self.count = max(0, self.count - deaths)
        
        return births, deaths
    
    @staticmethod
    def _poisson(expected: float) -> int:
        """Generate Poisson-distributed random number."""
        if expected <= 0:
            return 0
        if expected > 100:
            # Use normal approximation for large expected values
            return max(0, int(random.gauss(expected, math.sqrt(expected))))
        # Standard Poisson for small values
        L = math.exp(-expected)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1


@dataclass
class CompressionStats:
    """Statistics for compression operations."""
    total_compressed: int = 0
    total_promoted: int = 0
    compression_events: int = 0
    promotion_events: int = 0


class PopulationCompressor:
    """
    Manages population compression and promotion.
    
    Usage:
        compressor = PopulationCompressor()
        
        # Check if compression needed
        if compressor.should_compress(agent_system):
            compressor.compress_excess(agent_system, turn)
        
        # Check if promotion needed
        if compressor.should_promote(agent_system):
            compressor.promote_from_cohorts(agent_system, turn, world_map)
        
        # Advance cohorts each turn
        events = compressor.advance_cohorts(turn, district_resources)
    """
    
    def __init__(
        self,
        max_active: int = MAX_ACTIVE_AGENTS,
        compression_threshold: int = COMPRESSION_THRESHOLD,
        min_active: int = MIN_ACTIVE_AGENTS
    ):
        self.max_active = max_active
        self.compression_threshold = compression_threshold
        self.min_active = min_active
        
        # Cohorts by district
        self.cohorts: Dict[str, CohortStats] = {}
        
        # Statistics
        self.stats = CompressionStats()
        
        # Tracking for promotion
        self._promotion_needed: Dict[str, int] = {}
    
    def get_or_create_cohort(self, district_id: str) -> CohortStats:
        """Get or create cohort for a district."""
        if district_id not in self.cohorts:
            self.cohorts[district_id] = CohortStats(district_id=district_id)
        return self.cohorts[district_id]
    
    def should_compress(self, agent_system: 'HumanAgentSystem') -> bool:
        """Check if compression is needed."""
        active_count = len([a for a in agent_system.agents.values() if a.is_alive])
        return active_count > self.compression_threshold
    
    def should_promote(self, agent_system: 'HumanAgentSystem') -> bool:
        """Check if promotion from cohorts is needed."""
        active_count = len([a for a in agent_system.agents.values() if a.is_alive])
        total_cohort = sum(c.count for c in self.cohorts.values())
        
        # Promote if active count is low and cohorts have population
        return active_count < self.min_active and total_cohort > 0
    
    def compress_excess(
        self,
        agent_system: 'HumanAgentSystem',
        turn: int
    ) -> int:
        """
        Compress excess agents into cohorts.
        
        Selects least-active agents for compression.
        Returns number of agents compressed.
        """
        active_agents = [a for a in agent_system.agents.values() if a.is_alive]
        excess = len(active_agents) - self.max_active
        
        if excess <= 0:
            return 0
        
        # Score agents for compression (lower = more compressible)
        scored_agents: List[Tuple[float, 'HumanAgent']] = []
        
        for agent in active_agents:
            score = self._calculate_importance_score(agent)
            scored_agents.append((score, agent))
        
        # Sort by score (most compressible first)
        scored_agents.sort(key=lambda x: x[0])
        
        # Compress the least important agents
        compressed = 0
        for score, agent in scored_agents[:excess]:
            if self._compress_agent(agent, agent_system, turn):
                compressed += 1
        
        self.stats.total_compressed += compressed
        self.stats.compression_events += 1
        
        logger.info(f"Compressed {compressed} agents at turn {turn}")
        
        return compressed
    
    def _calculate_importance_score(self, agent: 'HumanAgent') -> float:
        """
        Calculate importance score for an agent.
        
        Higher score = more important = less likely to compress.
        """
        score = 0.0
        
        # Relationships make agent important
        score += len(agent.relationships) * 0.1
        
        # Active goals make agent important
        if agent.current_goal and agent.current_goal != 'idle':
            score += 1.0
        
        # Low needs make agent more stable (can compress)
        needs_stability = 1.0 - (agent.hunger + (1.0 - agent.energy)) / 2.0
        score -= needs_stability * 0.5
        
        # Parents with living children are important
        if hasattr(agent, 'children_ids') and agent.children_ids:
            score += len(agent.children_ids) * 0.2
        
        # Recent activity
        if agent.current_action not in ('idle', 'rest', 'sleep', None):
            score += 0.5
        
        return score
    
    def _compress_agent(
        self,
        agent: 'HumanAgent',
        agent_system: 'HumanAgentSystem',
        turn: int
    ) -> bool:
        """
        Compress a single agent into its district cohort.
        """
        district_id = agent.district
        if not district_id:
            district_id = 'unknown'
        
        cohort = self.get_or_create_cohort(district_id)
        
        # Add agent's stats to cohort (weighted average)
        old_count = cohort.count
        new_count = old_count + 1
        
        if old_count > 0:
            # Update running averages
            cohort.avg_age = (cohort.avg_age * old_count + agent.age) / new_count
            cohort.avg_hunger = (cohort.avg_hunger * old_count + agent.hunger) / new_count
            cohort.avg_energy = (cohort.avg_energy * old_count + agent.energy) / new_count
            cohort.avg_mood = (cohort.avg_mood * old_count + agent.mood) / new_count
            cohort.avg_health = (cohort.avg_health * old_count + agent.health) / new_count
            cohort.avg_wealth = (cohort.avg_wealth * old_count + agent.credits) / new_count
            
            # Update male fraction
            is_male = agent.gender == 'male' if hasattr(agent, 'gender') else random.random() < 0.5
            male_count = cohort.male_fraction * old_count + (1 if is_male else 0)
            cohort.male_fraction = male_count / new_count
            
            # Update reproductive fraction
            is_reproductive = 180 <= agent.age <= 500
            repro_count = cohort.reproductive_fraction * old_count + (1 if is_reproductive else 0)
            cohort.reproductive_fraction = repro_count / new_count
        else:
            # First agent in cohort
            cohort.avg_age = agent.age
            cohort.avg_hunger = agent.hunger
            cohort.avg_energy = agent.energy
            cohort.avg_mood = agent.mood
            cohort.avg_health = agent.health
            cohort.avg_wealth = agent.credits
            cohort.male_fraction = 0.5
            cohort.reproductive_fraction = 0.3
        
        cohort.count = new_count
        
        # Mark agent for removal (but don't kill - compress)
        agent.is_alive = False
        agent._compressed = True
        agent._compressed_turn = turn
        
        # Move to dead_agents (for tracking, not true death)
        agent_system.dead_agents[agent.id] = agent
        del agent_system.agents[agent.id]
        
        return True
    
    def promote_from_cohorts(
        self,
        agent_system: 'HumanAgentSystem',
        turn: int,
        world_map,
        count: int = 10
    ) -> int:
        """
        Promote agents from cohorts back to active simulation.
        
        Reconstructs plausible agent state from cohort distribution.
        """
        promoted = 0
        
        for district_id, cohort in self.cohorts.items():
            if cohort.count <= 0:
                continue
            
            # Calculate how many to promote from this district
            district_fraction = cohort.count / max(1, sum(c.count for c in self.cohorts.values()))
            to_promote = max(1, int(count * district_fraction))
            to_promote = min(to_promote, cohort.count)
            
            for _ in range(to_promote):
                if self._promote_agent(cohort, district_id, agent_system, turn, world_map):
                    promoted += 1
        
        self.stats.total_promoted += promoted
        self.stats.promotion_events += 1
        
        if promoted > 0:
            logger.info(f"Promoted {promoted} agents from cohorts at turn {turn}")
        
        return promoted
    
    def _promote_agent(
        self,
        cohort: CohortStats,
        district_id: str,
        agent_system: 'HumanAgentSystem',
        turn: int,
        world_map
    ) -> bool:
        """
        Create a new agent from cohort statistics.
        """
        if cohort.count <= 0:
            return False
        
        # Get location in district
        location = None
        if world_map and district_id in world_map.regions:
            region = world_map.regions[district_id]
            if region.locations:
                location = random.choice(region.locations).id
        
        if not location:
            location = f"{district_id}_0"
        
        # Generate agent with cohort-based stats
        age = max(0, int(random.gauss(cohort.avg_age, cohort.age_std)))
        gender = 'male' if random.random() < cohort.male_fraction else 'female'
        
        # Create new agent
        from ..human_agent import HumanAgent
        
        agent = HumanAgent(
            location=location,
            district=district_id,
            age=age,
            gender=gender
        )
        
        # Set needs from cohort averages (with noise)
        agent.hunger = max(0, min(1, cohort.avg_hunger + random.gauss(0, 0.1)))
        agent.energy = max(0, min(1, cohort.avg_energy + random.gauss(0, 0.1)))
        agent.mood = max(0, min(1, cohort.avg_mood + random.gauss(0, 0.1)))
        agent.health = max(0, min(1, cohort.avg_health + random.gauss(0, 0.1)))
        agent.credits = max(0, cohort.avg_wealth + random.gauss(0, 10))
        
        # Add to agent system
        agent_system.agents[agent.id] = agent
        
        # Decrement cohort count
        cohort.count -= 1
        
        return True
    
    def advance_cohorts(
        self,
        turn: int,
        district_resources: Dict[str, Dict]
    ) -> Tuple[int, int]:
        """
        Advance all cohorts by one turn.
        
        Returns (total_births, total_deaths).
        """
        total_births = 0
        total_deaths = 0
        
        for district_id, cohort in self.cohorts.items():
            if cohort.count <= 0:
                continue
            
            resources = district_resources.get(district_id, {'food_stock': 50})
            births, deaths = cohort.advance(turn, resources)
            
            total_births += births
            total_deaths += deaths
            
            # Track births for child pool
            if births > 0:
                self._promotion_needed[district_id] = (
                    self._promotion_needed.get(district_id, 0) + births
                )
        
        return total_births, total_deaths
    
    def get_total_compressed_population(self) -> int:
        """Get total population in cohorts."""
        return sum(c.count for c in self.cohorts.values())
    
    def get_cohort_summary(self) -> Dict:
        """Get summary of all cohorts."""
        return {
            district_id: {
                'count': cohort.count,
                'avg_age': cohort.avg_age,
                'avg_mood': cohort.avg_mood,
                'birth_rate': cohort.birth_rate,
                'death_rate': cohort.death_rate,
                'economic_contribution': cohort.get_economic_contribution(),
                'tension_contribution': cohort.get_tension_contribution(),
            }
            for district_id, cohort in self.cohorts.items()
            if cohort.count > 0
        }
    
    def get_statistics(self) -> Dict:
        """Get compression statistics."""
        return {
            'total_compressed': self.stats.total_compressed,
            'total_promoted': self.stats.total_promoted,
            'compression_events': self.stats.compression_events,
            'promotion_events': self.stats.promotion_events,
            'current_cohort_population': self.get_total_compressed_population(),
            'cohorts': self.get_cohort_summary(),
        }


# Global instance
_compressor: Optional[PopulationCompressor] = None


def get_population_compressor() -> PopulationCompressor:
    """Get or create the global population compressor."""
    global _compressor
    if _compressor is None:
        _compressor = PopulationCompressor()
    return _compressor


def reset_population_compressor():
    """Reset the global compressor (for testing)."""
    global _compressor
    _compressor = None
