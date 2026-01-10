"""Mortality and aging functions."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from living_matrix.human_agent import HumanAgent


def age_agent(agent: 'HumanAgent', turn: int, dead_agents: dict, agents: dict, 
               population_floor_active: bool = False) -> bool:
    """
    Age an agent and check for death.
    
    SYSTEM E: Population floor - suspend non-age deaths when population <= 2
    
    Args:
        agent: Agent to age
        turn: Current turn
        dead_agents: Dictionary of dead agents
        agents: Dictionary of active agents
        population_floor_active: Whether population floor is active
        
    Returns:
        True if agent died, False otherwise
    """
    if not agent.is_alive:
        return False
    
    # Slow down aging: age by 0.5 turns per simulation turn (agents live twice as long)
    # This gives agents more time to reproduce before becoming elders
    agent.age += 0.5
    
    # Update survival drives based on age (SYSTEM 10)
    # Reproduction drive peaks at reproductive age, decreases with age
    # Adjusted for slower aging and wider reproductive window
    age_int = int(agent.age)
    if age_int < 100:  # Very young - building up
        agent.reproduction_drive = min(0.9, agent.reproduction_drive + 0.02)
    elif 100 <= age_int <= 1000:  # Prime reproductive years (very wide window)
        agent.reproduction_drive = min(0.95, agent.reproduction_drive + 0.01)  # Keep high
    elif age_int > 1000:  # Elderly - declining but still possible
        agent.reproduction_drive = max(0.3, agent.reproduction_drive - 0.01)  # Slow decline
    
    # Legacy drive increases with age and losses
    agent.legacy_drive = min(1.0, agent.legacy_drive + (agent.age / 10000.0) + (agent.dead_friends_count * 0.1))
    
    # Check for death
    # SYSTEM E: Population floor - only allow age-based death when population <= 2
    # Use int() to handle fractional ages from slower aging
    if int(agent.age) >= agent.lifespan:
        # Age-based death is always allowed (natural death)
        agent.is_alive = False
        agent.death_turn = turn
        # Move to dead_agents
        dead_agents[agent.id] = agent
        # Remove from active agents
        if agent.id in agents:
            del agents[agent.id]
        return True
    
    return False
