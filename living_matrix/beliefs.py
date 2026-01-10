"""Agent Beliefs system: subjective reality for agents."""

import random
from typing import Dict, List, Optional
import logging

from .dataclasses import Belief
from .constants.beliefs_constants import (
    DEFAULT_BELIEF_DECAY_RATE, DEFAULT_BELIEF_SPREAD_PROBABILITY,
    RUMOR_CONFIDENCE_MIN, RUMOR_CONFIDENCE_MAX,
    EVENT_CONFIDENCE_MIN, EVENT_CONFIDENCE_MAX,
    INTERACTION_CONFIDENCE_MIN, INTERACTION_CONFIDENCE_MAX,
    EXPERIENCE_CONFIDENCE_MIN, EXPERIENCE_CONFIDENCE_MAX,
    SPREAD_CONFIDENCE_MULTIPLIER, MERGE_CONFIDENCE_DECAY,
    SAFETY_BELIEF_WEIGHT, FOOD_BELIEF_WEIGHT,
    CONFLICT_LIKELIHOOD_MULTIPLIER, CONFLICT_LIKELIHOOD_BASE,
    COOPERATION_LIKELIHOOD_MULTIPLIER, COOPERATION_LIKELIHOOD_BASE,
    COOPERATION_LIKELIHOOD_REDUCTION
)

logger = logging.getLogger(__name__)

# Belief is now imported from dataclasses
# The class definition is in dataclasses/belief_dataclasses.py


