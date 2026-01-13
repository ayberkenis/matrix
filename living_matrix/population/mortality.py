"""Mortality and aging functions.

HOT PATH - These functions are called for every agent every tick.
Optimized for minimal overhead.
"""

import random
from typing import TYPE_CHECKING, Optional, Dict, Tuple

if TYPE_CHECKING:
    from living_matrix.human_agent import HumanAgent

# PERF CRITICAL: Cache random function references
_random = random.random


def age_agent(agent: 'HumanAgent', turn: int, dead_agents: dict, agents: dict, 
               population_floor_active: bool = False, 
               district_resources: Optional[Dict] = None,
               weather_state: Optional[Dict] = None,
               population_count: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Age an agent and check for death from various causes.
    
    SYSTEM E: Population floor - suspend non-age deaths when population <= 2
    
    HOT PATH - CALLED PER AGENT PER TICK
    
    Args:
        agent: Agent to age
        turn: Current turn
        dead_agents: Dictionary of dead agents
        agents: Dictionary of active agents
        population_floor_active: Whether population floor is active
        district_resources: Optional district resources dict
        weather_state: Optional weather state dict
        
    Returns:
        Tuple of (True if agent died, death_cause string or None)
    """
    if not agent.is_alive:
        return (False, None)
    
    # PERF CRITICAL: Hoist frequently accessed attributes
    _needs = agent.needs
    _inventory = agent.inventory
    agent_id = agent.id
    
    # Slow down aging: age by 0.5 turns per simulation turn
    agent.age += 0.5
    
    # Update survival drives based on age (SYSTEM 10)
    age_int = int(agent.age)
    if age_int < 100:  # Very young
        agent.reproduction_drive = min(0.9, agent.reproduction_drive + 0.02)
    elif 100 <= age_int <= 1000:  # Prime reproductive years
        agent.reproduction_drive = min(0.95, agent.reproduction_drive + 0.01)
    elif age_int > 1000:  # Elderly
        agent.reproduction_drive = max(0.3, agent.reproduction_drive - 0.01)
    
    # Legacy drive increases with age and losses
    agent.legacy_drive = min(1.0, agent.legacy_drive + (agent.age * 0.0001) + (agent.dead_friends_count * 0.1))
    
    # Check for death from various causes (only if population floor is not active)
    if not population_floor_active:
        # 1. Check starvation (hunger > 95 and no food)
        hunger = _needs.hunger
        if hunger > 95:
            # Check if agent has food or district has food
            has_food = _inventory.food > 0
            if not has_food and district_resources:
                has_food = district_resources.get("food_stock", 0) > 10
            
            if not has_food:
                # Starvation death - higher chance the longer hunger persists
                starvation_chance = min(0.15, (hunger - 95) * 0.01)
                if _random() < starvation_chance:
                    agent.is_alive = False
                    agent.death_turn = turn
                    agent.death_cause = "starvation"
                    dead_agents[agent_id] = agent
                    if agent_id in agents:
                        del agents[agent_id]
                    return (True, "starvation")
        
        # 2. Check exhaustion (rest > 95)
        rest = _needs.rest
        if rest > 95:
            exhaustion_chance = min(0.10, (rest - 95) * 0.01)
            if _random() < exhaustion_chance:
                agent.is_alive = False
                agent.death_turn = turn
                agent.death_cause = "exhaustion"
                dead_agents[agent_id] = agent
                if agent_id in agents:
                    del agents[agent_id]
                return (True, "exhaustion")
        
        # 3. Check extreme weather
        if weather_state:
            is_extreme_weather = False
            weather_type = None
            
            wind = weather_state.get("wind", 0)
            precipitation = weather_state.get("precipitation", 0)
            temperature = weather_state.get("temperature", 0.5)
            
            if wind > 0.85:
                is_extreme_weather = True
                weather_type = "hurricane"
            elif precipitation > 0.90:
                is_extreme_weather = True
                weather_type = "flood"
            elif temperature < 0.1:
                is_extreme_weather = True
                weather_type = "extreme_cold"
            elif temperature > 0.9:
                is_extreme_weather = True
                weather_type = "extreme_heat"
            
            if is_extreme_weather:
                # More vulnerable if safety is low
                safety_modifier = 1.0 - (_needs.safety * 0.01)
                weather_death_chance = 0.02 * safety_modifier
                if _random() < weather_death_chance:
                    agent.is_alive = False
                    agent.death_turn = turn
                    death_cause = f"extreme_weather_{weather_type}"
                    agent.death_cause = death_cause
                    dead_agents[agent_id] = agent
                    if agent_id in agents:
                        del agents[agent_id]
                    return (True, death_cause)
    
    # 4. Check age-based death (always allowed, even with population floor)
    if age_int >= agent.lifespan:
        agent.is_alive = False
        agent.death_turn = turn
        agent.death_cause = "aging"
        dead_agents[agent_id] = agent
        if agent_id in agents:
            del agents[agent_id]
        return (True, "aging")
    
    return (False, None)
