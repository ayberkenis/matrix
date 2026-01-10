"""Map-related dataclasses."""

from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Location:
    """A location in the world."""
    id: str
    name: str
    region_id: str
    type_tag: str  # residential, market, transit, industrial, civic, edge
    crowd_density: float = 0.0  # 0.0-1.0, updated by agent system


@dataclass
class Region:
    """A region containing multiple locations."""
    id: str
    name: str
    locations: List[Location]
    tags: List[str] = field(default_factory=list)  # market, industrial, residential, garden, etc.
    food: float = 50.0  # 0-100
    materials: float = 50.0  # 0-100
    energy: float = 50.0  # 0-100
    infrastructure: float = 0.5  # 0-1, affects production stability
    tension: float = 0.2  # 0-1, increases with shortages
