"""
State Snapshot Pipeline for Gemini Visual Intelligence.

This module provides a lightweight, read-only state snapshot system
that captures aggregated simulation data for image generation.

The snapshot is:
- Cheap and allocation-light (no deep per-agent dumps)
- Pure function (receives state, returns JSON-serializable dict)
- Called once per hour (simulation time)
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import hashlib
import json


@dataclass
class StateSnapshot:
    """
    Aggregated state snapshot for Gemini image generation.
    
    Contains ONLY summarized/aggregated data, not per-agent details.
    This is the input to the Gemini prompt builder.
    """
    # Population metrics
    global_population: int
    active_agents: int
    compressed_population: int  # child_pool (compressed)
    
    # Average needs (0-1 scale normalized)
    average_hunger: float
    average_tension: float
    average_rest: float
    average_safety: float
    
    # Economy
    food_stock: float
    credits_pool: float
    jobs_available: int
    
    # Rates (per day approximation)
    conflict_rate: float  # Fraction of agents in conflict
    birth_rate: float
    death_rate: float
    
    # Dominant districts (top N by tension/population)
    dominant_districts: List[Dict[str, Any]]
    
    # Time
    simulation_day: int
    simulation_hour: int
    simulation_turn: int
    
    # Notable flags
    crisis_active: bool
    famine_risk: bool
    unrest_level: str  # "low", "medium", "high", "critical"
    collapse_risk: bool
    
    # World state
    world_state: str  # "alive", "dead_world"
    civilization_phase: str  # "survival", "growth", "stable", "strain", "decline"
    
    # Weather summary
    weather_condition: str
    
    # Multi-dimensional tension (aggregated)
    tension_economic: float
    tension_social: float
    tension_political: float
    tension_existential: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)
    
    def compute_hash(self) -> str:
        """
        Compute a deterministic hash of the snapshot.
        Used for caching and identifying unique states.
        """
        # Create a deterministic JSON string
        data = self.to_dict()
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def create_state_snapshot(
    simulation,
    state_store=None
) -> Optional[StateSnapshot]:
    """
    Create a lightweight state snapshot from simulation state.
    
    This is a PURE FUNCTION that only reads from simulation state.
    It does NOT modify any simulation data.
    
    Args:
        simulation: The Simulation instance
        state_store: Optional MatrixStateStore for additional data
    
    Returns:
        StateSnapshot or None if simulation not initialized
    """
    # Early exit if simulation not ready
    if not simulation or not simulation.world or not simulation.world.state:
        return None
    
    world_state = simulation.world.state
    
    # Get time info
    sim_day = 0
    sim_hour = 0
    if simulation.time_system:
        sim_day = simulation.time_system.day_index
        # Calculate hour from turn (assuming 24 ticks per day)
        if hasattr(simulation.time_system, 'hour'):
            sim_hour = simulation.time_system.hour
        else:
            sim_hour = world_state.turn % 24
    
    # Get population metrics
    global_pop = getattr(world_state, 'total_population', 0)
    active_agents = getattr(world_state, 'active_agents', 0)
    compressed_pop = getattr(world_state, 'total_child_pool', 0)
    
    # Get agent-level averages (lightweight - don't iterate deeply)
    avg_hunger = 0.0
    avg_rest = 0.0
    avg_safety = 0.0
    conflict_rate = 0.0
    
    if simulation.human_agent_system and simulation.human_agent_system.agents:
        agents = list(simulation.human_agent_system.agents.values())
        alive_agents = [a for a in agents if getattr(a, 'is_alive', True)]
        
        if alive_agents:
            active_agents = len(alive_agents)
            
            # Sample averages (don't iterate all agents if too many)
            sample_size = min(50, len(alive_agents))
            sample = alive_agents[:sample_size]
            
            total_hunger = sum(a.needs.hunger for a in sample if hasattr(a, 'needs'))
            total_rest = sum(a.needs.rest for a in sample if hasattr(a, 'needs'))
            total_safety = sum(a.needs.safety for a in sample if hasattr(a, 'needs'))
            
            avg_hunger = total_hunger / sample_size if sample_size > 0 else 0.0
            avg_rest = total_rest / sample_size if sample_size > 0 else 0.0
            avg_safety = total_safety / sample_size if sample_size > 0 else 0.0
            
            # Conflict rate: count agents with current_action containing "conflict"
            conflict_count = sum(
                1 for a in sample 
                if hasattr(a, 'current_action') and a.current_action and 'conflict' in str(a.current_action).lower()
            )
            conflict_rate = conflict_count / sample_size if sample_size > 0 else 0.0
    
    # Get global population if not set
    if global_pop == 0 and simulation.human_agent_system:
        child_pool_total = sum(simulation.human_agent_system.child_pools.values()) if hasattr(simulation.human_agent_system, 'child_pools') else 0
        global_pop = active_agents + child_pool_total
        compressed_pop = child_pool_total
    
    # Get economy/district aggregates
    total_food = 0.0
    total_credits = 0.0
    total_jobs = 0
    avg_tension = 0.0
    tension_economic = 0.0
    tension_social = 0.0
    tension_political = 0.0
    tension_existential = 0.0
    dominant_districts = []
    
    if simulation.world_dynamics_system:
        districts = simulation.world_dynamics_system.get_all_districts()
        
        if districts:
            total_food = sum(d.food_stock for d in districts)
            total_credits = sum(d.credits_pool for d in districts)
            total_jobs = sum(d.jobs_available for d in districts)
            avg_tension = sum(d.tension_state.tension for d in districts) / len(districts)
            
            # Multi-dimensional tension aggregates
            tension_economic = sum(d.tension_state.multi_tension.economic for d in districts) / len(districts)
            tension_social = sum(d.tension_state.multi_tension.social for d in districts) / len(districts)
            tension_political = sum(d.tension_state.multi_tension.political for d in districts) / len(districts)
            tension_existential = sum(d.tension_state.multi_tension.existential for d in districts) / len(districts)
            
            # Top 3 districts by tension
            sorted_districts = sorted(districts, key=lambda d: d.tension_state.tension, reverse=True)
            dominant_districts = [
                {
                    "name": d.district_name,
                    "tension": round(d.tension_state.tension, 1),
                    "population": getattr(d, 'total_population', 0)
                }
                for d in sorted_districts[:3]
            ]
    elif simulation.economy_system:
        # Fallback to old economy system
        districts = simulation.economy_system.get_all_districts()
        if districts:
            total_food = sum(d.food_stock for d in districts)
            total_credits = sum(d.credits_pool for d in districts)
            avg_tension = sum(d.tension for d in districts) / len(districts)
            
            # Use single tension for all dimensions
            tension_economic = avg_tension
            tension_social = avg_tension
            tension_political = avg_tension * 0.75
            tension_existential = avg_tension * 0.5
    
    # Birth/death rates (from recent history if available)
    birth_rate = 0.0
    death_rate = 0.0
    if simulation.human_agent_system:
        # Approximate rates based on population pressure
        pop_pressure = getattr(world_state, 'population_pressure', 0.0)
        extinction_risk = getattr(world_state, 'extinction_risk', 0.0)
        birth_rate = min(1.0, pop_pressure * 0.5)  # Normalized
        death_rate = min(1.0, extinction_risk * 0.5)  # Normalized
    
    # Determine crisis flags
    crisis_active = avg_tension > 70
    famine_risk = total_food < (active_agents * 0.5) if active_agents > 0 else False
    collapse_risk = getattr(world_state, 'extinction_risk', 0.0) > 0.5
    
    # Unrest level
    if avg_tension >= 85:
        unrest_level = "critical"
    elif avg_tension >= 70:
        unrest_level = "high"
    elif avg_tension >= 50:
        unrest_level = "medium"
    else:
        unrest_level = "low"
    
    # Weather
    weather_condition = "unknown"
    if simulation.weather_system:
        weather_condition = simulation.weather_system.format_weather_line()
    
    # World state and civilization phase
    world_state_str = getattr(world_state, 'world_state', "alive")
    civ_phase = getattr(world_state, 'civilization_phase', "survival")
    
    return StateSnapshot(
        global_population=global_pop,
        active_agents=active_agents,
        compressed_population=compressed_pop,
        average_hunger=round(avg_hunger, 3),
        average_tension=round(avg_tension, 1),
        average_rest=round(avg_rest, 3),
        average_safety=round(avg_safety, 3),
        food_stock=round(total_food, 1),
        credits_pool=round(total_credits, 1),
        jobs_available=total_jobs,
        conflict_rate=round(conflict_rate, 3),
        birth_rate=round(birth_rate, 3),
        death_rate=round(death_rate, 3),
        dominant_districts=dominant_districts,
        simulation_day=sim_day,
        simulation_hour=sim_hour,
        simulation_turn=world_state.turn,
        crisis_active=crisis_active,
        famine_risk=famine_risk,
        unrest_level=unrest_level,
        collapse_risk=collapse_risk,
        world_state=world_state_str,
        civilization_phase=civ_phase,
        weather_condition=weather_condition,
        tension_economic=round(tension_economic, 1),
        tension_social=round(tension_social, 1),
        tension_political=round(tension_political, 1),
        tension_existential=round(tension_existential, 1),
    )
