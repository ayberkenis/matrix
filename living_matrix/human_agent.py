"""HumanAgent model with needs, goals, traits, inventory, and conflict resolution."""

import random
from typing import List, Dict, Optional, Tuple
from collections import deque
from living_matrix.dataclasses import (
    HumanNeeds, HumanTraits, HumanInventory, HumanAgent
)
from living_matrix.beliefs import BeliefSystem
from living_matrix.dataclasses import Belief
from living_matrix.relationships_enhanced import RelationshipSystem
from living_matrix.dataclasses import Relationship
from living_matrix.constants import (
    MAX_ACTIVE_AGENTS, ADULTHOOD_AGE, MAX_CHILD_POOL_PER_DISTRICT,
    MIN_ADULT_SURVIVORS, MAX_ADULT_DEATH_RATE, ROLES, NAME_PARTS,
    INITIAL_AGE_YOUNG_PROBABILITY, INITIAL_AGE_MIDDLE_PROBABILITY,
    INITIAL_AGE_YOUNG_MIN, INITIAL_AGE_YOUNG_MAX,
    INITIAL_AGE_MIDDLE_MIN, INITIAL_AGE_MIDDLE_MAX,
    INITIAL_AGE_ELDERLY_MIN, INITIAL_AGE_ELDERLY_MAX,
    MIN_REMAINING_LIFESPAN, LIFESPAN_VARIANCE,
    INITIAL_HUNGER_MIN, INITIAL_HUNGER_MAX,
    INITIAL_REST_MIN, INITIAL_REST_MAX,
    INITIAL_SAFETY_MIN, INITIAL_SAFETY_MAX,
    INITIAL_BELONGING_MIN, INITIAL_BELONGING_MAX,
    INITIAL_PURPOSE_MIN, INITIAL_PURPOSE_MAX,
    INITIAL_RISK_MIN, INITIAL_RISK_MAX,
    INITIAL_EMPATHY_MIN, INITIAL_EMPATHY_MAX,
    INITIAL_AMBITION_MIN, INITIAL_AMBITION_MAX,
    INITIAL_PATIENCE_MIN, INITIAL_PATIENCE_MAX,
    INITIAL_FOOD_MIN, INITIAL_FOOD_MAX,
    INITIAL_CREDITS_MIN, INITIAL_CREDITS_MAX, INITIAL_TOOLS_MAX,
    INITIAL_SURVIVAL_DRIVE_MIN, INITIAL_SURVIVAL_DRIVE_MAX,
    INITIAL_LEGACY_DRIVE_MIN, INITIAL_LEGACY_DRIVE_MAX,
    REPRODUCTION_DRIVE_TOO_YOUNG_MIN, REPRODUCTION_DRIVE_TOO_YOUNG_MAX,
    REPRODUCTION_DRIVE_PEAK_MIN, REPRODUCTION_DRIVE_PEAK_MAX,
    REPRODUCTION_DRIVE_DECLINING_MIN, REPRODUCTION_DRIVE_DECLINING_MAX,
    REPRODUCTION_DRIVE_ELDERLY_MIN, REPRODUCTION_DRIVE_ELDERLY_MAX,
    INITIAL_RELATIONSHIP_CHANCE, INITIAL_RELATIONSHIP_POSITIVE_CHANCE,
    INITIAL_AFFECTION_MIN, INITIAL_AFFECTION_MAX,
    INITIAL_TRUST_MIN, INITIAL_TRUST_MAX,
    INITIAL_FAMILIARITY_MIN, INITIAL_FAMILIARITY_MAX,
    CHILD_MORTALITY_RATE_UNDER_10, CHILD_MORTALITY_RATE_UNDER_50, CHILD_MORTALITY_RATE_OVER_50,
    EMERGENCY_BIRTH_MULTIPLIER, BASE_PROMOTION_CHANCE,
    PROMOTION_FOOD_FACTOR_DIVISOR, PROMOTION_JOB_FACTOR_DIVISOR,
    MAX_CHILD_POOL_PER_DISTRICT
)
from living_matrix.utils.guards import (
    ensure_minimum_population, calculate_max_deaths_allowed,
    clamp_death_count, check_extinction_risk
)
from living_matrix.population.mortality import age_agent as population_age_agent
from living_matrix.population.reproduction import (
    check_reproduction as population_check_reproduction,
    add_child_to_pool as population_add_child_to_pool
)
from living_matrix.population.promotion import (
    promote_children_to_agents as population_promote_children_to_agents,
    promote_one_child as population_promote_one_child
)
from living_matrix.population.age_utils import age_child_pools as population_age_child_pools

# Dataclasses are now imported from living_matrix.dataclasses
# HumanNeeds, HumanTraits, HumanInventory, HumanAgent are imported above


