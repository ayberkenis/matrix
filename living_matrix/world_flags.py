"""World Flags system: irreversible world states that permanently bias the world."""

import random
from typing import Dict, List, Optional, Callable
import logging

from .dataclasses import WorldFlag, FlagTrigger
from .constants.world_flags_constants import (
    KORA_FAMINE_FOOD_THRESHOLD, RIFT_UNREST_TENSION_THRESHOLD,
    LUME_ECONOMIC_COLLAPSE_CREDITS_THRESHOLD, LUME_ECONOMIC_COLLAPSE_JOBS_THRESHOLD,
    ZEPH_DOMINANCE_FOOD_THRESHOLD, ZEPH_DOMINANCE_TENSION_THRESHOLD,
    POPULATION_DECLINE_FOOD_THRESHOLD, TRADE_COLLAPSE_CREDITS_THRESHOLD,
    TRADE_COLLAPSE_DISTRICT_COUNT, KORA_FAMINE_FOOD_NEED_MULTIPLIER,
    KORA_FAMINE_MIGRATION_RATE, KORA_FAMINE_TENSION_BASE,
    KORA_FAMINE_REPRODUCTION_REDUCTION, KORA_FAMINE_RELATIONSHIP_DECAY_MULTIPLIER,
    KORA_FAMINE_CONFLICT_MULTIPLIER, KORA_FAMINE_FOOD_SHORTAGE_MODIFIER,
    KORA_FAMINE_CONFLICT_MODIFIER, RIFT_UNREST_CONFLICT_PROBABILITY,
    RIFT_UNREST_COOPERATION_REDUCTION, RIFT_UNREST_TENSION_DECAY_REDUCTION,
    RIFT_UNREST_TRUST_FORMATION_REDUCTION, RIFT_UNREST_REPRODUCTION_REDUCTION,
    RIFT_UNREST_RIOT_MODIFIER, RIFT_UNREST_STRIKE_MODIFIER,
    LUME_COLLAPSE_JOB_AVAILABILITY_MULTIPLIER, LUME_COLLAPSE_TRADE_SUCCESS_REDUCTION,
    LUME_COLLAPSE_CREDITS_LOSS_RATE, LUME_COLLAPSE_UNEMPLOYMENT_MODIFIER,
    LUME_COLLAPSE_MIGRATION_MODIFIER, ZEPH_DOMINANCE_RESOURCE_ATTRACTION,
    ZEPH_DOMINANCE_MIGRATION_INFLOW, ZEPH_DOMINANCE_COOPERATION_BONUS,
    ZEPH_DOMINANCE_AID_MODIFIER, ZEPH_DOMINANCE_TRADE_SUCCESS_MODIFIER,
    POPULATION_DECLINE_REPRODUCTION_REDUCTION, POPULATION_DECLINE_MIGRATION_RATE,
    POPULATION_DECLINE_RELATIONSHIP_DECAY_MULTIPLIER, POPULATION_DECLINE_DEATH_MODIFIER,
    TRADE_COLLAPSE_TRADE_SUCCESS_REDUCTION, TRADE_COLLAPSE_TENSION_BASE,
    TRADE_COLLAPSE_TRUST_FORMATION_REDUCTION, TRADE_COLLAPSE_COOPERATION_REDUCTION,
    TRADE_COLLAPSE_CONFLICT_MODIFIER, TRADE_COLLAPSE_THEFT_MODIFIER
)

logger = logging.getLogger(__name__)

# WorldFlag and FlagTrigger are now imported from dataclasses
# The class definitions are in dataclasses/flag_dataclasses.py


