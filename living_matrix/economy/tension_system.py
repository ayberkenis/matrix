"""Tension system functions."""

from typing import Dict, List
from living_matrix.constants.economy_constants import TENSION_NORMALIZATION_DIVISOR


def calculate_tension_from_scarcity(food_stock: float, scarcity_threshold: float = 20.0,
                                    tension_increase: float = 2.0) -> float:
    """
    Calculate tension change from food scarcity.
    
    Args:
        food_stock: Current food stock
        scarcity_threshold: Scarcity threshold
        tension_increase: Tension increase per turn when scarce
        
    Returns:
        Tension change (positive = increase, negative = decrease)
    """
    if food_stock < scarcity_threshold:
        return tension_increase
    else:
        return -1.0  # Natural decay


def calculate_tension_from_unemployment(jobs_available: int, unemployment_threshold: int = 2,
                                       tension_increase: float = 1.0) -> float:
    """
    Calculate tension change from unemployment.
    
    Args:
        jobs_available: Available jobs
        unemployment_threshold: Unemployment threshold
        tension_increase: Tension increase per turn when unemployed
        
    Returns:
        Tension change (positive = increase, 0 = no change)
    """
    if jobs_available < unemployment_threshold:
        return tension_increase
    return 0.0


def calculate_tension_from_events(events: List[str]) -> float:
    """
    Calculate tension change from events.
    
    Args:
        events: List of event descriptions
        
    Returns:
        Net tension change
    """
    tension_change = 0.0
    for event in events:
        event_lower = event.lower()
        if "conflict" in event_lower or "theft" in event_lower:
            tension_change += 3.0
        elif "help" in event_lower or "aid" in event_lower:
            tension_change -= 2.0
        elif "strike" in event_lower or "protest" in event_lower:
            tension_change += 5.0
    return tension_change


def apply_tension_decay(tension: float, decay_rate: float = 0.5, min_tension: float = 0.0) -> float:
    """
    Apply natural tension decay.
    
    Args:
        tension: Current tension
        decay_rate: Decay rate per turn
        min_tension: Minimum tension
        
    Returns:
        New tension after decay
    """
    return max(min_tension, tension - decay_rate)


def apply_tension_change(tension: float, tension_change: float, 
                        min_tension: float = 0.0, max_tension: float = 100.0) -> float:
    """
    Apply tension change with clamping.
    
    Args:
        tension: Current tension
        tension_change: Tension change (positive or negative)
        min_tension: Minimum tension
        max_tension: Maximum tension
        
    Returns:
        New tension
    """
    return max(min_tension, min(max_tension, tension + tension_change))


def apply_tension_reduction(tension: float, reduction: float, min_tension: float = 0.0) -> float:
    """
    Apply tension reduction (SYSTEM B: Children reduce tension).
    
    Args:
        tension: Current tension
        reduction: Tension reduction amount
        min_tension: Minimum tension
        
    Returns:
        New tension
    """
    return max(min_tension, tension - reduction)


def apply_death_panic_tension_reduction(tension: float, reduction_factor: float = 0.7,
                                        min_tension: float = 0.0) -> float:
    """
    Apply death panic mode tension reduction (SYSTEM C).
    
    Args:
        tension: Current tension
        reduction_factor: Reduction factor (0.0-1.0)
        min_tension: Minimum tension
        
    Returns:
        New tension
    """
    return max(min_tension, tension * reduction_factor)


def apply_trauma_tension_reduction(tension: float, generational_trauma: float,
                                  trauma_multiplier: float = 15.0, min_tension: float = 0.0) -> float:
    """
    Apply generational trauma tension reduction (SYSTEM D).
    
    Args:
        tension: Current tension
        generational_trauma: Generational trauma level (0.0-1.0)
        trauma_multiplier: Trauma reduction multiplier
        min_tension: Minimum tension
        
    Returns:
        New tension
    """
    trauma_reduction = generational_trauma * trauma_multiplier
    return max(min_tension, tension - trauma_reduction)


def normalize_tension(tension: float, divisor: float = TENSION_NORMALIZATION_DIVISOR) -> float:
    """
    Normalize tension to 0.0-1.0 range.
    
    Args:
        tension: Tension value (0-100)
        divisor: Normalization divisor
        
    Returns:
        Normalized tension (0.0-1.0)
    """
    return tension / divisor
