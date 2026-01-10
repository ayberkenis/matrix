"""Promotion functions for children becoming adults."""

import random
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

from living_matrix.constants import (
    MAX_ACTIVE_AGENTS, ADULTHOOD_AGE, BASE_PROMOTION_CHANCE,
    PROMOTION_FOOD_FACTOR_DIVISOR, PROMOTION_JOB_FACTOR_DIVISOR,
    ROLES, NAME_PARTS
)

if TYPE_CHECKING:
    from living_matrix.human_agent import HumanAgent, HumanNeeds, HumanTraits, HumanInventory


def promote_children_to_agents(turn: int, district_resources: Dict,
                               child_pools: Dict[str, int], child_cohorts: Dict[str, Dict[int, int]],
                               agents: Dict[str, 'HumanAgent'], dead_agents: Dict[str, 'HumanAgent'],
                               districts: List[str], locations: List[str],
                               calculate_initial_reproduction_drive) -> List[Tuple[str, str, Optional[str]]]:
    """
    Promote children from pool to agents (stochastic, POPULATION COMPRESSION).
    Only promotes if active_agents < MAX_ACTIVE_AGENTS.
    
    Args:
        turn: Current turn
        district_resources: District resource dictionary
        child_pools: Dictionary of child pools per district
        child_cohorts: Dictionary of child cohorts per district
        agents: Dictionary of active agents
        dead_agents: Dictionary of dead agents
        districts: List of district IDs
        locations: List of location IDs
        calculate_initial_reproduction_drive: Function to calculate initial reproduction drive
        
    Returns:
        List of (agent_id, description, event_type) tuples for promotions
    """
    events = []
    
    # Check if we can promote (hard cap on active agents)
    active_count = len([a for a in agents.values() if a.is_alive])
    
    if active_count >= MAX_ACTIVE_AGENTS:
        return events  # Cannot promote - at capacity
    
    # Try to promote from each district
    for district_id in list(child_pools.keys()):
        if child_pools[district_id] == 0:
            continue
        
        # Calculate promotion probability based on district resources (per district)
        food_available = district_resources.get("food_stock", 50)
        jobs_available = district_resources.get("jobs_available", 5)
        tension = district_resources.get("tension", 20)
        
        # Base promotion probability (higher when resources are good)
        # But ensure minimum chance so population can grow even in hard times
        food_factor = min(1.0, food_available / PROMOTION_FOOD_FACTOR_DIVISOR)  # 0-1 based on food
        job_factor = min(1.0, jobs_available / PROMOTION_JOB_FACTOR_DIVISOR)  # 0-1 based on jobs
        tension_factor = max(0.0, 1.0 - (tension / 100.0))  # Lower tension = higher promotion
        
        promotion_chance = BASE_PROMOTION_CHANCE * food_factor * job_factor * tension_factor
        # Ensure minimum 20% chance even in worst conditions (survival instinct)
        promotion_chance = max(0.20, promotion_chance)
        
        # Check if any children are old enough (ADULTHOOD_AGE)
        eligible_count = 0
        total_children = child_pools[district_id]
        age_distribution = {}
        for age_bucket, count in child_cohorts[district_id].items():
            age_distribution[age_bucket] = count
            if age_bucket >= ADULTHOOD_AGE:
                eligible_count += count
        
        if eligible_count == 0:
            continue
        
        # Stochastic promotion: try to promote up to eligible_count children
        # But respect MAX_ACTIVE_AGENTS limit
        promotions_this_turn = 0
        max_promotions = min(eligible_count, MAX_ACTIVE_AGENTS - active_count)
        
        for _ in range(max_promotions):
            if random.random() < promotion_chance:
                # Promote one child
                promoted = promote_one_child(
                    district_id, turn, child_pools, child_cohorts,
                    agents, dead_agents, locations, calculate_initial_reproduction_drive
                )
                if promoted:
                    events.append((promoted.id, f"{promoted.name} reached adulthood in {district_id}", "promotion"))
                    promotions_this_turn += 1
                    active_count += 1
                    
                    # Stop if we hit the cap
                    if active_count >= MAX_ACTIVE_AGENTS:
                        break
    
    return events


def promote_one_child(district_id: str, turn: int,
                     child_pools: Dict[str, int], child_cohorts: Dict[str, Dict[int, int]],
                     agents: Dict[str, 'HumanAgent'], dead_agents: Dict[str, 'HumanAgent'],
                     locations: List[str], calculate_initial_reproduction_drive) -> Optional['HumanAgent']:
    """
    Promote one child from pool to agent.
    Returns the new agent, or None if promotion failed.
    
    Args:
        district_id: District ID
        turn: Current turn
        child_pools: Dictionary of child pools per district
        child_cohorts: Dictionary of child cohorts per district
        agents: Dictionary of active agents
        dead_agents: Dictionary of dead agents
        locations: List of location IDs
        calculate_initial_reproduction_drive: Function to calculate initial reproduction drive
        
    Returns:
        New agent or None
    """
    # Find oldest eligible child cohort
    eligible_ages = [age for age in child_cohorts[district_id].keys() 
                     if age >= ADULTHOOD_AGE and child_cohorts[district_id][age] > 0]
    
    if not eligible_ages:
        return None
    
    # Promote from oldest cohort
    promotion_age = max(eligible_ages)
    cohort_count = child_cohorts[district_id][promotion_age]
    
    if cohort_count <= 0:
        return None
    
    # Decrement pool
    child_pools[district_id] -= 1
    child_cohorts[district_id][promotion_age] -= 1
    if child_cohorts[district_id][promotion_age] == 0:
        del child_cohorts[district_id][promotion_age]
    
    # Create new adult agent
    agent_id = f"human_{len(agents) + len(dead_agents)}"
    name = random.choice(NAME_PARTS) + " " + random.choice(NAME_PARTS)
    location = random.choice(locations) if locations else "loc_default"
    role = random.choice(ROLES)
    
    # Import here to avoid circular dependency
    from living_matrix.human_agent import HumanAgent, HumanNeeds, HumanTraits, HumanInventory
    
    # Create agent with age = promotion_age
    agent = HumanAgent(
        id=agent_id,
        name=name,
        district=district_id,
        location=location,
        home_location=location,
        role=role,
        sex=random.choice(["male", "female"]),  # Random sex assignment (50/50)
        needs=HumanNeeds(
            hunger=random.randint(30, 50),
            rest=random.randint(40, 60),
            safety=random.randint(50, 70),
            belonging=random.randint(40, 60),
            purpose=random.randint(40, 60)
        ),
        traits=HumanTraits(
            risk=random.uniform(0.3, 0.7),
            empathy=random.uniform(0.3, 0.7),
            ambition=random.uniform(0.3, 0.7),
            patience=random.uniform(0.3, 0.7)
        ),
        inventory=HumanInventory(
            food=random.randint(2, 5),
            credits=random.randint(10, 25),
            tools=0
        ),
        age=promotion_age,
        lifespan=random.randint(2400, 4000),  # Long lifespan (doubled for slower aging)
        is_alive=True,
        survival_drive=random.uniform(0.7, 1.0),
        reproduction_drive=calculate_initial_reproduction_drive(promotion_age, 1500),
        legacy_drive=random.uniform(0.2, 0.4)
    )
    
    # Add to agents
    agents[agent_id] = agent
    
    return agent
