"""Culture-related dataclasses."""

from dataclasses import dataclass


@dataclass
class Culture:
    """Cultural traits of a district."""
    collectivism: float = 0.5  # 0.0 (individualistic) to 1.0 (collectivist)
    obedience: float = 0.5  # 0.0 (rebellious) to 1.0 (obedient)
    aggression: float = 0.5  # 0.0 (peaceful) to 1.0 (aggressive)
    risk_tolerance: float = 0.5  # 0.0 (risk-averse) to 1.0 (risk-seeking)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "collectivism": self.collectivism,
            "obedience": self.obedience,
            "aggression": self.aggression,
            "risk_tolerance": self.risk_tolerance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Culture":
        """Deserialize from dictionary."""
        return cls(
            collectivism=data.get("collectivism", 0.5),
            obedience=data.get("obedience", 0.5),
            aggression=data.get("aggression", 0.5),
            risk_tolerance=data.get("risk_tolerance", 0.5)
        )
    
    def normalize(self):
        """Ensure all values are in [0, 1] range."""
        self.collectivism = max(0.0, min(1.0, self.collectivism))
        self.obedience = max(0.0, min(1.0, self.obedience))
        self.aggression = max(0.0, min(1.0, self.aggression))
        self.risk_tolerance = max(0.0, min(1.0, self.risk_tolerance))
