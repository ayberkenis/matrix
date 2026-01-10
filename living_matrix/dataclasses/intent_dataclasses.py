"""Intent-related dataclasses."""

import random
from dataclasses import dataclass
from typing import Dict


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
    
    def __post_init__(self):
        """Import constants after initialization."""
        from living_matrix.constants.intent_constants import (
            DEFAULT_SURVIVE, DEFAULT_EXPLORE, DEFAULT_COOPERATE,
            DEFAULT_DOMINATE, DEFAULT_ESCAPE
        )
        # Set defaults if not provided
        if not hasattr(self, '_defaults_set'):
            self.survive = DEFAULT_SURVIVE if self.survive == 0.5 else self.survive
            self.explore = DEFAULT_EXPLORE if self.explore == 0.3 else self.explore
            self.cooperate = DEFAULT_COOPERATE if self.cooperate == 0.4 else self.cooperate
            self.dominate = DEFAULT_DOMINATE if self.dominate == 0.2 else self.dominate
            self.escape = DEFAULT_ESCAPE if self.escape == 0.1 else self.escape
            self._defaults_set = True
    
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
        from living_matrix.constants.intent_constants import DEFAULT_DRIFT_RATE
        drift_rate = rate if rate != 0.01 else DEFAULT_DRIFT_RATE
        self.survive += random.uniform(-drift_rate, drift_rate)
        self.explore += random.uniform(-drift_rate, drift_rate)
        self.cooperate += random.uniform(-drift_rate, drift_rate)
        self.dominate += random.uniform(-drift_rate, drift_rate)
        self.escape += random.uniform(-drift_rate, drift_rate)
        self.normalize()
    
    def apply_event(self, event_type: str, severity: float = 1.0):
        """Modify intent based on events."""
        from living_matrix.constants.intent_constants import (
            FOOD_SHORTAGE_SURVIVE_INCREASE, FOOD_SHORTAGE_COOPERATE_DECREASE,
            CONFLICT_DOMINATE_INCREASE, CONFLICT_SURVIVE_INCREASE, CONFLICT_COOPERATE_DECREASE,
            AID_COOPERATE_INCREASE, AID_SURVIVE_DECREASE, EXTREME_SCARCITY_ESCAPE_INCREASE,
            EXTREME_SCARCITY_SURVIVE_INCREASE, DISCOVERY_EXPLORE_INCREASE,
            STABILITY_COOPERATE_INCREASE, STABILITY_EXPLORE_INCREASE, STABILITY_ESCAPE_DECREASE
        )
        
        if event_type in ['food_shortage', 'starvation', 'scarcity']:
            self.survive = min(1.0, self.survive + FOOD_SHORTAGE_SURVIVE_INCREASE * severity)
            self.cooperate = max(0.0, self.cooperate - FOOD_SHORTAGE_COOPERATE_DECREASE * severity)
        elif event_type in ['conflict', 'violence', 'riot']:
            self.dominate = min(1.0, self.dominate + CONFLICT_DOMINATE_INCREASE * severity)
            self.survive = min(1.0, self.survive + CONFLICT_SURVIVE_INCREASE * severity)
            self.cooperate = max(0.0, self.cooperate - CONFLICT_COOPERATE_DECREASE * severity)
        elif event_type in ['aid', 'cooperation', 'trade_success']:
            self.cooperate = min(1.0, self.cooperate + AID_COOPERATE_INCREASE * severity)
            self.survive = max(0.0, self.survive - AID_SURVIVE_DECREASE * severity)
        elif event_type in ['extreme_scarcity', 'disaster']:
            self.escape = min(1.0, self.escape + EXTREME_SCARCITY_ESCAPE_INCREASE * severity)
            self.survive = min(1.0, self.survive + EXTREME_SCARCITY_SURVIVE_INCREASE * severity)
        elif event_type in ['discovery', 'exploration']:
            self.explore = min(1.0, self.explore + DISCOVERY_EXPLORE_INCREASE * severity)
        elif event_type in ['stability', 'prosperity']:
            self.cooperate = min(1.0, self.cooperate + STABILITY_COOPERATE_INCREASE * severity)
            self.explore = min(1.0, self.explore + STABILITY_EXPLORE_INCREASE * severity)
            self.escape = max(0.0, self.escape - STABILITY_ESCAPE_DECREASE * severity)
        
        self.normalize()
    
    def apply_tension(self, tension_economic: float, tension_social: float,
                     tension_political: float, tension_existential: float):
        """Modify intent based on multi-dimensional tension."""
        from living_matrix.constants.intent_constants import (
            ECONOMIC_TENSION_SURVIVE_INCREASE, ECONOMIC_TENSION_ESCAPE_INCREASE,
            ECONOMIC_TENSION_THRESHOLD, ECONOMIC_TENSION_HIGH_THRESHOLD,
            SOCIAL_TENSION_DOMINATE_INCREASE, SOCIAL_TENSION_COOPERATE_DECREASE,
            SOCIAL_TENSION_ESCAPE_INCREASE, SOCIAL_TENSION_THRESHOLD, SOCIAL_TENSION_HIGH_THRESHOLD,
            POLITICAL_TENSION_DOMINATE_INCREASE, POLITICAL_TENSION_ESCAPE_INCREASE,
            POLITICAL_TENSION_THRESHOLD, POLITICAL_TENSION_HIGH_THRESHOLD,
            EXISTENTIAL_TENSION_ESCAPE_INCREASE, EXISTENTIAL_TENSION_EXPLORE_INCREASE,
            EXISTENTIAL_TENSION_THRESHOLD
        )
        
        # Normalize tensions to 0-1
        econ = tension_economic / 100.0
        social = tension_social / 100.0
        pol = tension_political / 100.0
        exist = tension_existential / 100.0
        
        # Economic tension → survive, escape
        if econ > ECONOMIC_TENSION_THRESHOLD:
            self.survive = min(1.0, self.survive + ECONOMIC_TENSION_SURVIVE_INCREASE * econ)
            if econ > ECONOMIC_TENSION_HIGH_THRESHOLD:
                self.escape = min(1.0, self.escape + ECONOMIC_TENSION_ESCAPE_INCREASE * econ)
        
        # Social tension → dominate, escape
        if social > SOCIAL_TENSION_THRESHOLD:
            self.dominate = min(1.0, self.dominate + SOCIAL_TENSION_DOMINATE_INCREASE * social)
            self.cooperate = max(0.0, self.cooperate - SOCIAL_TENSION_COOPERATE_DECREASE * social)
            if social > SOCIAL_TENSION_HIGH_THRESHOLD:
                self.escape = min(1.0, self.escape + SOCIAL_TENSION_ESCAPE_INCREASE * social)
        
        # Political tension → dominate, escape
        if pol > POLITICAL_TENSION_THRESHOLD:
            self.dominate = min(1.0, self.dominate + POLITICAL_TENSION_DOMINATE_INCREASE * pol)
            if pol > POLITICAL_TENSION_HIGH_THRESHOLD:
                self.escape = min(1.0, self.escape + POLITICAL_TENSION_ESCAPE_INCREASE * pol)
        
        # Existential tension → escape, explore
        if exist > EXISTENTIAL_TENSION_THRESHOLD:
            self.escape = min(1.0, self.escape + EXISTENTIAL_TENSION_ESCAPE_INCREASE * exist)
            self.explore = min(1.0, self.explore + EXISTENTIAL_TENSION_EXPLORE_INCREASE * exist)
        
        self.normalize()
    
    def apply_pressure(self, food_pressure: float, scarcity: bool, weather_bad: bool):
        """Modify intent based on environmental pressure."""
        from living_matrix.constants.intent_constants import (
            FOOD_PRESSURE_SURVIVE_INCREASE, FOOD_PRESSURE_THRESHOLD,
            SCARCITY_ESCAPE_INCREASE, WEATHER_BAD_SURVIVE_INCREASE, WEATHER_BAD_EXPLORE_DECREASE
        )
        
        if food_pressure > FOOD_PRESSURE_THRESHOLD:
            self.survive = min(1.0, self.survive + FOOD_PRESSURE_SURVIVE_INCREASE * food_pressure)
            if scarcity:
                self.escape = min(1.0, self.escape + SCARCITY_ESCAPE_INCREASE)
        
        if weather_bad:
            self.survive = min(1.0, self.survive + WEATHER_BAD_SURVIVE_INCREASE)
            self.explore = max(0.0, self.explore - WEATHER_BAD_EXPLORE_DECREASE)
        
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