class HumanAgentSystem:
    """Manages human agents in the world with population compression."""
    
    # POPULATION COMPRESSION CONSTANTS (imported from constants module)
    # Access via: MAX_ACTIVE_AGENTS, ADULTHOOD_AGE, etc. from constants module
    
    # REQUIRED FIXES: Population continuity guards (imported from constants module)
    # Access via: MIN_ADULT_SURVIVORS, MAX_ADULT_DEATH_RATE from constants module

    
    def __init__(self, districts: List[str], locations: List[str], num_agents: int = 20, seed: int = 42):
        """Initialize human agent system."""
        self.seed = seed
        random.seed(seed)
        self.districts = districts  # District IDs (e.g., "region_kora")
        self.locations = locations
        self.agents: Dict[str, HumanAgent] = {}
        self.dead_agents: Dict[str, HumanAgent] = {}  # Historical record of dead agents
        self.belief_system = BeliefSystem(seed=seed)
        self.relationship_system = RelationshipSystem(seed=seed)
        
        # POPULATION COMPRESSION: Child pools per district
        # child_pools[district_id] = int (number of children in pool)
        # child_cohorts[district_id] = Dict[age_bucket, count] for statistical aging
        self.child_pools: Dict[str, int] = {d: 0 for d in districts}  # Total children per district
        self.child_cohorts: Dict[str, Dict[int, int]] = {d: {} for d in districts}  # Age buckets: {age_bucket: count}
        
        self._create_agents(num_agents)
    
    def _create_agents(self, num_agents: int):
        """Create human agents."""
        # Ensure we have at least some districts and locations
        if not self.districts:
            # Create a default district if none exist
            self.districts = ["region_default"]
        if not self.locations:
            # Create a default location if none exist
            self.locations = ["loc_default"]
        
        for i in range(num_agents):
            agent_id = f"human_{i}"
            name = random.choice(NAME_PARTS) + " " + random.choice(NAME_PARTS)
            district = random.choice(self.districts) if self.districts else "region_default"
            home_location = random.choice(self.locations) if self.locations else "loc_default"
            role = random.choice(ROLES)
            
            # Randomize age and lifespan for initial population
            # Most agents start young (0-200), some middle-aged (200-400), few elderly (400-600)
            age_roll = random.random()
            if age_roll < INITIAL_AGE_YOUNG_PROBABILITY:  # 60% young
                initial_age = random.randint(INITIAL_AGE_YOUNG_MIN, INITIAL_AGE_YOUNG_MAX)
            elif age_roll < INITIAL_AGE_MIDDLE_PROBABILITY:  # 30% middle-aged
                initial_age = random.randint(INITIAL_AGE_MIDDLE_MIN, INITIAL_AGE_MIDDLE_MAX)
            else:  # 10% elderly
                initial_age = random.randint(INITIAL_AGE_ELDERLY_MIN, INITIAL_AGE_ELDERLY_MAX)
            
            # Lifespan should be much longer - ensure agents have plenty of time left
            # Minimum lifespan ensures even elderly agents have at least 800 turns remaining
            min_remaining = MIN_REMAINING_LIFESPAN  # At least 800 turns of life remaining
            lifespan = initial_age + random.randint(min_remaining, min_remaining + LIFESPAN_VARIANCE)
            
            agent = HumanAgent(
                id=agent_id,
                name=name,
                district=district,
                location=home_location,
                home_location=home_location,
                role=role,
                sex=random.choice(["male", "female"]),  # Random sex assignment (50/50)
                needs=HumanNeeds(
                    hunger=random.randint(INITIAL_HUNGER_MIN, INITIAL_HUNGER_MAX),
                    rest=random.randint(INITIAL_REST_MIN, INITIAL_REST_MAX),
                    safety=random.randint(INITIAL_SAFETY_MIN, INITIAL_SAFETY_MAX),
                    belonging=random.randint(INITIAL_BELONGING_MIN, INITIAL_BELONGING_MAX),
                    purpose=random.randint(INITIAL_PURPOSE_MIN, INITIAL_PURPOSE_MAX)
                ),
                traits=HumanTraits(
                    risk=random.uniform(INITIAL_RISK_MIN, INITIAL_RISK_MAX),
                    empathy=random.uniform(INITIAL_EMPATHY_MIN, INITIAL_EMPATHY_MAX),
                    ambition=random.uniform(INITIAL_AMBITION_MIN, INITIAL_AMBITION_MAX),
                    patience=random.uniform(INITIAL_PATIENCE_MIN, INITIAL_PATIENCE_MAX)
                ),
                inventory=HumanInventory(
                    food=random.randint(INITIAL_FOOD_MIN, INITIAL_FOOD_MAX),
                    credits=random.randint(INITIAL_CREDITS_MIN, INITIAL_CREDITS_MAX),
                    tools=random.randint(0, INITIAL_TOOLS_MAX) if role in ['worker', 'builder'] else 0
                ),
                age=initial_age,
                lifespan=lifespan,
                is_alive=True,
                # Initialize survival drives (SYSTEM 10)
                survival_drive=random.uniform(INITIAL_SURVIVAL_DRIVE_MIN, INITIAL_SURVIVAL_DRIVE_MAX),  # Start high
                reproduction_drive=self._calculate_initial_reproduction_drive(initial_age, lifespan),
                legacy_drive=random.uniform(INITIAL_LEGACY_DRIVE_MIN, INITIAL_LEGACY_DRIVE_MAX)  # Starts low, increases with age
            )
            
            # Initial goals
            agent.goals = self._generate_initial_goals(agent)
            
            self.agents[agent_id] = agent
        
        # After creating all agents, form some initial relationships
        # This helps agents start with social connections for reproduction
        self._form_initial_relationships()
        
        # Log creation for debugging
        import logging
        logger = logging.getLogger(__name__)
        if len(self.agents) == 0:
            logger.warning(f"No agents created! districts={len(self.districts)}, locations={len(self.locations)}, num_agents={num_agents}")
        else:
            logger.info(f"Created {len(self.agents)} human agents")
    
    def _calculate_initial_reproduction_drive(self, age: int, lifespan: int) -> float:
        """Calculate initial reproduction drive based on age (peaks at reproductive age)."""
        # Peak reproduction drive around age 200-400
        if age < 100:
            return random.uniform(REPRODUCTION_DRIVE_TOO_YOUNG_MIN, REPRODUCTION_DRIVE_TOO_YOUNG_MAX)  # Too young
        elif 100 <= age <= 400:
            return random.uniform(REPRODUCTION_DRIVE_PEAK_MIN, REPRODUCTION_DRIVE_PEAK_MAX)  # Peak reproductive age
        elif 400 < age <= 600:
            return random.uniform(REPRODUCTION_DRIVE_DECLINING_MIN, REPRODUCTION_DRIVE_DECLINING_MAX)  # Declining
        else:
            return random.uniform(REPRODUCTION_DRIVE_ELDERLY_MIN, REPRODUCTION_DRIVE_ELDERLY_MAX)  # Elderly
    
    def _form_initial_relationships(self):
        """Form some initial relationships between agents in the same location."""
        # Group agents by location
        agents_by_location = {}
        for agent in self.agents.values():
            if agent.location not in agents_by_location:
                agents_by_location[agent.location] = []
            agents_by_location[agent.location].append(agent)
        
        # For each location, form some relationships
        for location, agents in agents_by_location.items():
            if len(agents) < 2:
                continue
            
            # Form relationships between some pairs (about 30% of possible pairs)
            for i, agent1 in enumerate(agents):
                for agent2 in agents[i+1:]:
                    if random.random() < INITIAL_RELATIONSHIP_CHANCE:  # 30% chance to form initial relationship
                        if agent2.id not in agent1.relationships:
                            rel = self.relationship_system.create_relationship(agent2.id, 0)
                            # Give initial relationship a boost (positive for most)
                            if random.random() < INITIAL_RELATIONSHIP_POSITIVE_CHANCE:  # 70% positive, 30% neutral
                                rel.affection = random.uniform(INITIAL_AFFECTION_MIN, INITIAL_AFFECTION_MAX)
                                rel.trust = random.uniform(INITIAL_TRUST_MIN, INITIAL_TRUST_MAX)
                                rel.familiarity = random.uniform(INITIAL_FAMILIARITY_MIN, INITIAL_FAMILIARITY_MAX)
                            else:
                                # Even neutral relationships start with minimum values for reproduction
                                rel.affection = 0.15  # Above minimum threshold
                                rel.trust = 0.15
                                rel.familiarity = 0.1
                            agent1.relationships[agent2.id] = rel
                            
                            # Also create reverse relationship
                            if agent1.id not in agent2.relationships:
                                rel2 = self.relationship_system.create_relationship(agent1.id, 0)
                                rel2.affection = rel.affection
                                rel2.trust = rel.trust
                                rel2.familiarity = rel.familiarity
                                agent2.relationships[agent1.id] = rel2
    
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
    
    def decide_action(self, agent: HumanAgent, district_resources: Dict, available_places: List[str], 
                     other_agents: List[HumanAgent] = None, extinction_risk: float = 0.0,
                     population_pressure: float = 0.0) -> str:
        """
        Decide action using utility function, influenced by relationships, beliefs, and survival drives.
        Returns action type: "move", "work", "trade", "rest", "socialize", "help", "theft", "idle"
        """
        if other_agents is None:
            other_agents = []
        
        # Score each possible action
        action_scores = {}
        
        # SURVIVAL DRIVE OVERRIDE (SYSTEM 10, 11, 12)
        # When extinction risk is high, survival drives override everything
        survival_override = (extinction_risk > 0.7) or (population_pressure > 0.8)
        
        # Rest action
        rest_score = agent.needs.rest * 0.5 - agent.traits.ambition * 20
        action_scores["rest"] = rest_score
        
        # Get food action
        if agent.needs.hunger > 50:
            if agent.inventory.credits >= 5 and district_resources.get("food_stock", 0) > 0:
                trade_score = agent.needs.hunger * 0.8 - agent.traits.risk * 10
                action_scores["trade"] = trade_score
            elif agent.inventory.credits < 5 and agent.needs.hunger > 70:
                # Desperate: consider theft (but check relationships - less likely with trusted agents nearby)
                nearby_trusted = [a for a in other_agents 
                                if a.location == agent.location and 
                                agent.relationships.get(a.id, None) and
                                agent.relationships[a.id].trust > 0.6]
                theft_penalty = len(nearby_trusted) * 20  # Less likely to steal if trusted agents nearby
                if agent.traits.risk > 0.6:
                    theft_score = agent.needs.hunger * 0.5 - (1.0 - agent.traits.risk) * 30 - theft_penalty
                    action_scores["theft"] = theft_score
        
        # Work action
        if agent.role in ['worker', 'builder'] and agent.needs.rest < 70:
            work_score = agent.needs.purpose * 0.4 + agent.traits.ambition * 20
            if district_resources.get("jobs_available", 0) > 0:
                work_score += 10
            action_scores["work"] = work_score
        
        # Socialize action (prefer agents with positive relationships)
        if agent.needs.belonging < 50:
            social_score = (100 - agent.needs.belonging) * 0.3 + agent.traits.empathy * 15
            # Boost if positive relationships nearby
            nearby_positive = [a for a in other_agents 
                             if a.location == agent.location and
                             agent.relationships.get(a.id, None) and
                             agent.relationships[a.id].affection > 0.3]
            social_score += len(nearby_positive) * 10
            # SURVIVAL DRIVE: Socialize increases with reproduction_drive (builds relationships for reproduction)
            social_score += agent.reproduction_drive * 20 + agent.survival_drive * 15
            if survival_override:
                social_score += 50  # Force socializing when extinction risk is high
            action_scores["socialize"] = social_score
        
        # Help action (prefer helping agents with positive relationships)
        if agent.traits.empathy > 0.7 and district_resources.get("tension", 0) > 50:
            help_score = agent.traits.empathy * 25 - agent.needs.hunger * 0.2
            # Boost if positive relationships nearby
            nearby_positive = [a for a in other_agents 
                             if a.location == agent.location and
                             agent.relationships.get(a.id, None) and
                             agent.relationships[a.id].affection > 0.2]
            help_score += len(nearby_positive) * 15
            action_scores["help"] = help_score
        
        # Move action (if needs can't be met here, or negative relationships nearby)
        nearby_negative = [a for a in other_agents 
                          if a.location == agent.location and
                          agent.relationships.get(a.id, None) and
                          agent.relationships[a.id].affection < -0.3]
        if nearby_negative:
            move_score = 30  # Strong desire to move away from enemies
            action_scores["move"] = move_score
        elif not action_scores or max(action_scores.values()) < 20:
            move_score = 10
            action_scores["move"] = move_score
        
        # SYSTEM A: If must_attempt_reproduction, prioritize socialize/move to find partners
        if agent.must_attempt_reproduction:
            # Seek partners - increase socialize and move scores
            if "socialize" in action_scores:
                action_scores["socialize"] += 100  # Massive boost
            if "move" in action_scores:
                action_scores["move"] += 50  # Move to find partners
            # Create socialize action if it doesn't exist
            if "socialize" not in action_scores:
                action_scores["socialize"] = 150  # Force socialize
        
        # SURVIVAL DRIVE SCORING (SYSTEM 10)
        # Every decision must include survival drives
        for action in action_scores:
            base_score = action_scores[action]
            survival_bonus = (
                agent.survival_drive * 0.4 * 30 +
                agent.reproduction_drive * 0.3 * 25 +
                agent.legacy_drive * 0.3 * 20
            )
            # Extinction risk multiplies survival bonus
            if extinction_risk > 0.6:
                survival_bonus *= (1.0 + extinction_risk * 2.0)
            action_scores[action] = base_score + survival_bonus
        
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
            nearby = [a for a in other_agents if a.location == agent.location and a.id != agent.id and a.is_alive]
            if nearby:
                other = random.choice(nearby)
                agent.needs.belonging = min(100, agent.needs.belonging + 10)
                other.needs.belonging = min(100, other.needs.belonging + 5)
                
                # Update relationship
                if other.id not in agent.relationships:
                    agent.relationships[other.id] = self.relationship_system.create_relationship(
                        other.id, agent.last_action_turn
                    )
                self.relationship_system.update_from_interaction(
                    agent.relationships[other.id], "socialize", agent.last_action_turn, True
                )
                
                # Update other's relationship too
                if agent.id not in other.relationships:
                    other.relationships[agent.id] = self.relationship_system.create_relationship(
                        agent.id, agent.last_action_turn
                    )
                self.relationship_system.update_from_interaction(
                    other.relationships[agent.id], "socialize", agent.last_action_turn, True
                )
                
                return (f"{agent.name} socializes with {other.name}", "social")
            return (f"{agent.name} looks for company but finds none", None)
        
        elif action == "help":
            # Find someone to help (prefer those with positive relationships)
            nearby = [a for a in other_agents if a.location == agent.location and a.id != agent.id and a.is_alive]
            if nearby:
                # Prefer helping agents with positive relationships
                scored = []
                for other in nearby:
                    rel = agent.relationships.get(other.id)
                    score = 0.5
                    if rel:
                        score += rel.affection * 0.3 + rel.trust * 0.2
                    scored.append((other, score))
                scored.sort(key=lambda x: x[1], reverse=True)
                other = scored[0][0]
                
                # Update relationship
                if other.id not in agent.relationships:
                    agent.relationships[other.id] = self.relationship_system.create_relationship(
                        other.id, agent.last_action_turn
                    )
                self.relationship_system.update_from_interaction(
                    agent.relationships[other.id], "cooperation", agent.last_action_turn, True
                )
            
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
    
    def check_conflicts(self, agents: List[HumanAgent], district_resources: Dict, 
                       death_panic_mode: bool = False, generational_trauma: float = 0.0,
                       population_floor_active: bool = False) -> List[Tuple[str, str, str]]:
        """
        Check for conflicts between agents.
        Returns list of (agent1_id, agent2_id, conflict_type) tuples.
        
        SYSTEM C: Death panic mode auto-resolves conflicts
        SYSTEM D: Generational trauma reduces conflicts
        SYSTEM E: Population floor suspends non-age deaths
        """
        conflicts = []
        
        # SYSTEM C: Death panic mode - auto-resolve conflicts (no conflicts occur)
        if death_panic_mode:
            return conflicts  # No conflicts in panic mode
        
        # SYSTEM D: Generational trauma reduces conflict likelihood
        trauma_conflict_reduction = generational_trauma * 0.5  # 50% reduction at max trauma
        
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
        
        # Individual conflicts: high hunger + low empathy, or relationship-based
        for agent in agents:
            if not agent.is_alive:
                continue
                
            # Check relationship-based conflict
            for target_id, rel in agent.relationships.items():
                conflict_likelihood = self.relationship_system.get_conflict_likelihood(rel)
                # conflict_likelihood already includes multiplier, so use directly
                if random.random() < conflict_likelihood:
                    target = next((a for a in agents if a.id == target_id and a.is_alive), None)
                    if target and target.location == agent.location:
                        conflicts.append((agent.id, target.id, "relationship_conflict"))
                        # Update relationship
                        self.relationship_system.update_from_interaction(
                            rel, "conflict", agent.last_action_turn, False
                        )
                        if agent.id in target.relationships:
                            self.relationship_system.update_from_interaction(
                                target.relationships[agent.id], "conflict", agent.last_action_turn, False
                            )
                        break
            
            # Original conflict logic (hunger + low empathy)
            if agent.needs.hunger > 80 and agent.traits.empathy < 0.4:
                nearby = [a for a in agents if a.location == agent.location and a.id != agent.id and a.is_alive]
                if nearby and random.random() < 0.15:
                    other = random.choice(nearby)
                    conflicts.append((agent.id, other.id, "argument"))
                    agent.needs.safety = max(0, agent.needs.safety - 5)
                    other.needs.safety = max(0, other.needs.safety - 5)
                    agent.memory.append(f"argument with {other.name}")
                    other.memory.append(f"argument with {agent.name}")
                    
                    # Update relationships
                    if other.id not in agent.relationships:
                        agent.relationships[other.id] = self.relationship_system.create_relationship(
                            other.id, agent.last_action_turn
                        )
                    self.relationship_system.update_from_interaction(
                        agent.relationships[other.id], "conflict", agent.last_action_turn, False
                    )
        
        return conflicts
    
    def _age_agent(self, agent: HumanAgent, turn: int, population_floor_active: bool = False) -> bool:
        """
        Age an agent and check for death.
        
        SYSTEM E: Population floor - suspend non-age deaths when population <= 2
        
        Returns:
            True if agent died, False otherwise
        """
        return population_age_agent(agent, turn, self.dead_agents, self.agents, population_floor_active)
    
    def _check_reproduction(self, agents: List[HumanAgent], district_resources: Dict, 
                           turn: int, world_flags_system=None, extinction_risk: float = 0.0,
                           population_pressure: float = 0.0, birth_pressure: float = 0.0) -> List[Tuple[str, str]]:
        """
        Check for reproduction opportunities (SYSTEM 12 - FORCED REPRODUCTION).
        
        Returns:
            List of (parent1_id, parent2_id) tuples for new births
        """
        return population_check_reproduction(
            agents, district_resources, turn, self.relationship_system,
            world_flags_system, extinction_risk, population_pressure, birth_pressure
        )
    
    def _add_child_to_pool(self, parent1_id: str, parent2_id: str, district: str, turn: int) -> bool:
        """
        Add a child to the child pool (POPULATION COMPRESSION).
        Children are NOT agents until they reach adulthood.
        
        Args:
            parent1_id: First parent ID
            parent2_id: Second parent ID
            district: District where child is born
            turn: Current turn
            
        Returns:
            True if child was added to pool
        """
        return population_add_child_to_pool(
            parent1_id, parent2_id, district, turn,
            self.child_pools, self.child_cohorts, MAX_CHILD_POOL_PER_DISTRICT
        )
    
    def _create_child(self, parent1_id: str, parent2_id: str, turn: int) -> HumanAgent:
        """
        DEPRECATED: Use _add_child_to_pool instead for population compression.
        This method is kept for backward compatibility but should not be used.
        
        Create a child agent from two parents (only used for direct agent creation during promotion).
        
        Args:
            parent1_id: First parent ID
            parent2_id: Second parent ID
            turn: Current turn
            
        Returns:
            New child agent (only when promoting from pool)
        """
        parent1 = self.agents.get(parent1_id) or self.dead_agents.get(parent1_id)
        parent2 = self.agents.get(parent2_id) or self.dead_agents.get(parent2_id)
        
        if not parent1 or not parent2:
            return None
        
        # Generate child ID
        child_id = f"human_{len(self.agents) + len(self.dead_agents)}"
        
        # Inherit district from parent1
        district = parent1.district
        home_location = parent1.home_location
        
        # Inherit role (randomized but influenced by parents)
        if random.random() < 0.5:
            role = parent1.role
        else:
            role = parent2.role
        
        # Create child
        child = HumanAgent(
            id=child_id,
            name=random.choice(self.NAME_PARTS) + " " + random.choice(self.NAME_PARTS),
            district=district,
            location=home_location,
            home_location=home_location,
            role=role,
            sex=random.choice(["male", "female"]),  # Random sex assignment (50/50)
            needs=HumanNeeds(
                hunger=random.randint(20, 40),  # Children start with lower needs
                rest=random.randint(30, 50),
                safety=random.randint(60, 90),
                belonging=random.randint(50, 80),
                purpose=random.randint(30, 60)
            ),
            traits=HumanTraits(
                # Inherit traits (average of parents with some variation)
                risk=(parent1.traits.risk + parent2.traits.risk) / 2 + random.uniform(-0.2, 0.2),
                empathy=(parent1.traits.empathy + parent2.traits.empathy) / 2 + random.uniform(-0.2, 0.2),
                ambition=(parent1.traits.ambition + parent2.traits.ambition) / 2 + random.uniform(-0.2, 0.2),
                patience=(parent1.traits.patience + parent2.traits.patience) / 2 + random.uniform(-0.2, 0.2)
            ),
            inventory=HumanInventory(
                food=random.randint(1, 3),
                credits=random.randint(5, 15),
                tools=0
            ),
            age=0,
            lifespan=random.randint(2400, 4000),  # Children get longer lifespans (doubled for slower aging)
            is_alive=True,
            parents_ids=[parent1_id, parent2_id],
            # SYSTEM 14: Child as world investment - survival drive starts at maximum
            survival_drive=1.0,  # Maximum survival drive
            reproduction_drive=random.uniform(0.5, 0.7),  # Moderate, will peak later
            legacy_drive=random.uniform(0.1, 0.3),  # Starts low
            # SYSTEM B: Children create resources (future_resource_bonus)
            future_resource_bonus=random.uniform(0.1, 0.3)  # Will be applied at maturity or in clusters
        )
        
        # SYSTEM 14: Inherit beliefs from parents (weighted mix)
        # Children inherit beliefs more strongly - they are the future
        for parent in [parent1, parent2]:
            for topic, belief in parent.beliefs.items():
                if random.random() < 0.5:  # 50% chance to inherit each belief (increased from 30%)
                    # Weighted mix: average polarity, higher confidence than before
                    if topic in child.beliefs:
                        # Average with existing belief
                        existing = child.beliefs[topic]
                        child.beliefs[topic] = Belief(
                            topic=topic,
                            polarity=(existing.polarity + belief.polarity) / 2.0,
                            confidence=max(existing.confidence, belief.confidence * 0.7),
                            source="inherited_mixed",
                            last_updated_turn=turn
                        )
                    else:
                        child_belief = Belief(
                            topic=topic,
                            polarity=belief.polarity,
                            confidence=belief.confidence * 0.7,  # Higher confidence (was 0.6)
                            source="inherited",
                            last_updated_turn=turn
                        )
                        child.beliefs[topic] = child_belief
        
        # Add child to parents
        if parent1_id in self.agents:
            self.agents[parent1_id].children_ids.append(child_id)
        if parent2_id in self.agents:
            self.agents[parent2_id].children_ids.append(child_id)
        
        # Add child to system
        self.agents[child_id] = child
        
        return child
    
    def advance(self, district_resources: Dict, available_places: List[str], 
                world_map, turn: int, extinction_risk: float = 0.0,
                population_pressure: float = 0.0, birth_pressure: float = 0.0) -> List[Tuple[str, str, Optional[str]]]:
        """
        Advance all agents one tick.
        Returns list of (agent_id, description, event_type) tuples.
        """
        # Always print to verify method is called
        print(f"[HUMAN_AGENT_SYSTEM] advance() called: turn={turn}, agents={len(self.agents)}, district_resources={district_resources}")
        
        events = []
        agents_list = [a for a in list(self.agents.values()) if a.is_alive]  # Only alive agents
        
        # SYSTEM 11: Update population pressure and extinction risk effects on agents
        # Population pressure increases reproduction drive
        for agent in agents_list:
            agent.reproduction_drive = min(1.0, agent.reproduction_drive + population_pressure * 0.1)
            # Extinction risk increases survival drive
            if extinction_risk > 0.6:
                agent.survival_drive = min(1.0, agent.survival_drive + 0.05)
            
            # SYSTEM A: Hard reproduction constraint
            if extinction_risk > 0.6:
                agent.must_attempt_reproduction = True  # HARD CONSTRAINT - not a choice
            else:
                agent.must_attempt_reproduction = False
        
        # Age agents and handle death
        # REQUIRED FIX 1: Minimum Viable Population Guard (Hard Rule)
        alive_count = len(agents_list)
        min_adult_survivors = MIN_ADULT_SURVIVORS
        skip_adult_deaths = alive_count <= min_adult_survivors  # Prevent total wipeout
        population_floor_active = skip_adult_deaths  # Alias for compatibility
        
        # REQUIRED FIX 4: Death Rate Clamp
        max_deaths_allowed = int(alive_count * MAX_ADULT_DEATH_RATE) if alive_count > 0 else 0
        
        dead_this_turn = []
        deaths_count = 0
        for agent in list(agents_list):
            # Skip deaths if we're at minimum viable population
            if skip_adult_deaths:
                break  # Don't process any deaths
            
            # Clamp death rate
            if clamp_death_count(deaths_count, max_deaths_allowed):
                break  # Stop processing deaths if we hit the limit
            
            if self._age_agent(agent, turn, skip_adult_deaths):
                dead_this_turn.append(agent.id)
                deaths_count += 1
                events.append((agent.id, f"{agent.name} died of old age", "death"))
        
        # Update agents list (remove dead)
        agents_list = [a for a in list(self.agents.values()) if a.is_alive]
        
        # Check for reproduction (POPULATION COMPRESSION: add to child pools, not agents)
        world_flags_system = getattr(self, '_world_flags_system', None)
        print(f"[HUMAN_AGENT_SYSTEM] About to check reproduction: {len(agents_list)} alive agents")
        births = self._check_reproduction(agents_list, district_resources, turn, world_flags_system,
                                         extinction_risk, population_pressure, birth_pressure)
        print(f"[HUMAN_AGENT_SYSTEM] Reproduction check returned {len(births)} births")
        for parent1_id, parent2_id in births:
            parent1 = self.agents.get(parent1_id)
            parent2 = self.agents.get(parent2_id)
            if parent1 and parent2:
                # Add to child pool instead of creating agent
                district = parent1.district
                if self._add_child_to_pool(parent1_id, parent2_id, district, turn):
                    events.append((parent1_id, f"Child born to {parent1.name} and {parent2.name} in {district}", "birth"))
        
        # POPULATION COMPRESSION: Age child pools statistically
        global_child_pool_before = sum(self.child_pools.values())
        print(f"[HUMAN_AGENT_SYSTEM] Before aging: {global_child_pool_before} children in pool")
        self._age_child_pools(turn)
        global_child_pool_after_aging = sum(self.child_pools.values())
        print(f"[HUMAN_AGENT_SYSTEM] After aging: {global_child_pool_after_aging} children in pool")
        
        # REQUIRED FIX 2: Emergency Birth Rule (Critical)
        # If adults exist but child_pool === 0, force reproduction
        global_child_pool = sum(self.child_pools.values())
        if alive_count > 0 and global_child_pool == 0:
            # Force emergency births across districts
            for district_id in self.districts:
                if district_id in self.child_pools:
                    emergency_births = max(1, int(alive_count * EMERGENCY_BIRTH_MULTIPLIER / len(self.districts)))
                    self.child_pools[district_id] += emergency_births
                    # Add to age 0 cohort
                    if district_id not in self.child_cohorts:
                        self.child_cohorts[district_id] = {}
                    if 0 not in self.child_cohorts[district_id]:
                        self.child_cohorts[district_id][0] = 0
                    self.child_cohorts[district_id][0] += emergency_births
                    events.append(("system", f"Emergency births triggered in {district_id}: {emergency_births} children", "emergency_birth"))
        
        # REQUIRED FIX 3: Bootstrap Recovery Rule (ABSOLUTELY REQUIRED)
        # When both are zero, inject a seed population
        if check_extinction_risk(alive_count, global_child_pool):
            self._spawn_emergency_founders(turn)
            events.append(("system", "Emergency founders spawned to prevent extinction", "bootstrap_recovery"))
            # Update alive_count after spawning
            agents_list = [a for a in list(self.agents.values()) if a.is_alive]
            alive_count = len(agents_list)
        
        # POPULATION COMPRESSION: Promote children to agents (stochastic)
        promotion_events = self._promote_children_to_agents(turn, district_resources)
        events.extend(promotion_events)
        
        # REQUIRED FIX: Debug logging
        global_child_pool_after = sum(self.child_pools.values())
        promotions_count = len(promotion_events)
        births_count = len([e for e in events if e[2] == "birth" or e[2] == "emergency_birth"])
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Population stats - Turn {turn}: adults={alive_count}, childPool={global_child_pool_after}, deaths={len(dead_this_turn)}, births={births_count}, promotions={promotions_count}")
        
        # REQUIRED FIX: Check for extinction state
        if check_extinction_risk(alive_count, global_child_pool_after):
            logger.warning(f"EXTINCTION DETECTED at turn {turn} - triggering emergency recovery")
            self._spawn_emergency_founders(turn)
        
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
            
            # Decay relationships (apply world flag effects)
            decay_multiplier = 1.0
            if hasattr(self, '_world_flags_system') and self._world_flags_system:
                for flag in self._world_flags_system.get_all_flags():
                    if "relationship_decay_multiplier" in flag.effects:
                        decay_multiplier = max(decay_multiplier, flag.effects["relationship_decay_multiplier"])
            
            for target_id, rel in list(agent.relationships.items()):
                # Apply decay with multiplier
                original_decay = self.relationship_system.decay_rate
                self.relationship_system.decay_rate = original_decay * decay_multiplier
                self.relationship_system.decay_relationship(rel, turn)
                self.relationship_system.decay_rate = original_decay  # Restore
                
                # Remove very weak relationships
                if rel.affection == 0.0 and rel.trust < 0.1 and rel.familiarity < 0.1:
                    del agent.relationships[target_id]
            
            # Decide and execute action (pass other agents for relationship-based decisions)
            other_agents = [a for a in agents_list if a.id != agent.id]
            action = self.decide_action(agent, district_resources, available_places, other_agents,
                                       extinction_risk, population_pressure)
            desc, event_type = self.execute_action(agent, action, district_resources, world_map, other_agents)
            
            events.append((agent.id, desc, event_type))
            
            # Record in memory
            if event_type:
                agent.memory.append(desc)
            
            agent.last_action_turn += 1
        
        # Check for conflicts (after all agents have been processed)
        # Pass death panic mode, generational trauma, and population floor
        conflicts = self.check_conflicts(agents_list, district_resources, 
                                       death_panic_mode=getattr(self, '_death_panic_mode', False),
                                       generational_trauma=getattr(self, '_generational_trauma', 0.0),
                                       population_floor_active=population_floor_active)
        for agent1_id, agent2_id, conflict_type in conflicts:
            agent1 = self.agents.get(agent1_id)
            agent2 = self.agents.get(agent2_id)
            if agent1 and agent2 and agent1.is_alive and agent2.is_alive:
                events.append((agent1_id, f"{agent1.name} and {agent2.name} have a {conflict_type}", "conflict"))
                district_resources["tension"] = min(100, district_resources.get("tension", 0) + 5)
        
        return events
    
    def get_population_stats(self) -> Dict:
        """Get population statistics."""
        alive = [a for a in self.agents.values() if a.is_alive]
        dead = list(self.dead_agents.values())
        
        age_groups = {
            "children": sum(1 for a in alive if a.age < 100),
            "adults": sum(1 for a in alive if 100 <= a.age < 800),
            "elderly": sum(1 for a in alive if a.age >= 800)
        }
        
        return {
            "alive": len(alive),
            "dead": len(dead),
            "total_ever": len(alive) + len(dead),
            "age_groups": age_groups,
            "average_age": sum(a.age for a in alive) / len(alive) if alive else 0,
            "births_this_turn": sum(1 for a in alive if a.age == 0),
            "deaths_this_turn": len([a for a in dead if a.death_turn == max((a.death_turn for a in dead), default=0)])
        }
    
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
    
    def _age_child_pools(self, turn: int):
        """
        Age child pools statistically (POPULATION COMPRESSION).
        Children age in cohorts, not individually.
        """
        population_age_child_pools(turn, self.child_pools, self.child_cohorts)
    
    def _promote_children_to_agents(self, turn: int, district_resources: Dict) -> List[Tuple[str, str, Optional[str]]]:
        """
        Promote children from pool to agents (stochastic, POPULATION COMPRESSION).
        Only promotes if active_agents < MAX_ACTIVE_AGENTS.
        
        Returns:
            List of (agent_id, description, event_type) tuples for promotions
        """
        return population_promote_children_to_agents(
            turn, district_resources, self.child_pools, self.child_cohorts,
            self.agents, self.dead_agents, self.districts, self.locations,
            self._calculate_initial_reproduction_drive
        )
    
    def _promote_one_child(self, district_id: str, turn: int) -> Optional[HumanAgent]:
        """
        Promote one child from pool to agent.
        Returns the new agent, or None if promotion failed.
        """
        return population_promote_one_child(
            district_id, turn, self.child_pools, self.child_cohorts,
            self.agents, self.dead_agents, self.locations,
            self._calculate_initial_reproduction_drive
        )
    
    def _spawn_emergency_founders(self, turn: int):
        """
        REQUIRED FIX 3: Bootstrap Recovery Rule (ABSOLUTELY REQUIRED)
        Spawn emergency founders when both activeAgents and childPool are 0.
        These should have high resilience, no reproduction first turn, low tension.
        Tagged as founder_generation.
        """
        num_founders = 3
        
        for i in range(num_founders):
            founder_id = f"founder_{turn}_{i}"
            district = random.choice(self.districts) if self.districts else "region_default"
            location = random.choice(self.locations) if self.locations else "loc_default"
            name = random.choice(self.NAME_PARTS) + " " + random.choice(self.NAME_PARTS)
            role = random.choice(self.ROLES)
            
            # Create founder with high resilience
            founder = HumanAgent(
                id=founder_id,
                name=name,
                district=district,
                location=location,
                home_location=location,
                role=role,
                sex=random.choice(["male", "female"]),  # Random sex assignment (50/50)
                needs=HumanNeeds(
                    hunger=random.randint(20, 40),  # Low needs (well-fed)
                    rest=random.randint(30, 50),
                    safety=random.randint(70, 90),  # High safety
                    belonging=random.randint(60, 80),
                    purpose=random.randint(70, 90)  # High purpose
                ),
                traits=HumanTraits(
                    risk=random.uniform(0.2, 0.4),  # Low risk-taking
                    empathy=random.uniform(0.6, 0.8),  # High empathy
                    ambition=random.uniform(0.5, 0.7),
                    patience=random.uniform(0.6, 0.8)  # High patience
                ),
                inventory=HumanInventory(
                    food=random.randint(10, 20),  # Well-supplied
                    credits=random.randint(30, 50),
                    tools=random.randint(1, 3)
                ),
                age=random.randint(50, 150),  # Prime age (reduced for younger start)
                lifespan=random.randint(3000, 5000),  # Long lifespan (doubled for slower aging)
                is_alive=True,
                survival_drive=1.0,  # Maximum survival drive
                reproduction_drive=0.3,  # Low initially (no reproduction first turn)
                legacy_drive=0.8  # High legacy drive (founders)
            )
            
            # Tag as founder generation (store in beliefs)
            founder.beliefs["founder_generation"] = Belief(
                topic="founder_generation",
                polarity=1.0,
                confidence=1.0,
                source="emergency_recovery",
                last_updated_turn=turn
            )
            
            # Add to agents
            self.agents[founder_id] = founder