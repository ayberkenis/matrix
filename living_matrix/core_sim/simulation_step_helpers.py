"""Helper functions for simulation step operations."""

from typing import Optional, List, Dict, Any
import logging

from living_matrix.constants import (
    EXPRESSION_SPEAK_THRESHOLD, MIN_VOCABULARY_SIZE, HEARTBEAT_INTERVAL,
    STIMULUS_DECAY_FACTOR, STIMULUS_DECAY_MIN_WEIGHT, INTERNAL_MOTIF_WEIGHT,
    INTERNAL_EDGE_WEIGHT, LOW_DIVERSITY_THRESHOLD, LOW_DIVERSITY_TURNS_THRESHOLD,
    AUTO_SAVE_INTERVAL
)

logger = logging.getLogger(__name__)


def should_generate_output(force_speak: bool, user_input: Optional[str], 
                          silence_mode: bool, expression_drive: float,
                          vocab_size: int, turn: int) -> bool:
    """
    Determine if we should generate visible output.
    
    Args:
        force_speak: Force output flag
        user_input: User input if provided
        silence_mode: Whether silence mode is enabled
        expression_drive: Current expression drive
        vocab_size: Vocabulary size
        turn: Current turn
        
    Returns:
        True if should generate output
    """
    return (
        force_speak or
        user_input is not None or  # Always speak when user provides input
        (not silence_mode and (
            # Adjusted conditions: expression threshold + vocabulary requirement
            (expression_drive > EXPRESSION_SPEAK_THRESHOLD and vocab_size >= MIN_VOCABULARY_SIZE) or
            turn % HEARTBEAT_INTERVAL == 0  # Heartbeat every 10 turns
        ))
    )


def calculate_stimulus_decay_weight(turns_since: int, decay_factor: float) -> float:
    """
    Calculate stimulus decay weight.
    
    Args:
        turns_since: Turns since last stimulus
        decay_factor: Decay factor per turn
        
    Returns:
        Decay weight (0.0 to 1.0)
    """
    if turns_since <= 0:
        return 1.0
    return decay_factor ** turns_since


def is_stimulus_significant(decay_weight: float) -> bool:
    """
    Check if stimulus is still significant.
    
    Args:
        decay_weight: Current decay weight
        
    Returns:
        True if still significant
    """
    return decay_weight > STIMULUS_DECAY_MIN_WEIGHT


def calculate_interaction_intensity(user_input: Optional[str]) -> float:
    """
    Calculate interaction intensity from user input.
    
    Args:
        user_input: User input string
        
    Returns:
        Interaction intensity (0.0 to 1.0)
    """
    if not user_input:
        return 0.0
    return min(1.0, len(user_input) / 100.0)  # Normalize


def should_inject_novelty(diversity: float, user_input: Optional[str]) -> bool:
    """
    Check if we should inject novelty.
    
    Args:
        diversity: Current diversity metric
        user_input: User input if provided
        
    Returns:
        True if should inject novelty
    """
    return not user_input and diversity < 0.2


def is_notable_interaction(interaction_intensity: float, output_tokens: List[str]) -> bool:
    """
    Check if interaction is notable for episodic memory.
    
    Args:
        interaction_intensity: Interaction intensity
        output_tokens: Output tokens
        
    Returns:
        True if notable
    """
    return interaction_intensity > 0.5 or len(output_tokens) > 10


def should_auto_save(turn: int, auto_save_interval: int) -> bool:
    """
    Check if we should auto-save.
    
    Args:
        turn: Current turn
        auto_save_interval: Auto-save interval
        
    Returns:
        True if should auto-save
    """
    return turn % auto_save_interval == 0


def calculate_tensor_modifier(tensor_cognition, stability_drive: float) -> float:
    """
    Calculate tensor modifier for event system.
    
    Args:
        tensor_cognition: Tensor cognition instance
        stability_drive: Current stability drive
        
    Returns:
        Tensor modifier (-0.1 to 0.1)
    """
    if not tensor_cognition:
        return 0.0
    
    world_state = tensor_cognition.get_world_state(stability_drive)
    # Use state_flux norm as a small modifier (-0.1 to 0.1)
    return (tensor_cognition.state_flux.norm().item() - 1.0) * 0.1


def extract_event_type_string(event: Any) -> str:
    """
    Extract event type as string from event object.
    
    Args:
        event: Event object
        
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


def get_emotional_weights_for_event(event_type_str: str) -> Dict[str, float]:
    """
    Get emotional weights for an event type.
    
    Args:
        event_type_str: Event type string
        
    Returns:
        Dictionary of emotion weights
    """
    event_type_lower = event_type_str.lower()
    if 'conflict' in event_type_lower or 'riot' in event_type_lower:
        return {'fear': 0.3, 'anger': 0.4, 'sadness': 0.2}
    elif 'aid' in event_type_lower or 'cooperation' in event_type_lower:
        return {'hope': 0.4, 'joy': 0.3}
    elif 'shortage' in event_type_lower or 'scarcity' in event_type_lower:
        return {'fear': 0.5, 'sadness': 0.3}
    return {}


def is_weather_bad(weather: str) -> bool:
    """
    Check if weather is bad.
    
    Args:
        weather: Weather condition string
        
    Returns:
        True if weather is bad
    """
    return weather in ['rain', 'storm', 'extreme_heat', 'extreme_cold']


def calculate_food_per_capita(food_stock: float, total_population: int) -> float:
    """
    Calculate food per capita.
    
    Args:
        food_stock: Food stock
        total_population: Total population
        
    Returns:
        Food per capita
    """
    return food_stock / max(1, total_population)


def calculate_jobs_per_capita(jobs_available: int, active_agents: int) -> float:
    """
    Calculate jobs per capita.
    
    Args:
        jobs_available: Jobs available
        active_agents: Active agents count
        
    Returns:
        Jobs per capita
    """
    return jobs_available / max(1, active_agents)


def calculate_child_to_adult_ratio(child_pool: int, active_agents: int) -> float:
    """
    Calculate child to adult ratio.
    
    Args:
        child_pool: Child pool size
        active_agents: Active agents count
        
    Returns:
        Child to adult ratio
    """
    if active_agents <= 0:
        return 0.0
    return child_pool / active_agents
