"""Causality-related dataclasses."""

from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime


@dataclass
class CausalRecord:
    """
    A record of a cause-effect relationship.
    """
    cause: str                    # What caused it
    effect: str                   # What happened
    confidence: float              # 0.0-1.0, how confident we are in this relationship
    duration: int                 # How long the effect lasted (turns)
    source: str                   # agent / district / world
    turn: int                     # When it was recorded
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def decay(self, decay_rate: float = 0.01):
        """Decay confidence over time."""
        self.confidence = max(0.0, self.confidence - decay_rate)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'cause': self.cause,
            'effect': self.effect,
            'confidence': self.confidence,
            'duration': self.duration,
            'source': self.source,
            'turn': self.turn,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CausalRecord":
        """Deserialize from dictionary."""
        return cls(
            cause=data['cause'],
            effect=data['effect'],
            confidence=data['confidence'],
            duration=data['duration'],
            source=data['source'],
            turn=data['turn'],
            timestamp=data.get('timestamp', datetime.utcnow().isoformat())
        )
