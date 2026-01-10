"""Event-related dataclasses."""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Event:
    """An event in the world."""
    turn: int
    event_type: str  # commute, market_trade, shift_start, shift_end, meal, rest, meeting, minor_conflict, helping, discovery
    description: str
    location_id: Optional[str] = None
    agent_ids: List[str] = None
