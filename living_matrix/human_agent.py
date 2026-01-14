"""HumanAgent model with needs, goals, traits, inventory, and conflict resolution."""

import random
import time
from typing import List, Dict, Optional, Tuple
from collections import deque
from living_matrix.dataclasses import (
    HumanNeeds, HumanTraits, HumanInventory, HumanAgent
)

# DEBUG PROFILING: Import profiler for performance analysis
# Enable via: LM_DEBUG_PROFILE=true environment variable
from living_matrix.utils.debug_profiler import get_profiler, is_profiling_enabled
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

# Import learning config and memory manager (optional - graceful fallback)
try:
    from living_matrix.config import get_config as get_learning_config
    from living_matrix.redis_memory import get_memory_manager
    _HAS_LEARNING = True
except ImportError:
    _HAS_LEARNING = False
    def get_learning_config():
        return None
    def get_memory_manager():
        return None

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
        # Death counts by cause: {"aging": 10, "starvation": 5, ...}
        self.death_counts: Dict[str, int] = {}
        self.belief_system = BeliefSystem(seed=seed)
        self.relationship_system = RelationshipSystem(seed=seed)
        
        # POPULATION COMPRESSION: Child pools per district
        # child_pools[district_id] = int (number of children in pool)
        # child_cohorts[district_id] = Dict[age_bucket, count] for statistical aging
        self.child_pools: Dict[str, int] = {d: 0 for d in districts}  # Total children per district
        self.child_cohorts: Dict[str, Dict[int, int]] = {d: {} for d in districts}  # Age buckets: {age_bucket: count}
        
        # Track children per couple: (parent1_id, parent2_id) -> count
        # Use sorted tuple to ensure (A, B) == (B, A)
        self.couple_children: Dict[Tuple[str, str], int] = {}
        
        # OPTIMIZATION 3: Spatial index for fast location-based queries
        from living_matrix.utils.spatial_index import SpatialIndex
        self.spatial_index = SpatialIndex()
        
        # PERFORMANCE: Agent tier manager for stratified simulation
        from living_matrix.core_sim.agent_tiers import AgentTierManager
        self.tier_manager = AgentTierManager(seed=seed)
        
        # PERFORMANCE: Population statistics tracker
        from living_matrix.core_sim.statistics import PopulationStats
        self.population_stats = PopulationStats()
        
        # PERFORMANCE: Parallel executor (lazy initialized)
        self._parallel_executor = None
        self._parallel_pool = None  # multiprocessing.Pool for true parallelism
        
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
        
        # POPULATION FIX: Concentrate initial agents in fewer districts
        # With agents scattered across 10 districts, reproduction fails due to poor pairing
        # Limit initial districts to max 3 to ensure viable population density
        initial_districts = self.districts[:min(3, len(self.districts))] if self.districts else ["region_default"]
        initial_locations = self.locations[:min(5, len(self.locations))] if self.locations else ["loc_default"]
        
        for i in range(num_agents):
            agent_id = f"human_{i}"
            name = random.choice(NAME_PARTS) + " " + random.choice(NAME_PARTS)
            district = random.choice(initial_districts)
            home_location = random.choice(initial_locations)
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
        
        # PERF CRITICAL: Defer relationship formation
        # Instead of creating all relationships eagerly, we use lazy creation
        # Relationships are formed on-demand during first interactions
        # Only seed a minimal set of critical relationships for population bootstrap
        self._seed_minimal_relationships()
        
        # OPTIMIZATION 3: Initialize spatial index with all agents
        self.spatial_index.rebuild(self.agents)
        
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
    
    def _seed_minimal_relationships(self):
        """Seed minimal initial relationships for population bootstrap.
        
        PERF CRITICAL: This is a lightweight alternative to full relationship formation.
        Only creates ~2-3 relationships per agent (enough for reproduction).
        Full relationship graphs are built lazily during interactions.
        """
        # HOT PATH - called once at init
        _random_sample = random.sample
        _random_random = random.random
        _random_uniform = random.uniform
        _create_rel = self.relationship_system.create_relationship
        
        # Only seed relationships for a subset of agents (enough for initial reproduction)
        agents_list = list(self.agents.values())
        agent_count = len(agents_list)
        
        # For very large populations, only seed relationships for a fraction
        if agent_count > 5000:
            sample_size = min(2000, agent_count // 3)
            agents_to_seed = _random_sample(agents_list, sample_size)
        else:
            agents_to_seed = agents_list
        
        # Group sampled agents by location for efficient pairing
        by_location = {}
        for agent in agents_to_seed:
            loc = agent.location
            if loc not in by_location:
                by_location[loc] = []
            by_location[loc].append(agent)
        
        # Create 2-3 relationships per agent (minimal for reproduction)
        MAX_SEED_RELATIONSHIPS = 3
        
        for loc, loc_agents in by_location.items():
            if len(loc_agents) < 2:
                continue
            
            for agent in loc_agents:
                if len(agent.relationships) >= MAX_SEED_RELATIONSHIPS:
                    continue
                
                # Pick 1-3 random partners
                others = [a for a in loc_agents if a.id != agent.id and a.id not in agent.relationships]
                if not others:
                    continue
                
                num_to_create = min(MAX_SEED_RELATIONSHIPS - len(agent.relationships), len(others))
                partners = _random_sample(others, num_to_create) if len(others) > num_to_create else others[:num_to_create]
                
                for partner in partners:
                    # Create bidirectional relationship
                    rel = _create_rel(partner.id, 0)
                    # Positive relationship for initial population
                    rel.affection = _random_uniform(INITIAL_AFFECTION_MIN, INITIAL_AFFECTION_MAX)
                    rel.trust = _random_uniform(INITIAL_TRUST_MIN, INITIAL_TRUST_MAX)
                    rel.familiarity = _random_uniform(INITIAL_FAMILIARITY_MIN, INITIAL_FAMILIARITY_MAX)
                    agent.relationships[partner.id] = rel
                    
                    # Reverse relationship
                    if agent.id not in partner.relationships:
                        rel2 = _create_rel(agent.id, 0)
                        rel2.affection = rel.affection
                        rel2.trust = rel.trust
                        rel2.familiarity = rel.familiarity
                        partner.relationships[agent.id] = rel2
    
    def get_or_create_relationship(self, agent: HumanAgent, target_id: str, turn: int) -> 'Relationship':
        """Get existing relationship or create a new one lazily.
        
        PERF CRITICAL: Called during interactions. Creates relationships on-demand
        instead of eagerly at initialization.
        """
        if target_id in agent.relationships:
            return agent.relationships[target_id]
        
        # Create new relationship on first interaction
        rel = self.relationship_system.create_relationship(target_id, turn)
        # Start with neutral values (will develop through interactions)
        rel.affection = 0.1
        rel.trust = 0.1
        rel.familiarity = 0.05
        agent.relationships[target_id] = rel
        return rel
    
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
        """Update agent needs each tick.
        
        HOT PATH - CALLED PER AGENT PER TICK
        """
        # PERF CRITICAL: Hoist needs reference
        _needs = agent.needs
        
        # Hunger increases
        _needs.hunger = min(100, _needs.hunger + 1)
        
        # Rest decreases if active
        action = agent.current_action
        if action != "rest" and action != "idle":
            _needs.rest = min(100, _needs.rest + 2)
        
        # Safety decreases with tension and conflicts
        if district_tension > 0.5 or nearby_conflicts > 0:
            safety_loss = (1 if district_tension > 0.5 else 0) + nearby_conflicts * 2
            _needs.safety = max(0, _needs.safety - safety_loss)
        
        # Belonging slowly decreases
        _needs.belonging = max(0, _needs.belonging - 0.5)
        
        # Purpose decreases if idle too long
        if action == "idle" and agent.last_action_turn > 5:
            _needs.purpose = min(100, _needs.purpose + 1)
    
    def update_mood(self, agent: HumanAgent):
        """Update mood from needs and recent events.
        
        HOT PATH - CALLED PER AGENT PER TICK
        """
        # PERF CRITICAL: Hoist needs reference
        _needs = agent.needs
        
        # Base mood from needs (lower needs = better mood)
        need_score = (
            (100 - _needs.hunger) * 0.2 +
            (100 - _needs.rest) * 0.2 +
            (100 - _needs.safety) * 0.3 +
            (100 - _needs.belonging) * 0.15 +
            (100 - _needs.purpose) * 0.15
        ) * 0.01  # Multiply by 0.01 instead of divide by 100
        
        # Recent events affect mood (only check last 3, avoid list copy if possible)
        event_modifier = 0.0
        memory = agent.memory
        mem_len = len(memory)
        if mem_len > 0:
            # Check last 3 events without creating a list slice
            start_idx = max(0, mem_len - 3)
            for i in range(start_idx, mem_len):
                event = memory[i].lower()
                if "conflict" in event or "theft" in event:
                    event_modifier -= 0.2
                elif "help" in event or "trade" in event:
                    event_modifier += 0.1
        
        agent.mood = max(-1.0, min(1.0, (need_score - 0.5) * 2.0 + event_modifier))
    
    def decide_action(self, agent: HumanAgent, district_resources: Dict, available_places: List[str], 
                     other_agents: List[HumanAgent] = None, extinction_risk: float = 0.0,
                     population_pressure: float = 0.0) -> str:
        """
        Decide action using utility function, influenced by relationships, beliefs, and survival drives.
        Returns action type: "move", "work", "trade", "rest", "socialize", "help", "theft", "idle", "farm", "hunt"
        
        HOT PATH - CALLED PER AGENT PER TICK
        """
        if other_agents is None:
            other_agents = []
        
        # PERF CRITICAL: Hoist attribute lookups (avoid repeated . access)
        _needs = agent.needs
        _traits = agent.traits
        _inventory = agent.inventory
        _relationships = agent.relationships
        _agent_location = agent.location
        _agent_role = agent.role
        
        # Cache needs values
        hunger = _needs.hunger
        rest = _needs.rest
        belonging = _needs.belonging
        purpose = _needs.purpose
        
        # Cache traits values
        risk = _traits.risk
        empathy = _traits.empathy
        ambition = _traits.ambition
        
        # Cache dict.get for repeated use
        _res_get = district_resources.get
        _rel_get = _relationships.get
        
        # PERF CRITICAL: Pre-compute nearby relationship stats once instead of multiple times
        # This replaces 4 separate list comprehensions with a single pass
        nearby_trusted = 0
        nearby_positive_high = 0
        nearby_positive_low = 0
        nearby_negative = 0
        
        for other in other_agents:
            if other.location != _agent_location:
                continue
            rel = _rel_get(other.id)
            if rel is None:
                continue
            affection = rel.affection
            if rel.trust > 0.6:
                nearby_trusted += 1
            if affection > 0.3:
                nearby_positive_high += 1
            if affection > 0.2:
                nearby_positive_low += 1
            if affection < -0.3:
                nearby_negative += 1
        
        # Score each possible action
        action_scores = {}
        
        # SURVIVAL DRIVE OVERRIDE (SYSTEM 10, 11, 12)
        survival_override = (extinction_risk > 0.7) or (population_pressure > 0.8)
        
        # Rest action
        action_scores["rest"] = rest * 0.5 - ambition * 20
        
        # Get food action
        if hunger > 50:
            credits = _inventory.credits
            if credits >= 5 and _res_get("food_stock", 0) > 0:
                action_scores["trade"] = hunger * 0.8 - risk * 10
            elif credits < 5 and hunger > 70:
                # Desperate: consider theft
                if risk > 0.6:
                    theft_score = hunger * 0.5 - (1.0 - risk) * 30 - nearby_trusted * 20
                    action_scores["theft"] = theft_score
        
        # Work action
        if _agent_role in ('worker', 'builder') and rest < 70:
            work_score = purpose * 0.4 + ambition * 20
            if _res_get("jobs_available", 0) > 0:
                work_score += 10
            action_scores["work"] = work_score
        
        # Farm action - farmers prioritize farming, others farm when hungry and no food
        food_stock = _res_get("food_stock", 50)
        food_per_capita = food_stock / max(1, _res_get("population", 100))
        food_scarcity = food_per_capita < 1.0
        
        if _agent_role == 'farmer':
            # Farmers farm as their primary activity
            farm_score = 40 + purpose * 0.3 + ambition * 10
            if food_scarcity:
                farm_score += 30  # More urgent when food is low
            if hunger > 50:
                farm_score += 20  # Personal hunger motivation
            if rest < 80:  # Not too tired
                action_scores["farm"] = farm_score
        elif food_scarcity and hunger > 60 and rest < 70:
            # Non-farmers consider farming when desperate
            action_scores["farm"] = 15 + hunger * 0.3
        
        # Hunt action - hunters prioritize hunting, others hunt when food is very scarce
        if _agent_role == 'hunter':
            # Hunters hunt as their primary activity
            hunt_score = 35 + _traits.risk * 15 + ambition * 10
            if food_scarcity:
                hunt_score += 25
            if hunger > 50:
                hunt_score += 15
            if rest < 80:
                action_scores["hunt"] = hunt_score
        elif food_scarcity and hunger > 70 and _traits.risk > 0.5:
            # Non-hunters consider hunting when desperate and brave
            action_scores["hunt"] = 10 + hunger * 0.2 + _traits.risk * 10
        
        # Socialize action
        if belonging < 50:
            social_score = (100 - belonging) * 0.3 + empathy * 15
            social_score += nearby_positive_high * 10
            social_score += agent.reproduction_drive * 20 + agent.survival_drive * 15
            if survival_override:
                social_score += 50
            action_scores["socialize"] = social_score
        
        # Help action
        if empathy > 0.7 and _res_get("tension", 0) > 50:
            help_score = empathy * 25 - hunger * 0.2
            help_score += nearby_positive_low * 15
            action_scores["help"] = help_score
        
        # Move action
        if nearby_negative > 0:
            action_scores["move"] = 30
        elif not action_scores or max(action_scores.values()) < 20:
            action_scores["move"] = 10
        
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
        
        HOT PATH - CALLED PER AGENT PER TICK
        """
        # PERF CRITICAL: Hoist attribute lookups
        _needs = agent.needs
        _traits = agent.traits
        _inventory = agent.inventory
        _relationships = agent.relationships
        _name = agent.name
        _location = agent.location
        _turn = agent.last_action_turn
        _rel_sys = self.relationship_system
        
        # Cache random for tight loops
        _random = random.random
        _randint = random.randint
        _choice = random.choice
        
        agent.current_action = action
        agent.last_action_turn = 0
        
        if action == "rest":
            _needs.rest = max(0, _needs.rest - 20)
            return (f"{_name} rests at {_location}", None)
        
        elif action == "work":
            if district_resources.get("jobs_available", 0) > 0:
                success_chance = 0.7 + _traits.ambition * 0.2 - (_needs.rest / 100.0) * 0.3
                if _random() < success_chance:
                    credits_earned = _randint(3, 8)
                    _inventory.credits += credits_earned
                    _needs.purpose = max(0, _needs.purpose - 15)
                    _needs.rest = min(100, _needs.rest + 5)
                    district_resources["credits_pool"] = district_resources.get("credits_pool", 0) + credits_earned
                    return (f"{_name} works successfully, earns {credits_earned} credits", "work")
                else:
                    _needs.rest = min(100, _needs.rest + 10)
                    return (f"{_name} struggles with work", "work")
            return (f"{_name} looks for work but finds none", None)
        
        elif action == "farm":
            # Farming produces food for the district
            base_food = 3  # Base food production
            skill_bonus = 1.5 if agent.role == 'farmer' else 1.0
            weather_bonus = district_resources.get("weather_farm_modifier", 1.0)
            success_chance = 0.8 + _traits.patience * 0.15 - (_needs.rest / 100.0) * 0.2
            
            if _random() < success_chance:
                food_produced = int(base_food * skill_bonus * weather_bonus * _random() * 0.4 + base_food * skill_bonus * weather_bonus * 0.8)
                food_produced = max(1, food_produced)
                
                # Add food to district
                current_food = district_resources.get("food_stock", 0)
                max_food = district_resources.get("food_capacity", 1000)
                district_resources["food_stock"] = min(max_food, current_food + food_produced)
                
                # Agent benefits
                _needs.purpose = max(0, _needs.purpose - 10)
                _needs.rest = min(100, _needs.rest + 8)
                _inventory.food += 1  # Keep a bit for self
                
                return (f"{_name} farms and produces {food_produced} food", "farm")
            else:
                _needs.rest = min(100, _needs.rest + 5)
                return (f"{_name} works the fields but yields little", "farm")
        
        elif action == "hunt":
            # Hunting produces food for the district (riskier but can yield more)
            base_food = 2
            skill_bonus = 1.3 if agent.role == 'hunter' else 1.0
            weather_bonus = district_resources.get("weather_hunt_modifier", 1.0)
            
            # Hunting success depends on risk-taking and rest
            success_chance = 0.6 + _traits.risk * 0.25 - (_needs.rest / 100.0) * 0.3
            
            if _random() < success_chance:
                # Hunters can get big catches
                food_produced = _randint(1, int(5 * skill_bonus * weather_bonus))
                food_produced = max(1, food_produced)
                
                # Add food to district
                current_food = district_resources.get("food_stock", 0)
                max_food = district_resources.get("food_capacity", 1000)
                district_resources["food_stock"] = min(max_food, current_food + food_produced)
                
                # Agent benefits
                _needs.purpose = max(0, _needs.purpose - 8)
                _needs.rest = min(100, _needs.rest + 10)
                _inventory.food += 1
                
                return (f"{_name} hunts successfully and brings {food_produced} food", "hunt")
            else:
                # Failed hunt is tiring
                _needs.rest = min(100, _needs.rest + 15)
                # Small chance of injury from failed hunt
                if _random() < 0.1:
                    _needs.safety = min(100, _needs.safety + 10)
                    return (f"{_name} returns from a failed hunt, slightly injured", "hunt")
                return (f"{_name} returns from an unsuccessful hunt", "hunt")
        
        elif action == "trade":
            if _inventory.credits >= 5 and district_resources.get("food_stock", 0) > 0:
                base_price = 5
                scarcity_mult = 1.0 + (100 - district_resources.get("food_stock", 50)) / 100.0
                price = int(base_price * scarcity_mult)
                
                if _inventory.credits >= price:
                    _inventory.credits -= price
                    _inventory.food += 3
                    _needs.hunger = max(0, _needs.hunger - 30)
                    district_resources["food_stock"] = max(0, district_resources.get("food_stock", 0) - 3)
                    district_resources["credits_pool"] = district_resources.get("credits_pool", 0) + price
                    return (f"{_name} trades for food (cost: {price} credits)", "trade")
            return (f"{_name} cannot trade (insufficient credits or no food)", None)
        
        elif action == "socialize":
            # Find nearby agents - inline filter for speed
            nearby = [a for a in other_agents if a.location == _location and a.id != agent.id and a.is_alive]
            if nearby:
                other = _choice(nearby)
                _needs.belonging = min(100, _needs.belonging + 10)
                other.needs.belonging = min(100, other.needs.belonging + 5)
                
                # PERF: Use lazy relationship creation
                rel = self.get_or_create_relationship(agent, other.id, _turn)
                _rel_sys.update_from_interaction(rel, "socialize", _turn, True)
                
                # Update other's relationship too
                rel2 = self.get_or_create_relationship(other, agent.id, _turn)
                _rel_sys.update_from_interaction(rel2, "socialize", _turn, True)
                
                return (f"{_name} socializes with {other.name}", "social")
            return (f"{_name} looks for company but finds none", None)
        
        elif action == "help":
            nearby = [a for a in other_agents if a.location == _location and a.id != agent.id and a.is_alive]
            if nearby:
                # Prefer helping agents with positive relationships
                _rel_get = _relationships.get
                best_other = nearby[0]
                best_score = 0.5
                for other in nearby:
                    rel = _rel_get(other.id)
                    score = 0.5
                    if rel:
                        score += rel.affection * 0.3 + rel.trust * 0.2
                    if score > best_score:
                        best_score = score
                        best_other = other
                other = best_other
                
                # PERF: Use lazy relationship creation
                rel = self.get_or_create_relationship(agent, other.id, _turn)
                _rel_sys.update_from_interaction(rel, "cooperation", _turn, True)
                
                # Reduce district tension
                tension_reduction = min(5, int(_traits.empathy * 10))
                district_resources["tension"] = max(0, district_resources.get("tension", 0) - tension_reduction)
                _needs.purpose = max(0, _needs.purpose - 10)
                return (f"{_name} helps others, reduces tension", "help")
            return (f"{_name} finds no one to help", None)
        
        elif action == "theft":
            # Conflict risk
            if _random() < 0.4:  # 40% chance of being caught
                district_resources["tension"] = min(100, district_resources.get("tension", 0) + 10)
                _needs.safety = max(0, _needs.safety - 15)
                agent.memory.append("caught stealing")
                return (f"{_name} attempts theft but is caught", "conflict")
            else:
                _inventory.food += 2
                _needs.hunger = max(0, _needs.hunger - 20)
                district_resources["food_stock"] = max(0, district_resources.get("food_stock", 0) - 2)
                district_resources["tension"] = min(100, district_resources.get("tension", 0) + 5)
                agent.memory.append("successful theft")
                return (f"{_name} steals food", "theft")
        
        elif action == "move":
            # Move to a different location in district
            available = [loc for loc in available_places if loc != _location] if available_places else []
            if available:
                new_location = _choice(available)
                agent.location = new_location
                # OPTIMIZATION 3: Update spatial index when agent moves
                self.spatial_index.add_agent(agent.id, new_location)
                return (f"{_name} moves to {new_location}", None)
        
        return (f"{_name} is idle", None)
    
    def check_conflicts(self, agents: List[HumanAgent], district_resources: Dict, 
                       death_panic_mode: bool = False, generational_trauma: float = 0.0,
                       population_floor_active: bool = False) -> List[Tuple[str, str, str]]:
        """
        Check for conflicts between agents.
        Returns list of (agent1_id, agent2_id, conflict_type) tuples.
        
        SYSTEM C: Death panic mode auto-resolves conflicts
        SYSTEM D: Generational trauma reduces conflicts
        SYSTEM E: Population floor suspends non-age deaths
        
        OPTIMIZATION: For large populations, only sample a subset of agents.
        """
        conflicts = []
        
        # SYSTEM C: Death panic mode - auto-resolve conflicts (no conflicts occur)
        if death_panic_mode:
            return conflicts  # No conflicts in panic mode
        
        # OPTIMIZATION: Sample agents for large populations
        # This maintains statistical conflict rates while reducing computation
        agents_to_check = agents
        population = len(agents)
        if population > 2000:
            # Sample 10% of agents for conflict checks
            sample_size = max(200, population // 10)
            agents_to_check = random.sample(agents, min(sample_size, population))
        elif population > 1000:
            # Sample 25% of agents
            sample_size = max(250, population // 4)
            agents_to_check = random.sample(agents, min(sample_size, population))
        
        # SYSTEM D: Generational trauma reduces conflict likelihood
        trauma_conflict_reduction = generational_trauma * 0.5  # 50% reduction at max trauma
        
        # Group conflicts: if tension high and multiple agents in same place
        if district_resources.get("tension", 0) > 60:
            location_groups: Dict[str, List[HumanAgent]] = {}
            for agent in agents_to_check:  # Use sampled list
                if agent.location not in location_groups:
                    location_groups[agent.location] = []
                location_groups[agent.location].append(agent)
            
            for location, group in location_groups.items():
                if len(group) >= 3 and random.random() < 0.2:  # 20% chance with 3+ agents
                    # Group conflict
                    agent1 = random.choice(group)
                    agent2 = random.choice([a for a in group if a.id != agent1.id])
                    conflicts.append((agent1.id, agent2.id, "group_conflict"))
                    # Update needs - only for sampled group
                    for a in group:
                        a.needs.safety = max(0, a.needs.safety - 10)
                        a.memory.append("witnessed group conflict")
        
        # Individual conflicts: high hunger + low empathy, or relationship-based
        for agent in agents_to_check:  # Use sampled list
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
                # OPTIMIZATION 3: Use spatial index for location queries
                nearby_agent_ids = self.spatial_index.get_agent_ids_at_location(agent.location)
                nearby = [a for a in agents if a.id in nearby_agent_ids and a.id != agent.id and a.is_alive]
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
    
    def _age_agent(self, agent: HumanAgent, turn: int, population_floor_active: bool = False,
                   district_resources: Optional[Dict] = None, weather_state: Optional[Dict] = None,
                   population_count: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Age an agent and check for death from various causes.
        
        SYSTEM E: Population floor - suspend non-age deaths when population <= 2
        
        Returns:
            Tuple of (True if agent died, death_cause string or None)
        """
        return population_age_agent(agent, turn, self.dead_agents, self.agents, population_floor_active,
                                    district_resources, weather_state, population_count)
    
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
            world_flags_system, extinction_risk, population_pressure, birth_pressure,
            couple_children=self.couple_children
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
        # Track children per couple (use sorted tuple for consistency)
        couple_key = tuple(sorted([parent1_id, parent2_id]))
        if couple_key not in self.couple_children:
            self.couple_children[couple_key] = 0
        self.couple_children[couple_key] += 1
        
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
                population_pressure: float = 0.0, birth_pressure: float = 0.0,
                weather_system=None) -> List[Tuple[str, str, Optional[str]]]:
        """
        Advance all agents one tick.
        Returns list of (agent_id, description, event_type) tuples.
        
        HOT PATH - Called every tick. Optimized for minimal overhead.
        
        Learning Integration:
        - If LEARNING_ENABLED: Uses memory manager for micro-memory and district learning
        - If LEARNING_DISABLED: Behavior is BIT-FOR-BIT identical to baseline
        """
        # DEBUG PROFILING: Get profiler for detailed timing
        _profiler = get_profiler()
        _profiler.start_phase("human_agent_advance")
        _advance_start = time.perf_counter()
        
        # PERF CRITICAL: Hoist frequently used methods and attributes
        # Reduces attribute lookup overhead in tight loops
        _agents = self.agents
        _tier_manager = self.tier_manager
        _spatial_index = self.spatial_index
        _child_pools = self.child_pools
        _districts = self.districts
        _relationship_system = self.relationship_system
        
        # Cache dict methods for hot path
        _agents_get = _agents.get
        
        # LEARNING INTEGRATION: Initialize memory manager for this tick
        _memory_manager = None
        _learning_enabled = False
        if _HAS_LEARNING:
            cfg = get_learning_config()
            if cfg and cfg.LEARNING_ENABLED:
                _memory_manager = get_memory_manager()
                if _memory_manager:
                    _memory_manager.begin_tick(turn, len(_agents))
                    _learning_enabled = _memory_manager.is_learning_enabled()
        _res_get = district_resources.get
        
        # PERFORMANCE: Get observer for optional performance tracking
        from living_matrix.utils.observability import get_observer
        observer = get_observer()
        observer.start_tick(turn)
        
        events = []
        # OPTIMIZATION 1: Cache agents_list once per turn (reused throughout method)
        # Use list comp with local reference for speed
        agents_list = [a for a in _agents.values() if a.is_alive]  # Only alive agents
        alive_count = len(agents_list)
        
        # PERFORMANCE: Record population metrics
        child_pool_total = sum(_child_pools.values())
        # Avoid repeated tier_manager calls by caching active set
        _is_active = _tier_manager.is_active
        active_count = sum(1 for a in agents_list if _is_active(a.id))
        observer.record_population(
            active=active_count,
            inactive=alive_count - active_count,
            children=child_pool_total
        )
        
        # SYSTEM 11: Update population pressure and extinction risk effects on agents
        # OPTIMIZATION: Skip drive updates for very large populations (update less frequently)
        update_drives = True
        if alive_count > 2000:
            update_drives = (turn % 2 == 0)  # Every other turn for large populations
        
        if update_drives:
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
        
        # DEBUG PROFILING: Start aging phase timing
        _profiler.start_phase("aging_death_phase")
        
        # Age agents and handle death
        # REQUIRED FIX 1: Minimum Viable Population Guard (Hard Rule)
        # (alive_count already calculated above)
        min_adult_survivors = MIN_ADULT_SURVIVORS
        skip_adult_deaths = alive_count <= min_adult_survivors  # Prevent total wipeout
        population_floor_active = skip_adult_deaths  # Alias for compatibility
        
        # REQUIRED FIX 4: Death Rate Clamp
        max_deaths_allowed = int(alive_count * MAX_ADULT_DEATH_RATE) if alive_count > 0 else 0
        
        dead_this_turn = []
        deaths_count = 0
        
        # Get weather state for agent's district (if world_map and weather_system available)
        weather_state_by_district = {}
        if world_map:
            # Try to get weather system from passed parameter, instance attribute, or world_map
            weather_sys = weather_system or getattr(self, '_weather_system', None) or getattr(world_map, '_weather_system', None)
            if weather_sys:
                # Cache weather states per district
                # Districts are typically region IDs, so we can use them directly
                for district_id in self.districts:
                    # Try district_id as region_id first
                    weather_snapshot = weather_sys.snapshot(district_id)
                    if weather_snapshot:
                        weather_state_by_district[district_id] = {
                            "wind": weather_snapshot.wind,
                            "precipitation": weather_snapshot.precipitation,
                            "temperature": weather_snapshot.temperature
                        }
                    else:
                        # Try to find region by location in district
                        if hasattr(world_map, 'get_region_by_location_id'):
                            for loc_id in self.locations:
                                test_region = world_map.get_region_by_location_id(loc_id)
                                if test_region and test_region.id == district_id:
                                    weather_snapshot = weather_sys.snapshot(test_region.id)
                                    if weather_snapshot:
                                        weather_state_by_district[district_id] = {
                                            "wind": weather_snapshot.wind,
                                            "precipitation": weather_snapshot.precipitation,
                                            "temperature": weather_snapshot.temperature
                                        }
                                    break
        
        # OPTIMIZATION: For very large populations, sample agents for aging
        # Young healthy agents rarely die, so we can skip some of them
        agents_to_age = agents_list
        if alive_count > 3000:
            # Only check elderly/at-risk agents every tick, sample young agents
            at_risk_agents = []
            young_healthy_agents = []
            for a in agents_list:
                # At-risk: old, hungry, tired, or in dangerous conditions
                if a.age > a.lifespan * 0.7 or a.needs.hunger > 80 or a.needs.rest > 90:
                    at_risk_agents.append(a)
                else:
                    young_healthy_agents.append(a)
            
            # Sample 20% of young healthy agents
            if len(young_healthy_agents) > 100:
                sample_size = max(100, len(young_healthy_agents) // 5)
                young_healthy_agents = random.sample(young_healthy_agents, sample_size)
            
            agents_to_age = at_risk_agents + young_healthy_agents
        
        for agent in list(agents_to_age):
            # Skip deaths if we're at minimum viable population
            if skip_adult_deaths:
                break  # Don't process any deaths
            
            # Clamp death rate
            if clamp_death_count(deaths_count, max_deaths_allowed):
                break  # Stop processing deaths if we hit the limit
            
            # Get weather state for this agent's district
            agent_weather_state = weather_state_by_district.get(agent.district)
            
            died, death_cause = self._age_agent(agent, turn, skip_adult_deaths, 
                                                district_resources, agent_weather_state, alive_count)
            if died:
                dead_this_turn.append(agent.id)
                deaths_count += 1
                # OPTIMIZATION 3: Remove dead agent from spatial index
                self.spatial_index.remove_agent(agent.id)
                # PERFORMANCE: Remove from tier manager
                self.tier_manager.remove_agent(agent.id)
                
                # Track death count by cause
                if death_cause:
                    self.death_counts[death_cause] = self.death_counts.get(death_cause, 0) + 1
                else:
                    self.death_counts["unknown"] = self.death_counts.get("unknown", 0) + 1
                
                # Format death message based on cause
                if death_cause == "starvation":
                    death_msg = f"{agent.name} died of starvation"
                elif death_cause == "exhaustion":
                    death_msg = f"{agent.name} died of exhaustion"
                elif death_cause and death_cause.startswith("extreme_weather_"):
                    weather_type = death_cause.replace("extreme_weather_", "")
                    weather_name = weather_type.replace("_", " ").title()
                    death_msg = f"{agent.name} died in {weather_name}"
                elif death_cause == "aging":
                    death_msg = f"{agent.name} died of old age"
                else:
                    death_msg = f"{agent.name} died"
                
                events.append((agent.id, death_msg, "death"))
        
        # OPTIMIZATION 1: Update cached agents_list (remove dead agents)
        agents_list = [a for a in agents_list if a.is_alive]
        
        _profiler.end_phase("aging_death_phase")
        
        # DEBUG PROFILING: Start reproduction phase timing
        _profiler.start_phase("reproduction_phase")
        
        # OPTIMIZATION: Skip reproduction check more frequently for large populations (performance)
        # This reduces computation significantly while maintaining growth patterns
        check_reproduction_this_turn = True
        if alive_count > 2000:
            # For very large populations (>2000), check reproduction every 5th turn
            check_reproduction_this_turn = (turn % 5 == 0)
        elif alive_count > 1500:
            # For large populations (>1500), check reproduction every 4th turn
            check_reproduction_this_turn = (turn % 4 == 0)
        elif alive_count > 1000:
            # For medium-large populations (>1000), check reproduction every 3rd turn
            check_reproduction_this_turn = (turn % 3 == 0)
        elif alive_count > 500:
            # For medium populations (>500), check reproduction every other turn
            check_reproduction_this_turn = (turn % 2 == 0)
        
        # Check for reproduction (POPULATION COMPRESSION: add to child pools, not agents)
        births = []
        if check_reproduction_this_turn:
            world_flags_system = getattr(self, '_world_flags_system', None)
            births = self._check_reproduction(agents_list, district_resources, turn, world_flags_system,
                                             extinction_risk, population_pressure, birth_pressure)
        for parent1_id, parent2_id in births:
            parent1 = self.agents.get(parent1_id)
            parent2 = self.agents.get(parent2_id)
            if parent1 and parent2:
                # Add to child pool instead of creating agent
                district = parent1.district
                if self._add_child_to_pool(parent1_id, parent2_id, district, turn):
                    events.append((parent1_id, f"Child born to {parent1.name} and {parent2.name} in {district}", "birth"))
        
        # POPULATION COMPRESSION: Age child pools statistically
        self._age_child_pools(turn)
        
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
            # OPTIMIZATION 1: Update cached agents_list after spawning
            agents_list = [a for a in self.agents.values() if a.is_alive]
            alive_count = len(agents_list)
        
        # POPULATION COMPRESSION: Promote children to agents (stochastic)
        promotion_events = self._promote_children_to_agents(turn, district_resources)
        events.extend(promotion_events)
        
        # PERFORMANCE: Add newly promoted agents to tier manager
        for event in promotion_events:
            agent_id = event[0]
            if agent_id in self.agents:
                self.tier_manager.add_agent(agent_id, turn)
        
        # OPTIMIZATION 3: Update spatial index after promotions (new agents added)
        if promotion_events:
            # Rebuild spatial index to include newly promoted agents
            agents_list = [a for a in self.agents.values() if a.is_alive]
            self.spatial_index.update_from_agents_list(agents_list)
        
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
        
        # OPTIMIZATION 3: Update spatial index from agents_list
        self.spatial_index.update_from_agents_list(agents_list)
        
        _profiler.end_phase("reproduction_phase")
        
        # DEBUG PROFILING: Start relationship update phase timing
        _profiler.start_phase("relationship_update_phase")
        
        # OPTIMIZATION 2: Batch relationship updates - skip for large populations
        # Only update relationships every N ticks based on population size
        # Also sample agents for very large populations
        update_relationships = True
        if alive_count > 5000:
            update_relationships = (turn % 20 == 0)  # Every 20 ticks
        elif alive_count > 3000:
            update_relationships = (turn % 10 == 0)  # Every 10 ticks
        elif alive_count > 1000:
            update_relationships = (turn % 5 == 0)   # Every 5 ticks
        
        if update_relationships:
            decay_multiplier = 1.0
            if hasattr(self, '_world_flags_system') and self._world_flags_system:
                for flag in self._world_flags_system.get_all_flags():
                    if "relationship_decay_multiplier" in flag.effects:
                        decay_multiplier = max(decay_multiplier, flag.effects["relationship_decay_multiplier"])
            
            # Batch update all relationships
            original_decay = self.relationship_system.decay_rate
            self.relationship_system.decay_rate = original_decay * decay_multiplier
            
            # OPTIMIZATION: For large populations, sample agents for relationship update
            agents_for_rel_update = agents_list
            if alive_count > 2000:
                # Sample 30% of agents for relationship updates
                sample_size = max(500, alive_count // 3)
                agents_for_rel_update = random.sample(agents_list, min(sample_size, alive_count))
            
            relationships_to_remove = []  # Collect relationships to remove
            for agent in agents_for_rel_update:
                for target_id, rel in list(agent.relationships.items()):
                    self.relationship_system.decay_relationship(rel, turn)
                    # Mark very weak relationships for removal
                    if rel.affection == 0.0 and rel.trust < 0.1 and rel.familiarity < 0.1:
                        relationships_to_remove.append((agent.id, target_id))
            
            # Restore decay rate
            self.relationship_system.decay_rate = original_decay
            
            # Remove weak relationships
            for agent_id, target_id in relationships_to_remove:
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    if target_id in agent.relationships:
                        del agent.relationships[target_id]
        
        # OPTIMIZATION: Cache expensive calculations
        district_tension = district_resources.get("tension", 0) / 100.0
        nearby_conflicts = sum(1 for e in events if "conflict" in str(e[2]))
        
        _profiler.end_phase("relationship_update_phase")
        
        # DEBUG PROFILING: Start agent action phase timing
        _profiler.start_phase("agent_action_phase")
        
        # PERFORMANCE: Update tier assignments for stratified simulation
        # This separates agents into active (fully simulated) and inactive (statistical update) tiers
        active_agent_ids, inactive_agent_ids = self.tier_manager.update_assignments(
            self.agents, turn
        )
        
        # OPTIMIZATION: Aggressive skip for large populations
        # The more agents, the more we skip expensive operations
        update_needs_mood = True
        update_goals = True
        
        if alive_count > 5000:
            # Very large: update rarely
            update_needs_mood = (turn % 5 == 0)
            update_goals = (turn % 10 == 0)
        elif alive_count > 3000:
            # Large: update infrequently
            update_needs_mood = (turn % 3 == 0)
            update_goals = (turn % 5 == 0)
        elif alive_count > 2000:
            update_needs_mood = (turn % 2 == 0)
            update_goals = (turn % 3 == 0)
        elif alive_count > 1000:
            update_goals = (turn % 2 == 0)
        
        # PERFORMANCE: Process active agents with full simulation
        active_agents = [a for a in agents_list if a.id in active_agent_ids]
        
        # Check if we should use parallel processing
        from living_matrix.constants.performance_constants import (
            ENABLE_PARALLEL, PARALLEL_THRESHOLD_AGENTS, WORKER_COUNT, AGENT_BATCH_SIZE
        )
        
        use_parallel = ENABLE_PARALLEL and len(active_agents) >= PARALLEL_THRESHOLD_AGENTS
        
        if use_parallel:
            # PARALLEL PATH: Use multiprocessing for large populations
            events.extend(self._process_agents_parallel(
                active_agents, district_resources, available_places,
                extinction_risk, population_pressure, turn, 
                update_needs_mood, update_goals, district_tension, nearby_conflicts
            ))
        else:
            # SEQUENTIAL PATH: Standard processing for small populations
            for agent in active_agents:
                # Update needs (skip for large populations on some turns)
                if update_needs_mood:
                    self.update_needs(agent, district_tension, nearby_conflicts)
                    # Update mood
                    self.update_mood(agent)
                
                # Update goals based on needs (skip more frequently for large populations)
                if update_goals:
                    agent.goals = self._generate_initial_goals(agent)
                
                # OPTIMIZATION 3: Use spatial index for location queries
                # Get nearby agents using spatial index (O(1) lookup instead of O(n) filter)
                nearby_agent_ids_at_loc = self.spatial_index.get_agent_ids_at_location(agent.location)
                other_agents = [a for a in agents_list if a.id in nearby_agent_ids_at_loc and a.id != agent.id]
                
                # Decide and execute action (pass other agents for relationship-based decisions)
                action = self.decide_action(agent, district_resources, available_places, other_agents,
                                           extinction_risk, population_pressure)
                desc, event_type = self.execute_action(agent, action, district_resources, world_map, other_agents)
                
                events.append((agent.id, desc, event_type))
                
                # Record in memory (limit memory size for performance)
                if event_type and len(agent.memory) < 50:  # Limit memory to 50 entries
                    agent.memory.append(desc)
                
                agent.last_action_turn += 1
        
        # PERFORMANCE: Process inactive agents with simplified updates (always fast)
        # Inactive agents get statistical updates (needs decay) but skip action selection
        for agent_id in inactive_agent_ids:
            agent = self.agents.get(agent_id)
            if not agent or not agent.is_alive:
                continue
            
            # Simplified needs update (only basic decay, no decisions)
            if self.tier_manager.should_update_inactive(agent_id, turn):
                # Basic needs decay for inactive agents
                agent.needs.hunger = min(100, agent.needs.hunger + 1)
                if agent.current_action not in ["rest", "idle"]:
                    agent.needs.rest = min(100, agent.needs.rest + 1)
                agent.needs.belonging = max(0, agent.needs.belonging - 0.25)
                agent.last_action_turn += 1
        
        _profiler.end_phase("agent_action_phase")
        
        # DEBUG PROFILING: Start conflict phase timing
        _profiler.start_phase("conflict_phase")
        
        # OPTIMIZATION: Skip conflict checks for very large populations (expensive O(n²) operation)
        # Check conflicts less frequently for large populations
        check_conflicts_this_turn = True
        if alive_count > 3000:
            check_conflicts_this_turn = (turn % 5 == 0)  # Every 5th turn
        elif alive_count > 2000:
            check_conflicts_this_turn = (turn % 3 == 0)  # Every 3rd turn
        elif alive_count > 1000:
            check_conflicts_this_turn = (turn % 2 == 0)  # Every other turn
        
        # Check for conflicts (after all agents have been processed)
        conflict_count = 0
        if check_conflicts_this_turn:
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
                    conflict_count += 1
        
        # PERFORMANCE: Record event metrics and end tick timing
        births_count = len([e for e in events if e[2] == "birth" or e[2] == "emergency_birth"])
        deaths_count_final = len([e for e in events if e[2] == "death"])
        promotions_count = len([e for e in events if e[2] == "promotion"])
        observer.record_events(
            births=births_count,
            deaths=deaths_count_final,
            promotions=promotions_count,
            conflicts=conflict_count
        )
        observer.end_tick()
        
        # LEARNING INTEGRATION: Flush memory and record population stats
        if _learning_enabled and _memory_manager:
            # Record population stats per district (O(1) per district)
            for district_id in _districts:
                district_agents = [a for a in agents_list if a.district == district_id]
                if district_agents:
                    avg_hunger = sum(a.needs.hunger for a in district_agents) / len(district_agents)
                    productivity = sum(1 for e in events if e[2] == "work") / max(1, len(district_agents))
                    _memory_manager.record_population_stats(
                        district_id,
                        hunger_avg=avg_hunger,
                        tension=district_resources.get("tension", 0),
                        death_count=deaths_count_final,
                        productivity=productivity
                    )
            
            # Flush all pending writes
            _memory_manager.end_tick()
        
        _profiler.end_phase("conflict_phase")
        
        # DEBUG PROFILING: End human agent advance phase and record events
        _profiler.record_events(
            births=births_count,
            deaths=deaths_count_final,
            promotions=promotions_count,
            conflicts=conflict_count
        )
        _profiler.end_phase("human_agent_advance")
        
        # DEBUG PROFILING: Log timing summary if enabled
        _advance_duration_ms = (time.perf_counter() - _advance_start) * 1000
        if is_profiling_enabled() and _advance_duration_ms > 500:
            import logging
            logging.getLogger(__name__).warning(
                f"[SLOW] HumanAgentSystem.advance() took {_advance_duration_ms:.1f}ms "
                f"(agents={alive_count}, events={len(events)})"
            )
        
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
        """Get all agents at a location (OPTIMIZATION 3: uses spatial index)."""
        # OPTIMIZATION 3: Use spatial index for O(1) lookup instead of O(n) filter
        agent_ids = self.spatial_index.get_agent_ids_at_location(location)
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents and self.agents[agent_id].is_alive]
    
    def _age_child_pools(self, turn: int):
        """
        Age child pools statistically (POPULATION COMPRESSION).
        Children age in cohorts, not individually.
        """
        population_age_child_pools(turn, self.child_pools, self.child_cohorts)
    
    def _process_agents_parallel(
        self,
        active_agents: List[HumanAgent],
        district_resources: Dict,
        available_places: List[str],
        extinction_risk: float,
        population_pressure: float,
        turn: int,
        update_needs_mood: bool,
        update_goals: bool,
        district_tension: float,
        nearby_conflicts: int
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Process agents in parallel using multiprocessing.
        
        This method uses 4 CPU cores to process agent decisions and actions
        in parallel, providing significant speedup for large populations.
        
        Returns:
            List of (agent_id, description, event_type) tuples
        """
        import multiprocessing as mp
        from living_matrix.constants.performance_constants import WORKER_COUNT, AGENT_BATCH_SIZE
        from living_matrix.core_sim.parallel_worker import (
            serialize_agent, process_agent_batch, apply_action_result
        )
        
        events = []
        
        # Serialize agents for parallel processing
        serialized_agents = [serialize_agent(a) for a in active_agents]
        
        # Create context dict for workers
        context = {
            "food_stock": district_resources.get("food_stock", 50),
            "tension": district_resources.get("tension", 20),
            "jobs_available": district_resources.get("jobs_available", 5),
            "credits_pool": district_resources.get("credits_pool", 100),
            "available_places": available_places,
            "extinction_risk": extinction_risk,
            "population_pressure": population_pressure,
            "nearby_count": 2  # Simplified for parallel
        }
        
        # Split into batches
        batches = []
        for i in range(0, len(serialized_agents), AGENT_BATCH_SIZE):
            batch = serialized_agents[i:i + AGENT_BATCH_SIZE]
            seed_offset = self.seed + turn * 1000 + i
            batches.append((batch, context, seed_offset))
        
        # Process batches in parallel
        try:
            # Create pool if needed (reuse for efficiency)
            if self._parallel_pool is None:
                self._parallel_pool = mp.Pool(processes=WORKER_COUNT)
            
            # Map batches to workers
            batch_results = self._parallel_pool.map(process_agent_batch, batches)
            
            # Flatten results
            all_results = []
            for batch_result in batch_results:
                all_results.extend(batch_result)
            
            # Apply results back to agents
            result_map = {r.agent_id: r for r in all_results}
            for agent in active_agents:
                if agent.id in result_map:
                    result = result_map[agent.id]
                    
                    # Apply needs/mood updates if enabled
                    if update_needs_mood:
                        self.update_needs(agent, district_tension, nearby_conflicts)
                        self.update_mood(agent)
                    
                    if update_goals:
                        agent.goals = self._generate_initial_goals(agent)
                    
                    # Apply action result
                    apply_action_result(agent, result)
                    
                    # Update spatial index if moved
                    if result.new_location:
                        self.spatial_index.add_agent(agent.id, result.new_location)
                    
                    events.append((agent.id, result.description, result.event_type))
                    
                    # Record in memory
                    if result.event_type and len(agent.memory) < 50:
                        agent.memory.append(result.description)
                    
                    agent.last_action_turn += 1
        
        except Exception as e:
            # Fallback to sequential on error
            import logging
            logging.getLogger(__name__).warning(f"Parallel processing failed, falling back to sequential: {e}")
            
            # Close broken pool
            if self._parallel_pool:
                try:
                    self._parallel_pool.terminate()
                except:
                    pass
                self._parallel_pool = None
            
            # Process sequentially
            for agent in active_agents:
                if update_needs_mood:
                    self.update_needs(agent, district_tension, nearby_conflicts)
                    self.update_mood(agent)
                if update_goals:
                    agent.goals = self._generate_initial_goals(agent)
                
                nearby_ids = self.spatial_index.get_agent_ids_at_location(agent.location)
                other = [a for a in active_agents if a.id in nearby_ids and a.id != agent.id]
                
                action = self.decide_action(agent, district_resources, available_places, other,
                                           extinction_risk, population_pressure)
                desc, event_type = self.execute_action(agent, action, district_resources, None, other)
                events.append((agent.id, desc, event_type))
                
                if event_type and len(agent.memory) < 50:
                    agent.memory.append(desc)
                agent.last_action_turn += 1
        
        return events
    
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