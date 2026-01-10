"""Mathematical utility functions."""

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def normalize_to_range(value: float, old_min: float, old_max: float, new_min: float, new_max: float) -> float:
    """Normalize a value from one range to another."""
    if old_max == old_min:
        return new_min
    normalized = (value - old_min) / (old_max - old_min)
    return new_min + normalized * (new_max - new_min)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by t (0-1)."""
    return a + (b - a) * t
