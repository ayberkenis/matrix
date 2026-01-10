"""Food system functions."""

import random
from typing import Dict
from living_matrix.constants.economy_constants import IDEAL_FOOD


def calculate_food_production(workers: int, production_rate: float, 
                              production_efficiency: float) -> int:
    """
    Calculate food production.
    
    Args:
        workers: Number of workers
        production_rate: Production rate multiplier
        production_efficiency: Production efficiency (0.0-1.0)
        
    Returns:
        Food produced
    """
    food_produced = int(workers * production_rate * production_efficiency * random.uniform(0.8, 1.2))
    return food_produced


def apply_food_production(food_stock: float, food_produced: int, max_food: float = 100.0) -> float:
    """
    Apply food production to food stock.
    
    Args:
        food_stock: Current food stock
        food_produced: Food produced this turn
        max_food: Maximum food stock
        
    Returns:
        New food stock
    """
    return min(max_food, food_stock + food_produced)


def calculate_food_consumption(agent_count: int, consumption_per_agent: float = 1.0) -> float:
    """
    Calculate food consumption.
    
    Args:
        agent_count: Number of agents
        consumption_per_agent: Food consumed per agent
        
    Returns:
        Food consumed
    """
    return agent_count * consumption_per_agent


def apply_food_consumption(food_stock: float, food_consumed: float, min_food: float = 0.0) -> float:
    """
    Apply food consumption to food stock.
    
    Args:
        food_stock: Current food stock
        food_consumed: Food consumed this turn
        min_food: Minimum food stock
        
    Returns:
        New food stock
    """
    return max(min_food, food_stock - food_consumed)


def calculate_production_efficiency(tension: float, max_tension: float = 200.0, 
                                    min_efficiency: float = 0.3) -> float:
    """
    Calculate production efficiency based on tension.
    
    Args:
        tension: Current tension
        max_tension: Maximum tension for calculation
        min_efficiency: Minimum efficiency
        
    Returns:
        Production efficiency (0.0-1.0)
    """
    return max(min_efficiency, 1.0 - tension / max_tension)


def apply_food_efficiency_bonus(food_stock: float, efficiency_bonus: float, 
                                max_food: float = 100.0) -> float:
    """
    Apply food efficiency bonus (SYSTEM B: Children create resources).
    
    Args:
        food_stock: Current food stock
        efficiency_bonus: Efficiency bonus multiplier
        max_food: Maximum food stock
        
    Returns:
        Adjusted food stock
    """
    return min(max_food, food_stock * (1.0 + efficiency_bonus))
