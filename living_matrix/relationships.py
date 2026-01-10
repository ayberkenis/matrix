"""Agent relationship graph: weighted social network."""

from typing import Dict, Optional, List, Tuple
import random

from .dataclasses import RelationshipData
from .constants.relationships_constants import (
    DEFAULT_TRUST, DEFAULT_CONFLICT, DEFAULT_DEPENDENCY,
    INITIAL_TRUST_MIN, INITIAL_TRUST_MAX,
    INITIAL_CONFLICT_MIN, INITIAL_CONFLICT_MAX,
    INITIAL_DEPENDENCY_MIN, INITIAL_DEPENDENCY_MAX,
    DEFAULT_DRIFT_RATE, EVOLUTION_COOPERATION_TRUST_INCREASE,
    EVOLUTION_COOPERATION_DEPENDENCY_INCREASE, EVOLUTION_COOPERATION_CONFLICT_DECREASE,
    EVOLUTION_CONFLICT_CONFLICT_INCREASE, EVOLUTION_CONFLICT_TRUST_DECREASE,
    EVOLUTION_CONFLICT_DEPENDENCY_DECREASE, EVOLUTION_TRADE_TRUST_INCREASE,
    EVOLUTION_TRADE_DEPENDENCY_INCREASE, EVOLUTION_RUMOR_TRUST_DECREASE,
    EVOLUTION_RUMOR_CONFLICT_INCREASE, DRIFT_TRUST_RATE, DRIFT_DEPENDENCY_RATE,
    DRIFT_CONFLICT_RATE, MIN_TRUST_FOR_ALLIES, MAX_CONFLICT_FOR_ALLIES,
    MIN_CONFLICT_FOR_ENEMIES, MIN_DEPENDENCY_FOR_DEPENDENTS,
    MIN_TRUST_FOR_COOPERATION, MAX_CONFLICT_FOR_COOPERATION,
    MIN_CONFLICT_FOR_CONFLICT, MIN_TRUST_FOR_CONFLICT, MAX_CONFLICT_FOR_CONFLICT
)

# RelationshipData is now imported from dataclasses
# The class definition is in dataclasses/relationship_dataclasses.py


# RelationshipData is now imported from dataclasses
# The class definition with methods is in dataclasses/relationship_dataclasses.py


class RelationshipGraph:
    """
    Weighted social graph between agents.
    relations[A][B] = RelationshipData
    """
    
    def __init__(self):
        """Initialize relationship graph."""
        self.relations: Dict[str, Dict[str, RelationshipData]] = {}
        self.drift_rate = DEFAULT_DRIFT_RATE  # Per turn drift
    
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
                trust=random.uniform(INITIAL_TRUST_MIN, INITIAL_TRUST_MAX),
                conflict=random.uniform(INITIAL_CONFLICT_MIN, INITIAL_CONFLICT_MAX),
                dependency=random.uniform(INITIAL_DEPENDENCY_MIN, INITIAL_DEPENDENCY_MAX)
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
    
    def get_allies(self, agent_id: str, min_trust: float = MIN_TRUST_FOR_ALLIES) -> List[Tuple[str, float]]:
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
            if rel_data.trust >= min_trust and rel_data.conflict < MAX_CONFLICT_FOR_ALLIES:
                allies.append((other_id, rel_data.trust))
        
        allies.sort(key=lambda x: x[1], reverse=True)
        return allies
    
    def get_enemies(self, agent_id: str, min_conflict: float = MIN_CONFLICT_FOR_ENEMIES) -> List[Tuple[str, float]]:
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
    
    def get_dependents(self, agent_id: str, min_dependency: float = MIN_DEPENDENCY_FOR_DEPENDENTS) -> List[Tuple[str, float]]:
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
        return rel.trust > MIN_TRUST_FOR_COOPERATION and rel.conflict < MAX_CONFLICT_FOR_COOPERATION
    
    def should_conflict(self, agent_a: str, agent_b: str) -> bool:
        """Check if two agents should conflict based on relationship."""
        rel = self.get(agent_a, agent_b)
        return rel.conflict > MIN_CONFLICT_FOR_CONFLICT or (rel.trust < MIN_TRUST_FOR_CONFLICT and rel.conflict > MAX_CONFLICT_FOR_CONFLICT)
    
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
