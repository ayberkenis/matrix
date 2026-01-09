"""World bulletin formatting."""

from typing import List, Optional
from .time import TimeSystem
from .map import WorldMap
from .weather import WeatherSystem
from .events import EventSystem
from .agents import AgentSystem


def format_world_bulletin(
    time: TimeSystem,
    world_map: WorldMap,
    weather: WeatherSystem,
    events: EventSystem,
    follow_agent_id: Optional[str] = None,
    agent_system: Optional[AgentSystem] = None
) -> str:
    """
    Format a world bulletin (4-8 lines).
    
    Args:
        time: TimeSystem instance
        world_map: WorldMap instance
        weather: WeatherSystem instance
        events: EventSystem instance
        follow_agent_id: Optional agent ID to include follow section
        agent_system: Optional AgentSystem for follow section
        
    Returns:
        Formatted bulletin string
    """
    lines = []
    
    # 1. Time line
    lines.append(time.format_time())
    
    # 2. Weather line
    lines.append(weather.format_weather_line())
    
    # 3. Hotspot line
    hotspots = world_map.get_hotspots(top_n=3)
    if hotspots:
        hotspot_strs = [f"{loc.name} ({int(density * 15)})" for loc, density in hotspots]
        lines.append(f"Hotspots: {', '.join(hotspot_strs)}")
    else:
        lines.append("Hotspots: (quiet)")
    
    # 4. Event lines (1-2 from latest events)
    recent_events = events.get_recent_events(n=5)
    if recent_events:
        # Show 1-2 most recent events
        for event in recent_events[-2:]:
            lines.append(f"Event: {event.description}")
    else:
        lines.append("Event: (quiet moment)")
    
    # 5. Resource warnings
    low_food_regions = [r for r in world_map.regions.values() if r.food < 20]
    if low_food_regions:
        region_names = [r.name for r in low_food_regions[:2]]
        lines.append(f"Warning: Food low in {', '.join(region_names)}")
    
    # 6. Optional rumor line (aggregate from event types and world state)
    if agent_system and len(recent_events) > 0:
        # Simple rumor generation from event types and world state
        event_types = [e.event_type for e in recent_events[-5:]]
        avg_tension = sum(r.tension for r in world_map.regions.values()) / len(world_map.regions) if world_map.regions else 0
        
        if avg_tension > 0.6 or 'minor_conflict' in event_types:
            lines.append("Rumor: people mention 'tensions' in the districts.")
        elif 'helping' in event_types:
            lines.append("Rumor: people mention 'cooperation' among workers.")
        elif 'discovery' in event_types:
            lines.append("Rumor: people mention 'new findings' in the regions.")
        elif sum(1 for r in world_map.regions.values() if r.food < 30) > len(world_map.regions) / 2:
            lines.append("Rumor: people mention 'shortage' across regions.")
    
    # 7. Follow section (if following an agent)
    if follow_agent_id and agent_system:
        agent = agent_system.get_agent(follow_agent_id)
        if agent:
            loc = world_map.get_location(agent.current_location)
            lines.append(f"Follow: {agent.name} ({agent.role}) is at {loc.name if loc else 'unknown'}, {agent.schedule}")
    
    return "\n".join(lines)
