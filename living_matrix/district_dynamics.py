"""
District Dynamics System - Handles district collapse, merging, and wars.

Features:
- District Collapse: Districts can collapse when conditions are critical
- District Merging: Adjacent districts with low population can merge
- District Wars: Districts can fight over resources

This system runs each turn and generates events that affect the world.
"""

import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque

logger = logging.getLogger(__name__)


class DistrictState(Enum):
    """State of a district."""
    ACTIVE = "active"           # Normal functioning district
    STRUGGLING = "struggling"   # Low resources/population, at risk
    COLLAPSING = "collapsing"   # In the process of collapse
    COLLAPSED = "collapsed"     # No longer functional, absorbed or abandoned
    AT_WAR = "at_war"          # Currently in conflict with another district
    MERGING = "merging"        # In the process of merging


class WarType(Enum):
    """Types of district wars."""
    FOOD_RAID = "food_raid"           # Quick raid for food
    TERRITORY_DISPUTE = "territory"   # Border/land dispute
    RESOURCE_WAR = "resource_war"     # Full resource war
    IDEOLOGICAL = "ideological"       # Cultural/belief conflict
    RETALIATION = "retaliation"       # Response to previous attack


@dataclass
class DistrictWar:
    """Represents an ongoing war between districts."""
    war_id: str
    attacker_id: str
    defender_id: str
    war_type: WarType
    started_turn: int
    duration: int = 0           # How many turns the war has lasted
    intensity: float = 0.5      # 0-1, how intense the fighting is
    attacker_strength: float = 0.5
    defender_strength: float = 0.5
    casualties_attacker: int = 0
    casualties_defender: int = 0
    resources_stolen: float = 0.0
    victor: Optional[str] = None
    is_active: bool = True
    
    def get_status(self) -> str:
        """Get war status description."""
        if not self.is_active:
            return f"Ended - Victor: {self.victor or 'Draw'}"
        if self.intensity > 0.7:
            return "Fierce fighting"
        elif self.intensity > 0.4:
            return "Active conflict"
        else:
            return "Skirmishes"


@dataclass
class DistrictMerge:
    """Represents a pending district merge."""
    merge_id: str
    absorbing_district_id: str  # The district that absorbs others
    absorbed_district_ids: List[str]  # Districts being absorbed
    started_turn: int
    completion_turn: int  # When the merge completes
    reason: str  # Why the merge is happening
    is_complete: bool = False


@dataclass  
class DistrictCollapse:
    """Represents a district collapse event."""
    collapse_id: str
    district_id: str
    started_turn: int
    completion_turn: int
    reason: str
    refugees_to_districts: Dict[str, int] = field(default_factory=dict)
    resources_distributed: Dict[str, float] = field(default_factory=dict)
    is_complete: bool = False


@dataclass
class DistrictDynamicsState:
    """Extended state for district dynamics."""
    state: DistrictState = DistrictState.ACTIVE
    struggling_turns: int = 0      # Consecutive turns in struggling state
    collapse_progress: float = 0.0  # 0-1, how close to collapse
    war_weariness: float = 0.0     # 0-1, fatigue from wars
    defensive_strength: float = 0.5 # 0-1, ability to defend
    offensive_strength: float = 0.3 # 0-1, ability to attack
    alliance_with: Set[str] = field(default_factory=set)  # Allied districts
    enemies: Set[str] = field(default_factory=set)  # Enemy districts
    last_attacked_turn: int = 0
    last_attack_by: Optional[str] = None
    recent_wars: deque = field(default_factory=lambda: deque(maxlen=10))


