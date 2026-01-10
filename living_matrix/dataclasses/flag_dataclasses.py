"""World flag-related dataclasses."""

from typing import Dict, Callable
from dataclasses import dataclass, field


@dataclass
class WorldFlag:
    """A permanent world state flag that cannot fully revert."""
    id: str
    description: str
    triggered_at_turn: int
    irreversible: bool = True
    effects: Dict = field(default_factory=dict)  # modifiers applied to world, districts, agents
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "triggered_at_turn": self.triggered_at_turn,
            "irreversible": self.irreversible,
            "effects": self.effects
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldFlag":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            triggered_at_turn=data["triggered_at_turn"],
            irreversible=data.get("irreversible", True),
            effects=data.get("effects", {})
        )


@dataclass
class FlagTrigger:
    """Definition of a condition that triggers a world flag."""
    flag_id: str
    description: str
    condition: Callable  # Function that returns True when flag should trigger
    effects: Dict  # Effects to apply when triggered