class BeliefSystem:
    """Manages agent beliefs and belief propagation."""
    
    def __init__(self, seed: int = 42):
        """Initialize belief system."""
        self.seed = seed
        random.seed(seed)
        self.belief_decay_rate = DEFAULT_BELIEF_DECAY_RATE  # Confidence decays by this per turn
        self.belief_spread_probability = DEFAULT_BELIEF_SPREAD_PROBABILITY  # Probability of spreading belief during interaction
    
    def create_belief_from_rumor(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from a rumor (lower confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(RUMOR_CONFIDENCE_MIN, RUMOR_CONFIDENCE_MAX),  # Rumors have lower confidence
            source="rumor",
            last_updated_turn=turn
        )
    
    def create_belief_from_event(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from an event (higher confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(EVENT_CONFIDENCE_MIN, EVENT_CONFIDENCE_MAX),  # Events have higher confidence
            source="event",
            last_updated_turn=turn
        )
    
    def create_belief_from_interaction(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from agent interaction (medium confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(INTERACTION_CONFIDENCE_MIN, INTERACTION_CONFIDENCE_MAX),
            source="agent_interaction",
            last_updated_turn=turn
        )
    
    def create_belief_from_experience(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from direct experience (highest confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(EXPERIENCE_CONFIDENCE_MIN, EXPERIENCE_CONFIDENCE_MAX),  # Direct experience is most confident
            source="direct_experience",
            last_updated_turn=turn
        )
    
    def update_belief(self, belief: Belief, new_polarity: float, new_confidence: float, 
                     source: str, turn: int):
        """
        Update an existing belief with new information.
        
        Args:
            belief: Existing belief to update
            new_polarity: New polarity value
            new_confidence: Confidence of new information
            source: Source of new information
            turn: Current turn
        """
        # Weighted average: existing belief weighted by its confidence, new info by its confidence
        total_confidence = belief.confidence + new_confidence
        if total_confidence > 0:
            belief.polarity = (belief.polarity * belief.confidence + new_polarity * new_confidence) / total_confidence
            belief.confidence = min(1.0, total_confidence * MERGE_CONFIDENCE_DECAY)  # Slight decay on merge
        else:
            belief.polarity = new_polarity
            belief.confidence = new_confidence
        
        belief.source = source
        belief.last_updated_turn = turn
    
    def decay_belief(self, belief: Belief, turn: int):
        """
        Decay belief confidence over time.
        
        Args:
            belief: Belief to decay
            turn: Current turn
        """
        turns_since_update = turn - belief.last_updated_turn
        if turns_since_update > 0:
            decay = self.belief_decay_rate * turns_since_update
            belief.confidence = max(0.0, belief.confidence - decay)
    
    def spread_belief(self, source_belief: Belief, target_beliefs: Dict[str, Belief], 
                      turn: int) -> bool:
        """
        Attempt to spread a belief to another agent.
        
        Args:
            source_belief: Belief to spread
            target_beliefs: Target agent's beliefs dictionary
            turn: Current turn
            
        Returns:
            True if belief was spread, False otherwise
        """
        if random.random() > self.belief_spread_probability:
            return False
        
        topic = source_belief.topic
        
        if topic in target_beliefs:
            # Update existing belief
            self.update_belief(
                target_beliefs[topic],
                source_belief.polarity,
                source_belief.confidence * SPREAD_CONFIDENCE_MULTIPLIER,  # Spread beliefs have reduced confidence
                "agent_interaction",
                turn
            )
        else:
            # Create new belief
            target_beliefs[topic] = Belief(
                topic=topic,
                polarity=source_belief.polarity,
                confidence=source_belief.confidence * SPREAD_CONFIDENCE_MULTIPLIER,  # Reduced confidence when spread
                source="agent_interaction",
                last_updated_turn=turn
            )
        
        logger.debug(f"Belief spread: {topic} from agent to agent")
        return True
    
    def get_belief_influence(self, beliefs: Dict[str, Belief], topic: str) -> float:
        """
        Get the influence of a belief on agent behavior.
        
        Args:
            beliefs: Agent's beliefs dictionary
            topic: Topic to check
            
        Returns:
            Influence value (-1.0 to 1.0), 0.0 if no belief
        """
        belief = beliefs.get(topic)
        if not belief:
            return 0.0
        
        # Influence = polarity * confidence
        return belief.polarity * belief.confidence
    
    def get_movement_bias(self, beliefs: Dict[str, Belief], location_id: str) -> float:
        """
        Get movement bias toward/away from a location based on beliefs.
        
        Args:
            beliefs: Agent's beliefs
            location_id: Location ID to check
            
        Returns:
            Bias value (-1.0 to 1.0), positive = attracted, negative = repelled
        """
        # Extract region from location_id (e.g., "loc_5" -> check for region beliefs)
        # This is simplified - in practice, you'd map location to region
        region_name = location_id.split("_")[0] if "_" in location_id else location_id
        
        # Check beliefs about this region
        topic = f"{region_name}_safety"
        safety_belief = self.get_belief_influence(beliefs, topic)
        
        topic = f"{region_name}_food_availability"
        food_belief = self.get_belief_influence(beliefs, topic)
        
        # Combined bias (weighted)
        return (safety_belief * SAFETY_BELIEF_WEIGHT + food_belief * FOOD_BELIEF_WEIGHT)
    
    def get_conflict_likelihood_modifier(self, beliefs: Dict[str, Belief], other_agent_id: str) -> float:
        """
        Get modifier for conflict likelihood based on beliefs about other agent.
        
        Args:
            beliefs: Agent's beliefs
            other_agent_id: Other agent ID
            
        Returns:
            Modifier (0.5 to 2.0), >1.0 = more likely to conflict
        """
        topic = f"agent_{other_agent_id}_trustworthiness"
        trust_belief = self.get_belief_influence(beliefs, topic)
        
        # Negative trust (hostile) increases conflict likelihood
        if trust_belief < 0:
            return CONFLICT_LIKELIHOOD_BASE + abs(trust_belief) * CONFLICT_LIKELIHOOD_MULTIPLIER  # Up to 1.5x conflict
        else:
            return CONFLICT_LIKELIHOOD_BASE - trust_belief * COOPERATION_LIKELIHOOD_REDUCTION  # Down to 0.7x conflict (less likely)
    
    def get_cooperation_likelihood_modifier(self, beliefs: Dict[str, Belief], other_agent_id: str) -> float:
        """
        Get modifier for cooperation likelihood based on beliefs.
        
        Args:
            beliefs: Agent's beliefs
            other_agent_id: Other agent ID
            
        Returns:
            Modifier (0.5 to 2.0), >1.0 = more likely to cooperate
        """
        topic = f"agent_{other_agent_id}_trustworthiness"
        trust_belief = self.get_belief_influence(beliefs, topic)
        
        # Positive trust increases cooperation
        if trust_belief > 0:
            return COOPERATION_LIKELIHOOD_BASE + trust_belief * COOPERATION_LIKELIHOOD_MULTIPLIER  # Up to 1.5x cooperation
        else:
            return COOPERATION_LIKELIHOOD_BASE - abs(trust_belief) * COOPERATION_LIKELIHOOD_REDUCTION  # Down to 0.7x cooperation
