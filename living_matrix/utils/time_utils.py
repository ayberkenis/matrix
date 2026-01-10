"""Time utility functions."""

def calculate_turns_since(last_turn: int, current_turn: int) -> int:
    """Calculate number of turns since last turn."""
    return current_turn - last_turn


def is_turn_interval(turn: int, interval: int) -> bool:
    """Check if current turn is a multiple of interval."""
    return turn % interval == 0
