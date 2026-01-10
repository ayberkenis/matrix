"""IPC-related dataclasses."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class MatrixState:
    """Read-only snapshot of world state."""
    turn: int
    day: int
    time: str
    weather: str
    districts: List[Dict[str, Any]]
    agents: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    economy: Dict[str, Any]
    timestamp: str
    weather_detail: Optional[Dict[str, Any]] = None  # Detailed weather info


@dataclass
class MatrixCommand:
    """Command to send to world runner."""
    command: str  # pause, resume, set_speed, reset, inject_event
    params: Dict[str, Any] = field(default_factory=dict)
