"""District Culture & Norms system: cultural traits that modify district behavior."""

import random
from typing import Dict, Optional
import logging

from .dataclasses import Culture
from .constants.culture_constants import (
    DEFAULT_COLLECTIVISM, DEFAULT_OBEDIENCE, DEFAULT_AGGRESSION, DEFAULT_RISK_TOLERANCE,
    INITIAL_COLLECTIVISM_MIN, INITIAL_COLLECTIVISM_MAX,
    INITIAL_OBEDIENCE_MIN, INITIAL_OBEDIENCE_MAX,
    INITIAL_AGGRESSION_MIN, INITIAL_AGGRESSION_MAX,
    INITIAL_RISK_TOLERANCE_MIN, INITIAL_RISK_TOLERANCE_MAX,
    DEFAULT_CULTURE_DRIFT_RATE, ESCALATION_AGGRESSION_FACTOR_MULTIPLIER,
    ESCALATION_OBEDIENCE_FACTOR_MULTIPLIER, ESCALATION_BASE_FACTOR,
    COOPERATION_COLLECTIVISM_FACTOR_MULTIPLIER, COOPERATION_AGGRESSION_FACTOR_MULTIPLIER,
    COOPERATION_BASE_FACTOR, VIOLENCE_AGGRESSION_FACTOR_MULTIPLIER,
    VIOLENCE_OBEDIENCE_FACTOR_MULTIPLIER, VIOLENCE_BASE_FACTOR,
    HIGH_OBEDIENCE_THRESHOLD, HIGH_AGGRESSION_THRESHOLD, HIGH_COLLECTIVISM_THRESHOLD,
    QUIET_SUFFERING_VIOLENCE_MOD, QUIET_SUFFERING_MIGRATION_MOD, QUIET_SUFFERING_COOPERATION_MOD,
    RIOTS_VIOLENCE_MOD, RIOTS_MIGRATION_MOD, RIOTS_COOPERATION_MOD,
    MUTUAL_AID_VIOLENCE_MOD, MUTUAL_AID_MIGRATION_MOD, MUTUAL_AID_COOPERATION_MOD,
    BALANCED_VIOLENCE_MOD, BALANCED_MIGRATION_MOD, BALANCED_COOPERATION_MOD,
    VIOLENCE_AGGRESSION_INCREASE, VIOLENCE_OBEDIENCE_DECREASE,
    COOPERATION_COLLECTIVISM_INCREASE, COOPERATION_AGGRESSION_DECREASE,
    AUTHORITY_OBEDIENCE_INCREASE
)

logger = logging.getLogger(__name__)

# Culture is now imported from dataclasses
# The class definition is in dataclasses/culture_dataclasses.py


class CultureSystem:
    """Manages district cultures and their effects."""
    
    def __init__(self, seed: int = 42):
        """Initialize culture system."""
        self.seed = seed
        random.seed(seed)
        self.cultures: Dict[str, Culture] = {}  # district_id -> Culture
        self.culture_drift_rate = DEFAULT_CULTURE_DRIFT_RATE  # Slow drift over time
    
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
                collectivism=random.uniform(INITIAL_COLLECTIVISM_MIN, INITIAL_COLLECTIVISM_MAX),
                obedience=random.uniform(INITIAL_OBEDIENCE_MIN, INITIAL_OBEDIENCE_MAX),
                aggression=random.uniform(INITIAL_AGGRESSION_MIN, INITIAL_AGGRESSION_MAX),
                risk_tolerance=random.uniform(INITIAL_RISK_TOLERANCE_MIN, INITIAL_RISK_TOLERANCE_MAX)
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
        aggression_factor = ESCALATION_BASE_FACTOR + (culture.aggression - 0.5) * ESCALATION_AGGRESSION_FACTOR_MULTIPLIER
        obedience_factor = ESCALATION_BASE_FACTOR - (culture.obedience - 0.5) * ESCALATION_OBEDIENCE_FACTOR_MULTIPLIER
        
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
        collectivism_factor = COOPERATION_BASE_FACTOR + (culture.collectivism - 0.5) * COOPERATION_COLLECTIVISM_FACTOR_MULTIPLIER
        aggression_factor = COOPERATION_BASE_FACTOR - (culture.aggression - 0.5) * COOPERATION_AGGRESSION_FACTOR_MULTIPLIER
        
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
        aggression_factor = VIOLENCE_BASE_FACTOR + (culture.aggression - 0.5) * VIOLENCE_AGGRESSION_FACTOR_MULTIPLIER
        obedience_factor = VIOLENCE_BASE_FACTOR - (culture.obedience - 0.5) * VIOLENCE_OBEDIENCE_FACTOR_MULTIPLIER
        
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
        
        if culture.obedience > HIGH_OBEDIENCE_THRESHOLD:
            # Quiet suffering
            violence_mod = QUIET_SUFFERING_VIOLENCE_MOD
            migration_mod = QUIET_SUFFERING_MIGRATION_MOD
            cooperation_mod = QUIET_SUFFERING_COOPERATION_MOD
        elif culture.aggression > HIGH_AGGRESSION_THRESHOLD:
            # Riots
            violence_mod = RIOTS_VIOLENCE_MOD
            migration_mod = RIOTS_MIGRATION_MOD
            cooperation_mod = RIOTS_COOPERATION_MOD
        elif culture.collectivism > HIGH_COLLECTIVISM_THRESHOLD:
            # Mutual aid
            violence_mod = MUTUAL_AID_VIOLENCE_MOD
            migration_mod = MUTUAL_AID_MIGRATION_MOD
            cooperation_mod = MUTUAL_AID_COOPERATION_MOD
        else:
            # Balanced
            violence_mod = BALANCED_VIOLENCE_MOD
            migration_mod = BALANCED_MIGRATION_MOD
            cooperation_mod = BALANCED_COOPERATION_MOD
        
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
            culture.aggression = min(1.0, culture.aggression + severity * VIOLENCE_AGGRESSION_INCREASE)
            culture.obedience = max(0.0, culture.obedience - severity * VIOLENCE_OBEDIENCE_DECREASE)
        elif event_type in ["aid", "cooperation", "mutual_aid"]:
            # Cooperation increases collectivism
            culture.collectivism = min(1.0, culture.collectivism + severity * COOPERATION_COLLECTIVISM_INCREASE)
            culture.aggression = max(0.0, culture.aggression - severity * COOPERATION_AGGRESSION_DECREASE)
        elif event_type in ["crackdown", "authority_intervention"]:
            # Authority increases obedience
            culture.obedience = min(1.0, culture.obedience + severity * AUTHORITY_OBEDIENCE_INCREASE)
        
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
