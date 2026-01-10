"""Episodic, semantic, emotional memory, and learned rules management."""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from collections import deque


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


class EpisodicMemory:
    """Rolling log of episodic memories."""
    
    def __init__(self, max_episodes: int = 1000):
        self.episodes: List[Episode] = []
        self.max_episodes = max_episodes
    
    def add(self, turn: int, user_input: str, system_output: str, notable: bool = False):
        """Add a new episode."""
        episode = Episode(
            turn=turn,
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            system_output=system_output,
            notable=notable
        )
        self.episodes.append(episode)
        
        # Trim if over limit
        if len(self.episodes) > self.max_episodes:
            self.episodes = self.episodes[-self.max_episodes:]
    
    def get_recent(self, n: int = 10) -> List[Episode]:
        """Get the most recent N episodes."""
        return self.episodes[-n:] if len(self.episodes) > n else self.episodes
    
    def get_notable(self) -> List[Episode]:
        """Get all notable episodes."""
        return [e for e in self.episodes if e.notable]
    
    def search(self, query: str) -> List[Episode]:
        """Search episodes by text content (simple substring match)."""
        query_lower = query.lower()
        return [
            e for e in self.episodes
            if query_lower in e.user_input.lower() or query_lower in e.system_output.lower()
        ]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "episodes": [
                {
                    "turn": e.turn,
                    "timestamp": e.timestamp,
                    "user_input": e.user_input,
                    "system_output": e.system_output,
                    "notable": e.notable
                }
                for e in self.episodes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EpisodicMemory":
        """Deserialize from dictionary."""
        memory = cls()
        for ep_data in data.get("episodes", []):
            episode = Episode(
                turn=ep_data["turn"],
                timestamp=ep_data["timestamp"],
                user_input=ep_data["user_input"],
                system_output=ep_data["system_output"],
                notable=ep_data.get("notable", False)
            )
            memory.episodes.append(episode)
        return memory


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


class EmotionalMemory:
    """Stores emotional traces attached to events."""
    
    def __init__(self, max_traces: int = 200):
        """Initialize emotional memory."""
        self.traces: deque = deque(maxlen=max_traces)
        self.decay_rate = 0.005  # Per turn decay
    
    def add(self, event: str, turn: int, fear: float = 0.0, anger: float = 0.0,
            hope: float = 0.0, joy: float = 0.0, sadness: float = 0.0, 
            surprise: float = 0.0):
        """Add an emotional trace."""
        trace = EmotionalTrace(
            event=event,
            turn=turn,
            timestamp=datetime.utcnow().isoformat(),
            fear=fear,
            anger=anger,
            hope=hope,
            joy=joy,
            sadness=sadness,
            surprise=surprise
        )
        self.traces.append(trace)
    
    def decay_all(self):
        """Decay all traces (called each turn)."""
        for trace in self.traces:
            trace.decay(self.decay_rate)
    
    def get_recent(self, limit: int = 20) -> List[EmotionalTrace]:
        """Get recent emotional traces."""
        return list(self.traces)[-limit:]
    
    def get_emotion_summary(self) -> Dict[str, float]:
        """Get average emotional state across all traces."""
        if not self.traces:
            return {
                'fear': 0.0, 'anger': 0.0, 'hope': 0.0,
                'joy': 0.0, 'sadness': 0.0, 'surprise': 0.0
            }
        
        recent = self.get_recent(limit=50)  # Last 50 traces
        return {
            'fear': sum(t.fear for t in recent) / len(recent),
            'anger': sum(t.anger for t in recent) / len(recent),
            'hope': sum(t.hope for t in recent) / len(recent),
            'joy': sum(t.joy for t in recent) / len(recent),
            'sadness': sum(t.sadness for t in recent) / len(recent),
            'surprise': sum(t.surprise for t in recent) / len(recent)
        }
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'traces': [t.to_dict() for t in self.traces],
            'summary': self.get_emotion_summary()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionalMemory":
        """Deserialize from dictionary."""
        memory = cls(max_traces=len(data.get('traces', [])) + 100)
        for t_data in data.get('traces', []):
            trace = EmotionalTrace.from_dict(t_data)
            memory.traces.append(trace)
        return memory


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
    
    def update_confidence(self, matched: bool):
        """Update confidence based on whether it matched."""
        if matched:
            self.matches += 1
            # Increase confidence slightly
            self.confidence = min(1.0, self.confidence + 0.01)
        else:
            self.failures += 1
            # Decrease confidence
            self.confidence = max(0.0, self.confidence - 0.02)
    
    def get_success_rate(self) -> float:
        """Get success rate (matches / total attempts)."""
        total = self.matches + self.failures
        return self.matches / total if total > 0 else 0.0
    
    def should_remove(self, min_confidence: float = 0.1) -> bool:
        """Check if rule should be removed (too low confidence)."""
        return self.confidence < min_confidence
    
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


class LearnedRulesSystem:
    """
    System that learns rules dynamically from repeated causal patterns.
    """
    
    def __init__(self, max_rules: int = 100):
        """Initialize learned rules system."""
        self.rules: List[LearnedRule] = []
        self.max_rules = max_rules
    
    def learn_rule(self, condition: str, effect: str, turn: int, 
                   initial_confidence: float = 0.3) -> LearnedRule:
        """
        Learn a new rule or strengthen existing one.
        
        Args:
            condition: The condition (e.g., "food < 5")
            effect: The effect (e.g., "social_tension += 0.3")
            turn: Current turn
            initial_confidence: Initial confidence
            
        Returns:
            The learned rule
        """
        # Check if rule already exists
        for rule in self.rules:
            if rule.condition == condition and rule.effect == effect:
                rule.update_confidence(matched=True)
                rule.last_matched = turn
                return rule
        
        # Create new rule
        rule = LearnedRule(
            condition=condition,
            effect=effect,
            confidence=initial_confidence,
            turn_created=turn,
            last_matched=turn
        )
        rule.update_confidence(matched=True)
        
        # Add rule
        self.rules.append(rule)
        
        # Trim if over limit (remove lowest confidence)
        if len(self.rules) > self.max_rules:
            self.rules.sort(key=lambda r: r.confidence, reverse=True)
            self.rules = self.rules[:self.max_rules]
        
        return rule
    
    def test_rule(self, condition: str, effect: str, matched: bool, turn: int):
        """
        Test a rule and update its confidence.
        
        Args:
            condition: The condition
            effect: The effect
            matched: Whether the rule matched reality
            turn: Current turn
        """
        for rule in self.rules:
            if rule.condition == condition and rule.effect == effect:
                rule.update_confidence(matched)
                if matched:
                    rule.last_matched = turn
                return
    
    def get_applicable_rules(self, context: Dict, min_confidence: float = 0.3) -> List[LearnedRule]:
        """
        Get rules that might apply to current context.
        This is a simplified version - in a full implementation,
        you'd parse and evaluate the condition string.
        
        Args:
            context: Current world context (food, weather, etc.)
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of applicable rules
        """
        applicable = []
        for rule in self.rules:
            if rule.confidence >= min_confidence:
                # Simple keyword matching (full implementation would parse condition)
                # Check if condition keywords match context
                condition_lower = rule.condition.lower()
                if any(key in condition_lower for key in context.keys()):
                    applicable.append(rule)
        
        return applicable
    
    def cleanup(self, turn: int, min_confidence: float = 0.1):
        """
        Remove rules with low confidence or that haven't matched recently.
        
        Args:
            turn: Current turn
            min_confidence: Minimum confidence to keep
        """
        self.rules = [
            r for r in self.rules
            if not r.should_remove(min_confidence) and (turn - r.last_matched) < 1000
        ]
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'rules': [r.to_dict() for r in self.rules]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LearnedRulesSystem":
        """Deserialize from dictionary."""
        system = cls(max_rules=len(data.get('rules', [])) + 50)
        for r_data in data.get('rules', []):
            rule = LearnedRule.from_dict(r_data)
            system.rules.append(rule)
        return system
