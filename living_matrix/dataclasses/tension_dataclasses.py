"""Tension-related dataclasses."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Tension:
    """
    Multi-dimensional tension system.
    Each dimension is 0-100, representing stored stress energy.
    """
    economic: float = 20.0      # Economic pressure (jobs, resources, trade)
    social: float = 20.0         # Social tension (conflicts, rumors, trust)
    political: float = 15.0      # Political tension (power, authority, control)
    existential: float = 10.0    # Existential tension (meaning, purpose, escape)
    
    def normalize(self):
        """Clamp all values to 0-100."""
        from living_matrix.constants.tension_constants import TENSION_NORMALIZATION_DIVISOR
        max_tension = TENSION_NORMALIZATION_DIVISOR
        self.economic = max(0.0, min(max_tension, self.economic))
        self.social = max(0.0, min(max_tension, self.social))
        self.political = max(0.0, min(max_tension, self.political))
        self.existential = max(0.0, min(max_tension, self.existential))
    
    def add(self, economic: float = 0.0, social: float = 0.0, 
            political: float = 0.0, existential: float = 0.0):
        """Add tension to dimensions."""
        self.economic += economic
        self.social += social
        self.political += political
        self.existential += existential
        self.normalize()
    
    def decay(self, rate: float = None):
        """
        Decay all tensions over time.
        
        Args:
            rate: Decay rate per turn (defaults to DEFAULT_TENSION_DECAY_RATE)
        """
        from living_matrix.constants.tension_constants import DEFAULT_TENSION_DECAY_RATE
        decay_rate = rate if rate is not None else DEFAULT_TENSION_DECAY_RATE
        self.economic = max(0.0, self.economic - decay_rate)
        self.social = max(0.0, self.social - decay_rate)
        self.political = max(0.0, self.political - decay_rate)
        self.existential = max(0.0, self.existential - decay_rate)
    
    def get_total(self) -> float:
        """Get total tension (sum of all dimensions)."""
        return self.economic + self.social + self.political + self.existential
    
    def get_average(self) -> float:
        """Get average tension across dimensions."""
        return self.get_total() / 4.0
    
    def get_max_dimension(self) -> str:
        """Get the dimension with highest tension."""
        dims = {
            'economic': self.economic,
            'social': self.social,
            'political': self.political,
            'existential': self.existential
        }
        return max(dims.items(), key=lambda x: x[1])[0]
    
    def apply_pressure(self, pressure_type: str, amount: float):
        """
        Apply pressure to specific tension dimension.
        
        Args:
            pressure_type: Type of pressure (food, jobs, weather, conflict, etc.)
            amount: Amount of pressure (0-100)
        """
        if pressure_type in ['food', 'scarcity', 'unemployment', 'trade_failure']:
            self.economic += amount
        elif pressure_type in ['conflict', 'rumor', 'violence', 'distrust']:
            self.social += amount
        elif pressure_type in ['protest', 'authority', 'power_struggle', 'control']:
            self.political += amount
        elif pressure_type in ['disaster', 'meaninglessness', 'despair', 'isolation']:
            self.existential += amount
        
        self.normalize()
    
    def release(self, dimension: str, amount: float):
        """
        Release tension from a specific dimension (e.g., through events).
        
        Args:
            dimension: Which dimension to release
            amount: How much to release
        """
        if dimension == 'economic':
            self.economic = max(0.0, self.economic - amount)
        elif dimension == 'social':
            self.social = max(0.0, self.social - amount)
        elif dimension == 'political':
            self.political = max(0.0, self.political - amount)
        elif dimension == 'existential':
            self.existential = max(0.0, self.existential - amount)
    
    def to_dict(self) -> Dict[str, float]:
        """Serialize to dictionary."""
        return {
            'economic': self.economic,
            'social': self.social,
            'political': self.political,
            'existential': self.existential,
            'total': self.get_total(),
            'average': self.get_average(),
            'max_dimension': self.get_max_dimension()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Tension":
        """Deserialize from dictionary."""
        from living_matrix.constants.tension_constants import (
            DEFAULT_ECONOMIC_TENSION, DEFAULT_SOCIAL_TENSION,
            DEFAULT_POLITICAL_TENSION, DEFAULT_EXISTENTIAL_TENSION
        )
        return cls(
            economic=data.get('economic', DEFAULT_ECONOMIC_TENSION),
            social=data.get('social', DEFAULT_SOCIAL_TENSION),
            political=data.get('political', DEFAULT_POLITICAL_TENSION),
            existential=data.get('existential', DEFAULT_EXISTENTIAL_TENSION)
        )
