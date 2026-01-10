"""Reproduction functions."""

import random
from typing import List, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from living_matrix.human_agent import HumanAgent

# Performance optimization: limit pair checks to prevent O(n²) slowdown
MAX_REPRODUCTION_PAIRS_TO_CHECK = 2000  # Limit pair checks per turn for performance


def check_reproduction(agents: List['HumanAgent'], district_resources: Dict, 
                      turn: int, relationship_system, world_flags_system=None, 
                      extinction_risk: float = 0.0, population_pressure: float = 0.0, 
                      birth_pressure: float = 0.0) -> List[Tuple[str, str]]:
    """
    Check for reproduction opportunities (SYSTEM 12 - FORCED REPRODUCTION).
    
    Args:
        agents: List of agents to check
        district_resources: District resource dictionary
        turn: Current turn
        relationship_system: Relationship system instance
        world_flags_system: Optional world flags system
        extinction_risk: Current extinction risk (0.0-1.0)
        population_pressure: Current population pressure (0.0-1.0)
        birth_pressure: Current birth pressure (0.0-1.0)
        
    Returns:
        List of (parent1_id, parent2_id) tuples for new births
    """
    births = []
    # Make food requirement less strict - only need food if tension is very high
    food_stock = district_resources.get("food_stock", 50)
    food_available = food_stock > 20  # Lowered from 30 to 20
    tension = district_resources.get("tension", 20)
    
    # Apply world flag effects to reproduction
    reproduction_modifier = 1.0
    if world_flags_system:
        for flag in world_flags_system.get_all_flags():
            if "reproduction_reduction" in flag.effects:
                reproduction_modifier *= (1.0 - flag.effects["reproduction_reduction"])
    
    # Only check alive agents of reproductive age
    # Very wide reproductive window: age 20 to (lifespan - 20) for maximum reproduction opportunity
    # Start earlier and end later to give agents maximum time to reproduce
    # Use int() to handle fractional ages from slower aging
    reproductive_agents = [a for a in agents 
                          if a.is_alive and 20 <= int(a.age) <= int(a.lifespan) - 20]
    
    # Check pairs
    # If no reproductive agents found, log warning but continue
    import logging
    logger = logging.getLogger(__name__)
    
    # OPTIMIZATION: Calculate population_count once
    population_count = len([a for a in agents if a.is_alive])
    survival_instinct = population_count < 20
    
    if len(reproductive_agents) == 0:
        alive_agents = [a for a in agents if a.is_alive]
        all_ages = [int(a.age) for a in alive_agents]
        all_lifespans = [int(a.lifespan) for a in alive_agents]
        sex_distribution = {}
        for a in alive_agents:
            sex = getattr(a, 'sex', 'unknown')
            sex_distribution[sex] = sex_distribution.get(sex, 0) + 1
        msg = f"No reproductive agents found. Total agents: {len(alive_agents)}, ages: {all_ages}, lifespans: {all_lifespans}, sex_dist: {sex_distribution}"
        logger.warning(msg)
        # Log why each agent is excluded
        for a in alive_agents:
            age_int = int(a.age)
            lifespan_int = int(a.lifespan)
            in_window = 20 <= age_int <= lifespan_int - 20
            detail = f"  Agent {a.id}: age={age_int}, lifespan={lifespan_int}, in_window={in_window}, sex={getattr(a, 'sex', 'unknown')}"
            logger.warning(detail)
        return births
    
    # OPTIMIZATION: Group agents by sex and location for faster pairing
    # Separate by sex first (cheapest check)
    males = [a for a in reproductive_agents if a.sex == 'male']
    females = [a for a in reproductive_agents if a.sex == 'female']
    
    # OPTIMIZATION: If too many agents, sample to limit pair checks
    # This prevents O(n²) slowdown with large populations
    if len(males) * len(females) > MAX_REPRODUCTION_PAIRS_TO_CHECK:
        # Sample agents to limit total pairs checked
        max_agents_per_sex = int((MAX_REPRODUCTION_PAIRS_TO_CHECK / 2) ** 0.5) + 1
        if len(males) > max_agents_per_sex:
            males = random.sample(males, max_agents_per_sex)
        if len(females) > max_agents_per_sex:
            females = random.sample(females, max_agents_per_sex)
    
    # Log reproductive agents info
    if len(reproductive_agents) > 0:
        sex_counts = {'male': len(males), 'female': len(females)}
        msg = f"Found {len(reproductive_agents)} reproductive agents, sex_dist: {sex_counts}"
        logger.debug(msg)
    
    pairs_checked = 0
    pairs_same_sex = 0
    pairs_different_location = 0
    pairs_passed_checks = 0
    
    # OPTIMIZATION: Only check opposite-sex pairs (males x females)
    # This reduces from O(n²) to O(m*f) where m= males, f=females
    for agent1 in males:
        # OPTIMIZATION: Early exit if we've checked too many pairs
        if pairs_checked >= MAX_REPRODUCTION_PAIRS_TO_CHECK:
            break
        for agent2 in females:
            # OPTIMIZATION: Early exit if we've checked too many pairs
            if pairs_checked >= MAX_REPRODUCTION_PAIRS_TO_CHECK:
                break
            pairs_checked += 1
            
            # OPTIMIZATION: Check location/district early (cheap checks before expensive relationship checks)
            same_district = getattr(agent1, 'district', None) == getattr(agent2, 'district', None)
            
            # Allow reproduction if: same location, same district, OR survival instinct active
            if agent1.location != agent2.location and not same_district and not survival_instinct:
                pairs_different_location += 1
                continue
            
            pairs_passed_checks += 1
            
            # OPTIMIZATION: Check relationship - create if doesn't exist with good initial values
            # Use get() with default to avoid KeyError
            rel = agent1.relationships.get(agent2.id)
            if not rel:
                # Create initial relationship with values that meet reproduction threshold
                rel = relationship_system.create_relationship(agent2.id, turn, initial_affection=0.2)
                rel.trust = 0.2  # Set trust above minimum
                rel.familiarity = 0.1  # Set familiarity above minimum
                agent1.relationships[agent2.id] = rel
                # Also create reverse relationship
                if agent1.id not in agent2.relationships:
                    rel2 = relationship_system.create_relationship(agent1.id, turn, initial_affection=0.2)
                    rel2.trust = 0.2
                    rel2.familiarity = 0.1
                    agent2.relationships[agent1.id] = rel2
            
            # SYSTEM A & 12: FORCED REPRODUCTION CONDITIONS
            # Reproduction MUST occur if ANY condition is true:
            # 1. Normal case: affection + trust > threshold
            # 2. Extinction risk > 0.6 (panic reproduction) - HARD CONSTRAINT
            # 3. Legacy drive > 0.8 (last chance behavior)
            # 4. Birth pressure > 0.7 (social enforcement)
            # 5. SYSTEM A: must_attempt_reproduction flag (hard constraint)
            
            # OPTIMIZATION: population_count already calculated above
            can_reproduce_normal = relationship_system.can_reproduce(rel, food_available, tension, food_stock, population_count)
            extinction_panic = extinction_risk > 0.6
            legacy_drive_high = agent1.legacy_drive > 0.8 or agent2.legacy_drive > 0.8
            birth_pressure_high = birth_pressure > 0.7
            must_reproduce = agent1.must_attempt_reproduction or agent2.must_attempt_reproduction
            
            # Make reproduction very easy: if agents are opposite sex and in reproductive age,
            # allow reproduction with minimal requirements (population maintenance priority)
            # Survival instinct: allow reproduction even at high tension if population is low
            
            # CRITICAL: For opposite-sex pairs in reproductive age, ALWAYS allow reproduction
            # unless relationship is extremely hostile. This is survival instinct behavior.
            # Only block if relationship is actively hostile (very negative)
            basic_conditions_met = (
                rel.affection > -0.5 and  # Only block if very strongly negative
                rel.trust >= -0.2 and  # Only block if very negative
                (tension < 100 or survival_instinct)  # Allow any tension if survival instinct active
            )
            
            # SYSTEM A: When extinction_risk > 0.6, override relationship requirements
            if extinction_panic or must_reproduce:
                # Force reproduction - ignore normal relationship thresholds
                should_reproduce = True
                # Boost relationship values to ensure they meet minimums
                if rel.affection < 0.2:
                    rel.affection = 0.3  # Boost to minimum
                if rel.trust < 0.2:
                    rel.trust = 0.3  # Boost to minimum
                if rel.familiarity < 0.1:
                    rel.familiarity = 0.2  # Boost to minimum
            else:
                # For opposite-sex pairs in reproductive age, ALWAYS allow reproduction
                # This is survival instinct - reproduction is instinctual behavior
                # Only block if relationship is extremely hostile (affection < -0.5)
                # Since we create relationships with affection=0.2, this should almost always pass
                should_reproduce = basic_conditions_met or can_reproduce_normal or legacy_drive_high or birth_pressure_high or survival_instinct
                
                # If still False, force it for survival (unless extremely hostile)
                if not should_reproduce and rel.affection > -0.5:
                    should_reproduce = True
                    logger.debug(f"Forcing reproduction for survival: {agent1.id} + {agent2.id}, affection={rel.affection:.2f}")
            
            if should_reproduce:
                # Base chance per turn, modified by world flags
                # Significantly increased to ensure reproduction happens
                base_chance = 0.15 * reproduction_modifier  # 15% per turn (increased from 8%)
                
                # FORCE reproduction under panic conditions
                if extinction_panic or must_reproduce:
                    base_chance = min(0.30, base_chance * 10.0)  # 10x chance, max 30% (HARD CONSTRAINT)
                if legacy_drive_high:
                    base_chance = min(0.15, base_chance * 5.0)  # 5x chance, max 15%
                if birth_pressure_high:
                    base_chance = min(0.12, base_chance * 4.0)  # 4x chance, max 12%
                
                # Add reproduction drive bonus (larger bonus)
                avg_reproduction_drive = (agent1.reproduction_drive + agent2.reproduction_drive) / 2.0
                base_chance += avg_reproduction_drive * 0.08  # Increased from 0.05
                
                # Bonus for being in prime reproductive age (age 100-1000)
                # Extended range to help elderly agents who are still in window
                age1_int = int(agent1.age)
                age2_int = int(agent2.age)
                if 100 <= age1_int <= 1000 and 100 <= age2_int <= 1000:
                    base_chance += 0.05  # Additional 5% bonus for prime age (increased)
                # Even if not in prime age, give bonus if still in reproductive window
                elif 20 <= age1_int <= int(agent1.lifespan) - 20 and 20 <= age2_int <= int(agent2.lifespan) - 20:
                    base_chance += 0.02  # 2% bonus for being in reproductive window
                
                if random.random() < base_chance:
                    births.append((agent1.id, agent2.id))
                    logger.debug(f"Reproduction successful: {agent1.id} ({agent1.sex}) + {agent2.id} ({agent2.sex}), chance was {base_chance:.2%}")
    
    # Log summary
    if pairs_checked > 0:
        msg = f"Reproduction check: {pairs_checked} pairs checked, {pairs_same_sex} same_sex, {pairs_different_location} different_location, {pairs_passed_checks} passed_checks, {len(births)} births"
        logger.info(msg)
    elif len(reproductive_agents) > 0:
        msg = f"Reproduction check: {len(reproductive_agents)} reproductive agents but 0 pairs checked (all same sex or different locations?)"
        logger.warning(msg)
    
    return births


def add_child_to_pool(parent1_id: str, parent2_id: str, district: str, turn: int,
                      child_pools: Dict[str, int], child_cohorts: Dict[str, Dict[int, int]],
                      max_child_pool_per_district: int) -> bool:
    """
    Add a child to the child pool (POPULATION COMPRESSION).
    Children are NOT agents until they reach adulthood.
    
    Args:
        parent1_id: First parent ID
        parent2_id: Second parent ID
        district: District where child is born
        turn: Current turn
        child_pools: Dictionary of child pools per district
        child_cohorts: Dictionary of child cohorts per district
        max_child_pool_per_district: Maximum children per district
        
    Returns:
        True if child was added to pool
    """
    if district not in child_pools:
        child_pools[district] = 0
        child_cohorts[district] = {}
    
    # Check soft cap
    if child_pools[district] >= max_child_pool_per_district:
        return False
    
    # Add to child pool
    child_pools[district] += 1
    
    # Add to age cohort (age 0 bucket)
    age_bucket = 0  # Newborns start at age 0
    if age_bucket not in child_cohorts[district]:
        child_cohorts[district][age_bucket] = 0
    child_cohorts[district][age_bucket] += 1
    
    return True
