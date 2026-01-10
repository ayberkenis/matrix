"""Intent system: goals and motivations for agents, districts, and world."""

import random
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Intent:
    """
    Intent represents internal goals and motivations.
    Values are 0.0-1.0, representing the strength of each intent.
    """
    survive: float = 0.5      # Basic survival needs
    explore: float = 0.3      # Curiosity, discovery
    cooperate: float = 0.4    # Social cooperation
    dominate: float = 0.2     # Control, power
    escape: float = 0.1       # Desire to leave/change situation
    
    def normalize(self):
        """Normalize intents to sum to reasonable range (optional)."""
        # Keep as-is, but clamp to [0, 1]
        self.survive = max(0.0, min(1.0, self.survive))
        self.explore = max(0.0, min(1.0, self.explore))
        self.cooperate = max(0.0, min(1.0, self.cooperate))
        self.dominate = max(0.0, min(1.0, self.dominate))
        self.escape = max(0.0, min(1.0, self.escape))
    
    def drift(self, rate: float = 0.01):
        """Slow drift over time (random walk)."""
        self.survive += random.uniform(-rate, rate)
        self.explore += random.uniform(-rate, rate)
        self.cooperate += random.uniform(-rate, rate)
        self.dominate += random.uniform(-rate, rate)
        self.escape += random.uniform(-rate, rate)
        self.normalize()
    
    def apply_event(self, event_type: str, severity: float = 1.0):
        """
        Modify intent based on events.
        
        Args:
            event_type: Type of event (food_shortage, conflict, aid, etc.)
            severity: How strong the effect is (0.0-1.0)
        """
        if event_type in ['food_shortage', 'starvation', 'scarcity']:
            self.survive = min(1.0, self.survive + 0.2 * severity)
            self.cooperate = max(0.0, self.cooperate - 0.1 * severity)
        elif event_type in ['conflict', 'violence', 'riot']:
            self.dominate = min(1.0, self.dominate + 0.15 * severity)
            self.survive = min(1.0, self.survive + 0.1 * severity)
            self.cooperate = max(0.0, self.cooperate - 0.2 * severity)
        elif event_type in ['aid', 'cooperation', 'trade_success']:
            self.cooperate = min(1.0, self.cooperate + 0.15 * severity)
            self.survive = max(0.0, self.survive - 0.1 * severity)
        elif event_type in ['extreme_scarcity', 'disaster']:
            self.escape = min(1.0, self.escape + 0.25 * severity)
            self.survive = min(1.0, self.survive + 0.2 * severity)
        elif event_type in ['discovery', 'exploration']:
            self.explore = min(1.0, self.explore + 0.2 * severity)
        elif event_type in ['stability', 'prosperity']:
            self.cooperate = min(1.0, self.cooperate + 0.1 * severity)
            self.explore = min(1.0, self.explore + 0.1 * severity)
            self.escape = max(0.0, self.escape - 0.1 * severity)
        
        self.normalize()
    
    def apply_tension(self, tension_economic: float, tension_social: float, 
                     tension_political: float, tension_existential: float):
        """
        Modify intent based on multi-dimensional tension.
        
        Args:
            tension_*: Tension values (0-100), normalized to 0-1 internally
        """
        # Normalize tensions to 0-1
        econ = tension_economic / 100.0
        social = tension_social / 100.0
        pol = tension_political / 100.0
        exist = tension_existential / 100.0
        
        # Economic tension → survive, escape
        if econ > 0.5:
            self.survive = min(1.0, self.survive + 0.1 * econ)
            if econ > 0.7:
                self.escape = min(1.0, self.escape + 0.15 * econ)
        
        # Social tension → dominate, escape
        if social > 0.5:
            self.dominate = min(1.0, self.dominate + 0.1 * social)
            self.cooperate = max(0.0, self.cooperate - 0.1 * social)
            if social > 0.7:
                self.escape = min(1.0, self.escape + 0.1 * social)
        
        # Political tension → dominate, escape
        if pol > 0.5:
            self.dominate = min(1.0, self.dominate + 0.15 * pol)
            if pol > 0.7:
                self.escape = min(1.0, self.escape + 0.1 * pol)
        
        # Existential tension → escape, explore (searching for meaning)
        if exist > 0.5:
            self.escape = min(1.0, self.escape + 0.2 * exist)
            self.explore = min(1.0, self.explore + 0.1 * exist)
        
        self.normalize()
    
    def apply_pressure(self, food_pressure: float, scarcity: bool, weather_bad: bool):
        """
        Modify intent based on environmental pressure.
        
        Args:
            food_pressure: 0-1, how much food pressure
            scarcity: Boolean, is there scarcity
            weather_bad: Boolean, is weather bad
        """
        if food_pressure > 0.6:
            self.survive = min(1.0, self.survive + 0.15 * food_pressure)
            if scarcity:
                self.escape = min(1.0, self.escape + 0.1)
        
        if weather_bad:
            self.survive = min(1.0, self.survive + 0.1)
            self.explore = max(0.0, self.explore - 0.05)
        
        self.normalize()
    
    def get_dominant(self) -> str:
        """Get the dominant intent."""
        intents = {
            'survive': self.survive,
            'explore': self.explore,
            'cooperate': self.cooperate,
            'dominate': self.dominate,
            'escape': self.escape
        }
        return max(intents.items(), key=lambda x: x[1])[0]
    
    def to_dict(self) -> Dict[str, float]:
        """Serialize to dictionary."""
        return {
            'survive': self.survive,
            'explore': self.explore,
            'cooperate': self.cooperate,
            'dominate': self.dominate,
            'escape': self.escape
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Intent":
        """Deserialize from dictionary."""
        return cls(
            survive=data.get('survive', 0.5),
            explore=data.get('explore', 0.3),
            cooperate=data.get('cooperate', 0.4),
            dominate=data.get('dominate', 0.2),
            escape=data.get('escape', 0.1)
        )
