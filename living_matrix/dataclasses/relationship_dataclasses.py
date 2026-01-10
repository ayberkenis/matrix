"""Relationship-related dataclasses."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Relationship:
    """Enhanced relationship between agents with affection, trust, and familiarity."""
    target_id: str
    affection: float = 0.0  # -1.0 (hate) to +1.0 (love)
    trust: float = 0.5  # 0.0 to 1.0
    familiarity: float = 0.0  # 0.0 to 1.0, grows with interaction
    last_interaction: int = 0  # Turn of last interaction
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "target_id": self.target_id,
            "affection": self.affection,
            "trust": self.trust,
            "familiarity": self.familiarity,
            "last_interaction": self.last_interaction
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        """Deserialize from dictionary."""
        return cls(
            target_id=data["target_id"],
            affection=data.get("affection", 0.0),
            trust=data.get("trust", 0.5),
            familiarity=data.get("familiarity", 0.0),
            last_interaction=data.get("last_interaction", 0)
        )
    
    def normalize(self):
        """Ensure values are in valid ranges."""
        self.affection = max(-1.0, min(1.0, self.affection))
        self.trust = max(0.0, min(1.0, self.trust))
        self.familiarity = max(0.0, min(1.0, self.familiarity))


@dataclass
class RelationshipData:
    """
    Weighted relationship data between two agents.
    """
    trust: float = 0.5          # 0.0-1.0, how much they trust each other
    conflict: float = 0.0       # 0.0-1.0, how much conflict between them
    dependency: float = 0.0     # 0.0-1.0, how much they depend on each other
    
    def normalize(self):
        """Clamp all values to 0-1."""
        self.trust = max(0.0, min(1.0, self.trust))
        self.conflict = max(0.0, min(1.0, self.conflict))
        self.dependency = max(0.0, min(1.0, self.dependency))
    
    def evolve(self, interaction_type: str, strength: float = 0.1):
        """
        Evolve relationship based on interaction.
        
        Args:
            interaction_type: Type of interaction (cooperation, conflict, trade, help, etc.)
            strength: How strong the interaction was (0.0-1.0)
        """
        from living_matrix.constants.relationships_constants import (
            EVOLUTION_COOPERATION_TRUST_INCREASE, EVOLUTION_COOPERATION_DEPENDENCY_INCREASE,
            EVOLUTION_COOPERATION_CONFLICT_DECREASE, EVOLUTION_CONFLICT_CONFLICT_INCREASE,
            EVOLUTION_CONFLICT_TRUST_DECREASE, EVOLUTION_CONFLICT_DEPENDENCY_DECREASE,
            EVOLUTION_TRADE_TRUST_INCREASE, EVOLUTION_TRADE_DEPENDENCY_INCREASE,
            EVOLUTION_RUMOR_TRUST_DECREASE, EVOLUTION_RUMOR_CONFLICT_INCREASE
        )
        
        if interaction_type in ['cooperation', 'help', 'trade', 'aid']:
            self.trust = min(1.0, self.trust + strength * EVOLUTION_COOPERATION_TRUST_INCREASE)
            self.dependency = min(1.0, self.dependency + strength * EVOLUTION_COOPERATION_DEPENDENCY_INCREASE)
            self.conflict = max(0.0, self.conflict - strength * EVOLUTION_COOPERATION_CONFLICT_DECREASE)
        elif interaction_type in ['conflict', 'fight', 'theft', 'betrayal']:
            self.conflict = min(1.0, self.conflict + strength * EVOLUTION_CONFLICT_CONFLICT_INCREASE)
            self.trust = max(0.0, self.trust - strength * EVOLUTION_CONFLICT_TRUST_DECREASE)
            self.dependency = max(0.0, self.dependency - strength * EVOLUTION_CONFLICT_DEPENDENCY_DECREASE)
        elif interaction_type in ['trade', 'exchange']:
            self.trust = min(1.0, self.trust + strength * EVOLUTION_TRADE_TRUST_INCREASE)
            self.dependency = min(1.0, self.dependency + strength * EVOLUTION_TRADE_DEPENDENCY_INCREASE)
        elif interaction_type in ['rumor', 'gossip']:
            self.trust = max(0.0, self.trust - strength * EVOLUTION_RUMOR_TRUST_DECREASE)
            self.conflict = min(1.0, self.conflict + strength * EVOLUTION_RUMOR_CONFLICT_INCREASE)
        
        self.normalize()
    
    def drift(self, rate: float = 0.01):
        """Slow drift over time (relationships fade if not maintained)."""
        from living_matrix.constants.relationships_constants import (
            DRIFT_TRUST_RATE, DRIFT_DEPENDENCY_RATE, DRIFT_CONFLICT_RATE
        )
        
        self.trust = max(0.0, self.trust - rate * DRIFT_TRUST_RATE)
        self.dependency = max(0.0, self.dependency - rate * DRIFT_DEPENDENCY_RATE)
        self.conflict = max(0.0, self.conflict - rate * DRIFT_CONFLICT_RATE)
    
    def get_strength(self) -> float:
        """Get overall relationship strength."""
        return (self.trust + self.dependency) - self.conflict
    
    def to_dict(self) -> Dict[str, float]:
        """Serialize to dictionary."""
        return {
            'trust': self.trust,
            'conflict': self.conflict,
            'dependency': self.dependency,
            'strength': self.get_strength()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RelationshipData":
        """Deserialize from dictionary."""
        return cls(
            trust=data.get('trust', 0.5),
            conflict=data.get('conflict', 0.0),
            dependency=data.get('dependency', 0.0)
        )
