"""Guard functions for safety checks."""

from typing import List, Any


def ensure_minimum_population(alive_count: int, min_survivors: int) -> bool:
    """
    Check if population is at minimum viable level.
    
    Returns:
        True if at minimum (should skip deaths), False otherwise
    """
    return alive_count <= min_survivors


def calculate_max_deaths_allowed(alive_count: int, max_death_rate: float) -> int:
    """
    Calculate maximum deaths allowed based on death rate limit.
    
    Args:
        alive_count: Current number of alive agents
        max_death_rate: Maximum death rate (0.0 to 1.0)
        
    Returns:
        Maximum number of deaths allowed
    """
    if alive_count <= 0:
        return 0
    return int(alive_count * max_death_rate)


def clamp_death_count(deaths_count: int, max_deaths_allowed: int) -> bool:
    """
    Check if death count exceeds maximum allowed.
    
    Returns:
        True if deaths should be stopped, False otherwise
    """
    return deaths_count >= max_deaths_allowed


def check_extinction_risk(alive_count: int, child_pool: int) -> bool:
    """
    Check if population is at extinction risk (both zero).
    
    Returns:
        True if both alive_count and child_pool are zero
    """
    return alive_count == 0 and child_pool == 0
