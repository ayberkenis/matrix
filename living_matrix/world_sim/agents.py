"""Agent system with needs, routines, and relationships."""

import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque


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
    """Relationship between agents."""
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


class AgentSystem:
    """Manages all agents in the world."""
    
    ROLE_NAMES = ['courier', 'worker', 'trader', 'keeper', 'wanderer', 'guard', 'builder', 'scout']
    NAME_PARTS = ['Ari', 'Kora', 'Vex', 'Lume', 'Nex', 'Zeph', 'Rift', 'Tara', 'Vey', 'Mira', 'Jax', 'Kira']
    
    def __init__(self, locations: List[str], num_agents: int = 80, seed: int = 42):
        """
        Initialize agent system.
        
        Args:
            locations: List of location IDs where agents can be
            num_agents: Number of agents to create
            seed: Random seed for deterministic behavior
        """
        self.seed = seed
        random.seed(seed)
        self.locations = locations
        self.agents: Dict[str, Agent] = {}
        self._create_agents(num_agents)
        self._create_relationships()
    
    def _create_agents(self, num_agents: int):
        """Create agents with fictional names and roles."""
        for i in range(num_agents):
            agent_id = f"agent_{i}"
            name = random.choice(self.NAME_PARTS) + random.choice(self.NAME_PARTS)
            role = random.choice(self.ROLE_NAMES)
            home_location = random.choice(self.locations)
            
            agent = Agent(
                id=agent_id,
                name=name,
                role=role,
                home_location=home_location,
                current_location=home_location,
                needs=AgentNeeds(
                    rest=random.uniform(0.3, 0.7),
                    food=random.uniform(0.3, 0.7),
                    safety=random.uniform(0.1, 0.4),
                    social=random.uniform(0.2, 0.6),
                    purpose=random.uniform(0.3, 0.7)
                ),
                mood=AgentMood(
                    calm=random.uniform(0.5, 0.8),
                    tense=random.uniform(0.1, 0.3),
                    curious=random.uniform(0.1, 0.4)
                )
            )
            
            self.agents[agent_id] = agent
    
    def _create_relationships(self):
        """Create relationships between agents (2-6 per agent)."""
        agent_list = list(self.agents.values())
        
        for agent in agent_list:
            num_relationships = random.randint(2, 6)
            candidates = [a for a in agent_list if a.id != agent.id]
            selected = random.sample(candidates, min(num_relationships, len(candidates)))
            
            for other in selected:
                rel_type = random.choice(['friend', 'colleague', 'neighbor', 'acquaintance'])
                strength = random.uniform(0.3, 0.9)
                agent.relationships.append(Relationship(
                    other_id=other.id,
                    type_tag=rel_type,
                    strength=strength
                ))
    
    def _update_schedule(self, agent: Agent, hour: int):
        """Update agent schedule based on time of day."""
        if 22 <= hour or hour < 6:
            agent.schedule = "sleep"
        elif 6 <= hour < 9 or 17 <= hour < 22:
            agent.schedule = "free"
        else:
            agent.schedule = "work"
    
    def _update_needs(self, agent: Agent):
        """Update agent needs (drift toward urgency)."""
        # Needs increase over time
        agent.needs.rest += random.uniform(0.01, 0.03)
        agent.needs.food += random.uniform(0.01, 0.02)
        agent.needs.social += random.uniform(0.005, 0.015)
        agent.needs.purpose += random.uniform(0.005, 0.01)
        
        # Clamp to [0, 1]
        agent.needs.rest = min(1.0, agent.needs.rest)
        agent.needs.food = min(1.0, agent.needs.food)
        agent.needs.social = min(1.0, agent.needs.social)
        agent.needs.purpose = min(1.0, agent.needs.purpose)
    
    def _update_mood(self, agent: Agent):
        """Update agent mood (slow drift)."""
        # Mood drifts slightly
        agent.mood.calm += random.uniform(-0.02, 0.02)
        agent.mood.tense += random.uniform(-0.02, 0.02)
        agent.mood.curious += random.uniform(-0.01, 0.01)
        
        # Normalize to sum to 1.0
        total = agent.mood.calm + agent.mood.tense + agent.mood.curious
        if total > 0:
            agent.mood.calm /= total
            agent.mood.tense /= total
            agent.mood.curious /= total
    
    def advance(self, world_map, hour: int) -> List[Tuple[str, str]]:
        """
        Advance all agents by one turn.
        
        Args:
            world_map: WorldMap instance
            hour: Current hour (0-23)
            
        Returns:
            List of (agent_id, action_description) tuples
        """
        actions = []
        
        for agent in self.agents.values():
            # Update schedule
            self._update_schedule(agent, hour)
            self._update_needs(agent)
            self._update_mood(agent)
            
            # Determine action based on schedule and needs
            action = self._determine_action(agent, world_map, hour)
            actions.append((agent.id, action))
            
            # Record in memory
            agent.memory.append(action)
        
        return actions
    
    def _determine_action(self, agent: Agent, world_map, hour: int) -> str:
        """Determine what action an agent takes this turn."""
        # If sleeping, stay at home
        if agent.schedule == "sleep" and agent.current_location != agent.home_location:
            agent.current_location = agent.home_location
            return f"{agent.name} returns home to rest"
        
        # If sleeping and at home, rest
        if agent.schedule == "sleep":
            agent.needs.rest = max(0.0, agent.needs.rest - 0.1)
            return f"{agent.name} rests at {world_map.get_location(agent.home_location).name}"
        
        # If work time, go to work location (or stay if already there)
        if agent.schedule == "work":
            work_locations = [loc for loc in world_map.locations.values() 
                            if loc.type_tag in ['industrial', 'civic', 'market']]
            if work_locations:
                if agent.current_location not in [loc.id for loc in work_locations]:
                    work_loc = random.choice(work_locations)
                    agent.current_location = work_loc.id
                    return f"{agent.name} goes to work at {work_loc.name}"
                else:
                    agent.needs.purpose = max(0.0, agent.needs.purpose - 0.05)
                    return f"{agent.name} works at {world_map.get_location(agent.current_location).name}"
        
        # Free time: satisfy needs
        if agent.needs.food > 0.7:
            market_locations = [loc for loc in world_map.locations.values() 
                              if loc.type_tag == 'market']
            if market_locations:
                market = random.choice(market_locations)
                agent.current_location = market.id
                agent.needs.food = max(0.0, agent.needs.food - 0.3)
                return f"{agent.name} trades for food at {market.name}"
        
        if agent.needs.rest > 0.7 and agent.current_location != agent.home_location:
            agent.current_location = agent.home_location
            return f"{agent.name} returns home to rest"
        
        if agent.needs.social > 0.6:
            # Go to a location with other agents
            crowded_locations = world_map.get_hotspots(top_n=5)
            if crowded_locations:
                loc, _ = random.choice(crowded_locations)
                agent.current_location = loc.id
                agent.needs.social = max(0.0, agent.needs.social - 0.2)
                return f"{agent.name} visits {loc.name} to socialize"
        
        # Default: stay or move randomly
        if random.random() < 0.3:
            transit_locations = [loc for loc in world_map.locations.values() 
                               if loc.type_tag == 'transit']
            if transit_locations:
                loc = random.choice(transit_locations)
                agent.current_location = loc.id
                return f"{agent.name} moves to {loc.name}"
        
        return f"{agent.name} is at {world_map.get_location(agent.current_location).name}"
    
    def update_crowd_densities(self, world_map):
        """Update crowd densities based on agent locations."""
        # Count agents per location
        location_counts: Dict[str, int] = {}
        for agent in self.agents.values():
            location_counts[agent.current_location] = location_counts.get(agent.current_location, 0) + 1
        
        # Update densities (normalize by max expected crowd)
        max_crowd = max(location_counts.values()) if location_counts else 0
        for loc_id, count in location_counts.items():
            density = min(1.0, count / 15.0)  # 15 agents = max density
            world_map.update_crowd_density(loc_id, density)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for agent in self.agents.values():
            if name_lower in agent.name.lower():
                return agent
        return None
    
    def get_agents_at_location(self, location_id: str) -> List[Agent]:
        """Get all agents at a location."""
        return [a for a in self.agents.values() if a.current_location == location_id]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "agents": {
                aid: {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "home_location": a.home_location,
                    "current_location": a.current_location,
                    "needs": {
                        "rest": a.needs.rest,
                        "food": a.needs.food,
                        "safety": a.needs.safety,
                        "social": a.needs.social,
                        "purpose": a.needs.purpose
                    },
                    "mood": {
                        "calm": a.mood.calm,
                        "tense": a.mood.tense,
                        "curious": a.mood.curious
                    },
                    "schedule": a.schedule,
                    "memory": list(a.memory),
                    "energy": getattr(a, 'energy', 0.7),
                    "stress": getattr(a, 'stress', 0.3),
                    "credits": getattr(a, 'credits', 10.0),
                    "risk": getattr(a, 'risk', 0.5),
                    "social_trait": getattr(a, 'social_trait', 0.5),
                    "work_ethic": getattr(a, 'work_ethic', 0.6),
                    "location_success": getattr(a, 'location_success', {}),
                    "location_failure": getattr(a, 'location_failure', {}),
                    "relationships": [
                        {
                            "other_id": r.other_id,
                            "type_tag": r.type_tag,
                            "strength": r.strength
                        }
                        for r in a.relationships
                    ]
                }
                for aid, a in self.agents.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict, locations: List[str]) -> "AgentSystem":
        """Deserialize from dictionary."""
        num_agents = len(data.get("agents", {}))
        obj = cls(locations=locations, num_agents=num_agents, seed=data.get("seed", 42))
        
        for aid, adata in data.get("agents", {}).items():
            if aid in obj.agents:
                agent = obj.agents[aid]
                agent.name = adata["name"]
                agent.role = adata["role"]
                agent.home_location = adata["home_location"]
                agent.current_location = adata["current_location"]
                agent.needs = AgentNeeds(**adata["needs"])
                agent.mood = AgentMood(**adata["mood"])
                agent.schedule = adata["schedule"]
                agent.memory = deque(adata["memory"], maxlen=20)
                agent.relationships = [
                    Relationship(**r) for r in adata["relationships"]
                ]
                # Restore new fields with defaults
                agent.energy = adata.get("energy", 0.7)
                agent.stress = adata.get("stress", 0.3)
                agent.credits = adata.get("credits", 10.0)
                agent.risk = adata.get("risk", 0.5)
                agent.social_trait = adata.get("social_trait", 0.5)
                agent.work_ethic = adata.get("work_ethic", 0.6)
                agent.location_success = adata.get("location_success", {})
                agent.location_failure = adata.get("location_failure", {})
        
        return obj
