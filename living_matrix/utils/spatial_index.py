"""Spatial indexing for efficient location-based agent queries."""

from typing import List, Dict, Set
from collections import defaultdict


class SpatialIndex:
    """
    Spatial index for fast location-based agent lookups.
    Uses a simple hash-based approach: location_id -> set of agent IDs.
    """
    
    def __init__(self):
        """Initialize empty spatial index."""
        # location_id -> set of agent IDs
        self._location_to_agents: Dict[str, Set[str]] = defaultdict(set)
        # agent_id -> location_id (for fast updates)
        self._agent_to_location: Dict[str, str] = {}
    
    def add_agent(self, agent_id: str, location_id: str):
        """Add or update agent location in index."""
        # Remove from old location if exists
        if agent_id in self._agent_to_location:
            old_location = self._agent_to_location[agent_id]
            if old_location in self._location_to_agents:
                self._location_to_agents[old_location].discard(agent_id)
                # Clean up empty sets
                if not self._location_to_agents[old_location]:
                    del self._location_to_agents[old_location]
        
        # Add to new location
        self._location_to_agents[location_id].add(agent_id)
        self._agent_to_location[agent_id] = location_id
    
    def remove_agent(self, agent_id: str):
        """Remove agent from index."""
        if agent_id in self._agent_to_location:
            location_id = self._agent_to_location[agent_id]
            if location_id in self._location_to_agents:
                self._location_to_agents[location_id].discard(agent_id)
                if not self._location_to_agents[location_id]:
                    del self._location_to_agents[location_id]
            del self._agent_to_location[agent_id]
    
    def get_agent_ids_at_location(self, location_id: str) -> Set[str]:
        """Get set of agent IDs at a location (O(1) lookup)."""
        return self._location_to_agents.get(location_id, set())
    
    def clear(self):
        """Clear all entries."""
        self._location_to_agents.clear()
        self._agent_to_location.clear()
    
    def rebuild(self, agents: Dict[str, object]):
        """
        Rebuild index from agent dictionary.
        Agents must have .location and .is_alive attributes.
        """
        self.clear()
        for agent_id, agent in agents.items():
            if hasattr(agent, 'is_alive') and agent.is_alive and hasattr(agent, 'location'):
                self.add_agent(agent_id, agent.location)
    
    def update_from_agents_list(self, agents_list: List[object]):
        """
        Update index from list of agents.
        Agents must have .id, .location, and .is_alive attributes.
        """
        # Get current agent IDs
        current_agent_ids = set(self._agent_to_location.keys())
        new_agent_ids = {agent.id for agent in agents_list if agent.is_alive}
        
        # Remove agents that are no longer alive
        for agent_id in current_agent_ids - new_agent_ids:
            self.remove_agent(agent_id)
        
        # Add/update alive agents
        for agent in agents_list:
            if agent.is_alive and hasattr(agent, 'location'):
                self.add_agent(agent.id, agent.location)
