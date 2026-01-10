"""Economy utility functions."""

from typing import Dict
from living_matrix.constants.economy_constants import (
    DEFAULT_FOOD_STOCK, DEFAULT_CREDITS_POOL, DEFAULT_JOBS_AVAILABLE,
    DEFAULT_SECURITY_LEVEL, IDEAL_FOOD, IDEAL_JOBS
)


def calculate_food_pressure(food_stock: float, ideal_food: float) -> float:
    """
    Calculate food pressure (0.0-1.0).
    
    Args:
        food_stock: Current food stock
        ideal_food: Ideal food level
        
    Returns:
        Food pressure (0.0 = no pressure, 1.0 = maximum pressure)
    """
    if ideal_food <= 0:
        return 0.0
    food_ratio = food_stock / ideal_food
    return max(0.0, min(1.0, 1.0 - food_ratio))


def calculate_job_pressure(jobs_available: int, ideal_jobs: int, active_agents: int) -> float:
    """
    Calculate job pressure (0.0-1.0).
    
    Args:
        jobs_available: Available jobs
        ideal_jobs: Ideal job count
        active_agents: Active agents count
        
    Returns:
        Job pressure (0.0 = no pressure, 1.0 = maximum pressure)
    """
    if active_agents <= 0:
        return 0.0
    jobs_per_capita = jobs_available / active_agents
    ideal_jobs_per_capita = ideal_jobs / max(1, active_agents)
    if ideal_jobs_per_capita <= 0:
        return 0.0
    job_ratio = jobs_per_capita / ideal_jobs_per_capita
    return max(0.0, min(1.0, 1.0 - job_ratio))


def calculate_child_pressure(child_pool: int, active_agents: int) -> float:
    """
    Calculate child pool pressure (0.0-1.0).
    
    Args:
        child_pool: Child pool size
        active_agents: Active agents count
        
    Returns:
        Child pressure (0.0 = no pressure, 1.0 = maximum pressure)
    """
    if active_agents <= 0:
        return 0.0
    child_to_adult_ratio = child_pool / active_agents
    # >0.5 ratio = pressure
    return max(0.0, min(1.0, (child_to_adult_ratio - 0.5) / 2.0))


def calculate_population_pressure(food_pressure: float, job_pressure: float, 
                                  child_pressure: float) -> float:
    """
    Calculate combined population pressure (0.0-1.0).
    
    Args:
        food_pressure: Food pressure (0.0-1.0)
        job_pressure: Job pressure (0.0-1.0)
        child_pressure: Child pressure (0.0-1.0)
        
    Returns:
        Combined population pressure
    """
    return (food_pressure * 0.4 + job_pressure * 0.3 + child_pressure * 0.3)


def calculate_food_per_capita(food_stock: float, total_population: int) -> float:
    """
    Calculate food per capita.
    
    Args:
        food_stock: Food stock
        total_population: Total population
        
    Returns:
        Food per capita
    """
    return food_stock / max(1, total_population)


def calculate_jobs_per_capita(jobs_available: int, active_agents: int) -> float:
    """
    Calculate jobs per capita.
    
    Args:
        jobs_available: Jobs available
        active_agents: Active agents count
        
    Returns:
        Jobs per capita
    """
    return jobs_available / max(1, active_agents)


def get_default_district_resources() -> Dict:
    """
    Get default district resources dictionary.
    
    Returns:
        Dictionary with default resource values
    """
    return {
        "food_stock": DEFAULT_FOOD_STOCK,
        "credits_pool": DEFAULT_CREDITS_POOL,
        "jobs_available": DEFAULT_JOBS_AVAILABLE,
        "security_level": DEFAULT_SECURITY_LEVEL,
        "tension": 20,
        "scarcity": False
    }


def is_scarcity(food_pressure: float, threshold: float = 0.7) -> bool:
    """
    Check if district is experiencing scarcity.
    
    Args:
        food_pressure: Food pressure (0.0-1.0)
        threshold: Scarcity threshold
        
    Returns:
        True if experiencing scarcity
    """
    return food_pressure > threshold
