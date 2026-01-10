"""Agent-related dataclasses."""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class HumanNeeds:
    """Human needs (0-100, higher = more urgent)."""
    hunger: int = 30
    rest: int = 40
    safety: int = 70
    belonging: int = 50
    purpose: int = 60


@dataclass
class HumanTraits:
    """Personality traits (0.0-1.0)."""
    risk: float = 0.5
    empathy: float = 0.5
    ambition: float = 0.5
    patience: float = 0.5


@dataclass
class HumanInventory:
    """Agent inventory."""
    food: int = 5
    credits: int = 20
    tools: int = 0


@dataclass
class HumanAgent:
    """A human agent with needs, goals, and traits."""
    id: str
    name: str
    district: str  # District/region name
    location: str  # Current place/location ID
    home_location: str  # Home place ID
    
    role: str  # worker, trader, guard, medic, student, etc.
    needs: HumanNeeds = field(default_factory=HumanNeeds)
    traits: HumanTraits = field(default_factory=HumanTraits)
    inventory: HumanInventory = field(default_factory=HumanInventory)
    
    goals: List[str] = field(default_factory=list)  # Dynamic goal list
    mood: float = 0.0  # -1.0 to +1.0, derived from needs + events
    memory: deque = field(default_factory=lambda: deque(maxlen=10))  # Last N events
    
    # State
    current_action: str = "idle"
    last_action_turn: int = 0
    
    # Beliefs (subjective reality) - forward reference
    beliefs: Dict[str, object] = field(default_factory=dict)  # topic -> Belief
    
    # Relationships (enhanced social graph) - forward reference
    relationships: Dict[str, object] = field(default_factory=dict)  # target_id -> Relationship
    
    # Sex/Gender (for reproduction)
    sex: str = "male"  # "male" or "female" - determines reproduction compatibility
    
    # Aging and life cycle
    age: int = 0  # Age in turns
    lifespan: int = 1000  # Randomized at birth (turns until death)
    is_alive: bool = True  # Whether agent is alive
    death_turn: Optional[int] = None  # Turn when agent died (None if alive)
    
    # Family relationships
    children_ids: List[str] = field(default_factory=list)
    parents_ids: List[str] = field(default_factory=list)
    
    # Survival instinct (SYSTEM 10)
    survival_drive: float = 0.8  # 0..1 (how urgently agent wants continuity)
    reproduction_drive: float = 0.5  # 0..1 (personal reproduction urge)
    legacy_drive: float = 0.3  # 0..1 (desire to leave something behind)
    
    # Track losses for legacy drive
    dead_friends_count: int = 0  # Dead friends/children increase legacy drive
    
    # SYSTEM A: Hard reproduction constraint
    must_attempt_reproduction: bool = False  # When extinction_risk > 0.6, this becomes True
    
    # SYSTEM B: Future resource bonus (children create resources)
    future_resource_bonus: float = 0.0  # Applied when child reaches maturity or in clusters


@dataclass
class AgentNeeds:
    """Agent needs (0.0-1.0, higher = more urgent)."""
    rest: float = 0.5
    food: float = 0.5  # hunger (renamed for clarity)
    safety: float = 0.3
    social: float = 0.4
    purpose: float = 0.5
    
    @property
    def hunger(self) -> float:
        """Alias for food need (hunger)."""
        return self.food
    
    @hunger.setter
    def hunger(self, value: float):
        """Set hunger (food need)."""
        self.food = max(0.0, min(1.0, value))


@dataclass
class AgentMood:
    """Agent mood state."""
    calm: float = 0.6
    tense: float = 0.2
    curious: float = 0.2


@dataclass
class Relationship:
    """Relationship between agents (world_sim version)."""
    other_id: str
    type_tag: str  # friend, colleague, neighbor, acquaintance
    strength: float  # 0.0-1.0


@dataclass
class Agent:
    """An agent in the world."""
    id: str
    name: str
    role: str  # courier, worker, trader, keeper, wanderer, etc.
    home_location: str
    current_location: str
    needs: AgentNeeds = field(default_factory=AgentNeeds)
    mood: AgentMood = field(default_factory=AgentMood)
    schedule: str = "free"  # sleep, work, free
    memory: deque = field(default_factory=lambda: deque(maxlen=20))
    relationships: List[Relationship] = field(default_factory=list)
    
    # New fields for consequence-driven simulation
    energy: float = 0.7  # 0.0-1.0, physical energy
    stress: float = 0.3  # 0.0-1.0, stress level
    credits: float = 10.0  # Abstract currency for trade
    risk: float = 0.5  # 0.0-1.0, risk tolerance
    social_trait: float = 0.5  # 0.0-1.0, social preference
    work_ethic: float = 0.6  # 0.0-1.0, work preference
    location_success: Dict[str, float] = field(default_factory=dict)  # region_id -> success count
    location_failure: Dict[str, float] = field(default_factory=dict)  # region_id -> failure count
    
    # Intent system - forward reference
    intent: object = field(default_factory=lambda: None)  # Will be set by Intent import
