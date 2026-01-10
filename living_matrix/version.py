"""Version tracking for Living Matrix."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class VersionManager:
    """Manages version information for the Living Matrix."""
    
    VERSION = "1.0.0"  # Current matrix version
    
    def __init__(self, data_dir: str = "data"):
        """Initialize version manager."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.version_file = self.data_dir / "version.json"
        self._version_data: Optional[Dict[str, Any]] = None
    
    def load(self) -> Dict[str, Any]:
        """Load version data from disk, or create new if missing."""
        if self._version_data is not None:
            return self._version_data
        
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    self._version_data = json.load(f)
                return self._version_data
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Could not load version data ({e}), creating new.")
        
        # Create new version data
        self._version_data = self._create_new_version()
        self.save()
        return self._version_data
    
    def _create_new_version(self) -> Dict[str, Any]:
        """Create new version data structure."""
        now = datetime.utcnow().isoformat()
        return {
            "matrix_version": self.VERSION,
            "created_at": now,
            "last_reset_at": None,
            "reset_count": 0,
            "initialized": True
        }
    
    def save(self):
        """Save version data to disk."""
        if self._version_data is None:
            self.load()
        
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(self._version_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving version data: {e}")
    
    def mark_reset(self):
        """Mark that the matrix was reset."""
        if self._version_data is None:
            self.load()
        
        self._version_data["last_reset_at"] = datetime.utcnow().isoformat()
        self._version_data["reset_count"] = self._version_data.get("reset_count", 0) + 1
        self.save()
    
    def get_info(self) -> Dict[str, Any]:
        """Get current version information."""
        if self._version_data is None:
            self.load()
        
        return {
            "matrix_version": self._version_data.get("matrix_version", self.VERSION),
            "created_at": self._version_data.get("created_at"),
            "last_reset_at": self._version_data.get("last_reset_at"),
            "reset_count": self._version_data.get("reset_count", 0),
            "is_reset": self._version_data.get("last_reset_at") is not None,
            "initialized": self._version_data.get("initialized", True)
        }