class WorldFlagsSystem:
    """Manages irreversible world state flags."""
    
    # Predefined flag triggers
    FLAG_DEFINITIONS = {
        "kora_famine": {
            "description": "Kora region enters permanent famine state",
            "condition": lambda world_state, districts: (
                any(d.get("food_stock", 50) < KORA_FAMINE_FOOD_THRESHOLD for d in districts.values() if "kora" in d.get("id", "").lower())
            ),
            "effects": {
                "agent_food_need_multiplier": KORA_FAMINE_FOOD_NEED_MULTIPLIER,
                "migration_rate": KORA_FAMINE_MIGRATION_RATE,
                "tension_base": KORA_FAMINE_TENSION_BASE,
                "reproduction_reduction": KORA_FAMINE_REPRODUCTION_REDUCTION,  # 70% reduction in birth rate
                "relationship_decay_multiplier": KORA_FAMINE_RELATIONSHIP_DECAY_MULTIPLIER,  # Relationships decay faster
                "conflict_multiplier": KORA_FAMINE_CONFLICT_MULTIPLIER,  # More conflicts
                "event_probability_modifier": {"food_shortage": KORA_FAMINE_FOOD_SHORTAGE_MODIFIER, "conflict": KORA_FAMINE_CONFLICT_MODIFIER}
            }
        },
        "rift_unrest": {
            "description": "Rift region enters permanent unrest state",
            "condition": lambda world_state, districts: (
                any(d.get("tension", 20) > RIFT_UNREST_TENSION_THRESHOLD for d in districts.values() if "rift" in d.get("id", "").lower())
            ),
            "effects": {
                "agent_conflict_probability": RIFT_UNREST_CONFLICT_PROBABILITY,
                "cooperation_reduction": RIFT_UNREST_COOPERATION_REDUCTION,
                "tension_decay_reduction": RIFT_UNREST_TENSION_DECAY_REDUCTION,
                "trust_formation_reduction": RIFT_UNREST_TRUST_FORMATION_REDUCTION,  # Harder to form trust
                "reproduction_reduction": RIFT_UNREST_REPRODUCTION_REDUCTION,  # Lower birth rate
                "event_probability_modifier": {"riot": RIFT_UNREST_RIOT_MODIFIER, "strike": RIFT_UNREST_STRIKE_MODIFIER}
            }
        },
        "lume_economic_collapse": {
            "description": "Lume region enters economic collapse",
            "condition": lambda world_state, districts: (
                any(d.get("credits_pool", 100) < LUME_ECONOMIC_COLLAPSE_CREDITS_THRESHOLD and d.get("jobs_available", 5) < LUME_ECONOMIC_COLLAPSE_JOBS_THRESHOLD 
                    for d in districts.values() if "lume" in d.get("id", "").lower())
            ),
            "effects": {
                "job_availability_multiplier": LUME_COLLAPSE_JOB_AVAILABILITY_MULTIPLIER,
                "trade_success_reduction": LUME_COLLAPSE_TRADE_SUCCESS_REDUCTION,
                "agent_credits_loss_rate": LUME_COLLAPSE_CREDITS_LOSS_RATE,
                "event_probability_modifier": {"unemployment_spike": LUME_COLLAPSE_UNEMPLOYMENT_MODIFIER, "migration": LUME_COLLAPSE_MIGRATION_MODIFIER}
            }
        },
        "zeph_dominance": {
            "description": "Zeph region achieves dominance",
            "condition": lambda world_state, districts: (
                any(d.get("food_stock", 50) > ZEPH_DOMINANCE_FOOD_THRESHOLD and d.get("tension", 20) < ZEPH_DOMINANCE_TENSION_THRESHOLD 
                    for d in districts.values() if "zeph" in d.get("id", "").lower())
            ),
            "effects": {
                "resource_attraction": ZEPH_DOMINANCE_RESOURCE_ATTRACTION,
                "migration_inflow": ZEPH_DOMINANCE_MIGRATION_INFLOW,
                "agent_cooperation_bonus": ZEPH_DOMINANCE_COOPERATION_BONUS,
                "event_probability_modifier": {"aid_distribution": ZEPH_DOMINANCE_AID_MODIFIER, "trade_success": ZEPH_DOMINANCE_TRADE_SUCCESS_MODIFIER}
            }
        },
        "population_decline": {
            "description": "Global population decline",
            "condition": lambda world_state, districts: (
                # Trigger if average food stock is very low across all districts
                len(districts) > 0 and 
                sum(d.get("food_stock", 50) for d in districts.values()) / len(districts) < POPULATION_DECLINE_FOOD_THRESHOLD
            ),
            "effects": {
                "reproduction_reduction": POPULATION_DECLINE_REPRODUCTION_REDUCTION,
                "migration_rate": POPULATION_DECLINE_MIGRATION_RATE,
                "relationship_decay_multiplier": POPULATION_DECLINE_RELATIONSHIP_DECAY_MULTIPLIER,
                "event_probability_modifier": {"death": POPULATION_DECLINE_DEATH_MODIFIER}
            }
        },
        "trade_collapse": {
            "description": "Trade system collapses",
            "condition": lambda world_state, districts: (
                # Trigger if multiple districts have very low credits
                sum(1 for d in districts.values() if d.get("credits_pool", 100) < TRADE_COLLAPSE_CREDITS_THRESHOLD) >= TRADE_COLLAPSE_DISTRICT_COUNT
            ),
            "effects": {
                "trade_success_reduction": TRADE_COLLAPSE_TRADE_SUCCESS_REDUCTION,
                "tension_base": TRADE_COLLAPSE_TENSION_BASE,
                "trust_formation_reduction": TRADE_COLLAPSE_TRUST_FORMATION_REDUCTION,
                "cooperation_reduction": TRADE_COLLAPSE_COOPERATION_REDUCTION,
                "event_probability_modifier": {"conflict": TRADE_COLLAPSE_CONFLICT_MODIFIER, "theft": TRADE_COLLAPSE_THEFT_MODIFIER}
            }
        }
    }
    
    def __init__(self, seed: int = 42):
        """Initialize world flags system."""
        self.seed = seed
        random.seed(seed)
        self.flags: Dict[str, WorldFlag] = {}
        self.triggered_flags: set = set()  # Track which flags have been triggered
    
    def check_triggers(self, world_state, districts: Dict) -> List[WorldFlag]:
        """
        Check all flag triggers and return newly triggered flags.
        
        Args:
            world_state: Current world state
            districts: Dictionary of district data (id -> district info)
            
        Returns:
            List of newly triggered WorldFlag objects
        """
        newly_triggered = []
        current_turn = getattr(world_state, 'turn', 0)
        
        for flag_id, flag_def in self.FLAG_DEFINITIONS.items():
            if flag_id in self.triggered_flags:
                continue  # Already triggered
            
            try:
                if flag_def["condition"](world_state, districts):
                    # Trigger the flag
                    flag = WorldFlag(
                        id=flag_id,
                        description=flag_def["description"],
                        triggered_at_turn=current_turn,
                        irreversible=True,
                        effects=flag_def["effects"]
                    )
                    self.flags[flag_id] = flag
                    self.triggered_flags.add(flag_id)
                    newly_triggered.append(flag)
                    
                    logger.info(f"World flag triggered: {flag_id} at turn {current_turn}")
            except Exception as e:
                logger.error(f"Error checking flag trigger {flag_id}: {e}")
        
        return newly_triggered
    
    def get_flag(self, flag_id: str) -> Optional[WorldFlag]:
        """Get a flag by ID."""
        return self.flags.get(flag_id)
    
    def get_all_flags(self) -> List[WorldFlag]:
        """Get all triggered flags."""
        return list(self.flags.values())
    
    def apply_flag_effects(self, flag_id: str, target: Dict) -> Dict:
        """
        Apply flag effects to a target (district, agent, etc.).
        
        Args:
            flag_id: Flag ID
            target: Target dictionary to modify
            
        Returns:
            Modified target dictionary
        """
        flag = self.flags.get(flag_id)
        if not flag:
            return target
        
        result = target.copy()
        effects = flag.effects
        
        # Apply various effect types
        for key, value in effects.items():
            if key.endswith("_multiplier"):
                base_key = key.replace("_multiplier", "")
                if base_key in result:
                    result[base_key] = result[base_key] * value
            elif key.endswith("_reduction"):
                base_key = key.replace("_reduction", "")
                if base_key in result:
                    result[base_key] = result[base_key] * (1.0 - value)
            elif key.endswith("_bonus"):
                base_key = key.replace("_bonus", "")
                if base_key in result:
                    result[base_key] = result[base_key] + value
            elif key == "tension_base":
                if "tension" in result:
                    result["tension"] = max(result.get("tension", 0), value)
            else:
                result[key] = value
        
        return result
    
    def modify_event_probability(self, event_type: str, base_probability: float) -> float:
        """
        Modify event probability based on active flags.
        
        Args:
            event_type: Type of event
            base_probability: Base probability (0-1)
            
        Returns:
            Modified probability
        """
        modified = base_probability
        
        for flag in self.flags.values():
            event_modifiers = flag.effects.get("event_probability_modifier", {})
            if event_type in event_modifiers:
                modified = modified * event_modifiers[event_type]
        
        return min(1.0, modified)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "flags": {fid: flag.to_dict() for fid, flag in self.flags.items()},
            "triggered_flags": list(self.triggered_flags)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldFlagsSystem":
        """Deserialize from dictionary."""
        obj = cls(seed=data.get("seed", 42))
        obj.triggered_flags = set(data.get("triggered_flags", []))
        
        for fid, flag_data in data.get("flags", {}).items():
            obj.flags[fid] = WorldFlag.from_dict(flag_data)
        
        return obj
