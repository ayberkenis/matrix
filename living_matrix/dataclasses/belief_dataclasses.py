"""Belief-related dataclasses."""

from dataclasses import dataclass


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
