"""World state management functions."""

from typing import Dict, Optional
from living_matrix.constants.world_constants import (
    DEFAULT_SEED, DEFAULT_TURN, DEFAULT_WORLD_STATE,
    DEFAULT_STABILITY, DEFAULT_NOVELTY, DEFAULT_COHESION, DEFAULT_EXPRESSION,
    TRAUMA_TRACKING_TURNS
)


def initialize_world_state_dict(seed: int = DEFAULT_SEED, turn: int = DEFAULT_TURN) -> Dict:
    """
    Initialize world state dictionary with defaults.
    
    Args:
        seed: Random seed
        turn: Initial turn
        
    Returns:
        World state dictionary
    """
    return {
        "turn": turn,
        "seed": seed,
        "world_state": DEFAULT_WORLD_STATE,
        "population_pressure": 0.0,
        "extinction_risk": 0.0,
        "turns_since_last_birth": 0,
        "generational_trauma": 0.0,
        "deaths_last_50_turns": 0,
        "total_population": 0,
        "active_agents": 0,
        "total_child_pool": 0,
        "civilization_phase": "survival"
    }


def update_world_state_metrics(world_state, active_agents: int, total_child_pool: int,
                               total_population: int):
    """
    Update world state population metrics.
    
    Args:
        world_state: World state object
        active_agents: Active agents count
        total_child_pool: Total child pool size
        total_population: Total population
    """
    world_state.active_agents = active_agents
    world_state.total_child_pool = total_child_pool
    world_state.total_population = total_population


def update_generational_trauma(world_state, recent_deaths: int, turn: int,
                               trauma_increase_per_death: float = 0.02,
                               trauma_decay_rate: float = 0.99):
    """
    Update generational trauma (SYSTEM D).
    
    Args:
        world_state: World state object
        recent_deaths: Deaths in last N turns
        turn: Current turn
        trauma_increase_per_death: Trauma increase per death
        trauma_decay_rate: Trauma decay rate per turn
    """
    world_state.deaths_last_50_turns = recent_deaths
    trauma_increase = recent_deaths * trauma_increase_per_death
    world_state.generational_trauma = min(1.0, 
        world_state.generational_trauma * trauma_decay_rate + trauma_increase)


def calculate_extinction_risk(alive_count: int, turns_since_last_birth: int,
                              critical_threshold: int = 10,
                              birth_threshold: int = 50) -> float:
    """
    Calculate extinction risk (SYSTEM 11).
    
    Args:
        alive_count: Current alive agent count
        turns_since_last_birth: Turns since last birth
        critical_threshold: Critical population threshold
        birth_threshold: Birth threshold for risk calculation
        
    Returns:
        Extinction risk (0.0-1.0)
    """
    if alive_count < critical_threshold:
        return 1.0 - (alive_count / critical_threshold)
    elif turns_since_last_birth > birth_threshold:
        return min(0.9, turns_since_last_birth / 100.0)
    return 0.0


def calculate_population_pressure(alive_count: int, safe_threshold: int = 30) -> float:
    """
    Calculate global population pressure (SYSTEM 11).
    
    Args:
        alive_count: Current alive agent count
        safe_threshold: Safe population threshold
        
    Returns:
        Population pressure (0.0-1.0)
    """
    return max(0.0, min(1.0, 1.0 - (alive_count / safe_threshold)))
