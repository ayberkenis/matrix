"""Enhanced Agent Relationships: love, hate, trust, familiarity."""

import random
from typing import Dict, Optional
import logging

from .dataclasses import Relationship
from .constants.relationships_enhanced_constants import (
    DEFAULT_DECAY_RATE, DEFAULT_FAMILIARITY_GAIN, DEFAULT_INITIAL_TRUST,
    COOPERATION_AFFECTION_INCREASE, COOPERATION_TRUST_INCREASE,
    COOPERATION_AFFECTION_DECREASE, COOPERATION_TRUST_DECREASE,
    CONFLICT_AFFECTION_DECREASE, CONFLICT_TRUST_DECREASE,
    TRADE_AFFECTION_INCREASE, TRADE_TRUST_INCREASE,
    TRADE_AFFECTION_DECREASE, TRADE_TRUST_DECREASE,
    SOCIALIZE_AFFECTION_INCREASE, SOCIALIZE_TRUST_INCREASE,
    WORK_AFFECTION_INCREASE, WORK_TRUST_INCREASE,
    CONFLICT_LIKELIHOOD_MULTIPLIER
)

logger = logging.getLogger(__name__)

# Relationship is now imported from dataclasses
# The class definition is in dataclasses/relationship_dataclasses.py


class RelationshipSystem:
    """Manages relationship evolution and effects."""
    
    def __init__(self, seed: int = 42):
        """Initialize relationship system."""
        self.seed = seed
        random.seed(seed)
        self.decay_rate = DEFAULT_DECAY_RATE  # Relationship decay per turn without interaction
        self.familiarity_gain = DEFAULT_FAMILIARITY_GAIN  # Familiarity gain per interaction
    
    def create_relationship(self, target_id: str, turn: int, initial_affection: float = 0.0) -> Relationship:
        """Create a new relationship."""
        return Relationship(
            target_id=target_id,
            affection=initial_affection,
            trust=DEFAULT_INITIAL_TRUST,  # Start with low trust
            familiarity=0.0,
            last_interaction=turn
        )
    
    def update_from_interaction(self, relationship: Relationship, interaction_type: str, 
                               turn: int, success: bool = True):
        """
        Update relationship based on interaction.
        
        Args:
            relationship: Relationship to update
            interaction_type: Type of interaction (cooperation, conflict, trade, socialize, work)
            turn: Current turn
            success: Whether interaction was successful
        """
        old_affection = relationship.affection
        old_trust = relationship.trust
        
        if interaction_type == "cooperation":
            if success:
                relationship.affection = min(1.0, relationship.affection + COOPERATION_AFFECTION_INCREASE)
                relationship.trust = min(1.0, relationship.trust + COOPERATION_TRUST_INCREASE)
            else:
                relationship.affection = max(-1.0, relationship.affection - COOPERATION_AFFECTION_DECREASE)
                relationship.trust = max(0.0, relationship.trust - COOPERATION_TRUST_DECREASE)
        
        elif interaction_type == "conflict":
            relationship.affection = max(-1.0, relationship.affection - CONFLICT_AFFECTION_DECREASE)
            relationship.trust = max(0.0, relationship.trust - CONFLICT_TRUST_DECREASE)
        
        elif interaction_type == "trade":
            if success:
                relationship.affection = min(1.0, relationship.affection + TRADE_AFFECTION_INCREASE)
                relationship.trust = min(1.0, relationship.trust + TRADE_TRUST_INCREASE)
            else:
                relationship.affection = max(-1.0, relationship.affection - TRADE_AFFECTION_DECREASE)
                relationship.trust = max(0.0, relationship.trust - TRADE_TRUST_DECREASE)
        
        elif interaction_type == "socialize":
            relationship.affection = min(1.0, relationship.affection + SOCIALIZE_AFFECTION_INCREASE)
            relationship.trust = min(1.0, relationship.trust + SOCIALIZE_TRUST_INCREASE)
        
        elif interaction_type == "work":
            if success:
                relationship.affection = min(1.0, relationship.affection + WORK_AFFECTION_INCREASE)
                relationship.trust = min(1.0, relationship.trust + WORK_TRUST_INCREASE)
        
        # Increase familiarity
        relationship.familiarity = min(1.0, relationship.familiarity + self.familiarity_gain)
        relationship.last_interaction = turn
        relationship.normalize()
    
    def update_from_rumor(self, relationship: Relationship, rumor_polarity: float, 
                          source_trust: float, turn: int):
        """
        Update relationship based on rumor about target.
        
        Args:
            relationship: Relationship to update
            rumor_polarity: Polarity of rumor (-1 to +1)
            source_trust: Trust in rumor source (0 to 1)
            turn: Current turn
        """
        # Rumors affect affection more than trust
        rumor_weight = source_trust * 0.3  # Weighted by source trust
        relationship.affection = max(-1.0, min(1.0, 
            relationship.affection + rumor_polarity * rumor_weight))
        relationship.normalize()
    
    def decay_relationship(self, relationship: Relationship, turn: int):
        """
        Decay relationship over time without interaction.
        
        Args:
            relationship: Relationship to decay
            turn: Current turn
        """
        turns_since_interaction = turn - relationship.last_interaction
        if turns_since_interaction > 0:
            # Affection decays toward neutral (0.0)
            if relationship.affection > 0:
                relationship.affection = max(0.0, relationship.affection - self.decay_rate * turns_since_interaction)
            elif relationship.affection < 0:
                relationship.affection = min(0.0, relationship.affection + self.decay_rate * turns_since_interaction)
            
            # Trust decays slowly
            relationship.trust = max(0.0, relationship.trust - self.decay_rate * turns_since_interaction * 0.5)
            
            # Familiarity decays very slowly
            relationship.familiarity = max(0.0, relationship.familiarity - self.decay_rate * turns_since_interaction * 0.2)
    
    def get_cooperation_likelihood(self, relationship: Relationship) -> float:
        """Get likelihood of cooperation based on relationship."""
        # High affection and trust = high cooperation
        base = 0.5
        affection_bonus = relationship.affection * 0.3
        trust_bonus = relationship.trust * 0.2
        return max(0.0, min(1.0, base + affection_bonus + trust_bonus))
    
    def get_conflict_likelihood(self, relationship: Relationship) -> float:
        """Get likelihood of conflict based on relationship."""
        # Low affection and trust = high conflict
        base = 0.1
        affection_penalty = -relationship.affection * 0.4  # Negative affection increases conflict
        trust_penalty = (1.0 - relationship.trust) * 0.3
        conflict_likelihood = max(0.0, min(1.0, base + affection_penalty + trust_penalty))
        # Apply multiplier for use in human_agent.py
        return conflict_likelihood * CONFLICT_LIKELIHOOD_MULTIPLIER
    
    def can_reproduce(self, relationship: Relationship, food_available: bool, 
                     tension: float, food_stock: float = 50, population_count: int = 20) -> bool:
        """
        Check if two agents can reproduce based on relationship and conditions.
        
        Args:
            relationship: Relationship between potential parents
            food_available: Whether sufficient food is available
            tension: Current district tension (0-100)
            food_stock: Current food stock level (for extreme condition checks)
            population_count: Current population count (for survival instinct)
            
        Returns:
            True if conditions are met for reproduction
        """
        # Survival instinct: if population is low, reproduction is instinctual even in bad conditions
        survival_instinct = population_count < 20
        
        # Very lenient thresholds to maximize reproduction opportunities
        # Only block if relationship is actively negative
        if relationship.affection < -0.2:  # Only block if strongly negative
            return False
        
        if relationship.trust < 0.0:  # Only block if trust is negative
            return False
        
        # Familiarity just needs to exist (created relationships have 0.1)
        # No minimum threshold - relationships are created with familiarity
        
        # Food availability - only block if food is critically low AND tension is high
        # But allow if survival instinct is active
        if not food_available and food_stock < 10 and tension > 80 and not survival_instinct:
            return False  # Only block in extreme conditions if not survival instinct
        
        # Tension threshold - allow high tension if survival instinct is active
        # Survival instinct overrides tension restrictions
        if tension > 90 and not survival_instinct:
            return False
        
        return True
    
    def get_bonding_strength(self, relationship: Relationship) -> float:
        """Get bonding strength (for family relationships)."""
        # Combination of affection, trust, and familiarity
        return (relationship.affection * 0.4 + relationship.trust * 0.3 + 
                relationship.familiarity * 0.3)
