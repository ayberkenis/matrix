"""HumanAgent model with needs, goals, traits, inventory, and conflict resolution."""

import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from living_matrix.beliefs import Belief, BeliefSystem


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
    
    # Beliefs (subjective reality)
    beliefs: Dict[str, Belief] = field(default_factory=dict)  # topic -> Belief


class HumanAgentSystem:
    """Manages human agents in the world."""
    
    ROLES = ['worker', 'trader', 'guard', 'medic', 'student', 'builder', 'scout', 'keeper']
    NAME_PARTS = ['Ari', 'Kora', 'Vex', 'Lume', 'Nex', 'Zeph', 'Rift', 'Tara', 'Vey', 'Mira', 'Jax', 'Kira', 'Nova', 'Rex']
    
    def __init__(self, districts: List[str], locations: List[str], num_agents: int = 20, seed: int = 42):
        """Initialize human agent system."""
        self.seed = seed
        random.seed(seed)
        self.districts = districts  # District IDs (e.g., "region_kora")
        self.locations = locations
        self.agents: Dict[str, HumanAgent] = {}
        self.belief_system = BeliefSystem(seed=seed)
        self._create_agents(num_agents)
    
    def _create_agents(self, num_agents: int):
        """Create human agents."""
        for i in range(num_agents):
            agent_id = f"human_{i}"
            name = random.choice(self.NAME_PARTS) + " " + random.choice(self.NAME_PARTS)
            district = random.choice(self.districts) if self.districts else "unknown"
            home_location = random.choice(self.locations) if self.locations else "unknown"
            role = random.choice(self.ROLES)
            
            agent = HumanAgent(
                id=agent_id,
                name=name,
                district=district,
                location=home_location,
                home_location=home_location,
                role=role,
                needs=HumanNeeds(
                    hunger=random.randint(20, 60),
                    rest=random.randint(30, 70),
                    safety=random.randint(50, 90),
                    belonging=random.randint(40, 70),
                    purpose=random.randint(40, 80)
                ),
                traits=HumanTraits(
                    risk=random.uniform(0.2, 0.8),
                    empathy=random.uniform(0.3, 0.9),
                    ambition=random.uniform(0.2, 0.8),
                    patience=random.uniform(0.3, 0.9)
                ),
                inventory=HumanInventory(
                    food=random.randint(2, 8),
                    credits=random.randint(10, 30),
                    tools=random.randint(0, 2) if role in ['worker', 'builder'] else 0
                )
            )
            
            # Initial goals
            agent.goals = self._generate_initial_goals(agent)
            
            self.agents[agent_id] = agent
    
    def _generate_initial_goals(self, agent: HumanAgent) -> List[str]:
        """Generate initial goals based on needs and role."""
        goals = []
        if agent.needs.hunger > 60:
            goals.append("get_food")
        if agent.needs.rest > 70:
            goals.append("rest")
        if agent.needs.belonging < 40:
            goals.append("socialize")
        if agent.role in ['worker', 'builder']:
            goals.append("work")
        if not goals:
            goals.append("idle")
        return goals
    
    def update_needs(self, agent: HumanAgent, district_tension: float, nearby_conflicts: int):
        """Update agent needs each tick."""
        # Hunger increases
        agent.needs.hunger = min(100, agent.needs.hunger + 1)
        
        # Rest decreases if active
        if agent.current_action not in ["rest", "idle"]:
            agent.needs.rest = min(100, agent.needs.rest + 2)
        
        # Safety decreases with tension and conflicts
        if district_tension > 0.5:
            agent.needs.safety = max(0, agent.needs.safety - 1)
        if nearby_conflicts > 0:
            agent.needs.safety = max(0, agent.needs.safety - nearby_conflicts * 2)
        
        # Belonging slowly decreases
        agent.needs.belonging = max(0, agent.needs.belonging - 0.5)
        
        # Purpose decreases if idle too long
        if agent.current_action == "idle" and agent.last_action_turn > 5:
            agent.needs.purpose = min(100, agent.needs.purpose + 1)
    
    def update_mood(self, agent: HumanAgent):
        """Update mood from needs and recent events."""
        # Base mood from needs (lower needs = better mood)
        need_score = (
            (100 - agent.needs.hunger) * 0.2 +
            (100 - agent.needs.rest) * 0.2 +
            (100 - agent.needs.safety) * 0.3 +
            (100 - agent.needs.belonging) * 0.15 +
            (100 - agent.needs.purpose) * 0.15
        ) / 100.0
        
        # Recent events affect mood
        event_modifier = 0.0
        for event in list(agent.memory)[-3:]:
            if "conflict" in event.lower() or "theft" in event.lower():
                event_modifier -= 0.2
            elif "help" in event.lower() or "trade" in event.lower():
                event_modifier += 0.1
        
        agent.mood = max(-1.0, min(1.0, (need_score - 0.5) * 2.0 + event_modifier))
    
    def decide_action(self, agent: HumanAgent, district_resources: Dict, available_places: List[str]) -> str:
        """
        Decide action using utility function.
        Returns action type: "move", "work", "trade", "rest", "socialize", "help", "theft", "idle"
        """
        # Score each possible action
        action_scores = {}
        
        # Rest action
        rest_score = agent.needs.rest * 0.5 - agent.traits.ambition * 20
        action_scores["rest"] = rest_score
        
        # Get food action
        if agent.needs.hunger > 50:
            if agent.inventory.credits >= 5 and district_resources.get("food_stock", 0) > 0:
                trade_score = agent.needs.hunger * 0.8 - agent.traits.risk * 10
                action_scores["trade"] = trade_score
            elif agent.inventory.credits < 5 and agent.needs.hunger > 70:
                # Desperate: consider theft
                if agent.traits.risk > 0.6:
                    theft_score = agent.needs.hunger * 0.5 - (1.0 - agent.traits.risk) * 30
                    action_scores["theft"] = theft_score
        
        # Work action
        if agent.role in ['worker', 'builder'] and agent.needs.rest < 70:
            work_score = agent.needs.purpose * 0.4 + agent.traits.ambition * 20
            if district_resources.get("jobs_available", 0) > 0:
                work_score += 10
            action_scores["work"] = work_score
        
        # Socialize action
        if agent.needs.belonging < 50:
            social_score = (100 - agent.needs.belonging) * 0.3 + agent.traits.empathy * 15
            action_scores["socialize"] = social_score
        
        # Help action (if empathy high and others in need)
        if agent.traits.empathy > 0.7 and district_resources.get("tension", 0) > 50:
            help_score = agent.traits.empathy * 25 - agent.needs.hunger * 0.2
            action_scores["help"] = help_score
        
        # Move action (if needs can't be met here)
        if not action_scores or max(action_scores.values()) < 20:
            move_score = 10
            action_scores["move"] = move_score
        
        # Select best action
        if action_scores:
            best_action = max(action_scores.items(), key=lambda x: x[1])[0]
            return best_action
        return "idle"
    
    def execute_action(self, agent: HumanAgent, action: str, district_resources: Dict, 
                      world_map, other_agents: List[HumanAgent], available_places: List[str] = None) -> Tuple[str, Optional[str]]:
        """
        Execute an action and return (description, event_type).
        event_type can be: None, "work", "trade", "conflict", "theft", "help", "social"
        """
        agent.current_action = action
        agent.last_action_turn = 0
        
        if action == "rest":
            agent.needs.rest = max(0, agent.needs.rest - 20)
            return (f"{agent.name} rests at {agent.location}", None)
        
        elif action == "work":
            if district_resources.get("jobs_available", 0) > 0:
                # Work success based on traits and needs
                success_chance = 0.7 + agent.traits.ambition * 0.2 - (agent.needs.rest / 100.0) * 0.3
                if random.random() < success_chance:
                    credits_earned = random.randint(3, 8)
                    agent.inventory.credits += credits_earned
                    agent.needs.purpose = max(0, agent.needs.purpose - 15)
                    agent.needs.rest = min(100, agent.needs.rest + 5)
                    district_resources["credits_pool"] = district_resources.get("credits_pool", 0) + credits_earned
                    return (f"{agent.name} works successfully, earns {credits_earned} credits", "work")
                else:
                    agent.needs.rest = min(100, agent.needs.rest + 10)
                    return (f"{agent.name} struggles with work", "work")
            return (f"{agent.name} looks for work but finds none", None)
        
        elif action == "trade":
            if agent.inventory.credits >= 5 and district_resources.get("food_stock", 0) > 0:
                # Price based on scarcity
                base_price = 5
                scarcity_mult = 1.0 + (100 - district_resources.get("food_stock", 50)) / 100.0
                price = int(base_price * scarcity_mult)
                
                if agent.inventory.credits >= price:
                    agent.inventory.credits -= price
                    agent.inventory.food += 3
                    agent.needs.hunger = max(0, agent.needs.hunger - 30)
                    district_resources["food_stock"] = max(0, district_resources.get("food_stock", 0) - 3)
                    district_resources["credits_pool"] = district_resources.get("credits_pool", 0) + price
                    return (f"{agent.name} trades for food (cost: {price} credits)", "trade")
            return (f"{agent.name} cannot trade (insufficient credits or no food)", None)
        
        elif action == "socialize":
            # Find nearby agents
            nearby = [a for a in other_agents if a.location == agent.location and a.id != agent.id]
            if nearby:
                other = random.choice(nearby)
                agent.needs.belonging = min(100, agent.needs.belonging + 10)
                other.needs.belonging = min(100, other.needs.belonging + 5)
                return (f"{agent.name} socializes with {other.name}", "social")
            return (f"{agent.name} looks for company but finds none", None)
        
        elif action == "help":
            # Reduce district tension
            tension_reduction = min(5, int(agent.traits.empathy * 10))
            district_resources["tension"] = max(0, district_resources.get("tension", 0) - tension_reduction)
            agent.needs.purpose = max(0, agent.needs.purpose - 10)
            return (f"{agent.name} helps others, reduces tension", "help")
        
        elif action == "theft":
            # Conflict risk
            if random.random() < 0.4:  # 40% chance of being caught
                district_resources["tension"] = min(100, district_resources.get("tension", 0) + 10)
                agent.needs.safety = max(0, agent.needs.safety - 15)
                agent.memory.append("caught stealing")
                return (f"{agent.name} attempts theft but is caught", "conflict")
            else:
                agent.inventory.food += 2
                agent.needs.hunger = max(0, agent.needs.hunger - 20)
                district_resources["food_stock"] = max(0, district_resources.get("food_stock", 0) - 2)
                district_resources["tension"] = min(100, district_resources.get("tension", 0) + 5)
                agent.memory.append("successful theft")
                return (f"{agent.name} steals food", "theft")
        
        elif action == "move":
            # Move to a different location in district
            available = [loc for loc in available_places if loc != agent.location] if available_places else []
            if available:
                agent.location = random.choice(available)
                return (f"{agent.name} moves to {agent.location}", None)
        
        return (f"{agent.name} is idle", None)
    
    def check_conflicts(self, agents: List[HumanAgent], district_resources: Dict) -> List[Tuple[str, str, str]]:
        """
        Check for conflicts between agents.
        Returns list of (agent1_id, agent2_id, conflict_type) tuples.
        """
        conflicts = []
        
        # Group conflicts: if tension high and multiple agents in same place
        if district_resources.get("tension", 0) > 60:
            location_groups: Dict[str, List[HumanAgent]] = {}
            for agent in agents:
                if agent.location not in location_groups:
                    location_groups[agent.location] = []
                location_groups[agent.location].append(agent)
            
            for location, group in location_groups.items():
                if len(group) >= 3 and random.random() < 0.2:  # 20% chance with 3+ agents
                    # Group conflict
                    agent1 = random.choice(group)
                    agent2 = random.choice([a for a in group if a.id != agent1.id])
                    conflicts.append((agent1.id, agent2.id, "group_conflict"))
                    # Update needs
                    for a in group:
                        a.needs.safety = max(0, a.needs.safety - 10)
                        a.memory.append("witnessed group conflict")
        
        # Individual conflicts: high hunger + low empathy
        for agent in agents:
            if agent.needs.hunger > 80 and agent.traits.empathy < 0.4:
                nearby = [a for a in agents if a.location == agent.location and a.id != agent.id]
                if nearby and random.random() < 0.15:
                    other = random.choice(nearby)
                    conflicts.append((agent.id, other.id, "argument"))
                    agent.needs.safety = max(0, agent.needs.safety - 5)
                    other.needs.safety = max(0, other.needs.safety - 5)
                    agent.memory.append(f"argument with {other.name}")
                    other.memory.append(f"argument with {agent.name}")
        
        return conflicts
    
    def advance(self, district_resources: Dict, available_places: List[str], 
                world_map, turn: int) -> List[Tuple[str, str, Optional[str]]]:
        """
        Advance all agents one tick.
        Returns list of (agent_id, description, event_type) tuples.
        """
        events = []
        agents_list = list(self.agents.values())
        
        # Update all agents
        for agent in agents_list:
            # Update needs
            district_tension = district_resources.get("tension", 0) / 100.0
            nearby_conflicts = sum(1 for e in events if "conflict" in str(e[2]))
            self.update_needs(agent, district_tension, nearby_conflicts)
            
            # Update mood
            self.update_mood(agent)
            
            # Update goals based on needs
            agent.goals = self._generate_initial_goals(agent)
            
            # Decide and execute action
            action = self.decide_action(agent, district_resources, available_places)
            other_agents = [a for a in agents_list if a.id != agent.id]
            desc, event_type = self.execute_action(agent, action, district_resources, world_map, other_agents)
            
            events.append((agent.id, desc, event_type))
            
            # Record in memory
            if event_type:
                agent.memory.append(desc)
            
            agent.last_action_turn += 1
        
        # Check for conflicts
        conflicts = self.check_conflicts(agents_list, district_resources)
        for agent1_id, agent2_id, conflict_type in conflicts:
            agent1 = self.agents[agent1_id]
            agent2 = self.agents[agent2_id]
            events.append((agent1_id, f"{agent1.name} and {agent2.name} have a {conflict_type}", "conflict"))
            district_resources["tension"] = min(100, district_resources.get("tension", 0) + 5)
        
        return events
    
    def get_agent(self, agent_id: str) -> Optional[HumanAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agent_by_name(self, name: str) -> Optional[HumanAgent]:
        """Get agent by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for agent in self.agents.values():
            if name_lower in agent.name.lower():
                return agent
        return None
    
    def get_agents_in_district(self, district: str) -> List[HumanAgent]:
        """Get all agents in a district."""
        return [a for a in self.agents.values() if a.district == district]
    
    def get_agents_at_location(self, location: str) -> List[HumanAgent]:
        """Get all agents at a location."""
        return [a for a in self.agents.values() if a.location == location]
