"""Causal memory: tracking cause-effect relationships."""

import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


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


class CausalitySystem:
    """
    Tracks cause-effect relationships and allows querying for patterns.
    """
    
    def __init__(self, max_records: int = 500):
        """
        Initialize causality system.
        
        Args:
            max_records: Maximum number of records to keep
        """
        self.records: deque = deque(maxlen=max_records)
        self.decay_rate = 0.001  # Per turn decay
    
    def record(self, cause: str, effect: str, source: str, 
               confidence: float = 0.5, duration: int = 1, turn: int = 0):
        """
        Record a cause-effect relationship.
        
        Args:
            cause: What caused the effect
            effect: What happened
            source: Where it came from (agent_id, district_id, 'world')
            confidence: Initial confidence (0.0-1.0)
            duration: How long the effect lasted
            turn: Current turn
        """
        record = CausalRecord(
            cause=cause,
            effect=effect,
            confidence=confidence,
            duration=duration,
            source=source,
            turn=turn
        )
        self.records.append(record)
    
    def find_patterns(self, cause: str, min_confidence: float = 0.3) -> List[CausalRecord]:
        """
        Find all records where this cause appeared.
        
        Args:
            cause: The cause to search for
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching causal records
        """
        matches = [
            r for r in self.records
            if r.cause == cause and r.confidence >= min_confidence
        ]
        # Sort by confidence descending
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
    
    def predict_effect(self, cause: str, min_confidence: float = 0.3) -> Optional[str]:
        """
        Predict what effect a cause might have, based on history.
        
        Args:
            cause: The cause to predict for
            min_confidence: Minimum confidence threshold
            
        Returns:
            Most likely effect, or None if no pattern found
        """
        patterns = self.find_patterns(cause, min_confidence)
        if not patterns:
            return None
        
        # Find most common effect
        effect_counts: Dict[str, float] = {}
        for pattern in patterns:
            effect = pattern.effect
            # Weight by confidence
            effect_counts[effect] = effect_counts.get(effect, 0.0) + pattern.confidence
        
        if effect_counts:
            return max(effect_counts.items(), key=lambda x: x[1])[0]
        return None
    
    def strengthen_pattern(self, cause: str, effect: str, amount: float = 0.1):
        """
        Strengthen confidence of matching patterns (learning).
        
        Args:
            cause: The cause
            effect: The effect
            amount: How much to increase confidence
        """
        for record in self.records:
            if record.cause == cause and record.effect == effect:
                record.confidence = min(1.0, record.confidence + amount)
    
    def weaken_pattern(self, cause: str, effect: str, amount: float = 0.1):
        """
        Weaken confidence of matching patterns (unlearning).
        
        Args:
            cause: The cause
            effect: The effect
            amount: How much to decrease confidence
        """
        for record in self.records:
            if record.cause == cause and record.effect == effect:
                record.confidence = max(0.0, record.confidence - amount)
    
    def decay_all(self):
        """Decay all records (called each turn)."""
        for record in self.records:
            record.decay(self.decay_rate)
        
        # Remove records with very low confidence
        self.records = deque(
            [r for r in self.records if r.confidence > 0.05],
            maxlen=self.records.maxlen
        )
    
    def get_recent(self, limit: int = 50) -> List[CausalRecord]:
        """Get recent causal records."""
        return list(self.records)[-limit:]
    
    def get_by_source(self, source: str, limit: int = 50) -> List[CausalRecord]:
        """Get records from a specific source."""
        matches = [r for r in self.records if r.source == source]
        return matches[-limit:]
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'records': [r.to_dict() for r in self.records],
            'decay_rate': self.decay_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CausalitySystem":
        """Deserialize from dictionary."""
        system = cls(max_records=len(data.get('records', [])) + 100)
        system.decay_rate = data.get('decay_rate', 0.001)
        
        for r_data in data.get('records', []):
            record = CausalRecord.from_dict(r_data)
            system.records.append(record)
        
        return system
