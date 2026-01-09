"""Terminal UI panels: minimap, heatmap, event feed, agent list."""

import os
import sys
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class UISettings:
    """UI settings."""
    enabled: bool = False
    clear_screen: bool = True
    mode: str = "full"  # "full" or "compact"
    fps_limit: int = 0  # 0 = no limit, render every tick


class UIPanels:
    """Terminal UI panel rendering system."""
    
    def __init__(self):
        """Initialize UI panels."""
        self.settings = UISettings()
        self.last_render_turn = -1
    
    def should_render(self, turn: int) -> bool:
        """Check if we should render this turn."""
        if not self.settings.enabled:
            return False
        if self.settings.fps_limit > 0:
            # Limit rendering frequency
            if turn - self.last_render_turn < self.settings.fps_limit:
                return False
        self.last_render_turn = turn
        return True
    
    def clear_screen(self):
        """Clear terminal screen (cross-platform)."""
        if self.settings.clear_screen:
            os.system("cls" if os.name == "nt" else "clear")
    
    def render_minimap(self, districts: List[str], agents: List, focused_agent_id: Optional[str] = None, 
                      width: int = 20, height: int = 8) -> List[str]:
        """
        Render minimap as ASCII grid.
        
        Args:
            districts: List of district names
            agents: List of agent objects with location/district
            focused_agent_id: ID of agent to highlight
            width: Grid width
            height: Grid height
            
        Returns:
            List of strings (lines) for minimap
        """
        lines = ["MINIMAP:"]
        
        # Simple representation: one char per district
        grid = [['.' for _ in range(width)] for _ in range(height)]
        
        # Map districts to grid positions
        district_positions = {}
        for i, district in enumerate(districts[:width * height]):
            x = i % width
            y = i // width
            district_positions[district] = (x, y)
            # Use first letter of district name
            char = district[0].upper() if district else '?'
            grid[y][x] = char
        
        # Place agents
        agent_chars = {}
        for agent in agents:
            district = getattr(agent, 'district', None) or getattr(agent, 'current_location', 'unknown')
            if district in district_positions:
                x, y = district_positions[district]
                agent_id = getattr(agent, 'id', '')
                
                # Highlight focused agent
                if agent_id == focused_agent_id:
                    grid[y][x] = '*'
                else:
                    # Use agent name initial
                    name = getattr(agent, 'name', '?')
                    char = name[0].upper() if name else '?'
                    if grid[y][x] == '.':
                        grid[y][x] = char
                    elif grid[y][x] not in agent_chars:
                        agent_chars[grid[y][x]] = 1
        
        # Convert grid to strings
        for row in grid:
            lines.append("".join(row))
        
        return lines
    
    def render_heatmap(self, districts: List, economy_system) -> List[str]:
        """
        Render heatmap showing district tension and food stocks.
        
        Args:
            districts: List of district objects or names
            economy_system: EconomySystem instance
            
        Returns:
            List of strings (lines) for heatmap
        """
        lines = ["HEATMAP:"]
        
        for district in districts:
            district_id = getattr(district, 'id', district) if isinstance(district, str) else district
            district_name = getattr(district, 'name', district_id) if not isinstance(district, str) else district_id.replace("region_", "").title()
            
            # Get economy data
            if economy_system:
                economy = economy_system.get_district(district_id)
                if economy:
                    tension = economy.tension
                    food_stock = economy.food_stock
                else:
                    tension = 20
                    food_stock = 50
            else:
                tension = 20
                food_stock = 50
            
            # Tension bar
            tension_bar_length = int(tension / 10)
            tension_bar = "#" * tension_bar_length + "." * (10 - tension_bar_length)
            
            # Food stock bar
            food_bar_length = int(food_stock / 10)
            food_bar = "#" * food_bar_length + "." * (10 - food_bar_length)
            
            lines.append(f"{district_name[:12]:12} Tension: [{tension_bar}] {tension}")
            lines.append(f"{'':12} Food:    [{food_bar}] {food_stock}")
        
        return lines
    
    def render_event_feed(self, events: List, max_events: int = 10) -> List[str]:
        """
        Render event feed.
        
        Args:
            events: List of event strings or tuples
            max_events: Maximum number of events to show
            
        Returns:
            List of strings (lines) for event feed
        """
        lines = ["EVENT FEED:"]
        
        # Get last N events
        recent_events = events[-max_events:] if len(events) > max_events else events
        
        for event in recent_events:
            # Handle both string and tuple formats
            if isinstance(event, tuple):
                if len(event) >= 2:
                    event_str = event[1]  # Description
                else:
                    event_str = str(event[0])
            else:
                event_str = str(event)
            
            lines.append(f"  • {event_str}")
        
        if not recent_events:
            lines.append("  (no recent events)")
        
        return lines
    
    def render_agent_list(self, agents: List, max_agents: int = 8, 
                         focused_agent_id: Optional[str] = None) -> List[str]:
        """
        Render agent list table.
        
        Args:
            agents: List of agent objects
            max_agents: Maximum number of agents to show
            focused_agent_id: ID of agent to highlight
            
        Returns:
            List of strings (lines) for agent list
        """
        lines = ["AGENTS:"]
        lines.append(f"{'Name':<12} {'Role':<10} {'Hunger':<8} {'Mood':<8} {'Location':<12}")
        lines.append("-" * 60)
        
        # Sort by relevance (focused first, then by hunger/mood)
        sorted_agents = sorted(agents, key=lambda a: (
            0 if getattr(a, 'id', '') == focused_agent_id else 1,
            getattr(a, 'needs', None) and getattr(a.needs, 'hunger', 0) or 0
        ))
        
        for agent in sorted_agents[:max_agents]:
            name = getattr(agent, 'name', '?')
            role = getattr(agent, 'role', '?')
            needs = getattr(agent, 'needs', None)
            hunger = getattr(needs, 'hunger', 0) if needs else 0
            mood = getattr(agent, 'mood', 0.0)
            location = getattr(agent, 'location', '?')
            
            # Highlight focused agent
            marker = ">" if getattr(agent, 'id', '') == focused_agent_id else " "
            
            lines.append(f"{marker}{name:<11} {role:<10} {hunger:<8} {mood:+.2f}   {location[:11]:<12}")
        
        return lines
    
    def render_agent_panel(self, agent) -> List[str]:
        """
        Render detailed agent panel (for AGENT camera mode).
        
        Args:
            agent: Agent object
            
        Returns:
            List of strings (lines) for agent panel
        """
        if not agent:
            return ["AGENT: (not found)"]
        
        lines = [f"AGENT: {getattr(agent, 'name', '?')}"]
        lines.append("-" * 40)
        
        # Basic info
        role = getattr(agent, 'role', '?')
        district = getattr(agent, 'district', '?')
        location = getattr(agent, 'location', '?')
        lines.append(f"Role: {role} | District: {district} | Location: {location}")
        
        # Needs
        needs = getattr(agent, 'needs', None)
        if needs:
            hunger = getattr(needs, 'hunger', 0)
            rest = getattr(needs, 'rest', 0)
            safety = getattr(needs, 'safety', 0)
            belonging = getattr(needs, 'belonging', 0)
            purpose = getattr(needs, 'purpose', 0)
            
            lines.append("\nNeeds:")
            lines.append(f"  Hunger:   [{self._bar(hunger, 100)}] {hunger}")
            lines.append(f"  Rest:     [{self._bar(rest, 100)}] {rest}")
            lines.append(f"  Safety:   [{self._bar(safety, 100)}] {safety}")
            lines.append(f"  Belonging:[{self._bar(belonging, 100)}] {belonging}")
            lines.append(f"  Purpose:  [{self._bar(purpose, 100)}] {purpose}")
        
        # Inventory
        inventory = getattr(agent, 'inventory', None)
        if inventory:
            food = getattr(inventory, 'food', 0)
            credits = getattr(inventory, 'credits', 0)
            tools = getattr(inventory, 'tools', 0)
            lines.append(f"\nInventory: Food={food}, Credits={credits}, Tools={tools}")
        
        # Goals
        goals = getattr(agent, 'goals', [])
        if goals:
            lines.append(f"\nGoals: {', '.join(goals)}")
        
        # Mood
        mood = getattr(agent, 'mood', 0.0)
        lines.append(f"\nMood: {mood:+.2f}")
        
        # Current action
        action = getattr(agent, 'current_action', 'idle')
        lines.append(f"Action: {action}")
        
        # Recent memory
        memory = getattr(agent, 'memory', [])
        if memory:
            lines.append(f"\nRecent:")
            for mem in list(memory)[-3:]:
                lines.append(f"  • {mem}")
        
        return lines
    
    def _bar(self, value: int, max_value: int, length: int = 20) -> str:
        """Create a text bar."""
        filled = int((value / max_value) * length)
        return "#" * filled + "." * (length - filled)
    
    def render_screen(self, header: str, minimap_lines: List[str], heatmap_lines: List[str],
                     event_feed_lines: List[str], agent_list_lines: Optional[List[str]] = None,
                     agent_panel_lines: Optional[List[str]] = None, mode: str = "full"):
        """
        Render the full screen with all panels.
        
        Args:
            header: Header line (day/time/weather)
            minimap_lines: Minimap lines
            heatmap_lines: Heatmap lines
            event_feed_lines: Event feed lines
            agent_list_lines: Optional agent list lines
            agent_panel_lines: Optional agent panel lines (for AGENT mode)
            mode: "full" or "compact"
        """
        if not self.settings.enabled:
            return
        
        self.clear_screen()
        
        # Header
        print(header)
        print("=" * 80)
        
        if mode == "compact":
            # Compact mode: single column
            print("\n".join(minimap_lines))
            print()
            print("\n".join(heatmap_lines))
            print()
            print("\n".join(event_feed_lines))
        else:
            # Full mode: side-by-side layout (simplified for text)
            # Left: Minimap, Right: Heatmap
            min_height = max(len(minimap_lines), len(heatmap_lines))
            
            for i in range(min_height):
                left = minimap_lines[i] if i < len(minimap_lines) else ""
                right = heatmap_lines[i] if i < len(heatmap_lines) else ""
                print(f"{left:<40} {right}")
            
            print()
            print("-" * 80)
            
            # Event feed
            print("\n".join(event_feed_lines))
            
            # Agent list or panel
            if agent_panel_lines:
                print()
                print("-" * 80)
                print("\n".join(agent_panel_lines))
            elif agent_list_lines:
                print()
                print("-" * 80)
                print("\n".join(agent_list_lines))
        
        print("=" * 80)
