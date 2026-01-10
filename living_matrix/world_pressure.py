"""World Pressure → AI Feedback system: environmental effects on behavior."""

from typing import Dict, Optional
from dataclasses import dataclass
from living_matrix.dataclasses import Intent
from living_matrix.tension import Tension


@dataclass
class WorldConditions:
    """Current world conditions."""
    weather: str = "clear"           # clear, rain, storm, etc.
    time_of_day: str = "day"        # day, night, dawn, dusk
    day_of_week: int = 0             # 0-6
    season: str = "spring"           # spring, summer, fall, winter
    rain_duration: int = 0           # Consecutive turns of rain
    sunshine_duration: int = 0       # Consecutive turns of sunshine


class WorldPressureSystem:
    """
    System that applies world pressure to modify drives, intent, and emotional memory.
    The world actively pushes back on AI behavior.
    """
    
    def __init__(self):
        """Initialize world pressure system."""
        pass
    
    def apply_pressure(self, conditions: WorldConditions, intent: Intent, 
                       tension: Tension, turn: int) -> Dict[str, float]:
        """
        Apply world pressure to modify intent and tension.
        
        Args:
            conditions: Current world conditions
            intent: Intent to modify
            tension: Tension to modify
            turn: Current turn
            
        Returns:
            Dictionary of pressure effects applied
        """
        effects = {}
        
        # Long rain → existential tension ↑
        if conditions.rain_duration > 10:
            tension.existential += 2.0 * (conditions.rain_duration / 10.0)
            intent.escape += 0.05 * (conditions.rain_duration / 10.0)
            intent.survive += 0.03 * (conditions.rain_duration / 10.0)
            effects['rain_pressure'] = conditions.rain_duration / 10.0
        
        # Night → crime probability ↑, social tension ↑
        if conditions.time_of_day == "night":
            tension.social += 1.5
            intent.dominate += 0.02
            intent.survive += 0.01
            effects['night_pressure'] = 1.0
        
        # Sunshine → hope ↑, social tension ↓
        if conditions.sunshine_duration > 5:
            tension.social = max(0.0, tension.social - 0.5 * (conditions.sunshine_duration / 5.0))
            intent.cooperate += 0.03 * (conditions.sunshine_duration / 5.0)
            intent.explore += 0.02 * (conditions.sunshine_duration / 5.0)
            effects['sunshine_boost'] = conditions.sunshine_duration / 5.0
        
        # Storm → existential tension ↑, survive ↑
        if conditions.weather == "storm":
            tension.existential += 3.0
            tension.economic += 1.0
            intent.survive += 0.1
            intent.escape += 0.05
            effects['storm_pressure'] = 1.0
        
        # Extreme weather → all tensions ↑
        if conditions.weather in ["extreme_heat", "extreme_cold", "blizzard"]:
            tension.economic += 2.0
            tension.social += 1.5
            tension.existential += 2.5
            intent.survive += 0.15
            intent.escape += 0.1
            effects['extreme_weather_pressure'] = 1.0
        
        # Winter → economic tension ↑ (resources harder to get)
        if conditions.season == "winter":
            tension.economic += 1.0
            intent.survive += 0.05
            effects['winter_pressure'] = 0.5
        
        # Summer → social tension can increase (heat, crowding)
        if conditions.season == "summer" and conditions.weather == "clear":
            tension.social += 0.5
            effects['summer_pressure'] = 0.3
        
        # Normalize after modifications
        intent.normalize()
        tension.normalize()
        
        return effects
    
    def get_conditions_from_world(self, weather_system, time_system) -> WorldConditions:
        """
        Extract world conditions from weather and time systems.
        
        Args:
            weather_system: Weather system instance
            time_system: Time system instance
            
        Returns:
            WorldConditions object
        """
        conditions = WorldConditions()
        
        # Get weather
        if weather_system:
            # Try to get weather state
            weather_state = getattr(weather_system, 'current_weather', 'clear')
            if isinstance(weather_state, dict):
                conditions.weather = weather_state.get('sky', 'clear')
            else:
                conditions.weather = str(weather_state)
        
        # Get time
        if time_system:
            hour = time_system.get_hour()
            if 6 <= hour < 18:
                conditions.time_of_day = "day"
            elif 18 <= hour < 22:
                conditions.time_of_day = "dusk"
            elif 22 <= hour or hour < 6:
                conditions.time_of_day = "night"
            else:
                conditions.time_of_day = "dawn"
            
            # Get day of week (if available)
            if hasattr(time_system, 'day_index'):
                conditions.day_of_week = time_system.day_index % 7
            
            # Get season (if available)
            if hasattr(time_system, 'get_season'):
                conditions.season = time_system.get_season()
        
        return conditions
