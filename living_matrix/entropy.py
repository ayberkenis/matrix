"""Entropy/Glitch system: controlled randomness and anomalies."""

import random
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AnomalyType(Enum):
    """Types of anomalies/glitches."""
    SUDDEN_RUMOR = "sudden_rumor"
    UNEXPECTED_ALLIANCE = "unexpected_alliance"
    SYSTEM_FAILURE = "system_failure"
    UNEXPLAINED_DISAPPEARANCE = "unexplained_disappearance"
    RANDOM_EVENT = "random_event"
    MEMORY_GLITCH = "memory_glitch"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    CAUSAL_BREAK = "causal_break"


@dataclass
class Anomaly:
    """An anomaly/glitch event."""
    anomaly_type: AnomalyType
    description: str
    turn: int
    severity: float = 0.5  # 0.0-1.0
    duration: int = 1  # Turns
    effects: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'type': self.anomaly_type.value,
            'description': self.description,
            'turn': self.turn,
            'severity': self.severity,
            'duration': self.duration,
            'effects': self.effects,
            'timestamp': self.timestamp
        }


class EntropySystem:
    """
    Manages entropy/glitch system for controlled randomness.
    Low probability, small direct effects, potentially large cascading consequences.
    """
    
    def __init__(self, base_entropy_rate: float = 0.001, seed: int = 42):
        """
        Initialize entropy system.
        
        Args:
            base_entropy_rate: Base probability of anomaly per turn (0.0-1.0)
            seed: Random seed
        """
        self.base_entropy_rate = base_entropy_rate
        self.current_entropy_rate = base_entropy_rate
        self.anomalies: List[Anomaly] = []
        self.max_anomalies = 100
        random.seed(seed)
    
    def check_anomaly(self, turn: int, context: Optional[Dict] = None) -> Optional[Anomaly]:
        """
        Check if an anomaly should occur this turn.
        
        Args:
            turn: Current turn
            context: Current world context (optional)
            
        Returns:
            Anomaly if one occurs, None otherwise
        """
        if random.random() < self.current_entropy_rate:
            return self._generate_anomaly(turn, context)
        return None
    
    def _generate_anomaly(self, turn: int, context: Optional[Dict] = None) -> Anomaly:
        """
        Generate a random anomaly.
        
        Args:
            turn: Current turn
            context: Current world context
            
        Returns:
            Generated anomaly
        """
        anomaly_type = random.choice(list(AnomalyType))
        severity = random.uniform(0.2, 0.8)
        
        descriptions = {
            AnomalyType.SUDDEN_RUMOR: "A sudden rumor spreads with no clear source",
            AnomalyType.UNEXPECTED_ALLIANCE: "An unexpected alliance forms",
            AnomalyType.SYSTEM_FAILURE: "A system failure occurs",
            AnomalyType.UNEXPLAINED_DISAPPEARANCE: "Someone disappears without explanation",
            AnomalyType.RANDOM_EVENT: "A random event occurs",
            AnomalyType.MEMORY_GLITCH: "A memory glitch causes confusion",
            AnomalyType.TEMPORAL_ANOMALY: "Time seems to skip or repeat",
            AnomalyType.CAUSAL_BREAK: "Cause and effect seem disconnected"
        }
        
        description = descriptions.get(anomaly_type, "An anomaly occurs")
        
        # Determine effects based on type
        effects = self._get_anomaly_effects(anomaly_type, severity, context)
        
        anomaly = Anomaly(
            anomaly_type=anomaly_type,
            description=description,
            turn=turn,
            severity=severity,
            duration=random.randint(1, 3),
            effects=effects
        )
        
        self.anomalies.append(anomaly)
        if len(self.anomalies) > self.max_anomalies:
            self.anomalies = self.anomalies[-self.max_anomalies:]
        
        return anomaly
    
    def _get_anomaly_effects(self, anomaly_type: AnomalyType, 
                             severity: float, context: Optional[Dict]) -> Dict:
        """
        Get effects for an anomaly type.
        
        Args:
            anomaly_type: Type of anomaly
            severity: Severity (0.0-1.0)
            context: Current context
            
        Returns:
            Dictionary of effects
        """
        effects = {}
        
        if anomaly_type == AnomalyType.SUDDEN_RUMOR:
            effects['social_tension'] = severity * 5.0
            effects['trust_decrease'] = severity * 0.1
        elif anomaly_type == AnomalyType.UNEXPECTED_ALLIANCE:
            effects['cooperation_increase'] = severity * 0.15
            effects['political_tension'] = severity * 3.0
        elif anomaly_type == AnomalyType.SYSTEM_FAILURE:
            effects['economic_tension'] = severity * 8.0
            effects['existential_tension'] = severity * 5.0
        elif anomaly_type == AnomalyType.UNEXPLAINED_DISAPPEARANCE:
            effects['fear'] = severity * 0.2
            effects['social_tension'] = severity * 6.0
            effects['existential_tension'] = severity * 8.0
        elif anomaly_type == AnomalyType.RANDOM_EVENT:
            # Random small effects
            effects['random_effect'] = random.uniform(-severity * 5.0, severity * 5.0)
        elif anomaly_type == AnomalyType.MEMORY_GLITCH:
            effects['confusion'] = severity * 0.1
            effects['trust_decrease'] = severity * 0.05
        elif anomaly_type == AnomalyType.TEMPORAL_ANOMALY:
            effects['existential_tension'] = severity * 10.0
            effects['confusion'] = severity * 0.15
        elif anomaly_type == AnomalyType.CAUSAL_BREAK:
            effects['existential_tension'] = severity * 12.0
            effects['fear'] = severity * 0.25
        
        return effects
    
    def adjust_entropy_rate(self, factor: float):
        """
        Adjust entropy rate (e.g., during high tension).
        
        Args:
            factor: Multiplier for entropy rate (e.g., 2.0 = double)
        """
        self.current_entropy_rate = min(0.1, self.base_entropy_rate * factor)
    
    def reset_entropy_rate(self):
        """Reset entropy rate to base."""
        self.current_entropy_rate = self.base_entropy_rate
    
    def get_recent_anomalies(self, limit: int = 20) -> List[Anomaly]:
        """Get recent anomalies."""
        return self.anomalies[-limit:]
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'base_entropy_rate': self.base_entropy_rate,
            'current_entropy_rate': self.current_entropy_rate,
            'anomalies': [a.to_dict() for a in self.anomalies]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EntropySystem":
        """Deserialize from dictionary."""
        system = cls(
            base_entropy_rate=data.get('base_entropy_rate', 0.001),
            seed=42
        )
        system.current_entropy_rate = data.get('current_entropy_rate', system.base_entropy_rate)
        
        for a_data in data.get('anomalies', []):
            anomaly = Anomaly(
                anomaly_type=AnomalyType(a_data['type']),
                description=a_data['description'],
                turn=a_data['turn'],
                severity=a_data['severity'],
                duration=a_data['duration'],
                effects=a_data['effects'],
                timestamp=a_data.get('timestamp', datetime.utcnow().isoformat())
            )
            system.anomalies.append(anomaly)
        
        return system
