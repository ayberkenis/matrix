"""Random utility functions."""

import random


def random_int_in_range(min_val: int, max_val: int) -> int:
    """Generate random integer in range [min_val, max_val]."""
    return random.randint(min_val, max_val)


def random_float_in_range(min_val: float, max_val: float) -> float:
    """Generate random float in range [min_val, max_val]."""
    return random.uniform(min_val, max_val)


def random_choice(choices):
    """Choose a random element from choices."""
    return random.choice(choices)


def random_sample(choices, k: int):
    """Choose k random elements from choices."""
    return random.sample(choices, k)


def random_probability() -> float:
    """Generate random probability (0.0 to 1.0)."""
    return random.random()


def weighted_choice(choices, weights):
    """Choose a random element from choices based on weights."""
    total_weight = sum(weights)
    if total_weight == 0:
        return random.choice(choices)
    r = random.random() * total_weight
    cumulative = 0.0
    for i, weight in enumerate(weights):
        cumulative += weight
        if r <= cumulative:
            return choices[i]
    return choices[-1]
