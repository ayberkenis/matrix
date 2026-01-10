"""World simulation state persistence."""

import json
from pathlib import Path
from typing import Optional

from .time import TimeSystem
from .map import WorldMap
from .weather import WeatherSystem
from .agents import AgentSystem
from .events import EventSystem


class WorldSimState:
    """Manages persistence of world simulation state."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize world simulation state manager.
        
        Args:
            data_dir: Directory for saving state files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / "world_state.json"
        self.backup_file = self.data_dir / "world_state.json.bak"
    
    def save(self, time: TimeSystem, world_map: WorldMap, weather: WeatherSystem,
             agents: AgentSystem, events: EventSystem):
        """
        Save world simulation state to PostgreSQL (fire-and-forget).
        
        This method does NOT block. Errors are logged but not propagated.
        
        Args:
            time: TimeSystem instance
            world_map: WorldMap instance
            weather: WeatherSystem instance
            agents: AgentSystem instance
            events: EventSystem instance
        """
        data = {
            "schema_version": 1,
            "time": time.to_dict(),
            "world_map": world_map.to_dict(),
            "weather": weather.to_dict(),
            "agents": agents.to_dict(),
            "events": events.to_dict()
        }
        
        # Write to PostgreSQL asynchronously
        try:
            from living_matrix.persistence.snapshot_writer import write_snapshot
            turn = time.day_index if hasattr(time, 'day_index') else 0
            write_snapshot(turn, data)
        except Exception as e:
            # Log error but don't propagate - simulation must continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving world simulation state: {e}", exc_info=True)
    
    def load(self, seed: int = 42) -> Optional[tuple]:
        """
        Load world simulation state from disk.
        
        Args:
            seed: Seed to use if creating new state
            
        Returns:
            Tuple of (time, world_map, weather, agents, events) or None if failed
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check schema version
            schema_version = data.get("schema_version", 0)
            if schema_version != 1:
                print(f"Warning: World state schema version {schema_version} may be incompatible.")
            
            # Load components
            time = TimeSystem.from_dict(data.get("time", {}))
            world_map = WorldMap.from_dict(data.get("world_map", {}))
            
            region_ids = list(world_map.regions.keys())
            weather = WeatherSystem.from_dict(data.get("weather", {}), region_ids)
            
            location_ids = list(world_map.locations.keys())
            agents = AgentSystem.from_dict(data.get("agents", {}), location_ids)
            
            events = EventSystem.from_dict(data.get("events", {}))
            
            return (time, world_map, weather, agents, events)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Try backup
            if self.backup_file.exists():
                try:
                    with open(self.backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    time = TimeSystem.from_dict(data.get("time", {}))
                    world_map = WorldMap.from_dict(data.get("world_map", {}))
                    region_ids = list(world_map.regions.keys())
                    weather = WeatherSystem.from_dict(data.get("weather", {}), region_ids)
                    location_ids = list(world_map.locations.keys())
                    agents = AgentSystem.from_dict(data.get("agents", {}), location_ids)
                    events = EventSystem.from_dict(data.get("events", {}))
                    
                    return (time, world_map, weather, agents, events)
                except:
                    pass
            
            print(f"Error loading world state: {e}")
            return None
