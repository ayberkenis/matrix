"""Event runner functions for processing events."""

from typing import List, Any, Dict
from living_matrix.events.event_utils import (
    extract_event_type_string, get_event_description, get_event_district_id,
    get_event_duration, is_conflict_event, is_cooperation_event, is_scarcity_event
)


def record_event_causality(event: Any, causality_system, turn: int):
    """
    Record event in causality system.
    
    Args:
        event: Event object
        causality_system: Causality system instance
        turn: Current turn
    """
    event_type_str = extract_event_type_string(event)
    cause = f"event:{event_type_str}"
    effect = get_event_description(event)
    source = get_event_district_id(event)
    duration = get_event_duration(event)
    
    causality_system.record(
        cause=cause,
        effect=effect,
        source=source,
        confidence=0.5,
        duration=duration,
        turn=turn
    )


def record_event_emotions(event: Any, emotional_memory, turn: int):
    """
    Record event emotions in emotional memory.
    
    Args:
        event: Event object
        emotional_memory: Emotional memory instance
        turn: Current turn
    """
    event_type_str = extract_event_type_string(event)
    event_desc = get_event_description(event)
    
    if is_conflict_event(event_type_str):
        emotional_memory.add(event_desc, turn, fear=0.3, anger=0.4, sadness=0.2)
    elif is_cooperation_event(event_type_str):
        emotional_memory.add(event_desc, turn, hope=0.4, joy=0.3)
    elif is_scarcity_event(event_type_str):
        emotional_memory.add(event_desc, turn, fear=0.5, sadness=0.3)


def process_events_for_causality_and_emotions(events: List[Any], causality_system,
                                             emotional_memory, turn: int):
    """
    Process events for causality and emotional recording.
    
    Args:
        events: List of events
        causality_system: Causality system instance
        emotional_memory: Emotional memory instance
        turn: Current turn
    """
    if not events:
        return
    
    for event in events:
        record_event_causality(event, causality_system, turn)
        record_event_emotions(event, emotional_memory, turn)
