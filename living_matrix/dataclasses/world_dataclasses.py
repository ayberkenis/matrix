"""World-related dataclasses."""

from typing import List, Optional, Dict
from dataclasses import dataclass, field
from collections import deque
from enum import Enum


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
class Drives:
    """Internal drives that influence behavior."""
    stability: float = 0.5  # Prefers repeating coherent motifs
    novelty: float = 0.5    # Prefers introducing new symbols
    cohesion: float = 0.5   # Prefers tightening clusters/relationships
    expression: float = 0.5 # Prefers producing longer/structured output
    
    def normalize(self):
        """Ensure all drives are in [0, 1] range."""
        self.stability = max(0.0, min(1.0, self.stability))
        self.novelty = max(0.0, min(1.0, self.novelty))
        self.cohesion = max(0.0, min(1.0, self.cohesion))
        self.expression = max(0.0, min(1.0, self.expression))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "stability": self.stability,
            "novelty": self.novelty,
            "cohesion": self.cohesion,
            "expression": self.expression
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Drives":
        """Deserialize from dictionary."""
        return cls(
            stability=data.get("stability", 0.5),
            novelty=data.get("novelty", 0.5),
            cohesion=data.get("cohesion", 0.5),
            expression=data.get("expression", 0.5)
        )


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
    
    # New multi-dimensional tension - forward reference
    multi_tension: object = field(default_factory=lambda: None)  # Will be set by Tension import


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
    
    # Intent (district-level goals) - forward reference
    intent: object = field(default_factory=lambda: None)  # Will be set by Intent import
    
    # Active events
    active_events: List[WorldEvent] = field(default_factory=list)
    
    # Migration tracking
    population_in: int = 0
    population_out: int = 0
    
    # Culture - forward reference
    culture: object = field(default_factory=lambda: None)  # Will be set by Culture import
    
    # Social enforcement of birth (SYSTEM 13)
    birth_pressure: float = 0.0  # 0..1 (district-level pressure for reproduction)
    
    # POPULATION COMPRESSION: Child pool tracking
    child_pool: int = 0  # Number of children in compressed pool
    active_agents: int = 0  # Number of active agents in this district
    total_population: int = 0  # active_agents + child_pool
    population_pressure: float = 0.0  # 0..1 (pressure from population size vs resources)


# Note: WorldState is complex and references SemanticGraph and EpisodicMemory classes
# It should remain in world.py for now, or we can move just the dataclass definition here
# For now, keeping WorldState in world.py since it has complex dependencies
