"""Agent Beliefs system: subjective reality for agents."""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    """A belief held by an agent about a topic."""
    topic: str  # e.g., "kora_food_availability", "rift_safety", "zeph_trustworthiness"
    polarity: float  # -1.0 (hostile) to +1.0 (favorable)
    confidence: float  # 0.0 to 1.0
    source: str  # "rumor", "event", "agent_interaction", "direct_experience"
    last_updated_turn: int
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "topic": self.topic,
            "polarity": self.polarity,
            "confidence": self.confidence,
            "source": self.source,
            "last_updated_turn": self.last_updated_turn
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Belief":
        """Deserialize from dictionary."""
        return cls(
            topic=data["topic"],
            polarity=data["polarity"],
            confidence=data["confidence"],
            source=data["source"],
            last_updated_turn=data["last_updated_turn"]
        )


class BeliefSystem:
    """Manages agent beliefs and belief propagation."""
    
    def __init__(self, seed: int = 42):
        """Initialize belief system."""
        self.seed = seed
        random.seed(seed)
        self.belief_decay_rate = 0.01  # Confidence decays by this per turn
        self.belief_spread_probability = 0.15  # Probability of spreading belief during interaction
    
    def create_belief_from_rumor(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from a rumor (lower confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(0.3, 0.6),  # Rumors have lower confidence
            source="rumor",
            last_updated_turn=turn
        )
    
    def create_belief_from_event(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from an event (higher confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(0.6, 0.9),  # Events have higher confidence
            source="event",
            last_updated_turn=turn
        )
    
    def create_belief_from_interaction(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from agent interaction (medium confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(0.4, 0.7),
            source="agent_interaction",
            last_updated_turn=turn
        )
    
    def create_belief_from_experience(self, topic: str, polarity: float, turn: int) -> Belief:
        """Create a belief from direct experience (highest confidence)."""
        return Belief(
            topic=topic,
            polarity=polarity,
            confidence=random.uniform(0.7, 1.0),  # Direct experience is most confident
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
            belief.confidence = min(1.0, total_confidence * 0.9)  # Slight decay on merge
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
                source_belief.confidence * 0.7,  # Spread beliefs have reduced confidence
                "agent_interaction",
                turn
            )
        else:
            # Create new belief
            target_beliefs[topic] = Belief(
                topic=topic,
                polarity=source_belief.polarity,
                confidence=source_belief.confidence * 0.7,  # Reduced confidence when spread
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
        return (safety_belief * 0.6 + food_belief * 0.4)
    
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
            return 1.0 + abs(trust_belief) * 0.5  # Up to 1.5x conflict
        else:
            return 1.0 - trust_belief * 0.3  # Down to 0.7x conflict (less likely)
    
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
            return 1.0 + trust_belief * 0.5  # Up to 1.5x cooperation
        else:
            return 1.0 - abs(trust_belief) * 0.3  # Down to 0.7x cooperation
