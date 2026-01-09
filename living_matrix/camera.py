"""Camera/POV system for different view modes."""

from typing import Optional, Tuple
from enum import Enum


class CameraMode(Enum):
    """Camera view modes."""
    GOD = "god"
    DISTRICT = "district"
    AGENT = "agent"
    PLACE = "place"


class Camera:
    """Camera system for different POV modes."""
    
    def __init__(self):
        """Initialize camera."""
        self.mode = CameraMode.GOD
        self.target_district: Optional[str] = None
        self.target_agent_id: Optional[str] = None
        self.target_place: Optional[str] = None
    
    def set_mode(self, mode: str, target: Optional[str] = None):
        """
        Set camera mode.
        
        Args:
            mode: "god", "district", "agent", or "place"
            target: District name, agent ID/name, or place name
        """
        mode_lower = mode.lower()
        if mode_lower == "god":
            self.mode = CameraMode.GOD
            self.target_district = None
            self.target_agent_id = None
            self.target_place = None
        elif mode_lower == "district":
            self.mode = CameraMode.DISTRICT
            self.target_district = target
            self.target_agent_id = None
            self.target_place = None
        elif mode_lower == "agent":
            self.mode = CameraMode.AGENT
            self.target_agent_id = target
            self.target_district = None
            self.target_place = None
        elif mode_lower == "place":
            self.mode = CameraMode.PLACE
            self.target_place = target
            self.target_district = None
            self.target_agent_id = None
        else:
            return False
        return True
    
    def get_mode_string(self) -> str:
        """Get current mode as string."""
        if self.mode == CameraMode.GOD:
            return "GOD"
        elif self.mode == CameraMode.DISTRICT:
            return f"DISTRICT ({self.target_district})"
        elif self.mode == CameraMode.AGENT:
            return f"AGENT ({self.target_agent_id})"
        elif self.mode == CameraMode.PLACE:
            return f"PLACE ({self.target_place})"
        return "UNKNOWN"
    
    def get_focus_info(self) -> Tuple[CameraMode, Optional[str]]:
        """Get current focus info."""
        if self.mode == CameraMode.DISTRICT:
            return (self.mode, self.target_district)
        elif self.mode == CameraMode.AGENT:
            return (self.mode, self.target_agent_id)
        elif self.mode == CameraMode.PLACE:
            return (self.mode, self.target_place)
        return (self.mode, None)
