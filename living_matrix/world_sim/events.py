"""Event system for world simulation."""

import random
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class Event:
    """An event in the world."""
    turn: int
    event_type: str  # commute, market_trade, shift_start, shift_end, meal, rest, meeting, minor_conflict, helping, discovery
    description: str
    location_id: Optional[str] = None
    agent_ids: List[str] = None


class EventSystem:
    """Manages event generation and logging."""
    
    EVENT_TYPES = [
        'commute', 'market_trade', 'shift_start', 'shift_end',
        'meal', 'rest', 'meeting', 'minor_conflict', 'helping', 'discovery'
    ]
    
    def __init__(self, seed: int = 42):
        """
        Initialize event system.
        
        Args:
            seed: Random seed for deterministic behavior
        """
        self.seed = seed
        random.seed(seed)
        self.event_log: deque = deque(maxlen=200)
        self.turn = 0
    
    def advance(self, world_map, agents, agent_actions: List[tuple], 
                tensor_modifier: float = 0.0) -> List[Event]:
        """
        Advance event system and generate new events.
        
        Args:
            world_map: WorldMap instance
            agents: AgentSystem instance
            agent_actions: List of (agent_id, action) tuples from agent system
            tensor_modifier: Small modifier from tensor core (-0.1 to 0.1)
            
        Returns:
            List of newly generated events
        """
        self.turn += 1
        new_events = []
        
        # Generate events from agent actions
        for agent_id, action in agent_actions:
            agent = agents.get_agent(agent_id)
            if not agent:
                continue
            
            # Determine event type from action
            event_type = self._classify_action(action, agent)
            
            # Apply tensor modifier (subtle influence)
            if event_type in ['minor_conflict', 'helping']:
                if tensor_modifier > 0.05:
                    event_type = 'helping'
                elif tensor_modifier < -0.05:
                    event_type = 'minor_conflict'
            
            # Create event
            event = Event(
                turn=self.turn,
                event_type=event_type,
                description=action,
                location_id=agent.current_location,
                agent_ids=[agent_id]
            )
            
            new_events.append(event)
            self.event_log.append(event)
        
        # Generate occasional spontaneous events
        if random.random() < 0.1:  # 10% chance per turn
            event = self._generate_spontaneous_event(world_map, agents)
            if event:
                new_events.append(event)
                self.event_log.append(event)
        
        return new_events
    
    def _classify_action(self, action: str, agent) -> str:
        """Classify an action into an event type."""
        action_lower = action.lower()
        
        if 'work' in action_lower or 'shift' in action_lower:
            if 'goes to work' in action_lower:
                return 'shift_start'
            return 'shift_end'
        elif 'market' in action_lower or 'trade' in action_lower:
            return 'market_trade'
        elif 'rest' in action_lower or 'sleep' in action_lower:
            return 'rest'
        elif 'food' in action_lower or 'meal' in action_lower:
            return 'meal'
        elif 'socialize' in action_lower or 'visit' in action_lower:
            return 'meeting'
        elif 'move' in action_lower or 'transit' in action_lower:
            return 'commute'
        else:
            return 'rest'  # Default
    
    def _generate_spontaneous_event(self, world_map, agents) -> Optional[Event]:
        """Generate a spontaneous event (conflict, helping, discovery)."""
        event_type = random.choice(['minor_conflict', 'helping', 'discovery'])
        
        # Get random location with agents
        hotspots = world_map.get_hotspots(top_n=5)
        if not hotspots:
            return None
        
        loc, _ = random.choice(hotspots)
        agents_at_loc = agents.get_agents_at_location(loc.id)
        
        if len(agents_at_loc) < 2:
            return None
        
        agent1, agent2 = random.sample(agents_at_loc, 2)
        
        if event_type == 'minor_conflict':
            desc = f"{agent1.name} and {agent2.name} have a brief disagreement at {loc.name}; it fades quickly."
        elif event_type == 'helping':
            desc = f"{agent1.name} helps {agent2.name} at {loc.name}."
        else:  # discovery
            desc = f"{agent1.name} discovers something interesting at {loc.name}."
        
        return Event(
            turn=self.turn,
            event_type=event_type,
            description=desc,
            location_id=loc.id,
            agent_ids=[agent1.id, agent2.id]
        )
    
    def get_recent_events(self, n: int = 10) -> List[Event]:
        """Get the last N events."""
        return list(self.event_log)[-n:]
    
    def get_events_by_type(self, event_type: str) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.event_log if e.event_type == event_type]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "turn": self.turn,
            "events": [
                {
                    "turn": e.turn,
                    "event_type": e.event_type,
                    "description": e.description,
                    "location_id": e.location_id,
                    "agent_ids": e.agent_ids or []
                }
                for e in self.event_log
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EventSystem":
        """Deserialize from dictionary."""
        obj = cls(seed=data.get("seed", 42))
        obj.turn = data.get("turn", 0)
        
        for edata in data.get("events", []):
            event = Event(
                turn=edata["turn"],
                event_type=edata["event_type"],
                description=edata["description"],
                location_id=edata.get("location_id"),
                agent_ids=edata.get("agent_ids", [])
            )
            obj.event_log.append(event)
        
        return obj
