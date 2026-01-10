"""District Culture & Norms system: cultural traits that modify district behavior."""

import random
from typing import Dict, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


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


class CultureSystem:
    """Manages district cultures and their effects."""
    
    def __init__(self, seed: int = 42):
        """Initialize culture system."""
        self.seed = seed
        random.seed(seed)
        self.cultures: Dict[str, Culture] = {}  # district_id -> Culture
        self.culture_drift_rate = 0.005  # Slow drift over time
    
    def initialize_district_culture(self, district_id: str, base_culture: Optional[Culture] = None):
        """
        Initialize culture for a district.
        
        Args:
            district_id: District ID
            base_culture: Optional base culture (otherwise random)
        """
        if base_culture:
            self.cultures[district_id] = base_culture
        else:
            # Generate random culture
            self.cultures[district_id] = Culture(
                collectivism=random.uniform(0.2, 0.8),
                obedience=random.uniform(0.2, 0.8),
                aggression=random.uniform(0.2, 0.8),
                risk_tolerance=random.uniform(0.2, 0.8)
            )
    
    def get_culture(self, district_id: str) -> Optional[Culture]:
        """Get culture for a district."""
        if district_id not in self.cultures:
            # Initialize if missing
            self.initialize_district_culture(district_id)
        return self.cultures.get(district_id)
    
    def modify_escalation_speed(self, district_id: str, base_speed: float) -> float:
        """
        Modify escalation speed based on culture.
        
        Args:
            district_id: District ID
            base_speed: Base escalation speed
            
        Returns:
            Modified speed
        """
        culture = self.get_culture(district_id)
        if not culture:
            return base_speed
        
        # High aggression and low obedience = faster escalation
        aggression_factor = 1.0 + (culture.aggression - 0.5) * 0.4
        obedience_factor = 1.0 - (culture.obedience - 0.5) * 0.3
        
        return base_speed * aggression_factor * obedience_factor
    
    def modify_cooperation_likelihood(self, district_id: str, base_likelihood: float) -> float:
        """
        Modify cooperation likelihood based on culture.
        
        Args:
            district_id: District ID
            base_likelihood: Base cooperation likelihood
            
        Returns:
            Modified likelihood
        """
        culture = self.get_culture(district_id)
        if not culture:
            return base_likelihood
        
        # High collectivism = more cooperation
        # High aggression = less cooperation
        collectivism_factor = 1.0 + (culture.collectivism - 0.5) * 0.4
        aggression_factor = 1.0 - (culture.aggression - 0.5) * 0.3
        
        return base_likelihood * collectivism_factor * aggression_factor
    
    def modify_violence_likelihood(self, district_id: str, base_likelihood: float) -> float:
        """
        Modify violence likelihood based on culture.
        
        Args:
            district_id: District ID
            base_likelihood: Base violence likelihood
            
        Returns:
            Modified likelihood
        """
        culture = self.get_culture(district_id)
        if not culture:
            return base_likelihood
        
        # High aggression = more violence
        # High obedience = less violence (authority prevents it)
        aggression_factor = 1.0 + (culture.aggression - 0.5) * 0.5
        obedience_factor = 1.0 - (culture.obedience - 0.5) * 0.4
        
        return base_likelihood * aggression_factor * obedience_factor
    
    def modify_stress_reaction(self, district_id: str, stress_level: float) -> Dict[str, float]:
        """
        Modify how district reacts to stress based on culture.
        
        Args:
            district_id: District ID
            stress_level: Current stress level (0-1)
            
        Returns:
            Dictionary with reaction modifiers
        """
        culture = self.get_culture(district_id)
        if not culture:
            return {"cooperation": 1.0, "violence": 1.0, "migration": 1.0}
        
        # High obedience + high stress = quiet suffering (low violence, low migration)
        # Low obedience + high stress = riots (high violence, high migration)
        # High collectivism + high stress = mutual aid (high cooperation)
        
        if culture.obedience > 0.7:
            # Quiet suffering
            violence_mod = 0.6
            migration_mod = 0.5
            cooperation_mod = 0.8
        elif culture.aggression > 0.7:
            # Riots
            violence_mod = 1.5
            migration_mod = 1.3
            cooperation_mod = 0.7
        elif culture.collectivism > 0.7:
            # Mutual aid
            violence_mod = 0.7
            migration_mod = 0.8
            cooperation_mod = 1.4
        else:
            # Balanced
            violence_mod = 1.0
            migration_mod = 1.0
            cooperation_mod = 1.0
        
        return {
            "cooperation": cooperation_mod,
            "violence": violence_mod,
            "migration": migration_mod
        }
    
    def drift_culture(self, district_id: str):
        """
        Slowly drift culture over time (cultural evolution).
        
        Args:
            district_id: District ID
        """
        culture = self.get_culture(district_id)
        if not culture:
            return
        
        # Small random drift
        culture.collectivism += random.uniform(-self.culture_drift_rate, self.culture_drift_rate)
        culture.obedience += random.uniform(-self.culture_drift_rate, self.culture_drift_rate)
        culture.aggression += random.uniform(-self.culture_drift_rate, self.culture_drift_rate)
        culture.risk_tolerance += random.uniform(-self.culture_drift_rate, self.culture_drift_rate)
        
        culture.normalize()
    
    def evolve_from_events(self, district_id: str, event_type: str, severity: float):
        """
        Evolve culture based on events.
        
        Args:
            district_id: District ID
            event_type: Type of event (e.g., "riot", "aid", "conflict")
            severity: Event severity (0-1)
        """
        culture = self.get_culture(district_id)
        if not culture:
            return
        
        if event_type in ["riot", "violence", "conflict"]:
            # Violence increases aggression, decreases obedience
            culture.aggression = min(1.0, culture.aggression + severity * 0.1)
            culture.obedience = max(0.0, culture.obedience - severity * 0.05)
        elif event_type in ["aid", "cooperation", "mutual_aid"]:
            # Cooperation increases collectivism
            culture.collectivism = min(1.0, culture.collectivism + severity * 0.1)
            culture.aggression = max(0.0, culture.aggression - severity * 0.05)
        elif event_type in ["crackdown", "authority_intervention"]:
            # Authority increases obedience
            culture.obedience = min(1.0, culture.obedience + severity * 0.1)
        
        culture.normalize()
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "cultures": {did: culture.to_dict() for did, culture in self.cultures.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CultureSystem":
        """Deserialize from dictionary."""
        obj = cls(seed=data.get("seed", 42))
        
        for did, culture_data in data.get("cultures", {}).items():
            obj.cultures[did] = Culture.from_dict(culture_data)
        
        return obj
