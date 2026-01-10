"""Escalation Chains system: progressive crisis chains that advance over time."""

import random
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class EscalationChain:
    """A progressive escalation chain representing a crisis."""
    id: str
    trigger_condition: str  # Description of trigger condition
    stages: List[str]  # List of stage names
    current_stage: int  # Current stage index (0 = first stage)
    severity: float  # 0.0-1.0, overall severity
    district_id: Optional[str] = None  # District where chain is active
    triggered_at_turn: int = 0
    last_advance_turn: int = 0
    stalled_turns: int = 0  # Turns since last advance
    
    def get_current_stage_name(self) -> str:
        """Get name of current stage."""
        if 0 <= self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return "unknown"
    
    def is_final_stage(self) -> bool:
        """Check if chain is at final stage."""
        return self.current_stage >= len(self.stages) - 1
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "trigger_condition": self.trigger_condition,
            "stages": self.stages,
            "current_stage": self.current_stage,
            "severity": self.severity,
            "district_id": self.district_id,
            "triggered_at_turn": self.triggered_at_turn,
            "last_advance_turn": self.last_advance_turn,
            "stalled_turns": self.stalled_turns
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EscalationChain":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            trigger_condition=data["trigger_condition"],
            stages=data["stages"],
            current_stage=data["current_stage"],
            severity=data["severity"],
            district_id=data.get("district_id"),
            triggered_at_turn=data.get("triggered_at_turn", 0),
            last_advance_turn=data.get("last_advance_turn", 0),
            stalled_turns=data.get("stalled_turns", 0)
        )


