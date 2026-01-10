"""Multi-dimensional tension system."""

from dataclasses import dataclass, field
from typing import Dict, Optional
import random


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
        self.economic = max(0.0, min(100.0, self.economic))
        self.social = max(0.0, min(100.0, self.social))
        self.political = max(0.0, min(100.0, self.political))
        self.existential = max(0.0, min(100.0, self.existential))
    
    def add(self, economic: float = 0.0, social: float = 0.0, 
            political: float = 0.0, existential: float = 0.0):
        """Add tension to dimensions."""
        self.economic += economic
        self.social += social
        self.political += political
        self.existential += existential
        self.normalize()
    
    def decay(self, rate: float = 0.5):
        """
        Decay all tensions over time.
        
        Args:
            rate: Decay rate per turn
        """
        self.economic = max(0.0, self.economic - rate)
        self.social = max(0.0, self.social - rate)
        self.political = max(0.0, self.political - rate)
        self.existential = max(0.0, self.existential - rate)
    
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
        return cls(
            economic=data.get('economic', 20.0),
            social=data.get('social', 20.0),
            political=data.get('political', 15.0),
            existential=data.get('existential', 10.0)
        )
