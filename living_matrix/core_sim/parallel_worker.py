"""Parallel worker functions for agent processing.

These functions run in separate processes and handle batches of agents.
They must be picklable and not depend on instance methods.
"""

import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class AgentState:
    """Minimal serializable agent state for parallel processing."""
    id: str
    location: str
    district: str
    role: str
    current_action: str
    hunger: int
    rest: int
    safety: int
    belonging: int
    purpose: int
    mood: float
    risk: float
    empathy: float
    ambition: float
    patience: float
    credits: int
    food: int
    reproduction_drive: float
    survival_drive: float
    must_attempt_reproduction: bool


@dataclass
class ActionResult:
    """Result from processing an agent's action."""
    agent_id: str
    action: str
    description: str
    event_type: Optional[str]
    hunger_delta: int = 0
    rest_delta: int = 0
    safety_delta: int = 0
    belonging_delta: float = 0
    purpose_delta: int = 0
    credits_delta: int = 0
    food_delta: int = 0
    new_location: Optional[str] = None


def decide_action_pure(
    agent: AgentState,
    food_stock: float,
    tension: float,
    jobs_available: int,
    nearby_agent_count: int,
    extinction_risk: float,
    population_pressure: float
) -> str:
    """
    Pure function to decide agent action.
    
    This is a simplified version of decide_action that doesn't
    require the full agent object or relationships.
    """
    action_scores = {}
    
    # Survival override
    survival_override = (extinction_risk > 0.7) or (population_pressure > 0.8)
    
    # Rest action
    rest_score = agent.rest * 0.5 - agent.ambition * 20
    action_scores["rest"] = rest_score
    
    # Get food action
    if agent.hunger > 50:
        if agent.credits >= 5 and food_stock > 0:
            trade_score = agent.hunger * 0.8 - agent.risk * 10
            action_scores["trade"] = trade_score
        elif agent.credits < 5 and agent.hunger > 70:
            if agent.risk > 0.6:
                theft_score = agent.hunger * 0.5 - (1.0 - agent.risk) * 30
                action_scores["theft"] = theft_score
    
    # Work action
    if agent.role in ['worker', 'builder'] and agent.rest < 70:
        work_score = agent.purpose * 0.4 + agent.ambition * 20
        if jobs_available > 0:
            work_score += 10
        action_scores["work"] = work_score
    
    # Socialize action
    if agent.belonging < 50:
        social_score = (100 - agent.belonging) * 0.3 + agent.empathy * 15
        social_score += nearby_agent_count * 5
        social_score += agent.reproduction_drive * 20 + agent.survival_drive * 15
        if survival_override:
            social_score += 50
        action_scores["socialize"] = social_score
    
    # Help action
    if agent.empathy > 0.7 and tension > 50:
        help_score = agent.empathy * 25 - agent.hunger * 0.2
        action_scores["help"] = help_score
    
    # Move action
    if not action_scores or max(action_scores.values()) < 20:
        action_scores["move"] = 10
    
    # Must reproduce override
    if agent.must_attempt_reproduction:
        action_scores["socialize"] = action_scores.get("socialize", 0) + 100
    
    # Survival bonus
    for action in action_scores:
        survival_bonus = (
            agent.survival_drive * 0.4 * 30 +
            agent.reproduction_drive * 0.3 * 25
        )
        if extinction_risk > 0.6:
            survival_bonus *= (1.0 + extinction_risk * 2.0)
        action_scores[action] += survival_bonus
    
    if action_scores:
        return max(action_scores.items(), key=lambda x: x[1])[0]
    return "idle"


