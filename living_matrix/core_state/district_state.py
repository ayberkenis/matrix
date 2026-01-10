"""District state management functions."""

from typing import Dict, Optional
from living_matrix.constants.economy_constants import (
    DEFAULT_FOOD_STOCK, DEFAULT_CREDITS_POOL, DEFAULT_JOBS_AVAILABLE,
    DEFAULT_SECURITY_LEVEL
)


def initialize_district_resources_dict() -> Dict:
    """
    Initialize district resources dictionary with defaults.
    
    Returns:
        District resources dictionary
    """
    return {
        "food_stock": DEFAULT_FOOD_STOCK,
        "credits_pool": DEFAULT_CREDITS_POOL,
        "jobs_available": DEFAULT_JOBS_AVAILABLE,
        "security_level": DEFAULT_SECURITY_LEVEL,
        "tension": 20,
        "scarcity": False
    }


def update_district_population_metrics(district, child_pool: int, active_agents: int,
                                       total_population: int):
    """
    Update district population metrics (POPULATION COMPRESSION).
    
    Args:
        district: District object
        child_pool: Child pool size
        active_agents: Active agents count
        total_population: Total population
    """
    district.child_pool = child_pool
    district.active_agents = active_agents
    district.total_population = total_population


def create_district_resources_from_advanced(district, food_efficiency_bonus: float = 0.0,
                                           tension_reduction: float = 0.0) -> Dict:
    """
    Create district resources dictionary from advanced district.
    
    Args:
        district: Advanced district object
        food_efficiency_bonus: Food efficiency bonus (SYSTEM B)
        tension_reduction: Tension reduction (SYSTEM B)
        
    Returns:
        District resources dictionary
    """
    return {
        "food_stock": district.food_stock * (1.0 + food_efficiency_bonus),  # SYSTEM B: Children create resources
        "credits_pool": district.credits_pool,
        "jobs_available": district.jobs_available,
        "security_level": district.security_level,
        "tension": max(0, district.tension_state.tension - tension_reduction),  # SYSTEM B: Lower tension
        "scarcity": district.pressure.food > 0.7  # Derived from pressure
    }


def apply_death_panic_mode_to_district(district, district_resources: Dict,
                                       tension_reduction_factor: float = 0.7,
                                       food_boost_factor: float = 1.2,
                                       tension_reduction_amount: float = 20.0,
                                       food_boost_amount: float = 1.15):
    """
    Apply death panic mode effects to district (SYSTEM C).
    
    Args:
        district: District object
        district_resources: District resources dictionary
        tension_reduction_factor: Tension reduction factor
        food_boost_factor: Food boost factor
        tension_reduction_amount: Additional tension reduction
        food_boost_amount: Additional food boost
    """
    # Auto-resolve conflicts (reduce tension aggressively)
    district.tension_state.tension = max(0, district.tension_state.tension * tension_reduction_factor)
    # Share food automatically (increase food stock)
    district.food_stock = min(100, district.food_stock * food_boost_factor)
    # Force migration toward fertile zones (handled in agent movement)
    district_resources["tension"] = max(0, district_resources["tension"] - tension_reduction_amount)
    district_resources["food_stock"] = min(100, district_resources["food_stock"] * food_boost_amount)


def apply_trauma_effects_to_district(district_resources: Dict, generational_trauma: float,
                                    trauma_threshold: float = 0.3,
                                    trauma_reduction_multiplier: float = 15.0,
                                    birth_pressure_multiplier: float = 0.2) -> float:
    """
    Apply generational trauma effects to district (SYSTEM D).
    
    Args:
        district_resources: District resources dictionary
        generational_trauma: Generational trauma level (0.0-1.0)
        trauma_threshold: Trauma threshold for effects
        trauma_reduction_multiplier: Trauma reduction multiplier
        birth_pressure_multiplier: Birth pressure multiplier
        
    Returns:
        Birth pressure from trauma
    """
    birth_pressure = 0.0
    if generational_trauma > trauma_threshold:
        # Trauma reduces conflict, increases cooperation
        trauma_reduction = generational_trauma * trauma_reduction_multiplier
        district_resources["tension"] = max(0, district_resources["tension"] - trauma_reduction)
        # Increase reproduction urgency
        birth_pressure += generational_trauma * birth_pressure_multiplier
    return birth_pressure
