"""Memory-related dataclasses."""

from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Episode:
    """A single episodic memory entry."""
    turn: int
    timestamp: str
    user_input: str
    system_output: str
    notable: bool = False  # Marked as notable event


@dataclass
class SemanticGraph:
    """Semantic memory: weighted graph of tokens and relationships."""
    nodes: Dict[str, float] = field(default_factory=dict)  # token -> weight
    edges: Dict[str, Dict[str, float]] = field(default_factory=dict)  # token -> {neighbor -> weight}
    
    def add_token(self, token: str, weight: float = 1.0):
        """Add or update a token node."""
        self.nodes[token] = self.nodes.get(token, 0.0) + weight
    
    def add_edge(self, token1: str, token2: str, weight: float = 1.0):
        """Add or update an edge between two tokens."""
        if token1 not in self.edges:
            self.edges[token1] = {}
        self.edges[token1][token2] = self.edges[token1].get(token2, 0.0) + weight
    
    def get_neighbors(self, token: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get top neighbors of a token by edge weight."""
        if token not in self.edges:
            return []
        neighbors = list(self.edges[token].items())
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[:top_k]
    
    def get_cluster(self, token: str, depth: int = 2, top_k: int = 20) -> List[str]:
        """Get a cluster of related tokens via breadth-first traversal."""
        visited = set()
        cluster = []
        queue = [(token, 0)]
        visited.add(token)
        
        while queue and len(cluster) < top_k:
            current, current_depth = queue.pop(0)
            if current_depth < depth:
                if current in self.edges:
                    neighbors = self.get_neighbors(current, top_k=top_k)
                    for neighbor, weight in neighbors:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            cluster.append(neighbor)
                            queue.append((neighbor, current_depth + 1))
        
        return cluster
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "nodes": self.nodes,
            "edges": self.edges
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SemanticGraph":
        """Deserialize from dictionary."""
        graph = cls()
        graph.nodes = data.get("nodes", {})
        graph.edges = data.get("edges", {})
        return graph


@dataclass
class EmotionalTrace:
    """Emotional memory attached to events."""
    event: str                    # Event description
    turn: int                     # When it happened
    timestamp: str                # ISO timestamp
    fear: float = 0.0            # -1.0 to 1.0
    anger: float = 0.0
    hope: float = 0.0
    joy: float = 0.0
    sadness: float = 0.0
    surprise: float = 0.0
    
    def decay(self, rate: float = 0.01):
        """Decay emotional intensity over time."""
        self.fear *= (1.0 - rate)
        self.anger *= (1.0 - rate)
        self.hope *= (1.0 - rate)
        self.joy *= (1.0 - rate)
        self.sadness *= (1.0 - rate)
        self.surprise *= (1.0 - rate)
    
    def get_dominant_emotion(self) -> str:
        """Get the dominant emotion."""
        emotions = {
            'fear': abs(self.fear),
            'anger': abs(self.anger),
            'hope': abs(self.hope),
            'joy': abs(self.joy),
            'sadness': abs(self.sadness),
            'surprise': abs(self.surprise)
        }
        return max(emotions.items(), key=lambda x: x[1])[0] if emotions else 'neutral'
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'event': self.event,
            'turn': self.turn,
            'timestamp': self.timestamp,
            'fear': self.fear,
            'anger': self.anger,
            'hope': self.hope,
            'joy': self.joy,
            'sadness': self.sadness,
            'surprise': self.surprise,
            'dominant': self.get_dominant_emotion()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionalTrace":
        """Deserialize from dictionary."""
        return cls(
            event=data['event'],
            turn=data['turn'],
            timestamp=data.get('timestamp', datetime.utcnow().isoformat()),
            fear=data.get('fear', 0.0),
            anger=data.get('anger', 0.0),
            hope=data.get('hope', 0.0),
            joy=data.get('joy', 0.0),
            sadness=data.get('sadness', 0.0),
            surprise=data.get('surprise', 0.0)
        )


@dataclass
class LearnedRule:
    """
    A learned rule from repeated causal patterns.
    Format: IF condition THEN effect
    """
    condition: str                # e.g., "food < 5 AND weather == 'rain'"
    effect: str                   # e.g., "social_tension += 0.3"
    confidence: float              # 0.0-1.0, how confident in this rule
    matches: int = 0              # How many times it matched
    failures: int = 0             # How many times it failed
    turn_created: int = 0          # When it was learned
    last_matched: int = 0         # Last turn it matched
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'condition': self.condition,
            'effect': self.effect,
            'confidence': self.confidence,
            'matches': self.matches,
            'failures': self.failures,
            'turn_created': self.turn_created,
            'last_matched': self.last_matched,
            'success_rate': self.get_success_rate()
        }
    
    def update_confidence(self, matched: bool, confidence_increase: float = 0.01, confidence_decrease: float = 0.02):
        """Update confidence based on whether it matched."""
        if matched:
            self.matches += 1
            # Increase confidence slightly
            self.confidence = min(1.0, self.confidence + confidence_increase)
        else:
            self.failures += 1
            # Decrease confidence
            self.confidence = max(0.0, self.confidence - confidence_decrease)
    
    def get_success_rate(self) -> float:
        """Get success rate (matches / total attempts)."""
        total = self.matches + self.failures
        return self.matches / total if total > 0 else 0.0
    
    def should_remove(self, min_confidence: float = 0.1) -> bool:
        """Check if rule should be removed (too low confidence)."""
        return self.confidence < min_confidence
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LearnedRule":
        """Deserialize from dictionary."""
        return cls(
            condition=data['condition'],
            effect=data['effect'],
            confidence=data['confidence'],
            matches=data.get('matches', 0),
            failures=data.get('failures', 0),
            turn_created=data.get('turn_created', 0),
            last_matched=data.get('last_matched', 0)
        )


# Note: EmotionalMemory and EpisodicMemory are classes, not dataclasses, so they stay in memory.py
