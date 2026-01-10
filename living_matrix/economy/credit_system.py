"""Credit system functions."""

import random
from typing import Dict
from living_matrix.constants.economy_constants import DEFAULT_CREDITS_POOL


def calculate_credits_production(jobs_available: int, production_rate: float,
                                production_efficiency: float, multiplier: float = 2.0) -> int:
    """
    Calculate credits production.
    
    Args:
        jobs_available: Available jobs
        production_rate: Production rate multiplier
        production_efficiency: Production efficiency (0.0-1.0)
        multiplier: Credits production multiplier
        
    Returns:
        Credits produced
    """
    if jobs_available <= 0:
        return 0
    credits_produced = int(jobs_available * production_rate * production_efficiency * multiplier)
    return credits_produced


def apply_credits_production(credits_pool: float, credits_produced: int, 
                            max_credits: float = 200.0) -> float:
    """
    Apply credits production to credits pool.
    
    Args:
        credits_pool: Current credits pool
        credits_produced: Credits produced this turn
        max_credits: Maximum credits pool
        
    Returns:
        New credits pool
    """
    return min(max_credits, credits_pool + credits_produced)


def regenerate_jobs(jobs_available: int, ideal_jobs: int, tension: float,
                   max_tension: float = 150.0, min_regen_rate: float = 0.1) -> int:
    """
    Regenerate jobs slowly (reduced by tension).
    
    Args:
        jobs_available: Current jobs available
        ideal_jobs: Ideal job count
        tension: Current tension
        max_tension: Maximum tension for calculation
        min_regen_rate: Minimum regeneration rate
        
    Returns:
        New jobs available
    """
    if jobs_available >= ideal_jobs:
        return jobs_available
    
    regen_rate = max(min_regen_rate, 1.0 - tension / max_tension)
    if random.random() < regen_rate:
        return min(ideal_jobs, jobs_available + 1)
    return jobs_available