# Constants for district dynamics
COLLAPSE_POPULATION_THRESHOLD = 5       # Min population before collapse risk
COLLAPSE_FOOD_THRESHOLD = 10.0          # Min food before collapse risk
COLLAPSE_TENSION_THRESHOLD = 95.0       # Tension level triggering collapse
STRUGGLING_TURNS_TO_COLLAPSE = 20       # Turns of struggling before collapse
MERGE_POPULATION_THRESHOLD = 20         # Max population for merge consideration
WAR_COOLDOWN_TURNS = 30                 # Min turns between wars
WAR_MAX_DURATION = 50                   # Max war duration
WAR_MIN_POPULATION_TO_ATTACK = 30       # Need this many people to start war
RAID_SUCCESS_FOOD_FRACTION = 0.3        # Fraction of food stolen in raid


class DistrictDynamicsSystem:
    """Manages district collapse, merging, and wars."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Track district dynamics state
        self.district_states: Dict[str, DistrictDynamicsState] = {}
        
        # Active conflicts and events
        self.active_wars: Dict[str, DistrictWar] = {}
        self.pending_merges: Dict[str, DistrictMerge] = {}
        self.pending_collapses: Dict[str, DistrictCollapse] = {}
        
        # History
        self.war_history: List[DistrictWar] = []
        self.merge_history: List[DistrictMerge] = []
        self.collapse_history: List[DistrictCollapse] = []
        
        # Event log for UI
        self.recent_events: deque = deque(maxlen=50)
        
        # Turn counter
        self.current_turn: int = 0
    
    def initialize_district(self, district_id: str):
        """Initialize dynamics state for a district."""
        if district_id not in self.district_states:
            self.district_states[district_id] = DistrictDynamicsState()
    
    def get_district_state(self, district_id: str) -> DistrictDynamicsState:
        """Get or create district dynamics state."""
        if district_id not in self.district_states:
            self.initialize_district(district_id)
        return self.district_states[district_id]
    
    def advance(self, districts: Dict, agents_by_district: Dict[str, int], 
                turn: int) -> List[Tuple[str, str, str]]:
        """
        Advance district dynamics by one turn.
        
        Args:
            districts: Dict of district_id -> AdvancedDistrict
            agents_by_district: Dict of district_id -> agent count
            turn: Current turn number
            
        Returns:
            List of (event_type, description, district_id) events
        """
        self.current_turn = turn
        events = []
        
        # Initialize any new districts
        for district_id in districts:
            self.initialize_district(district_id)
        
        # Phase 1: Update district states based on conditions
        for district_id, district in districts.items():
            state_events = self._update_district_state(
                district_id, district, 
                agents_by_district.get(district_id, 0)
            )
            events.extend(state_events)
        
        # Phase 2: Check for war opportunities
        war_events = self._check_war_opportunities(districts, agents_by_district)
        events.extend(war_events)
        
        # Phase 3: Advance active wars
        active_war_events = self._advance_wars(districts, agents_by_district)
        events.extend(active_war_events)
        
        # Phase 4: Check for mergers
        merge_events = self._check_merge_opportunities(districts, agents_by_district)
        events.extend(merge_events)
        
        # Phase 5: Advance pending merges
        merge_progress_events = self._advance_merges(districts)
        events.extend(merge_progress_events)
        
        # Phase 6: Check for collapses
        collapse_events = self._check_collapse_conditions(districts, agents_by_district)
        events.extend(collapse_events)
        
        # Phase 7: Advance pending collapses
        collapse_progress_events = self._advance_collapses(districts, agents_by_district)
        events.extend(collapse_progress_events)
        
        # Store events
        for event in events:
            self.recent_events.append((turn, *event))
        
        return events
    
    def _update_district_state(self, district_id: str, district, 
                               agent_count: int) -> List[Tuple[str, str, str]]:
        """Update district state based on current conditions."""
        events = []
        state = self.get_district_state(district_id)
        
        # Skip if already collapsed
        if state.state == DistrictState.COLLAPSED:
            return events
        
        # Check if district is struggling
        is_struggling = (
            agent_count < COLLAPSE_POPULATION_THRESHOLD * 2 or
            district.food_stock < COLLAPSE_FOOD_THRESHOLD * 2 or
            district.tension_state.tension > COLLAPSE_TENSION_THRESHOLD * 0.8
        )
        
        if is_struggling:
            if state.state != DistrictState.STRUGGLING:
                state.state = DistrictState.STRUGGLING
                state.struggling_turns = 1
                events.append(("district_struggling", 
                    f"{district.district_name} is struggling with {agent_count} residents",
                    district_id))
                logger.info(f"District {district_id} entered struggling state")
            else:
                state.struggling_turns += 1
        else:
            if state.state == DistrictState.STRUGGLING:
                state.state = DistrictState.ACTIVE
                state.struggling_turns = 0
                events.append(("district_recovered",
                    f"{district.district_name} has recovered from crisis",
                    district_id))
        
        # Update military strength based on population and resources
        pop_factor = min(1.0, agent_count / 100.0)
        resource_factor = min(1.0, district.food_stock / 200.0)
        tension_penalty = district.tension_state.tension / 200.0
        weariness_penalty = state.war_weariness * 0.5
        
        state.defensive_strength = max(0.1, 
            0.3 + pop_factor * 0.4 + resource_factor * 0.2 - tension_penalty - weariness_penalty
        )
        state.offensive_strength = max(0.05,
            0.1 + pop_factor * 0.5 + resource_factor * 0.3 - tension_penalty - weariness_penalty
        )
        
        # Decay war weariness
        state.war_weariness = max(0, state.war_weariness - 0.01)
        
        return events
    
    def _check_war_opportunities(self, districts: Dict, 
                                  agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Check if any district wants to start a war."""
        events = []
        
        for attacker_id, attacker in districts.items():
            attacker_state = self.get_district_state(attacker_id)
            attacker_pop = agents_by_district.get(attacker_id, 0)
            
            # Skip if already at war, collapsing, or too weak
            if (attacker_state.state in [DistrictState.AT_WAR, DistrictState.COLLAPSING, 
                                          DistrictState.COLLAPSED] or
                attacker_pop < WAR_MIN_POPULATION_TO_ATTACK):
                continue
            
            # Check war cooldown
            if self.current_turn - attacker_state.last_attacked_turn < WAR_COOLDOWN_TURNS:
                continue
            
            # Check if already in an active war
            in_war = any(
                w.attacker_id == attacker_id or w.defender_id == attacker_id
                for w in self.active_wars.values() if w.is_active
            )
            if in_war:
                continue
            
            # Determine if district wants to attack
            # More likely if: low food, high tension, high dominate intent
            food_scarcity = max(0, 1.0 - attacker.food_stock / 100.0)
            tension_factor = attacker.tension_state.tension / 100.0
            dominate_intent = attacker.intent.dominate if hasattr(attacker.intent, 'dominate') else 0.1
            
            attack_chance = (
                food_scarcity * 0.3 +
                tension_factor * 0.2 +
                dominate_intent * 0.3 +
                attacker_state.offensive_strength * 0.2
            ) * 0.1  # Base 10% modifier
            
            # Revenge motivation
            if attacker_state.last_attack_by and attacker_state.last_attack_by in districts:
                if self.current_turn - attacker_state.last_attacked_turn < 100:
                    attack_chance += 0.15  # Higher chance to retaliate
            
            if self.rng.random() < attack_chance:
                # Choose target - prefer weaker neighbors with more resources
                target = self._choose_war_target(attacker_id, attacker_state, 
                                                  districts, agents_by_district)
                if target:
                    war_events = self._start_war(attacker_id, target, districts)
                    events.extend(war_events)
        
        return events
    
    def _choose_war_target(self, attacker_id: str, attacker_state: DistrictDynamicsState,
                           districts: Dict, agents_by_district: Dict[str, int]) -> Optional[str]:
        """Choose a target for war."""
        candidates = []
        
        for target_id, target in districts.items():
            if target_id == attacker_id:
                continue
            
            # Skip allies
            if target_id in attacker_state.alliance_with:
                continue
            
            target_state = self.get_district_state(target_id)
            target_pop = agents_by_district.get(target_id, 0)
            
            # Skip collapsed or collapsing
            if target_state.state in [DistrictState.COLLAPSED, DistrictState.COLLAPSING]:
                continue
            
            # Score based on: resources available, weakness, revenge factor
            resource_score = target.food_stock / 100.0
            weakness_score = 1.0 - target_state.defensive_strength
            revenge_score = 0.5 if target_id in attacker_state.enemies else 0.0
            
            total_score = resource_score * 0.4 + weakness_score * 0.4 + revenge_score * 0.2
            
            if total_score > 0.2:  # Minimum viable target
                candidates.append((target_id, total_score))
        
        if not candidates:
            return None
        
        # Weight selection by score
        total_weight = sum(c[1] for c in candidates)
        if total_weight <= 0:
            return None
        
        r = self.rng.random() * total_weight
        cumulative = 0
        for target_id, score in candidates:
            cumulative += score
            if r <= cumulative:
                return target_id
        
        return candidates[-1][0]
    
    def _start_war(self, attacker_id: str, defender_id: str, 
                   districts: Dict) -> List[Tuple[str, str, str]]:
        """Start a war between two districts."""
        events = []
        
        attacker = districts[attacker_id]
        defender = districts[defender_id]
        attacker_state = self.get_district_state(attacker_id)
        defender_state = self.get_district_state(defender_id)
        
        # Determine war type
        if attacker.food_stock < 50:
            war_type = WarType.FOOD_RAID
        elif attacker_id == defender_state.last_attack_by:
            war_type = WarType.RETALIATION
        elif self.rng.random() < 0.3:
            war_type = WarType.IDEOLOGICAL
        else:
            war_type = WarType.RESOURCE_WAR
        
        war_id = f"war_{self.current_turn}_{attacker_id}_{defender_id}"
        
        war = DistrictWar(
            war_id=war_id,
            attacker_id=attacker_id,
            defender_id=defender_id,
            war_type=war_type,
            started_turn=self.current_turn,
            attacker_strength=attacker_state.offensive_strength,
            defender_strength=defender_state.defensive_strength,
            intensity=0.3 + self.rng.random() * 0.4
        )
        
        self.active_wars[war_id] = war
        
        # Update states
        attacker_state.state = DistrictState.AT_WAR
        defender_state.state = DistrictState.AT_WAR
        attacker_state.enemies.add(defender_id)
        defender_state.enemies.add(attacker_id)
        
        # Generate event
        war_desc = f"{attacker.district_name} declares {war_type.value} on {defender.district_name}!"
        events.append(("war_declared", war_desc, attacker_id))
        events.append(("war_declared", f"{defender.district_name} is under attack by {attacker.district_name}!", defender_id))
        
        logger.warning(f"WAR: {attacker_id} attacks {defender_id} ({war_type.value})")
        
        return events
    
    def _advance_wars(self, districts: Dict, 
                      agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Advance all active wars."""
        events = []
        wars_to_end = []
        
        for war_id, war in self.active_wars.items():
            if not war.is_active:
                continue
            
            war.duration += 1
            
            # Get current districts
            if war.attacker_id not in districts or war.defender_id not in districts:
                wars_to_end.append(war_id)
                continue
            
            attacker = districts[war.attacker_id]
            defender = districts[war.defender_id]
            attacker_pop = agents_by_district.get(war.attacker_id, 0)
            defender_pop = agents_by_district.get(war.defender_id, 0)
            
            attacker_state = self.get_district_state(war.attacker_id)
            defender_state = self.get_district_state(war.defender_id)
            
            # Calculate battle outcome this turn
            attacker_power = attacker_state.offensive_strength * (1 + attacker_pop / 200.0)
            defender_power = defender_state.defensive_strength * (1 + defender_pop / 200.0)
            
            # Random factors
            attacker_roll = self.rng.random() * 0.3 + 0.85
            defender_roll = self.rng.random() * 0.3 + 0.85
            
            attacker_power *= attacker_roll
            defender_power *= defender_roll
            
            # Determine casualties (1-3% of population per turn of war)
            casualty_rate = war.intensity * 0.03
            attacker_casualties = max(0, int(attacker_pop * casualty_rate * defender_power / max(0.1, attacker_power)))
            defender_casualties = max(0, int(defender_pop * casualty_rate * attacker_power / max(0.1, defender_power)))
            
            war.casualties_attacker += attacker_casualties
            war.casualties_defender += defender_casualties
            
            # War effects on tension
            attacker.tension_state.tension = min(100, attacker.tension_state.tension + 2)
            defender.tension_state.tension = min(100, defender.tension_state.tension + 3)
            
            # Increase war weariness
            attacker_state.war_weariness = min(1.0, attacker_state.war_weariness + 0.02)
            defender_state.war_weariness = min(1.0, defender_state.war_weariness + 0.025)
            
            # Check for raid success (quick food grab)
            if war.war_type == WarType.FOOD_RAID and war.duration >= 3:
                if attacker_power > defender_power * 1.2:
                    # Raid successful
                    stolen_food = defender.food_stock * RAID_SUCCESS_FOOD_FRACTION
                    defender.food_stock -= stolen_food
                    attacker.food_stock += stolen_food * 0.8  # Some lost in transport
                    war.resources_stolen += stolen_food
                    war.victor = war.attacker_id
                    wars_to_end.append(war_id)
                    events.append(("raid_success", 
                        f"{attacker.district_name} raids {defender.district_name}, stealing {stolen_food:.0f} food!",
                        war.attacker_id))
                elif war.duration > 10:
                    # Raid failed - retreat
                    war.victor = war.defender_id
                    wars_to_end.append(war_id)
                    events.append(("raid_failed",
                        f"{attacker.district_name}'s raid on {defender.district_name} fails!",
                        war.attacker_id))
            
            # Check for war end conditions
            elif war.duration >= WAR_MAX_DURATION:
                # War exhaustion - draw
                war.victor = None
                wars_to_end.append(war_id)
                events.append(("war_exhaustion",
                    f"War between {attacker.district_name} and {defender.district_name} ends in exhaustion",
                    war.attacker_id))
            
            elif attacker_pop < 10 or attacker_state.war_weariness > 0.9:
                # Attacker gives up
                war.victor = war.defender_id
                wars_to_end.append(war_id)
                events.append(("war_surrender",
                    f"{attacker.district_name} surrenders to {defender.district_name}!",
                    war.defender_id))
            
            elif defender_pop < 10 or defender_state.war_weariness > 0.9:
                # Defender surrenders
                war.victor = war.attacker_id
                # Transfer resources
                transfer = defender.food_stock * 0.5
                defender.food_stock -= transfer
                attacker.food_stock += transfer * 0.7
                war.resources_stolen += transfer
                wars_to_end.append(war_id)
                events.append(("war_victory",
                    f"{attacker.district_name} defeats {defender.district_name}! Resources seized.",
                    war.attacker_id))
            
            # Generate periodic battle events
            elif war.duration % 5 == 0 and war.intensity > 0.5:
                battle_desc = f"Fighting continues between {attacker.district_name} and {defender.district_name}"
                if war.casualties_attacker + war.casualties_defender > 10:
                    battle_desc += f" ({war.casualties_attacker + war.casualties_defender} casualties so far)"
                events.append(("battle", battle_desc, war.attacker_id))
        
        # End wars
        for war_id in wars_to_end:
            self._end_war(war_id, districts)
        
        return events
    
    def _end_war(self, war_id: str, districts: Dict):
        """End a war and update states."""
        if war_id not in self.active_wars:
            return
        
        war = self.active_wars[war_id]
        war.is_active = False
        
        # Update district states
        attacker_state = self.get_district_state(war.attacker_id)
        defender_state = self.get_district_state(war.defender_id)
        
        # Return to active state if not struggling
        if war.attacker_id in districts:
            attacker = districts[war.attacker_id]
            if attacker.food_stock > COLLAPSE_FOOD_THRESHOLD * 2:
                attacker_state.state = DistrictState.ACTIVE
        
        if war.defender_id in districts:
            defender = districts[war.defender_id]
            if defender.food_stock > COLLAPSE_FOOD_THRESHOLD * 2:
                defender_state.state = DistrictState.ACTIVE
        
        # Track revenge
        if war.victor == war.defender_id:
            attacker_state.last_attacked_turn = self.current_turn
            attacker_state.last_attack_by = war.defender_id
        
        # Store in history
        self.war_history.append(war)
        
        logger.info(f"War {war_id} ended. Victor: {war.victor or 'Draw'}")
    
    def _check_merge_opportunities(self, districts: Dict, 
                                   agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Check if districts should merge."""
        events = []
        
        # Find struggling districts with low population
        struggling = []
        for district_id, district in districts.items():
            state = self.get_district_state(district_id)
            pop = agents_by_district.get(district_id, 0)
            
            if (state.state == DistrictState.STRUGGLING and 
                pop < MERGE_POPULATION_THRESHOLD and
                state.struggling_turns > 10):
                struggling.append(district_id)
        
        if len(struggling) < 2:
            return events
        
        # Check if any pair should merge
        for i, d1_id in enumerate(struggling):
            for d2_id in struggling[i+1:]:
                d1_state = self.get_district_state(d1_id)
                d2_state = self.get_district_state(d2_id)
                
                # Skip if enemies
                if d2_id in d1_state.enemies or d1_id in d2_state.enemies:
                    continue
                
                # Skip if already in merge/collapse
                if any(d1_id in m.absorbed_district_ids or d2_id in m.absorbed_district_ids 
                       for m in self.pending_merges.values()):
                    continue
                
                # Merge chance based on desperation
                d1 = districts[d1_id]
                d2 = districts[d2_id]
                merge_chance = (
                    (d1_state.struggling_turns + d2_state.struggling_turns) / 100.0 +
                    (1.0 - d1.food_stock / 100.0) * 0.2 +
                    (1.0 - d2.food_stock / 100.0) * 0.2
                )
                
                if self.rng.random() < merge_chance * 0.05:
                    merge_events = self._start_merge(d1_id, d2_id, districts, agents_by_district)
                    events.extend(merge_events)
                    break
        
        return events
    
    def _start_merge(self, d1_id: str, d2_id: str, districts: Dict,
                     agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Start a district merge."""
        events = []
        
        d1 = districts[d1_id]
        d2 = districts[d2_id]
        pop1 = agents_by_district.get(d1_id, 0)
        pop2 = agents_by_district.get(d2_id, 0)
        
        # Larger district absorbs smaller
        if pop1 >= pop2:
            absorbing_id, absorbed_id = d1_id, d2_id
            absorbing, absorbed = d1, d2
        else:
            absorbing_id, absorbed_id = d2_id, d1_id
            absorbing, absorbed = d2, d1
        
        merge_id = f"merge_{self.current_turn}_{absorbing_id}_{absorbed_id}"
        
        merge = DistrictMerge(
            merge_id=merge_id,
            absorbing_district_id=absorbing_id,
            absorbed_district_ids=[absorbed_id],
            started_turn=self.current_turn,
            completion_turn=self.current_turn + 10,  # 10 turns to merge
            reason=f"Population consolidation"
        )
        
        self.pending_merges[merge_id] = merge
        
        # Update states
        absorbing_state = self.get_district_state(absorbing_id)
        absorbed_state = self.get_district_state(absorbed_id)
        
        absorbed_state.state = DistrictState.MERGING
        
        events.append(("merge_started",
            f"{absorbed.district_name} is merging into {absorbing.district_name} for survival",
            absorbing_id))
        
        logger.info(f"MERGE: {absorbed_id} merging into {absorbing_id}")
        
        return events
    
    def _advance_merges(self, districts: Dict) -> List[Tuple[str, str, str]]:
        """Advance pending merges."""
        events = []
        completed_merges = []
        
        for merge_id, merge in self.pending_merges.items():
            if merge.is_complete:
                continue
            
            if self.current_turn >= merge.completion_turn:
                # Complete the merge
                merge.is_complete = True
                completed_merges.append(merge_id)
                
                absorbing = districts.get(merge.absorbing_district_id)
                
                for absorbed_id in merge.absorbed_district_ids:
                    if absorbed_id in districts:
                        absorbed = districts[absorbed_id]
                        
                        # Transfer resources to absorbing district
                        if absorbing:
                            absorbing.food_stock += absorbed.food_stock * 0.7
                            absorbing.credits_pool += absorbed.credits_pool * 0.7
                            absorbing.jobs_available += absorbed.jobs_available
                        
                        # Mark as collapsed (will be removed from active simulation)
                        absorbed_state = self.get_district_state(absorbed_id)
                        absorbed_state.state = DistrictState.COLLAPSED
                        
                        events.append(("merge_complete",
                            f"{absorbed.district_name} has been absorbed into {absorbing.district_name if absorbing else 'unknown'}",
                            absorbed_id))
                
                self.merge_history.append(merge)
        
        return events
    
    def _check_collapse_conditions(self, districts: Dict, 
                                   agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Check if any district should collapse."""
        events = []
        
        for district_id, district in districts.items():
            state = self.get_district_state(district_id)
            pop = agents_by_district.get(district_id, 0)
            
            # Skip if already collapsing or collapsed
            if state.state in [DistrictState.COLLAPSING, DistrictState.COLLAPSED]:
                continue
            
            # Check collapse conditions
            should_collapse = False
            reason = ""
            
            if pop < COLLAPSE_POPULATION_THRESHOLD:
                should_collapse = True
                reason = f"Population too low ({pop} residents)"
            elif district.food_stock < COLLAPSE_FOOD_THRESHOLD and pop > 0:
                should_collapse = True
                reason = f"Starvation (no food)"
            elif district.tension_state.tension > COLLAPSE_TENSION_THRESHOLD:
                if state.struggling_turns > STRUGGLING_TURNS_TO_COLLAPSE:
                    should_collapse = True
                    reason = "Civil unrest and prolonged crisis"
            elif state.struggling_turns > STRUGGLING_TURNS_TO_COLLAPSE * 2:
                should_collapse = True
                reason = "Extended period of struggle"
            
            if should_collapse:
                collapse_events = self._start_collapse(district_id, district, reason, 
                                                       districts, agents_by_district)
                events.extend(collapse_events)
        
        return events
    
    def _start_collapse(self, district_id: str, district, reason: str,
                        districts: Dict, agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Start a district collapse."""
        events = []
        
        collapse_id = f"collapse_{self.current_turn}_{district_id}"
        
        # Calculate refugee distribution
        pop = agents_by_district.get(district_id, 0)
        refugees_to = {}
        
        if pop > 0:
            # Distribute refugees to other districts
            other_districts = [d for d in districts.keys() if d != district_id]
            if other_districts:
                per_district = pop // len(other_districts)
                remainder = pop % len(other_districts)
                
                for i, other_id in enumerate(other_districts):
                    refugees_to[other_id] = per_district + (1 if i < remainder else 0)
        
        # Distribute resources
        resources_to = {}
        if district.food_stock > 0:
            other_districts = [d for d in districts.keys() if d != district_id]
            if other_districts:
                per_district = district.food_stock / len(other_districts)
                for other_id in other_districts:
                    resources_to[other_id] = per_district
        
        collapse = DistrictCollapse(
            collapse_id=collapse_id,
            district_id=district_id,
            started_turn=self.current_turn,
            completion_turn=self.current_turn + 5,  # 5 turns to collapse
            reason=reason,
            refugees_to_districts=refugees_to,
            resources_distributed=resources_to
        )
        
        self.pending_collapses[collapse_id] = collapse
        
        state = self.get_district_state(district_id)
        state.state = DistrictState.COLLAPSING
        
        events.append(("collapse_started",
            f"{district.district_name} is collapsing! {reason}",
            district_id))
        
        logger.warning(f"COLLAPSE: {district_id} is collapsing - {reason}")
        
        return events
    
    def _advance_collapses(self, districts: Dict, 
                           agents_by_district: Dict[str, int]) -> List[Tuple[str, str, str]]:
        """Advance pending collapses."""
        events = []
        
        for collapse_id, collapse in self.pending_collapses.items():
            if collapse.is_complete:
                continue
            
            if self.current_turn >= collapse.completion_turn:
                collapse.is_complete = True
                
                if collapse.district_id in districts:
                    district = districts[collapse.district_id]
                    
                    # Distribute resources to other districts
                    for other_id, resources in collapse.resources_distributed.items():
                        if other_id in districts:
                            districts[other_id].food_stock += resources * 0.5  # 50% lost
                    
                    # Mark as collapsed
                    state = self.get_district_state(collapse.district_id)
                    state.state = DistrictState.COLLAPSED
                    
                    # Zero out resources
                    district.food_stock = 0
                    district.credits_pool = 0
                    district.jobs_available = 0
                    
                    events.append(("collapse_complete",
                        f"{district.district_name} has collapsed! Refugees flee to nearby districts.",
                        collapse.district_id))
                    
                    # Notify receiving districts
                    for other_id, refugee_count in collapse.refugees_to_districts.items():
                        if other_id in districts and refugee_count > 0:
                            events.append(("refugees_arrived",
                                f"{refugee_count} refugees from {district.district_name} arrive in {districts[other_id].district_name}",
                                other_id))
                
                self.collapse_history.append(collapse)
        
        return events
    
    def get_war_status(self, district_id: str) -> Optional[Dict]:
        """Get current war status for a district."""
        for war in self.active_wars.values():
            if war.is_active and (war.attacker_id == district_id or war.defender_id == district_id):
                return {
                    "war_id": war.war_id,
                    "war_type": war.war_type.value,
                    "role": "attacker" if war.attacker_id == district_id else "defender",
                    "opponent": war.defender_id if war.attacker_id == district_id else war.attacker_id,
                    "duration": war.duration,
                    "intensity": war.intensity,
                    "status": war.get_status()
                }
        return None
    
    def get_district_summary(self, district_id: str) -> Dict:
        """Get summary of district dynamics."""
        state = self.get_district_state(district_id)
        
        return {
            "state": state.state.value,
            "struggling_turns": state.struggling_turns,
            "war_weariness": state.war_weariness,
            "defensive_strength": state.defensive_strength,
            "offensive_strength": state.offensive_strength,
            "allies": list(state.alliance_with),
            "enemies": list(state.enemies),
            "current_war": self.get_war_status(district_id)
        }
    
    def get_global_status(self) -> Dict:
        """Get global district dynamics status."""
        active_districts = sum(1 for s in self.district_states.values() 
                               if s.state == DistrictState.ACTIVE)
        struggling = sum(1 for s in self.district_states.values() 
                        if s.state == DistrictState.STRUGGLING)
        at_war = sum(1 for s in self.district_states.values() 
                    if s.state == DistrictState.AT_WAR)
        collapsed = sum(1 for s in self.district_states.values() 
                       if s.state == DistrictState.COLLAPSED)
        
        return {
            "active_districts": active_districts,
            "struggling_districts": struggling,
            "districts_at_war": at_war,
            "collapsed_districts": collapsed,
            "active_wars": len([w for w in self.active_wars.values() if w.is_active]),
            "total_wars": len(self.war_history),
            "total_merges": len(self.merge_history),
            "total_collapses": len(self.collapse_history),
            "recent_events": list(self.recent_events)[-10:]
        }
