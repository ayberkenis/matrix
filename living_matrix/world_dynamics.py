"""Advanced world dynamics: pressure signals, tension as stored energy, events, psychology.

Features:
- Pressure signals (food, jobs, weather, migration, rumor, inequality)
- Multi-dimensional tension (economic, social, political, existential)
- District events (riots, strikes, migrations, shutdowns)
- District dynamics (collapse, merging, wars between districts)
"""

import random
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
from living_matrix.tension import Tension as MultiTension
from living_matrix.dataclasses import Intent
from living_matrix.culture import Culture, CultureSystem
from living_matrix.district_dynamics import (
    DistrictDynamicsSystem, DistrictState, DistrictDynamicsState,
    DistrictWar, WarType
)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types with tension effects."""
    # TENSION INCREASING
    FOOD_SHORTAGE_WAVE = "food_shortage_wave"
    UNEMPLOYMENT_SPIKE = "unemployment_spike"
    EXTREME_WEATHER = "extreme_weather"
    RUMOR_SPREAD = "rumor_spread"
    INEQUALITY_AWARENESS = "inequality_awareness"
    AGENT_CONFLICT = "agent_conflict"
    
    # TENSION DECREASING
    AID_DISTRIBUTION = "aid_distribution"
    TRADE_SUCCESS = "trade_success"
    COMMUNAL_REST = "communal_rest"
    CULTURAL_EVENT = "cultural_event"
    MEDIATION = "mediation"
    AUTHORITY_INTERVENTION = "authority_intervention"
    
    # TENSION RELEASE (non-linear)
    RIOT = "riot"
    STRIKE = "strike"
    MASS_MIGRATION = "mass_migration"
    DISTRICT_SHUTDOWN = "district_shutdown"


@dataclass
class DistrictPressure:
    """Continuous pressure signals per district."""
    food: float = 0.0  # 0-1, clamp(1 - food_stock / ideal_food, 0, 1)
    jobs: float = 0.0  # 0-1, clamp(1 - jobs_available / ideal_jobs, 0, 1)
    weather: float = 0.0  # 0-1, accumulated over prolonged bad weather
    migration: float = 0.0  # 0-1, incoming/outgoing population imbalance
    rumor: float = 0.0  # 0-1, propagated via social events
    inequality: float = 0.0  # 0-1, comparison with neighboring districts


@dataclass
class DistrictPsychology:
    """District memory and psychological state."""
    trauma_score: float = 0.0  # 0-1, increases with riots, disasters
    trust_score: float = 0.5  # 0-1, increases with aid, stability
    fatigue_score: float = 0.0  # 0-1, chronic stress indicator
    recent_events: deque = field(default_factory=lambda: deque(maxlen=20))  # Rolling window


@dataclass
class DistrictTension:
    """Tension as stored stress energy (now multi-dimensional)."""
    # Keep old single tension for backward compatibility
    tension: float = 20.0  # 0-100, stored energy (legacy, use multi_tension instead)
    tension_pressure: float = 0.0  # Accumulating pressure this turn
    tension_release: float = 0.0  # Episodic release
    tension_decay: float = 0.5  # Baseline decay per turn
    last_turn: int = 0  # Track for trend calculation
    
    # New multi-dimensional tension
    multi_tension: MultiTension = field(default_factory=lambda: MultiTension(
        economic=20.0,
        social=20.0,
        political=15.0,
        existential=10.0
    ))
    
    def get_tension(self) -> float:
        """Get legacy single tension value (average of multi-dimensional)."""
        return self.multi_tension.get_average()
    
    def set_tension(self, value: float):
        """Set legacy tension (distributes to all dimensions)."""
        self.multi_tension.economic = value
        self.multi_tension.social = value
        self.multi_tension.political = value * 0.75
        self.multi_tension.existential = value * 0.5
        self.tension = value


@dataclass
class WorldEvent:
    """A world event with effects."""
    event_type: EventType
    district_id: str
    turn: int
    severity: float  # 0-1
    duration: int  # Turns remaining (0 = instant)
    effects: Dict[str, float]  # tension_change, resource_change, etc.


@dataclass
class AdvancedDistrict:
    """Advanced district with pressure, tension, psychology."""
    district_id: str
    district_name: str
    
    # Resources
    food_stock: float = 50.0  # 0-100
    credits_pool: float = 100.0
    jobs_available: int = 5
    security_level: float = 70.0  # 0-100
    
    # Production
    production_rate: float = 1.0
    workplace_count: int = 2
    
    # Ideal levels (for pressure calculation)
    ideal_food: float = 50.0
    ideal_jobs: int = 8
    
    # Pressure signals
    pressure: DistrictPressure = field(default_factory=DistrictPressure)
    
    # Tension as stored energy
    tension_state: DistrictTension = field(default_factory=DistrictTension)
    
    # Psychology
    psychology: DistrictPsychology = field(default_factory=DistrictPsychology)
    
    # Intent (district-level goals)
    intent: Intent = field(default_factory=lambda: Intent(
        survive=0.4,
        explore=0.2,
        cooperate=0.5,
        dominate=0.1,
        escape=0.1
    ))
    
    # Active events
    active_events: List[WorldEvent] = field(default_factory=list)
    
    # Migration tracking
    population_in: int = 0
    population_out: int = 0
    
    # Culture
    culture: Culture = field(default_factory=lambda: Culture())
    
    # Social enforcement of birth (SYSTEM 13)
    birth_pressure: float = 0.0  # 0..1 (district-level pressure for reproduction)
    
    # POPULATION COMPRESSION: Child pool tracking
    child_pool: int = 0  # Number of children in compressed pool
    active_agents: int = 0  # Number of active agents in this district
    total_population: int = 0  # active_agents + child_pool
    population_pressure: float = 0.0  # 0..1 (pressure from population size vs resources)
    
    # AGENT-DRIVEN FOOD SYSTEM
    food_capacity: float = 500.0  # Dynamic max food storage
    population: int = 0  # Current total population (for agent decisions)
    weather_farm_modifier: float = 1.0  # Weather impact on farming
    weather_hunt_modifier: float = 1.0  # Weather impact on hunting
    
    # DISTRICT DYNAMICS: State, wars, alliances
    dynamics_state: DistrictState = DistrictState.ACTIVE
    is_at_war: bool = False
    war_opponent: Optional[str] = None
    war_casualties: int = 0
    allies: Set[str] = field(default_factory=set)
    enemies: Set[str] = field(default_factory=set)
    is_collapsed: bool = False
    collapse_reason: Optional[str] = None


class WorldDynamicsSystem:
    """Manages advanced world dynamics with pressure, tension, events, psychology."""
    
    def __init__(self, districts: List[str], seed: int = 42):
        """Initialize world dynamics system."""
        self.seed = seed
        random.seed(seed)
        self.districts: Dict[str, AdvancedDistrict] = {}
        self.global_turn: int = 0
        self.culture_system = CultureSystem(seed=seed)
        
        # DISTRICT DYNAMICS: Wars, mergers, collapses
        self.district_dynamics = DistrictDynamicsSystem(seed=seed)
        
        # Initialize districts
        for district_id in districts:
            district_name = district_id.replace("region_", "").title()
            # Start with reasonable food supply
            initial_food = random.uniform(150, 300)  # Enough for ~50-100 agents initially
            district = AdvancedDistrict(
                district_id=district_id,
                district_name=district_name,
                food_stock=initial_food,
                food_capacity=500.0,  # Will be dynamically adjusted
                credits_pool=random.uniform(50, 150),
                jobs_available=random.randint(3, 8),
                security_level=random.uniform(60, 90),
                production_rate=random.uniform(0.8, 1.2),
                workplace_count=random.randint(1, 4),
                ideal_food=random.uniform(45, 55),
                ideal_jobs=random.randint(6, 10)
            )
            # Initialize culture for district
            self.culture_system.initialize_district_culture(district_id)
            district.culture = self.culture_system.get_culture(district_id)
            self.districts[district_id] = district
            
            # Initialize district dynamics state
            self.district_dynamics.initialize_district(district_id)
    
    def calculate_pressures(self, district_id: str, weather_state: Dict, 
                           neighboring_districts: List[str]) -> DistrictPressure:
        """Calculate pressure signals for a district."""
        if district_id not in self.districts:
            return DistrictPressure()
        
        district = self.districts[district_id]
        pressure = DistrictPressure()
        
        # Food pressure
        if district.ideal_food > 0:
            food_ratio = district.food_stock / district.ideal_food
            pressure.food = max(0.0, min(1.0, 1.0 - food_ratio))
        
        # Job pressure
        if district.ideal_jobs > 0:
            job_ratio = district.jobs_available / district.ideal_jobs
            pressure.jobs = max(0.0, min(1.0, 1.0 - job_ratio))
        
        # Weather pressure (accumulated over bad weather)
        if weather_state:
            precip = weather_state.get("precipitation", 0)
            wind = weather_state.get("wind", 0)
            if precip > 0.7 or wind > 0.7:
                pressure.weather = min(1.0, district.pressure.weather + 0.1)
            else:
                pressure.weather = max(0.0, district.pressure.weather - 0.05)
        else:
            pressure.weather = max(0.0, district.pressure.weather - 0.05)
        
        # Migration pressure (population imbalance)
        if district.population_in > district.population_out:
            imbalance = (district.population_in - district.population_out) / max(1, district.population_in + district.population_out)
            pressure.migration = min(1.0, imbalance * 0.5)
        else:
            pressure.migration = max(0.0, district.pressure.migration - 0.05)
        
        # Rumor pressure (from psychology)
        pressure.rumor = district.psychology.trauma_score * 0.5 + district.psychology.fatigue_score * 0.3
        
        # Inequality pressure (compare with neighbors)
        if neighboring_districts:
            neighbor_tensions = []
            for neighbor_id in neighboring_districts:
                if neighbor_id in self.districts:
                    neighbor = self.districts[neighbor_id]
                    neighbor_tensions.append(neighbor.tension_state.tension)
            
            if neighbor_tensions:
                avg_neighbor_tension = sum(neighbor_tensions) / len(neighbor_tensions)
                if district.tension_state.tension < avg_neighbor_tension * 0.7:
                    # We're better off, but aware of inequality
                    pressure.inequality = min(1.0, (avg_neighbor_tension - district.tension_state.tension) / 100.0 * 0.3)
                else:
                    pressure.inequality = 0.0
        
        return pressure
    
    def update_tension(self, district_id: str, turn: int):
        """Update tension as stored stress energy."""
        if district_id not in self.districts:
            return
        
        district = self.districts[district_id]
        tension = district.tension_state
        
        # Calculate weighted pressure sum
        weights = {
            "food": 0.25,
            "jobs": 0.20,
            "weather": 0.15,
            "migration": 0.10,
            "rumor": 0.15,
            "inequality": 0.15
        }
        
        pressure_sum = (
            district.pressure.food * weights["food"] +
            district.pressure.jobs * weights["jobs"] +
            district.pressure.weather * weights["weather"] +
            district.pressure.migration * weights["migration"] +
            district.pressure.rumor * weights["rumor"] +
            district.pressure.inequality * weights["inequality"]
        )
        
        # Modify by psychology
        trauma_multiplier = 1.0 + district.psychology.trauma_score * 0.5
        trust_multiplier = 1.0 - district.psychology.trust_score * 0.3
        
        # Accumulate pressure
        tension.tension_pressure = pressure_sum * trauma_multiplier * trust_multiplier
        
        # Add to tension
        tension.tension += tension.tension_pressure
        
        # Apply release (from events)
        tension.tension -= tension.tension_release
        tension.tension_release = 0.0  # Reset after application
        
        # Calculate decay (adaptive) - prevents tension plateaus
        base_decay = tension.tension_decay
        if tension.tension > 85:
            # Increase decay at extreme values to prevent saturation
            # Exponential increase: decay becomes very strong at 95+
            excess = max(0, tension.tension - 85)
            adaptive_decay = base_decay * (1.0 + excess / 10.0 * 3.0)  # Up to 3x at 95+
        elif tension.tension > 70:
            # Moderate increase
            adaptive_decay = base_decay * (1.0 + (tension.tension - 70) / 15.0 * 0.5)
        else:
            adaptive_decay = base_decay
        
        # Trust increases decay (feedback loop)
        trust_bonus = district.psychology.trust_score * 0.3
        final_decay = adaptive_decay + trust_bonus
        
        # Apply decay
        tension.tension -= final_decay
        
        # Clamp tension
        tension.tension = max(0.0, min(100.0, tension.tension))
        
        # Update psychology based on tension
        if tension.tension > 70:
            district.psychology.fatigue_score = min(1.0, district.psychology.fatigue_score + 0.01)
        else:
            district.psychology.fatigue_score = max(0.0, district.psychology.fatigue_score - 0.005)
        
        tension.last_turn = turn
    
    def generate_events(self, district_id: str, turn: int, weather_state: Dict, 
                        world_flags_system=None) -> List[WorldEvent]:
        """Generate events based on district state."""
        if district_id not in self.districts:
            return []
        
        district = self.districts[district_id]
        events = []
        
        # Event probabilities modified by psychology
        trauma_modifier = 1.0 + district.psychology.trauma_score * 0.5
        fatigue_modifier = 1.0 + district.psychology.fatigue_score * 0.3
        
        # TENSION INCREASING EVENTS
        
        # Food shortage wave
        base_prob = 0.15 * trauma_modifier
        if world_flags_system:
            base_prob = world_flags_system.modify_event_probability("food_shortage", base_prob)
        if district.pressure.food > 0.7 and random.random() < base_prob:
            events.append(WorldEvent(
                event_type=EventType.FOOD_SHORTAGE_WAVE,
                district_id=district_id,
                turn=turn,
                severity=district.pressure.food,
                duration=random.randint(3, 8),
                effects={"tension_change": 5.0, "food_change": -5.0}
            ))
        
        # Unemployment spike
        if district.pressure.jobs > 0.6 and random.random() < 0.12 * fatigue_modifier:
            events.append(WorldEvent(
                event_type=EventType.UNEMPLOYMENT_SPIKE,
                district_id=district_id,
                turn=turn,
                severity=district.pressure.jobs,
                duration=random.randint(2, 6),
                effects={"tension_change": 4.0, "jobs_change": -1}
            ))
        
        # Extreme weather
        if district.pressure.weather > 0.8 and weather_state and random.random() < 0.2:
            events.append(WorldEvent(
                event_type=EventType.EXTREME_WEATHER,
                district_id=district_id,
                turn=turn,
                severity=district.pressure.weather,
                duration=random.randint(2, 5),
                effects={"tension_change": 3.0, "food_change": -3.0}
            ))
        
        # Rumor spread
        if district.pressure.rumor > 0.5 and random.random() < 0.1:
            events.append(WorldEvent(
                event_type=EventType.RUMOR_SPREAD,
                district_id=district_id,
                turn=turn,
                severity=district.pressure.rumor,
                duration=random.randint(1, 4),
                effects={"tension_change": 2.0, "rumor_pressure": 0.1}
            ))
        
        # Agent conflict
        if district.tension_state.tension > 60 and random.random() < 0.08 * trauma_modifier:
            events.append(WorldEvent(
                event_type=EventType.AGENT_CONFLICT,
                district_id=district_id,
                turn=turn,
                severity=district.tension_state.tension / 100.0,
                duration=0,  # Instant
                effects={"tension_change": 3.0, "trauma": 0.05}
            ))
        
        # TENSION DECREASING EVENTS
        
        # Aid distribution
        if district.tension_state.tension > 70 and district.pressure.food > 0.5 and random.random() < 0.1:
            events.append(WorldEvent(
                event_type=EventType.AID_DISTRIBUTION,
                district_id=district_id,
                turn=turn,
                severity=0.6,
                duration=0,
                effects={"tension_change": -8.0, "food_change": 15.0, "trust": 0.1}
            ))
        
        # Trade success
        if district.pressure.food < 0.5 and random.random() < 0.15:
            events.append(WorldEvent(
                event_type=EventType.TRADE_SUCCESS,
                district_id=district_id,
                turn=turn,
                severity=0.4,
                duration=0,
                effects={"tension_change": -3.0, "food_change": 5.0, "trust": 0.05}
            ))
        
        # Communal rest
        if district.psychology.fatigue_score > 0.6 and random.random() < 0.12:
            events.append(WorldEvent(
                event_type=EventType.COMMUNAL_REST,
                district_id=district_id,
                turn=turn,
                severity=0.5,
                duration=random.randint(1, 3),
                effects={"tension_change": -4.0, "fatigue": -0.1}
            ))
        
        # TENSION RELEASE EVENTS (non-linear, reduce tension after)
        
        # Riot (forced release if tension too high)
        if district.tension_state.tension > 90 and random.random() < 0.3:
            release_amount = min(30.0, district.tension_state.tension * 0.3)
            events.append(WorldEvent(
                event_type=EventType.RIOT,
                district_id=district_id,
                turn=turn,
                severity=0.9,
                duration=random.randint(1, 3),
                effects={"tension_change": 10.0, "tension_release": release_amount, "trauma": 0.2, "security": -10.0}
            ))
        
        # Strike
        if district.pressure.jobs > 0.7 and district.tension_state.tension > 75 and random.random() < 0.2:
            release_amount = min(20.0, district.tension_state.tension * 0.2)
            events.append(WorldEvent(
                event_type=EventType.STRIKE,
                district_id=district_id,
                turn=turn,
                severity=0.7,
                duration=random.randint(2, 5),
                effects={"tension_change": 5.0, "tension_release": release_amount, "jobs_change": -2}
            ))
        
        return events
    
    def apply_event(self, event: WorldEvent):
        """Apply event effects to district."""
        if event.district_id not in self.districts:
            return
        
        district = self.districts[event.district_id]
        
        # Apply effects
        if "tension_change" in event.effects:
            district.tension_state.tension = max(0.0, min(100.0, 
                district.tension_state.tension + event.effects["tension_change"]))
        
        if "tension_release" in event.effects:
            district.tension_state.tension_release += event.effects["tension_release"]
        
        if "food_change" in event.effects:
            district.food_stock = max(0.0, min(100.0, district.food_stock + event.effects["food_change"]))
        
        if "jobs_change" in event.effects:
            district.jobs_available = max(0, district.jobs_available + int(event.effects["jobs_change"]))
        
        if "trauma" in event.effects:
            district.psychology.trauma_score = min(1.0, district.psychology.trauma_score + event.effects["trauma"])
        
        if "trust" in event.effects:
            district.psychology.trust_score = min(1.0, district.psychology.trust_score + event.effects["trust"])
        
        if "fatigue" in event.effects:
            district.psychology.fatigue_score = max(0.0, min(1.0, 
                district.psychology.fatigue_score + event.effects["fatigue"]))
        
        if "security" in event.effects:
            district.security_level = max(0.0, min(100.0, district.security_level + event.effects["security"]))
        
        if "rumor_pressure" in event.effects:
            district.pressure.rumor = min(1.0, district.pressure.rumor + event.effects["rumor_pressure"])
        
        # Record event in psychology
        district.psychology.recent_events.append({
            "type": event.event_type.value,
            "severity": event.severity,
            "turn": event.turn
        })
        
        # Update trauma for destructive events
        if event.event_type in [EventType.RIOT, EventType.STRIKE, EventType.EXTREME_WEATHER]:
            district.psychology.trauma_score = min(1.0, district.psychology.trauma_score + 0.1)
    
    def advance(self, district_id: str, agent_count: int, weather_state: Dict, 
               neighboring_districts: List[str], turn: int):
        """Advance district one turn."""
        if district_id not in self.districts:
            return
        
        district = self.districts[district_id]
        self.global_turn = turn
        
        # Production efficiency (reduced by tension)
        production_efficiency = max(0.3, 1.0 - district.tension_state.tension / 200.0)
        
        # =====================================================================
        # AGENT-DRIVEN FOOD SYSTEM
        # Food is produced by agents farming/hunting (in execute_action)
        # Here we only handle: consumption, spoilage, natural regen, capacity
        # =====================================================================
        
        # Calculate food capacity (scales with population)
        from living_matrix.constants.economy_constants import (
            FOOD_PER_CAPITA_CAPACITY, MIN_FOOD_CAPACITY, MAX_FOOD_CAPACITY,
            FOOD_CONSUMPTION_PER_AGENT, FOOD_CONSUMPTION_CHILD,
            NATURAL_FOOD_REGEN_BASE, FOOD_SPOILAGE_RATE, FOOD_SPOILAGE_THRESHOLD,
            STARVATION_THRESHOLD, SCARCITY_THRESHOLD
        )
        
        total_pop = agent_count + district.child_pool
        district.food_capacity = max(
            MIN_FOOD_CAPACITY,
            min(MAX_FOOD_CAPACITY, total_pop * FOOD_PER_CAPITA_CAPACITY + 100)
        )
        
        # Store population for agent decision making
        district.population = total_pop
        
        # Calculate weather modifiers for agent actions
        weather_farm_mod = 1.0
        weather_hunt_mod = 1.0
        if weather_state:
            precip = weather_state.get('precipitation', 0)
            temp = weather_state.get('temperature', 20)
            if precip > 0.7 or temp > 40 or temp < -10:
                weather_farm_mod = 0.3
                weather_hunt_mod = 0.5
            elif precip > 0.4 or temp > 35 or temp < 0:
                weather_farm_mod = 0.6
                weather_hunt_mod = 0.8
            elif precip < 0.2 and 15 < temp < 30:
                weather_farm_mod = 1.3
                weather_hunt_mod = 1.1
        district.weather_farm_modifier = weather_farm_mod
        district.weather_hunt_modifier = weather_hunt_mod
        
        # Natural food regeneration (environment provides some food)
        natural_regen = NATURAL_FOOD_REGEN_BASE * production_efficiency * weather_farm_mod
        district.food_stock = min(district.food_capacity, district.food_stock + natural_regen)
        
        # Food consumption (passive - agents also eat via trade action)
        # Reduced consumption since agents also eat via actions
        agent_consumption = agent_count * FOOD_CONSUMPTION_PER_AGENT
        child_consumption = district.child_pool * FOOD_CONSUMPTION_CHILD
        total_consumption = agent_consumption + child_consumption
        district.food_stock = max(0.0, district.food_stock - total_consumption)
        
        # Food spoilage (only if above threshold)
        if district.food_stock > FOOD_SPOILAGE_THRESHOLD:
            spoilage = (district.food_stock - FOOD_SPOILAGE_THRESHOLD) * FOOD_SPOILAGE_RATE
            district.food_stock -= spoilage
        
        # Calculate food per capita for pressure calculation
        food_per_capita = district.food_stock / max(1, total_pop)
        
        # Calculate food pressure (inverse of abundance)
        if food_per_capita < STARVATION_THRESHOLD:
            district.pressure.food = 1.0  # Maximum pressure
        elif food_per_capita < SCARCITY_THRESHOLD:
            district.pressure.food = 0.7 + (SCARCITY_THRESHOLD - food_per_capita) / SCARCITY_THRESHOLD * 0.3
        else:
            district.pressure.food = max(0.0, 0.7 - food_per_capita * 0.2)
        
        # =====================================================================
        # CREDITS PRODUCTION (unchanged)
        # =====================================================================
        if district.workplace_count > 0 and district.jobs_available > 0:
            credits_produced = int(district.jobs_available * district.production_rate * production_efficiency * 2)
            district.credits_pool = min(200.0, district.credits_pool + credits_produced)
        
        # Jobs regenerate slowly (reduced by tension)
        if district.jobs_available < district.ideal_jobs:
            regen_rate = max(0.1, 1.0 - district.tension_state.tension / 150.0)
            if random.random() < regen_rate:
                district.jobs_available = min(district.ideal_jobs, district.jobs_available + 1)
        
        # Update active events
        for event in list(district.active_events):
            event.duration -= 1
            if event.duration <= 0:
                district.active_events.remove(event)
        
        # Calculate pressures
        district.pressure = self.calculate_pressures(district_id, weather_state, neighboring_districts)
        
        # Update tension
        self.update_tension(district_id, turn)
        
        # Prevent tension plateaus: forced release if stuck at extreme
        if district.tension_state.tension > 95:
            # Very high tension: force release event
            if random.random() < 0.4:  # 40% chance per turn
                release_amount = min(25.0, district.tension_state.tension * 0.25)
                district.tension_state.tension_release += release_amount
                # Create a release event
                release_event = WorldEvent(
                    event_type=EventType.RIOT,
                    district_id=district_id,
                    turn=turn,
                    severity=0.95,
                    duration=random.randint(1, 2),
                    effects={"tension_change": 5.0, "tension_release": release_amount, "trauma": 0.15}
                )
                self.apply_event(release_event)
                if release_event.duration > 0:
                    district.active_events.append(release_event)
        
        # Generate new events (pass world_flags_system if available)
        world_flags_system = getattr(self, '_world_flags_system', None)
        new_events = self.generate_events(district_id, turn, weather_state, world_flags_system)
        for event in new_events:
            self.apply_event(event)
            if event.duration > 0:
                district.active_events.append(event)
        
        # Natural psychology decay
        district.psychology.trauma_score = max(0.0, district.psychology.trauma_score - 0.001)
        district.psychology.trust_score = min(1.0, district.psychology.trust_score + 0.0005)
        
        # Feedback loops: high tension reduces productivity (already applied above)
        # Aid events increase trust and reduce tension (handled in events)
        # Migration tracking (simplified)
        if district.tension_state.tension > 80:
            # High tension: some agents might leave
            if random.random() < 0.1:
                district.population_out += 1
        elif district.tension_state.tension < 30:
            # Low tension: might attract agents
            if random.random() < 0.05:
                district.population_in += 1
    
    def get_tension_trend(self, district_id: str) -> str:
        """Get tension trend: rising, falling, or stable."""
        if district_id not in self.districts:
            return "stable"
        
        district = self.districts[district_id]
        pressure_sum = (
            district.pressure.food + district.pressure.jobs + 
            district.pressure.weather + district.pressure.migration +
            district.pressure.rumor + district.pressure.inequality
        ) / 6.0
        
        if pressure_sum > 0.6:
            return "rising"
        elif pressure_sum < 0.3:
            return "falling"
        else:
            return "stable"
    
    def get_risk_flags(self, district_id: str) -> Dict[str, bool]:
        """Get risk flags for a district."""
        if district_id not in self.districts:
            return {"riot_risk": False, "migration_risk": False, "collapse_risk": False}
        
        district = self.districts[district_id]
        tension = district.tension_state.tension
        
        return {
            "riot_risk": tension > 85,
            "migration_risk": tension > 70 and district.pressure.migration > 0.5,
            "collapse_risk": tension > 95 and district.psychology.trust_score < 0.2
        }
    
    def get_district(self, district_id: str) -> Optional[AdvancedDistrict]:
        """Get district by ID."""
        return self.districts.get(district_id)
    
    def get_all_districts(self) -> List[AdvancedDistrict]:
        """Get all districts."""
        return list(self.districts.values())
    
    # =========================================================================
    # DISTRICT DYNAMICS: Wars, Mergers, Collapses
    # =========================================================================
    
    def advance_district_dynamics(self, agents_by_district: Dict[str, int], 
                                   turn: int) -> List[Tuple[str, str, str]]:
        """
        Advance district dynamics (wars, mergers, collapses) for one turn.
        
        This should be called ONCE per turn after all individual district advances.
        
        Args:
            agents_by_district: Dict of district_id -> agent count
            turn: Current turn number
            
        Returns:
            List of (event_type, description, district_id) events
        """
        events = self.district_dynamics.advance(
            self.districts, agents_by_district, turn
        )
        
        # Handle create_district_request events
        filtered_events = []
        for event in events:
            if event[0] == "create_district_request":
                # Parse the request: CREATE:proposal_id:name:pioneer_count:source_district_id
                parts = event[1].split(":")
                if len(parts) >= 5 and parts[0] == "CREATE":
                    proposal_id = parts[1]
                    new_name = parts[2]
                    pioneer_count = int(parts[3])
                    source_id = parts[4]
                    
                    # Generate new district ID
                    new_id = f"region_{new_name.lower().replace(' ', '_').replace("'", '')}"
                    
                    # Get initial resources from proposal
                    proposal = self.district_dynamics.pending_new_districts.get(proposal_id)
                    if proposal:
                        initial_food = proposal.initial_resources.get("food", 100.0)
                        initial_credits = proposal.initial_resources.get("credits", 50.0)
                    else:
                        initial_food = 100.0
                        initial_credits = 50.0
                    
                    # Create the district
                    self.create_new_district(
                        district_id=new_id,
                        district_name=new_name,
                        initial_food=initial_food,
                        initial_credits=initial_credits,
                        source_district_id=source_id
                    )
                # Don't include create_district_request in returned events
            else:
                filtered_events.append(event)
        events = filtered_events
        
        # Sync district state with dynamics system
        for district_id, district in self.districts.items():
            dyn_state = self.district_dynamics.get_district_state(district_id)
            
            # Update district fields from dynamics state
            district.dynamics_state = dyn_state.state
            district.is_at_war = dyn_state.state == DistrictState.AT_WAR
            district.is_collapsed = dyn_state.state == DistrictState.COLLAPSED
            district.allies = dyn_state.alliance_with
            district.enemies = dyn_state.enemies
            
            # Get war info
            war_status = self.district_dynamics.get_war_status(district_id)
            if war_status:
                district.war_opponent = war_status.get('opponent')
                district.war_casualties = self._get_war_casualties(district_id)
            else:
                district.war_opponent = None
                district.war_casualties = 0
        
        return events
    
    def _get_war_casualties(self, district_id: str) -> int:
        """Get total war casualties for a district."""
        casualties = 0
        for war in self.district_dynamics.active_wars.values():
            if war.attacker_id == district_id:
                casualties += war.casualties_attacker
            elif war.defender_id == district_id:
                casualties += war.casualties_defender
        return casualties
    
    def get_district_war_status(self, district_id: str) -> Optional[Dict]:
        """Get war status for a specific district."""
        return self.district_dynamics.get_war_status(district_id)
    
    def get_district_dynamics_summary(self, district_id: str) -> Dict:
        """Get dynamics summary for a district."""
        return self.district_dynamics.get_district_summary(district_id)
    
    def get_global_dynamics_status(self) -> Dict:
        """Get global district dynamics status."""
        return self.district_dynamics.get_global_status()
    
    def get_active_wars(self) -> List[Dict]:
        """Get list of all active wars."""
        wars = []
        for war in self.district_dynamics.active_wars.values():
            if war.is_active:
                attacker = self.districts.get(war.attacker_id)
                defender = self.districts.get(war.defender_id)
                wars.append({
                    "war_id": war.war_id,
                    "attacker": war.attacker_id,
                    "attacker_name": attacker.district_name if attacker else war.attacker_id,
                    "defender": war.defender_id,
                    "defender_name": defender.district_name if defender else war.defender_id,
                    "war_type": war.war_type.value,
                    "duration": war.duration,
                    "intensity": war.intensity,
                    "casualties_attacker": war.casualties_attacker,
                    "casualties_defender": war.casualties_defender,
                    "status": war.get_status()
                })
        return wars
    
    def get_collapsed_districts(self) -> List[str]:
        """Get list of collapsed district IDs."""
        return [
            d_id for d_id, state in self.district_dynamics.district_states.items()
            if state.state == DistrictState.COLLAPSED
        ]
    
    def is_district_active(self, district_id: str) -> bool:
        """Check if a district is still active (not collapsed)."""
        state = self.district_dynamics.get_district_state(district_id)
        return state.state != DistrictState.COLLAPSED
    
    def force_alliance(self, district1_id: str, district2_id: str):
        """Force an alliance between two districts."""
        state1 = self.district_dynamics.get_district_state(district1_id)
        state2 = self.district_dynamics.get_district_state(district2_id)
        
        state1.alliance_with.add(district2_id)
        state2.alliance_with.add(district1_id)
        
        # Remove from enemies if present
        state1.enemies.discard(district2_id)
        state2.enemies.discard(district1_id)
        
        logger.info(f"Alliance formed between {district1_id} and {district2_id}")
    
    def force_war(self, attacker_id: str, defender_id: str) -> bool:
        """Force a war to start between two districts."""
        if attacker_id not in self.districts or defender_id not in self.districts:
            return False
        
        events = self.district_dynamics._start_war(attacker_id, defender_id, self.districts)
        return len(events) > 0
    
    def create_new_district(self, district_id: str, district_name: str, 
                            initial_food: float = 100.0, initial_credits: float = 50.0,
                            source_district_id: str = None) -> bool:
        """
        Create a new district (typically from expansion).
        
        Args:
            district_id: Unique ID for the new district
            district_name: Display name for the district
            initial_food: Starting food stock
            initial_credits: Starting credits pool
            source_district_id: ID of district pioneers came from (optional)
            
        Returns:
            True if district was created successfully
        """
        if district_id in self.districts:
            logger.warning(f"District {district_id} already exists")
            return False
        
        # Create the new district
        district = AdvancedDistrict(
            district_id=district_id,
            district_name=district_name,
            food_stock=initial_food,
            food_capacity=500.0,
            credits_pool=initial_credits,
            jobs_available=2,  # Start with few jobs
            security_level=50.0,  # Lower security initially
            production_rate=0.8,  # Lower productivity initially
            workplace_count=1,
            ideal_food=50.0,
            ideal_jobs=5
        )
        
        # Initialize culture (slightly different from source if available)
        self.culture_system.initialize_district_culture(district_id)
        district.culture = self.culture_system.get_culture(district_id)
        
        # Add to districts
        self.districts[district_id] = district
        
        # Initialize district dynamics state
        self.district_dynamics.initialize_district(district_id)
        
        logger.info(f"NEW DISTRICT CREATED: {district_name} ({district_id})")
        
        return True
    
    def get_pending_new_districts(self) -> List[Dict]:
        """Get list of pending new district proposals."""
        return self.district_dynamics.get_pending_districts()
    
    def get_new_district_history(self) -> List[Dict]:
        """Get history of established new districts."""
        return self.district_dynamics.get_established_districts_history()