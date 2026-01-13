"""
Context Store for Gemini Visual Continuity.

This module provides a sliding window context store that maintains
recent daily summaries for visual continuity in image generation.

Features:
- Stores last N days of compressed summaries
- Thread-safe operations
- Capped context size
- Automatic cleanup of old context
"""

import threading
from typing import List, Dict, Optional
from collections import deque
from dataclasses import dataclass, asdict
import json


@dataclass
class DayContext:
    """Context for a single day."""
    day: int
    summary: str
    tension_avg: float
    population_end: int
    phase: str
    notable_events: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class ContextStore:
    """
    Sliding window context store for daily summaries.
    
    Maintains the last N days of context for visual continuity.
    Context is used to inform Gemini about recent history.
    
    Thread-safe for concurrent access.
    """
    
    DEFAULT_WINDOW_SIZE = 7  # Last 7 days
    MAX_CONTEXT_CHARS = 3000  # Maximum total context size
    
    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE):
        """
        Initialize context store.
        
        Args:
            window_size: Number of days to retain (default 7)
        """
        self._lock = threading.Lock()
        self._window_size = window_size
        self._contexts: deque = deque(maxlen=window_size)
        self._current_day_snapshots: List = []  # Accumulates hourly snapshots
        self._last_processed_day: int = -1
    
    def add_hourly_snapshot(self, snapshot) -> None:
        """
        Add an hourly snapshot to accumulate for daily summary.
        
        Args:
            snapshot: StateSnapshot from the current hour
        """
        with self._lock:
            current_day = snapshot.simulation_day
            
            # If new day started, finalize previous day
            if current_day > self._last_processed_day and self._current_day_snapshots:
                self._finalize_day(self._last_processed_day)
                self._current_day_snapshots = []
            
            self._current_day_snapshots.append(snapshot)
            self._last_processed_day = current_day
    
    def _finalize_day(self, day: int) -> None:
        """
        Finalize a day's context from accumulated snapshots.
        
        Called internally when a new day begins.
        """
        if not self._current_day_snapshots:
            return
        
        snapshots = self._current_day_snapshots
        final = snapshots[-1]
        
        # Build summary
        from .prompt_builder import build_daily_summary
        summary = build_daily_summary(snapshots, day)
        
        # Extract notable events
        notable = []
        if any(s.crisis_active for s in snapshots):
            notable.append("crisis")
        if any(s.collapse_risk for s in snapshots):
            notable.append("collapse_risk")
        if any(s.famine_risk for s in snapshots):
            notable.append("famine")
        
        # Calculate average tension
        avg_tension = sum(s.average_tension for s in snapshots) / len(snapshots)
        
        context = DayContext(
            day=day,
            summary=summary,
            tension_avg=round(avg_tension, 1),
            population_end=final.global_population,
            phase=final.civilization_phase,
            notable_events=notable
        )
        
        self._contexts.append(context)
    
    def get_context_for_prompt(self) -> str:
        """
        Get combined context string for image generation prompt.
        
        Returns:
            Combined context from recent days, capped at MAX_CONTEXT_CHARS
        """
        with self._lock:
            if not self._contexts:
                return ""
            
            # Build context string from most recent days
            parts = ["Recent history:"]
            total_chars = len(parts[0])
            
            for ctx in reversed(list(self._contexts)):
                entry = f"- {ctx.summary}"
                if total_chars + len(entry) + 1 > self.MAX_CONTEXT_CHARS:
                    break
                parts.append(entry)
                total_chars += len(entry) + 1
            
            return "\n".join(parts)
    
    def get_recent_contexts(self, n: Optional[int] = None) -> List[DayContext]:
        """
        Get recent day contexts.
        
        Args:
            n: Number of days to return (default: all in window)
        
        Returns:
            List of DayContext objects
        """
        with self._lock:
            contexts = list(self._contexts)
            if n is not None:
                contexts = contexts[-n:]
            return contexts
    
    def get_stats(self) -> Dict:
        """Get context store statistics."""
        with self._lock:
            return {
                "days_stored": len(self._contexts),
                "window_size": self._window_size,
                "current_day_snapshots": len(self._current_day_snapshots),
                "last_processed_day": self._last_processed_day
            }
    
    def clear(self) -> None:
        """Clear all stored context."""
        with self._lock:
            self._contexts.clear()
            self._current_day_snapshots = []
            self._last_processed_day = -1
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for persistence."""
        with self._lock:
            return {
                "window_size": self._window_size,
                "contexts": [ctx.to_dict() for ctx in self._contexts],
                "last_processed_day": self._last_processed_day
            }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContextStore":
        """Deserialize from dictionary."""
        store = cls(window_size=data.get("window_size", cls.DEFAULT_WINDOW_SIZE))
        store._last_processed_day = data.get("last_processed_day", -1)
        
        for ctx_data in data.get("contexts", []):
            ctx = DayContext(
                day=ctx_data.get("day", 0),
                summary=ctx_data.get("summary", ""),
                tension_avg=ctx_data.get("tension_avg", 0.0),
                population_end=ctx_data.get("population_end", 0),
                phase=ctx_data.get("phase", "unknown"),
                notable_events=ctx_data.get("notable_events", [])
            )
            store._contexts.append(ctx)
        
        return store


# Singleton instance
_context_store: Optional[ContextStore] = None


def get_context_store() -> ContextStore:
    """Get the singleton context store instance."""
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store
