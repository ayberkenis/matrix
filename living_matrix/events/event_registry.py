"""Event registry and type definitions."""

from typing import List
from living_matrix.constants.event_constants import EVENT_TYPES


def get_all_event_types() -> List[str]:
    """
    Get all registered event types.
    
    Returns:
        List of event type strings
    """
    return EVENT_TYPES.copy()


def is_valid_event_type(event_type: str) -> bool:
    """
    Check if event type is valid.
    
    Args:
        event_type: Event type string
        
    Returns:
        True if valid
    """
    return event_type in EVENT_TYPES


def get_spontaneous_event_types() -> List[str]:
    """
    Get event types that can occur spontaneously.
    
    Returns:
        List of spontaneous event types
    """
    return ['minor_conflict', 'helping', 'discovery']
