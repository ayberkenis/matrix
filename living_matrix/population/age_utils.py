"""Age-related utility functions."""

from typing import Dict

from living_matrix.constants import (
    CHILD_MORTALITY_RATE_UNDER_10, CHILD_MORTALITY_RATE_UNDER_50, CHILD_MORTALITY_RATE_OVER_50
)

# Track turn counter for slower child aging (age every 2 turns to match 0.5x adult aging)
_child_aging_counter = {}


def age_child_pools(turn: int, child_pools: Dict[str, int], 
                   child_cohorts: Dict[str, Dict[int, int]]):
    """
    Age child pools statistically (POPULATION COMPRESSION).
    Children age in cohorts, not individually.
    Ages at 0.5x rate to match adult aging (every 2 turns).
    
    Args:
        turn: Current turn
        child_pools: Dictionary of child pools per district
        child_cohorts: Dictionary of child cohorts per district
    """
    global _child_aging_counter
    
    # Initialize counter for each district if needed
    for district_id in child_pools.keys():
        if district_id not in _child_aging_counter:
            _child_aging_counter[district_id] = 0
    
    for district_id in list(child_pools.keys()):
        if child_pools[district_id] == 0:
            continue
        
        # Age every 2 turns (0.5x rate to match adult aging)
        _child_aging_counter[district_id] += 1
        if _child_aging_counter[district_id] < 2:
            continue  # Skip aging this turn
        _child_aging_counter[district_id] = 0  # Reset counter
        
        # Age cohorts probabilistically
        new_cohorts = {}
        for age_bucket, count in child_cohorts[district_id].items():
            if count <= 0:
                continue
            
            # Age bucket by 1 turn (but only every 2 simulation turns)
            new_age = age_bucket + 1
            
            # Some children may die (infant mortality, accidents)
            # Mortality rate decreases with age - very young children are most vulnerable
            # With ADULTHOOD_AGE=3, we want most children to survive to age 3
            if age_bucket == 0:
                # Newborns are most vulnerable
                mortality_rate = CHILD_MORTALITY_RATE_UNDER_10 * 2.0  # Slightly higher for newborns
            elif age_bucket < 3:
                # Very young children (age 1-2) - lower mortality
                mortality_rate = CHILD_MORTALITY_RATE_UNDER_10
            elif age_bucket < 10:
                # Older children (age 3-9) - very low mortality
                mortality_rate = CHILD_MORTALITY_RATE_UNDER_50
            elif age_bucket < 50:
                # Pre-adult children - extremely low mortality
                mortality_rate = CHILD_MORTALITY_RATE_OVER_50
            else:
                # Very old children (shouldn't happen with ADULTHOOD_AGE=3)
                mortality_rate = CHILD_MORTALITY_RATE_OVER_50
            survivors = int(count * (1.0 - mortality_rate))
            
            if survivors > 0:
                if new_age not in new_cohorts:
                    new_cohorts[new_age] = 0
                new_cohorts[new_age] += survivors
        
        child_cohorts[district_id] = new_cohorts
        # Update total pool count
        child_pools[district_id] = sum(new_cohorts.values())