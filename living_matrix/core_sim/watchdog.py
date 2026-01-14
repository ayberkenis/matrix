"""Turn Time Watchdog - Emergency Performance Safety.

This module monitors turn execution time and activates emergency
degradation mode when turns consistently exceed thresholds.

EMERGENCY MODE:
When activated, emergency mode:
- Increases all tick intervals (heartbeat)
- Reduces maximum active agents
- Forces more aggressive compression
- Logs warnings

This prevents the simulation from freezing when performance degrades.

RECOVERY:
Emergency mode deactivates when turn times return to normal for
several consecutive turns.
"""

import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque

from ..constants.performance_constants import (
    EMERGENCY_TURN_TIME_MS,
    SLOW_TURNS_BEFORE_EMERGENCY,
    EMERGENCY_INTERVAL_MULTIPLIER,
    EMERGENCY_MAX_ACTIVE_AGENTS,
    SLOW_TICK_THRESHOLD_MS,
)

logger = logging.getLogger(__name__)


@dataclass
class TurnTiming:
    """Timing data for a single turn."""
    turn: int
    duration_ms: float
    phase_timings: Dict[str, float] = field(default_factory=dict)
    agent_count: int = 0
    was_emergency: bool = False


class TurnTimeWatchdog:
    """
    Monitors turn times and triggers emergency mode when needed.
    
    Usage:
        watchdog = TurnTimeWatchdog()
        
        # At start of turn
        watchdog.start_turn(turn)
        
        # At end of turn
        watchdog.end_turn(turn, phase_timings)
        
        # Check if emergency mode is active
        if watchdog.is_emergency_mode:
            # Apply emergency settings
    """
    
    def __init__(
        self,
        emergency_threshold_ms: float = EMERGENCY_TURN_TIME_MS,
        slow_turns_threshold: int = SLOW_TURNS_BEFORE_EMERGENCY,
        recovery_turns: int = 5
    ):
        self.emergency_threshold_ms = emergency_threshold_ms
        self.slow_turns_threshold = slow_turns_threshold
        self.recovery_turns = recovery_turns
        
        self._turn_start_time: float = 0.0
        self._current_turn: int = 0
        
        # History
        self._turn_history: deque = deque(maxlen=100)
        self._slow_turn_streak: int = 0
        self._fast_turn_streak: int = 0
        
        # Emergency mode state
        self._emergency_mode: bool = False
        self._emergency_activated_turn: int = 0
        
        # Statistics
        self._total_turns: int = 0
        self._slow_turns: int = 0
        self._emergency_activations: int = 0
    
    @property
    def is_emergency_mode(self) -> bool:
        """Check if emergency mode is active."""
        return self._emergency_mode
    
    def start_turn(self, turn: int):
        """Start timing a turn."""
        self._current_turn = turn
        self._turn_start_time = time.perf_counter()
    
    def end_turn(
        self,
        turn: int,
        phase_timings: Dict[str, float] = None,
        agent_count: int = 0
    ) -> TurnTiming:
        """
        End timing a turn and check for emergency mode.
        
        Returns TurnTiming with results.
        """
        duration_ms = (time.perf_counter() - self._turn_start_time) * 1000
        
        timing = TurnTiming(
            turn=turn,
            duration_ms=duration_ms,
            phase_timings=phase_timings or {},
            agent_count=agent_count,
            was_emergency=self._emergency_mode
        )
        
        self._turn_history.append(timing)
        self._total_turns += 1
        
        # Check if this was a slow turn
        if duration_ms > self.emergency_threshold_ms:
            self._slow_turn_streak += 1
            self._fast_turn_streak = 0
            self._slow_turns += 1
            
            logger.warning(
                f"⚠ SLOW TURN {turn}: {duration_ms:.0f}ms "
                f"(threshold: {self.emergency_threshold_ms}ms, "
                f"streak: {self._slow_turn_streak})"
            )
            
            # Check if emergency mode should activate
            if not self._emergency_mode and self._slow_turn_streak >= self.slow_turns_threshold:
                self._activate_emergency_mode(turn)
        
        elif duration_ms < SLOW_TICK_THRESHOLD_MS:
            self._fast_turn_streak += 1
            self._slow_turn_streak = 0
            
            # Check if emergency mode should deactivate
            if self._emergency_mode and self._fast_turn_streak >= self.recovery_turns:
                self._deactivate_emergency_mode(turn)
        
        else:
            # Normal turn, reset streaks slowly
            self._slow_turn_streak = max(0, self._slow_turn_streak - 1)
            self._fast_turn_streak = 0
        
        return timing
    
    def _activate_emergency_mode(self, turn: int):
        """Activate emergency mode."""
        self._emergency_mode = True
        self._emergency_activated_turn = turn
        self._emergency_activations += 1
        
        logger.warning(
            f"🚨 EMERGENCY MODE ACTIVATED at turn {turn} "
            f"(slow turn streak: {self._slow_turn_streak})"
        )
    
    def _deactivate_emergency_mode(self, turn: int):
        """Deactivate emergency mode."""
        self._emergency_mode = False
        duration = turn - self._emergency_activated_turn
        
        logger.info(
            f"✓ Emergency mode deactivated at turn {turn} "
            f"(was active for {duration} turns)"
        )
    
    def get_emergency_settings(self) -> Dict:
        """
        Get settings to apply during emergency mode.
        
        Returns dict with:
        - interval_multiplier: multiply all tick intervals by this
        - max_active_agents: cap on active agents
        - force_compression: whether to force population compression
        """
        if not self._emergency_mode:
            return {
                'interval_multiplier': 1,
                'max_active_agents': None,
                'force_compression': False,
            }
        
        return {
            'interval_multiplier': EMERGENCY_INTERVAL_MULTIPLIER,
            'max_active_agents': EMERGENCY_MAX_ACTIVE_AGENTS,
            'force_compression': True,
        }
    
    def get_statistics(self) -> Dict:
        """Get watchdog statistics."""
        avg_duration = 0.0
        if self._turn_history:
            avg_duration = sum(t.duration_ms for t in self._turn_history) / len(self._turn_history)
        
        return {
            'total_turns': self._total_turns,
            'slow_turns': self._slow_turns,
            'slow_turn_percentage': (
                self._slow_turns / self._total_turns * 100
                if self._total_turns > 0 else 0
            ),
            'emergency_activations': self._emergency_activations,
            'currently_emergency': self._emergency_mode,
            'current_streak': (
                self._slow_turn_streak if self._slow_turn_streak > 0
                else -self._fast_turn_streak
            ),
            'avg_turn_duration_ms': avg_duration,
        }
    
    def get_recent_timings(self, count: int = 10) -> List[TurnTiming]:
        """Get most recent turn timings."""
        return list(self._turn_history)[-count:]
    
    def get_phase_breakdown(self) -> Dict[str, float]:
        """Get average duration by phase from recent turns."""
        if not self._turn_history:
            return {}
        
        phase_totals: Dict[str, float] = {}
        phase_counts: Dict[str, int] = {}
        
        for timing in self._turn_history:
            for phase, duration in timing.phase_timings.items():
                phase_totals[phase] = phase_totals.get(phase, 0.0) + duration
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        return {
            phase: total / phase_counts[phase]
            for phase, total in phase_totals.items()
            if phase in phase_counts and phase_counts[phase] > 0
        }


# Global instance
_watchdog: Optional[TurnTimeWatchdog] = None


def get_watchdog() -> TurnTimeWatchdog:
    """Get or create the global watchdog."""
    global _watchdog
    if _watchdog is None:
        _watchdog = TurnTimeWatchdog()
    return _watchdog


def reset_watchdog():
    """Reset the global watchdog (for testing)."""
    global _watchdog
    _watchdog = None
