"""Agent relationship graph: weighted social network."""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import random


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
        if interaction_type in ['cooperation', 'help', 'trade', 'aid']:
            self.trust = min(1.0, self.trust + strength * 0.1)
            self.dependency = min(1.0, self.dependency + strength * 0.05)
            self.conflict = max(0.0, self.conflict - strength * 0.05)
        elif interaction_type in ['conflict', 'fight', 'theft', 'betrayal']:
            self.conflict = min(1.0, self.conflict + strength * 0.2)
            self.trust = max(0.0, self.trust - strength * 0.15)
            self.dependency = max(0.0, self.dependency - strength * 0.1)
        elif interaction_type in ['trade', 'exchange']:
            self.trust = min(1.0, self.trust + strength * 0.05)
            self.dependency = min(1.0, self.dependency + strength * 0.1)
        elif interaction_type in ['rumor', 'gossip']:
            self.trust = max(0.0, self.trust - strength * 0.05)
            self.conflict = min(1.0, self.conflict + strength * 0.05)
        
        self.normalize()
    
    def drift(self, rate: float = 0.01):
        """Slow drift over time (relationships fade if not maintained)."""
        self.trust = max(0.0, self.trust - rate * 0.5)
        self.dependency = max(0.0, self.dependency - rate * 0.3)
        self.conflict = max(0.0, self.conflict - rate * 0.2)
    
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


class RelationshipGraph:
    """
    Weighted social graph between agents.
    relations[A][B] = RelationshipData
    """
    
    def __init__(self):
        """Initialize relationship graph."""
        self.relations: Dict[str, Dict[str, RelationshipData]] = {}
        self.drift_rate = 0.001  # Per turn drift
    
    def get(self, agent_a: str, agent_b: str) -> RelationshipData:
        """
        Get relationship between two agents.
        Creates if doesn't exist.
        """
        if agent_a not in self.relations:
            self.relations[agent_a] = {}
        if agent_b not in self.relations[agent_a]:
            # Initialize with random values
            self.relations[agent_a][agent_b] = RelationshipData(
                trust=random.uniform(0.3, 0.7),
                conflict=random.uniform(0.0, 0.2),
                dependency=random.uniform(0.0, 0.3)
            )
        return self.relations[agent_a][agent_b]
    
    def record_interaction(self, agent_a: str, agent_b: str, 
                          interaction_type: str, strength: float = 0.1):
        """
        Record an interaction between two agents.
        
        Args:
            agent_a: First agent ID
            agent_b: Second agent ID
            interaction_type: Type of interaction
            strength: Strength of interaction
        """
        # Update both directions (symmetric)
        rel_ab = self.get(agent_a, agent_b)
        rel_ba = self.get(agent_b, agent_a)
        
        rel_ab.evolve(interaction_type, strength)
        rel_ba.evolve(interaction_type, strength)
    
    def get_allies(self, agent_id: str, min_trust: float = 0.6) -> List[Tuple[str, float]]:
        """
        Get agents this agent trusts (allies).
        
        Args:
            agent_id: Agent ID
            min_trust: Minimum trust threshold
            
        Returns:
            List of (agent_id, trust_score) tuples
        """
        if agent_id not in self.relations:
            return []
        
        allies = []
        for other_id, rel_data in self.relations[agent_id].items():
            if rel_data.trust >= min_trust and rel_data.conflict < 0.3:
                allies.append((other_id, rel_data.trust))
        
        allies.sort(key=lambda x: x[1], reverse=True)
        return allies
    
    def get_enemies(self, agent_id: str, min_conflict: float = 0.5) -> List[Tuple[str, float]]:
        """
        Get agents this agent has conflict with (enemies).
        
        Args:
            agent_id: Agent ID
            min_conflict: Minimum conflict threshold
            
        Returns:
            List of (agent_id, conflict_score) tuples
        """
        if agent_id not in self.relations:
            return []
        
        enemies = []
        for other_id, rel_data in self.relations[agent_id].items():
            if rel_data.conflict >= min_conflict:
                enemies.append((other_id, rel_data.conflict))
        
        enemies.sort(key=lambda x: x[1], reverse=True)
        return enemies
    
    def get_dependents(self, agent_id: str, min_dependency: float = 0.4) -> List[Tuple[str, float]]:
        """
        Get agents this agent depends on.
        
        Args:
            agent_id: Agent ID
            min_dependency: Minimum dependency threshold
            
        Returns:
            List of (agent_id, dependency_score) tuples
        """
        if agent_id not in self.relations:
            return []
        
        dependents = []
        for other_id, rel_data in self.relations[agent_id].items():
            if rel_data.dependency >= min_dependency:
                dependents.append((other_id, rel_data.dependency))
        
        dependents.sort(key=lambda x: x[1], reverse=True)
        return dependents
    
    def should_cooperate(self, agent_a: str, agent_b: str) -> bool:
        """Check if two agents should cooperate based on relationship."""
        rel = self.get(agent_a, agent_b)
        return rel.trust > 0.5 and rel.conflict < 0.3
    
    def should_conflict(self, agent_a: str, agent_b: str) -> bool:
        """Check if two agents should conflict based on relationship."""
        rel = self.get(agent_a, agent_b)
        return rel.conflict > 0.6 or (rel.trust < 0.3 and rel.conflict > 0.3)
    
    def drift_all(self):
        """Drift all relationships (called each turn)."""
        for agent_a in self.relations:
            for agent_b in self.relations[agent_a]:
                self.relations[agent_a][agent_b].drift(self.drift_rate)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'relations': {
                agent_a: {
                    agent_b: rel_data.to_dict()
                    for agent_b, rel_data in rels.items()
                }
                for agent_a, rels in self.relations.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RelationshipGraph":
        """Deserialize from dictionary."""
        graph = cls()
        for agent_a, rels in data.get('relations', {}).items():
            graph.relations[agent_a] = {}
            for agent_b, rel_data_dict in rels.items():
                graph.relations[agent_a][agent_b] = RelationshipData.from_dict(rel_data_dict)
        return graph