def execute_action_pure(
    agent: AgentState,
    action: str,
    food_stock: float,
    tension: float,
    credits_pool: float,
    available_places: List[str]
) -> ActionResult:
    """
    Pure function to execute an agent action.
    
    Returns deltas to apply to agent state.
    """
    result = ActionResult(
        agent_id=agent.id,
        action=action,
        description=f"{agent.id} is idle",
        event_type=None
    )
    
    if action == "rest":
        result.rest_delta = -20
        result.description = f"{agent.id} rests"
    
    elif action == "work":
        if random.random() < 0.7 + agent.ambition * 0.2:
            credits_earned = random.randint(3, 8)
            result.credits_delta = credits_earned
            result.purpose_delta = -15
            result.rest_delta = 5
            result.description = f"{agent.id} works, earns {credits_earned} credits"
            result.event_type = "work"
        else:
            result.rest_delta = 10
            result.description = f"{agent.id} struggles with work"
            result.event_type = "work"
    
    elif action == "trade":
        if agent.credits >= 5 and food_stock > 0:
            result.credits_delta = -5
            result.food_delta = 3
            result.hunger_delta = -30
            result.description = f"{agent.id} trades for food"
            result.event_type = "trade"
    
    elif action == "socialize":
        result.belonging_delta = 10
        result.description = f"{agent.id} socializes"
        result.event_type = "social"
    
    elif action == "help":
        result.purpose_delta = -10
        result.description = f"{agent.id} helps others"
        result.event_type = "help"
    
    elif action == "theft":
        if random.random() < 0.4:
            result.safety_delta = -15
            result.description = f"{agent.id} caught stealing"
            result.event_type = "conflict"
        else:
            result.food_delta = 2
            result.hunger_delta = -20
            result.description = f"{agent.id} steals food"
            result.event_type = "theft"
    
    elif action == "move":
        if available_places:
            new_loc = random.choice([p for p in available_places if p != agent.location] or available_places)
            result.new_location = new_loc
            result.description = f"{agent.id} moves to {new_loc}"
    
    return result


def process_agent_batch(args: Tuple) -> List[ActionResult]:
    """
    Process a batch of agents in parallel.
    
    Args is a tuple of:
        - batch_agents: List of AgentState
        - context: Dict with food_stock, tension, jobs_available, etc.
        - seed_offset: int for deterministic RNG
    
    Returns list of ActionResults.
    """
    batch_agents, context, seed_offset = args
    
    # Set deterministic RNG for this batch
    random.seed(seed_offset)
    
    results = []
    
    for agent in batch_agents:
        # Decide action
        action = decide_action_pure(
            agent,
            food_stock=context["food_stock"],
            tension=context["tension"],
            jobs_available=context["jobs_available"],
            nearby_agent_count=context.get("nearby_count", 2),
            extinction_risk=context.get("extinction_risk", 0.0),
            population_pressure=context.get("population_pressure", 0.0)
        )
        
        # Execute action
        result = execute_action_pure(
            agent,
            action,
            food_stock=context["food_stock"],
            tension=context["tension"],
            credits_pool=context["credits_pool"],
            available_places=context["available_places"]
        )
        
        results.append(result)
    
    return results


def serialize_agent(agent) -> AgentState:
    """Convert HumanAgent to serializable AgentState."""
    return AgentState(
        id=agent.id,
        location=agent.location,
        district=agent.district,
        role=agent.role,
        current_action=agent.current_action,
        hunger=agent.needs.hunger,
        rest=agent.needs.rest,
        safety=agent.needs.safety,
        belonging=agent.needs.belonging,
        purpose=agent.needs.purpose,
        mood=agent.mood,
        risk=agent.traits.risk,
        empathy=agent.traits.empathy,
        ambition=agent.traits.ambition,
        patience=agent.traits.patience,
        credits=agent.inventory.credits,
        food=agent.inventory.food,
        reproduction_drive=agent.reproduction_drive,
        survival_drive=agent.survival_drive,
        must_attempt_reproduction=agent.must_attempt_reproduction
    )


def apply_action_result(agent, result: ActionResult) -> None:
    """Apply ActionResult deltas back to agent."""
    agent.current_action = result.action
    
    # Apply deltas
    agent.needs.hunger = max(0, min(100, agent.needs.hunger + result.hunger_delta))
    agent.needs.rest = max(0, min(100, agent.needs.rest + result.rest_delta))
    agent.needs.safety = max(0, min(100, agent.needs.safety + result.safety_delta))
    agent.needs.belonging = max(0, min(100, agent.needs.belonging + result.belonging_delta))
    agent.needs.purpose = max(0, min(100, agent.needs.purpose + result.purpose_delta))
    agent.inventory.credits = max(0, agent.inventory.credits + result.credits_delta)
    agent.inventory.food = max(0, agent.inventory.food + result.food_delta)
    
    if result.new_location:
        agent.location = result.new_location
