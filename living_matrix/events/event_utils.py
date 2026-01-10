"""Event utility functions."""

from typing import Any, Dict, List
from living_matrix.constants.event_constants import (
    SPONTANEOUS_EVENT_CHANCE, TENSOR_MODIFIER_POSITIVE_THRESHOLD,
    TENSOR_MODIFIER_NEGATIVE_THRESHOLD
)


def classify_action_to_event_type(action: str) -> str:
    """
    Classify an action string into an event type.
    
    Args:
        action: Action description string
        
    Returns:
        Event type string
    """
    action_lower = action.lower()
    
    if 'work' in action_lower or 'shift' in action_lower:
        if 'goes to work' in action_lower:
            return 'shift_start'
        return 'shift_end'
    elif 'market' in action_lower or 'trade' in action_lower:
        return 'market_trade'
    elif 'rest' in action_lower or 'sleep' in action_lower:
        return 'rest'
    elif 'food' in action_lower or 'meal' in action_lower:
        return 'meal'
    elif 'socialize' in action_lower or 'visit' in action_lower:
        return 'meeting'
    elif 'move' in action_lower or 'transit' in action_lower:
        return 'commute'
    else:
        return 'rest'  # Default


def apply_tensor_modifier_to_event_type(event_type: str, tensor_modifier: float) -> str:
    """
    Apply tensor modifier to event type (subtle influence).
    
    Args:
        event_type: Original event type
        tensor_modifier: Tensor modifier (-0.1 to 0.1)
        
    Returns:
        Modified event type
    """
    if event_type in ['minor_conflict', 'helping']:
        if tensor_modifier > TENSOR_MODIFIER_POSITIVE_THRESHOLD:
            return 'helping'
        elif tensor_modifier < TENSOR_MODIFIER_NEGATIVE_THRESHOLD:
            return 'minor_conflict'
    return event_type


def should_generate_spontaneous_event() -> bool:
    """
    Check if should generate spontaneous event.
    
    Returns:
        True if should generate
    """
    import random
    return random.random() < SPONTANEOUS_EVENT_CHANCE


def extract_event_type_string(event: Any) -> str:
    """
    Extract event type as string from event object.
    
    Args:
        event: Event object (can be Enum or string)
        
    Returns:
        Event type as string
    """
    event_type_str = 'unknown'
    if hasattr(event, 'event_type'):
        if hasattr(event.event_type, 'value'):
            # It's an Enum
            event_type_str = event.event_type.value
        else:
            # It's already a string
            event_type_str = str(event.event_type)
    return event_type_str


def get_event_description(event: Any) -> str:
    """
    Get event description from event object.
    
    Args:
        event: Event object
        
    Returns:
        Event description string
    """
    if hasattr(event, 'description'):
        return event.description
    return str(event)


def get_event_district_id(event: Any, default: str = 'world') -> str:
    """
    Get district ID from event object.
    
    Args:
        event: Event object
        default: Default district ID
        
    Returns:
        District ID
    """
    if hasattr(event, 'district_id'):
        return event.district_id
    return default


def get_event_duration(event: Any, default: int = 1) -> int:
    """
    Get event duration from event object.
    
    Args:
        event: Event object
        default: Default duration
        
    Returns:
        Event duration
    """
    if hasattr(event, 'duration'):
        return event.duration
    return default


def is_conflict_event(event_type_str: str) -> bool:
    """
    Check if event is a conflict event.
    
    Args:
        event_type_str: Event type string
        
    Returns:
        True if conflict event
    """
    event_type_lower = event_type_str.lower()
    return 'conflict' in event_type_lower or 'riot' in event_type_lower


def is_cooperation_event(event_type_str: str) -> bool:
    """
    Check if event is a cooperation event.
    
    Args:
        event_type_str: Event type string
        
    Returns:
        True if cooperation event
    """
    event_type_lower = event_type_str.lower()
    return 'aid' in event_type_lower or 'cooperation' in event_type_lower


def is_scarcity_event(event_type_str: str) -> bool:
    """
    Check if event is a scarcity event.
    
    Args:
        event_type_str: Event type string
        
    Returns:
        True if scarcity event
    """
    event_type_lower = event_type_str.lower()
    return 'shortage' in event_type_lower or 'scarcity' in event_type_lower
