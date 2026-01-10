"""Agent state management functions."""

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from living_matrix.human_agent import HumanAgent


def get_alive_agents(agents: Dict[str, 'HumanAgent']) -> List['HumanAgent']:
    """
    Get list of alive agents.
    
    Args:
        agents: Dictionary of agents
        
    Returns:
        List of alive agents
    """
    return [a for a in agents.values() if a.is_alive]


def get_agents_in_district(agents: Dict[str, 'HumanAgent'], district_id: str) -> List['HumanAgent']:
    """
    Get agents in a specific district.
    
    Args:
        agents: Dictionary of agents
        district_id: District ID
        
    Returns:
        List of agents in district
    """
    return [a for a in agents.values() if a.district == district_id and a.is_alive]


def count_agents_in_district(agents: Dict[str, 'HumanAgent'], district_id: str) -> int:
    """
    Count agents in a specific district.
    
    Args:
        agents: Dictionary of agents
        district_id: District ID
        
    Returns:
        Count of agents in district
    """
    return len(get_agents_in_district(agents, district_id))


def get_agents_at_location(agents: Dict[str, 'HumanAgent'], location_id: str) -> List['HumanAgent']:
    """
    Get agents at a specific location.
    
    Args:
        agents: Dictionary of agents
        location_id: Location ID
        
    Returns:
        List of agents at location
    """
    return [a for a in agents.values() if a.location == location_id and a.is_alive]


def count_alive_agents(agents: Dict[str, 'HumanAgent']) -> int:
    """
    Count alive agents.
    
    Args:
        agents: Dictionary of agents
        
    Returns:
        Count of alive agents
    """
    return len(get_alive_agents(agents))


def get_recent_deaths(dead_agents: Dict[str, 'HumanAgent'], current_turn: int,
                     window: int = 50) -> int:
    """
    Get count of recent deaths.
    
    Args:
        dead_agents: Dictionary of dead agents
        current_turn: Current turn
        window: Time window for recent deaths
        
    Returns:
        Count of recent deaths
    """
    return sum(1 for a in dead_agents.values() 
              if a.death_turn and (current_turn - a.death_turn) <= window)


def is_death_panic_mode(alive_count: int, threshold: int = 15) -> bool:
    """
    Check if in death panic mode (SYSTEM C).
    
    Args:
        alive_count: Current alive agent count
        threshold: Death panic threshold
        
    Returns:
        True if in death panic mode
    """
    return alive_count < threshold