class EscalationSystem:
    """Manages escalation chains for progressive crises."""
    
    # Predefined escalation chain templates
    CHAIN_TEMPLATES = {
        "food_crisis": {
            "stages": ["shortage", "hoarding", "theft", "violence", "collapse"],
            "trigger_condition": "food_stock < 20 for 3+ turns",
            "advance_condition": lambda district, turn, last_advance: (
                district.get("food_stock", 50) < 30 and (turn - last_advance) >= 2
            ),
            "mitigation_condition": lambda district: district.get("food_stock", 50) > 50,
            "final_stage_effect": "trigger_world_flag:kora_famine"
        },
        "political_tension": {
            "stages": ["complaints", "protests", "clashes", "crackdown", "regime_shift"],
            "trigger_condition": "tension > 70 for 5+ turns",
            "advance_condition": lambda district, turn, last_advance: (
                district.get("tension", 20) > 75 and (turn - last_advance) >= 3
            ),
            "mitigation_condition": lambda district: district.get("tension", 20) < 50,
            "final_stage_effect": "trigger_world_flag:rift_unrest"
        },
        "economic_collapse": {
            "stages": ["decline", "layoffs", "strikes", "bankruptcy", "collapse"],
            "trigger_condition": "credits_pool < 30 and jobs_available < 3",
            "advance_condition": lambda district, turn, last_advance: (
                district.get("credits_pool", 100) < 40 and 
                district.get("jobs_available", 5) < 4 and
                (turn - last_advance) >= 2
            ),
            "mitigation_condition": lambda district: (
                district.get("credits_pool", 100) > 60 and 
                district.get("jobs_available", 5) > 5
            ),
            "final_stage_effect": "trigger_world_flag:lume_economic_collapse"
        }
    }
    
    def __init__(self, seed: int = 42):
        """Initialize escalation system."""
        self.seed = seed
        random.seed(seed)
        self.chains: Dict[str, EscalationChain] = {}
        self.active_chains: Dict[str, EscalationChain] = {}  # district_id -> chain
    
    def check_triggers(self, districts: Dict, turn: int) -> List[EscalationChain]:
        """
        Check for new escalation chain triggers.
        
        Args:
            districts: Dictionary of district data
            turn: Current turn
            
        Returns:
            List of newly triggered chains
        """
        newly_triggered = []
        
        for chain_id, template in self.CHAIN_TEMPLATES.items():
            # Check each district for trigger conditions
            for district_id, district in districts.items():
                # Skip if chain already active in this district
                if district_id in self.active_chains:
                    continue
                
                # Check trigger condition
                if chain_id == "food_crisis":
                    if district.get("food_stock", 50) < 20:
                        # Check if condition persists (simplified - would track over turns)
                        chain = EscalationChain(
                            id=f"{chain_id}_{district_id}_{turn}",
                            trigger_condition=template["trigger_condition"],
                            stages=template["stages"].copy(),
                            current_stage=0,
                            severity=0.3,
                            district_id=district_id,
                            triggered_at_turn=turn,
                            last_advance_turn=turn
                        )
                        self.chains[chain.id] = chain
                        self.active_chains[district_id] = chain
                        newly_triggered.append(chain)
                        logger.info(f"Escalation chain triggered: {chain_id} in {district_id} at turn {turn}")
                
                elif chain_id == "political_tension":
                    if district.get("tension", 20) > 70:
                        chain = EscalationChain(
                            id=f"{chain_id}_{district_id}_{turn}",
                            trigger_condition=template["trigger_condition"],
                            stages=template["stages"].copy(),
                            current_stage=0,
                            severity=0.4,
                            district_id=district_id,
                            triggered_at_turn=turn,
                            last_advance_turn=turn
                        )
                        self.chains[chain.id] = chain
                        self.active_chains[district_id] = chain
                        newly_triggered.append(chain)
                        logger.info(f"Escalation chain triggered: {chain_id} in {district_id} at turn {turn}")
                
                elif chain_id == "economic_collapse":
                    if district.get("credits_pool", 100) < 30 and district.get("jobs_available", 5) < 3:
                        chain = EscalationChain(
                            id=f"{chain_id}_{district_id}_{turn}",
                            trigger_condition=template["trigger_condition"],
                            stages=template["stages"].copy(),
                            current_stage=0,
                            severity=0.35,
                            district_id=district_id,
                            triggered_at_turn=turn,
                            last_advance_turn=turn
                        )
                        self.chains[chain.id] = chain
                        self.active_chains[district_id] = chain
                        newly_triggered.append(chain)
                        logger.info(f"Escalation chain triggered: {chain_id} in {district_id} at turn {turn}")
        
        return newly_triggered
    
    def advance_chains(self, districts: Dict, turn: int, world_flags_system=None) -> List[str]:
        """
        Advance all active escalation chains.
        
        Args:
            districts: Dictionary of district data
            turn: Current turn
            world_flags_system: Optional WorldFlagsSystem to trigger flags
            
        Returns:
            List of stage transition messages
        """
        transitions = []
        chains_to_remove = []
        
        for district_id, chain in list(self.active_chains.items()):
            if district_id not in districts:
                chains_to_remove.append(district_id)
                continue
            
            district = districts[district_id]
            # Extract base chain type from chain ID (e.g., "food_crisis_region_kora_123" -> "food_crisis")
            chain_parts = chain.id.split("_")
            base_chain_type = "_".join(chain_parts[:2]) if len(chain_parts) >= 2 else chain_parts[0]
            template = self.CHAIN_TEMPLATES.get(base_chain_type)
            
            if not template:
                continue
            
            # Check if chain should advance
            advance_condition = template.get("advance_condition")
            if advance_condition and advance_condition(district, turn, chain.last_advance_turn):
                if not chain.is_final_stage():
                    chain.current_stage += 1
                    chain.last_advance_turn = turn
                    chain.stalled_turns = 0
                    chain.severity = min(1.0, chain.severity + 0.15)
                    
                    stage_name = chain.get_current_stage_name()
                    transitions.append(f"Escalation in {district_id}: advanced to {stage_name}")
                    logger.info(f"Escalation chain {chain.id} advanced to stage {chain.current_stage}: {stage_name}")
                    
                    # Check if final stage - trigger world flag
                    if chain.is_final_stage() and world_flags_system:
                        final_effect = template.get("final_stage_effect", "")
                        if final_effect.startswith("trigger_world_flag:"):
                            flag_id = final_effect.split(":")[1]
                            # Manually trigger the flag (would need to check conditions)
                            logger.info(f"Final stage reached: would trigger world flag {flag_id}")
                else:
                    # Final stage - chain is locked
                    chain.stalled_turns += 1
            else:
                # Check for mitigation (reverse)
                mitigation_condition = template.get("mitigation_condition")
                if mitigation_condition and mitigation_condition(district):
                    if chain.current_stage > 0:
                        chain.current_stage -= 1
                        chain.last_advance_turn = turn
                        chain.stalled_turns = 0
                        chain.severity = max(0.1, chain.severity - 0.1)
                        
                        stage_name = chain.get_current_stage_name()
                        transitions.append(f"Escalation in {district_id}: reversed to {stage_name}")
                        logger.info(f"Escalation chain {chain.id} reversed to stage {chain.current_stage}: {stage_name}")
                    else:
                        # Reversed to beginning - chain ends
                        chains_to_remove.append(district_id)
                        transitions.append(f"Escalation in {district_id}: resolved")
                        logger.info(f"Escalation chain {chain.id} resolved")
                else:
                    chain.stalled_turns += 1
        
        # Remove resolved chains
        for district_id in chains_to_remove:
            if district_id in self.active_chains:
                del self.active_chains[district_id]
        
        return transitions
    
    def get_chain(self, chain_id: str) -> Optional[EscalationChain]:
        """Get chain by ID."""
        return self.chains.get(chain_id)
    
    def get_active_chains(self) -> List[EscalationChain]:
        """Get all active chains."""
        return list(self.active_chains.values())
    
    def get_district_chain(self, district_id: str) -> Optional[EscalationChain]:
        """Get active chain for a district."""
        return self.active_chains.get(district_id)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "chains": {cid: chain.to_dict() for cid, chain in self.chains.items()},
            "active_chains": {did: cid for did, cid in self.active_chains.items() 
                            if cid in self.chains}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EscalationSystem":
        """Deserialize from dictionary."""
        obj = cls(seed=data.get("seed", 42))
        
        # Restore chains
        for cid, chain_data in data.get("chains", {}).items():
            obj.chains[cid] = EscalationChain.from_dict(chain_data)
        
        # Restore active chains mapping
        active_mapping = data.get("active_chains", {})
        for district_id, chain_id in active_mapping.items():
            if chain_id in obj.chains:
                obj.active_chains[district_id] = obj.chains[chain_id]
        
        return obj
