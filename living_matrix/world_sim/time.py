"""Time system for world simulation."""

import random
from typing import Tuple


class TimeSystem:
    """Tracks time in the world simulation."""
    
    def __init__(self, day_index: int = 0, minute_of_day: int = 0, seed: int = 42):
        """
        Initialize time system.
        
        Args:
            day_index: Starting day (0 = first day)
            minute_of_day: Starting minute (0-1439, 0 = midnight)
            seed: Random seed for deterministic behavior
        """
        self.day_index = day_index
        self.minute_of_day = minute_of_day
        self.tick_length_minutes = 15  # Each turn = 15 minutes
        self.seed = seed
        random.seed(seed)
    
    def advance(self, turns: int = 1) -> Tuple[int, int]:
        """
        Advance time by specified number of turns.
        
        Args:
            turns: Number of turns to advance
            
        Returns:
            Tuple of (day_index, minute_of_day) after advance
        """
        minutes_to_add = turns * self.tick_length_minutes
        self.minute_of_day += minutes_to_add
        
        # Handle day rollover
        while self.minute_of_day >= 1440:  # 24 hours = 1440 minutes
            self.minute_of_day -= 1440
            self.day_index += 1
        
        return (self.day_index, self.minute_of_day)
    
    def format_time(self) -> str:
        """
        Format current time as string.
        
        Returns:
            Formatted time string like "Day 12 • 03:45 (Night)"
        """
        hours = self.minute_of_day // 60
        minutes = self.minute_of_day % 60
        
        # Determine time of day
        if 5 <= hours < 12:
            period = "Morning"
        elif 12 <= hours < 17:
            period = "Day"
        elif 17 <= hours < 21:
            period = "Evening"
        else:
            period = "Night"
        
        return f"Day {self.day_index} • {hours:02d}:{minutes:02d} ({period})"
    
    def get_hour(self) -> int:
        """Get current hour (0-23)."""
        return self.minute_of_day // 60
    
    def is_night(self) -> bool:
        """Check if it's nighttime (21:00-04:59)."""
        hour = self.get_hour()
        return hour >= 21 or hour < 5
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "day_index": self.day_index,
            "minute_of_day": self.minute_of_day,
            "tick_length_minutes": self.tick_length_minutes,
            "seed": self.seed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TimeSystem":
        """Deserialize from dictionary."""
        obj = cls(
            day_index=data.get("day_index", 0),
            minute_of_day=data.get("minute_of_day", 0),
            seed=data.get("seed", 42)
        )
        obj.tick_length_minutes = data.get("tick_length_minutes", 15)
        return obj
