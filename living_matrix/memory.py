"""Episodic, semantic, emotional memory, and learned rules management."""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from collections import deque

from .dataclasses import Episode, SemanticGraph, EmotionalTrace, LearnedRule
from .constants.memory_constants import (
    DEFAULT_MAX_EPISODES, DEFAULT_RECENT_EPISODES,
    DEFAULT_MAX_TRACES, DEFAULT_DECAY_RATE, DEFAULT_EMOTIONAL_TRACE_DECAY_RATE,
    DEFAULT_EMOTION_SUMMARY_LIMIT, DEFAULT_MAX_RULES, DEFAULT_INITIAL_CONFIDENCE,
    DEFAULT_CONFIDENCE_INCREASE, DEFAULT_CONFIDENCE_DECREASE, DEFAULT_MIN_CONFIDENCE,
    DEFAULT_RULE_CLEANUP_AGE, DEFAULT_TOKEN_WEIGHT, DEFAULT_EDGE_WEIGHT,
    DEFAULT_TOP_K_NEIGHBORS, DEFAULT_CLUSTER_DEPTH, DEFAULT_CLUSTER_TOP_K
)

# Dataclasses are now imported from living_matrix.dataclasses
# Episode, SemanticGraph, EmotionalTrace, LearnedRule are imported above
# SemanticGraph is a dataclass with methods, so it stays as imported


class EpisodicMemory:
    """Rolling log of episodic memories."""
    
    def __init__(self, max_episodes: int = DEFAULT_MAX_EPISODES):
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
    
    def get_recent(self, n: int = DEFAULT_RECENT_EPISODES) -> List[Episode]:
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


# EmotionalTrace is now imported from dataclasses
# The class definition with methods is in dataclasses/memory_dataclasses.py


class EmotionalMemory:
    """Stores emotional traces attached to events."""
    
    def __init__(self, max_traces: int = DEFAULT_MAX_TRACES):
        """Initialize emotional memory."""
        self.traces: deque = deque(maxlen=max_traces)
        self.decay_rate = DEFAULT_DECAY_RATE  # Per turn decay
    
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
            trace.decay(DEFAULT_EMOTIONAL_TRACE_DECAY_RATE)
    
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
        
        recent = self.get_recent(limit=DEFAULT_EMOTION_SUMMARY_LIMIT)  # Last N traces
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


# LearnedRule is now imported from dataclasses
# The class definition with methods is in dataclasses/memory_dataclasses.py


class LearnedRulesSystem:
    """
    System that learns rules dynamically from repeated causal patterns.
    """
    
    def __init__(self, max_rules: int = DEFAULT_MAX_RULES):
        """Initialize learned rules system."""
        self.rules: List[LearnedRule] = []
        self.max_rules = max_rules
    
    def learn_rule(self, condition: str, effect: str, turn: int, 
                   initial_confidence: float = DEFAULT_INITIAL_CONFIDENCE) -> LearnedRule:
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
                rule.update_confidence(matched=True, 
                                     confidence_increase=DEFAULT_CONFIDENCE_INCREASE,
                                     confidence_decrease=DEFAULT_CONFIDENCE_DECREASE)
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
        rule.update_confidence(matched=True,
                               confidence_increase=DEFAULT_CONFIDENCE_INCREASE,
                               confidence_decrease=DEFAULT_CONFIDENCE_DECREASE)
        
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
                rule.update_confidence(matched,
                                     confidence_increase=DEFAULT_CONFIDENCE_INCREASE,
                                     confidence_decrease=DEFAULT_CONFIDENCE_DECREASE)
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
    
    def cleanup(self, turn: int, min_confidence: float = DEFAULT_MIN_CONFIDENCE):
        """
        Remove rules with low confidence or that haven't matched recently.
        
        Args:
            turn: Current turn
            min_confidence: Minimum confidence to keep
        """
        self.rules = [
            r for r in self.rules
            if not r.should_remove(min_confidence) and (turn - r.last_matched) < DEFAULT_RULE_CLEANUP_AGE
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
