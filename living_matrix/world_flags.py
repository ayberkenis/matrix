"""World Flags system: irreversible world states that permanently bias the world."""

import random
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorldFlag:
    """A permanent world state flag that cannot fully revert."""
    id: str
    description: str
    triggered_at_turn: int
    irreversible: bool = True
    effects: Dict = field(default_factory=dict)  # modifiers applied to world, districts, agents
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "triggered_at_turn": self.triggered_at_turn,
            "irreversible": self.irreversible,
            "effects": self.effects
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldFlag":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            triggered_at_turn=data["triggered_at_turn"],
            irreversible=data.get("irreversible", True),
            effects=data.get("effects", {})
        )


@dataclass
class FlagTrigger:
    """Definition of a condition that triggers a world flag."""
    flag_id: str
    description: str
    condition: Callable  # Function that returns True when flag should trigger
    effects: Dict  # Effects to apply when triggered


class WorldFlagsSystem:
    """Manages irreversible world state flags."""
    
    # Predefined flag triggers
    FLAG_DEFINITIONS = {
        "kora_famine": {
            "description": "Kora region enters permanent famine state",
            "condition": lambda world_state, districts: (
                any(d.get("food_stock", 50) < 10 for d in districts.values() if "kora" in d.get("id", "").lower())
            ),
            "effects": {
                "agent_food_need_multiplier": 1.5,
                "migration_rate": 0.3,
                "tension_base": 20.0,
                "event_probability_modifier": {"food_shortage": 1.5, "conflict": 1.3}
            }
        },
        "rift_unrest": {
            "description": "Rift region enters permanent unrest state",
            "condition": lambda world_state, districts: (
                any(d.get("tension", 20) > 80 for d in districts.values() if "rift" in d.get("id", "").lower())
            ),
            "effects": {
                "agent_conflict_probability": 1.4,
                "cooperation_reduction": 0.2,
                "tension_decay_reduction": 0.3,
                "event_probability_modifier": {"riot": 1.5, "strike": 1.3}
            }
        },
        "lume_economic_collapse": {
            "description": "Lume region enters economic collapse",
            "condition": lambda world_state, districts: (
                any(d.get("credits_pool", 100) < 20 and d.get("jobs_available", 5) < 2 
                    for d in districts.values() if "lume" in d.get("id", "").lower())
            ),
            "effects": {
                "job_availability_multiplier": 0.5,
                "trade_success_reduction": 0.4,
                "agent_credits_loss_rate": 1.3,
                "event_probability_modifier": {"unemployment_spike": 1.6, "migration": 1.4}
            }
        },
        "zeph_dominance": {
            "description": "Zeph region achieves dominance",
            "condition": lambda world_state, districts: (
                any(d.get("food_stock", 50) > 80 and d.get("tension", 20) < 30 
                    for d in districts.values() if "zeph" in d.get("id", "").lower())
            ),
            "effects": {
                "resource_attraction": 0.2,
                "migration_inflow": 0.3,
                "agent_cooperation_bonus": 0.15,
                "event_probability_modifier": {"aid_distribution": 1.3, "trade_success": 1.2}
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
