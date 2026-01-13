"""Zero-cost observability for performance monitoring.

All instrumentation has zero overhead when disabled. Metrics are only
collected when ENABLE_METRICS is True.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps

from living_matrix.constants.performance_constants import (
    ENABLE_METRICS, METRICS_INTERVAL, SLOW_TICK_THRESHOLD_MS, ENABLE_PHASE_TIMING
)

logger = logging.getLogger(__name__)


@dataclass
class TickMetrics:
    """Metrics for a single simulation tick."""
    turn: int = 0
    duration_ms: float = 0.0
    active_agents: int = 0
    inactive_agents: int = 0
    child_pool: int = 0
    phases: Dict[str, float] = field(default_factory=dict)  # phase_name -> duration_ms
    births: int = 0
    deaths: int = 0
    promotions: int = 0
    conflicts: int = 0
    worker_utilization: float = 0.0  # 0.0 to 1.0


@dataclass 
class AggregateMetrics:
    """Aggregate metrics over multiple ticks."""
    ticks_measured: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    slow_tick_count: int = 0
    phase_totals: Dict[str, float] = field(default_factory=dict)
    
    def update(self, tick: TickMetrics):
        """Update aggregates with a new tick."""
        self.ticks_measured += 1
        self.total_duration_ms += tick.duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.ticks_measured
        self.max_duration_ms = max(self.max_duration_ms, tick.duration_ms)
        self.min_duration_ms = min(self.min_duration_ms, tick.duration_ms)
        if tick.duration_ms > SLOW_TICK_THRESHOLD_MS:
            self.slow_tick_count += 1
        for phase, duration in tick.phases.items():
            self.phase_totals[phase] = self.phase_totals.get(phase, 0.0) + duration


class PerformanceObserver:
    """
    Zero-cost performance observer.
    
    When ENABLE_METRICS is False, all methods are essentially no-ops.
    """
    
    __slots__ = ('_enabled', '_current_tick', '_aggregates', '_history', '_phase_start')
    
    def __init__(self):
        self._enabled = ENABLE_METRICS
        self._current_tick: Optional[TickMetrics] = None
        self._aggregates = AggregateMetrics()
        self._history: List[TickMetrics] = []  # Circular buffer
        self._phase_start: float = 0.0
    
    def start_tick(self, turn: int) -> None:
        """Start measuring a tick. No-op when disabled."""
        if not self._enabled:
            return
        self._current_tick = TickMetrics(turn=turn)
        self._current_tick.duration_ms = -time.perf_counter() * 1000  # Will be added at end
    
    def end_tick(self) -> Optional[TickMetrics]:
        """End tick measurement and return metrics. No-op when disabled."""
        if not self._enabled or self._current_tick is None:
            return None
        
        self._current_tick.duration_ms += time.perf_counter() * 1000
        
        # Check for slow tick
        if self._current_tick.duration_ms > SLOW_TICK_THRESHOLD_MS:
            logger.warning(
                f"Slow tick {self._current_tick.turn}: "
                f"{self._current_tick.duration_ms:.1f}ms "
                f"(threshold: {SLOW_TICK_THRESHOLD_MS}ms)"
            )
        
        # Update aggregates
        self._aggregates.update(self._current_tick)
        
        # Store in history (keep last 100)
        self._history.append(self._current_tick)
        if len(self._history) > 100:
            self._history.pop(0)
        
        result = self._current_tick
        self._current_tick = None
        return result
    
    def start_phase(self, phase_name: str) -> None:
        """Start measuring a phase. No-op when disabled or phase timing disabled."""
        if not self._enabled or not ENABLE_PHASE_TIMING:
            return
        self._phase_start = time.perf_counter()
    
    def end_phase(self, phase_name: str) -> None:
        """End phase measurement. No-op when disabled or phase timing disabled."""
        if not self._enabled or not ENABLE_PHASE_TIMING or self._current_tick is None:
            return
        duration = (time.perf_counter() - self._phase_start) * 1000
        self._current_tick.phases[phase_name] = duration
    
    @contextmanager
    def phase(self, phase_name: str):
        """Context manager for phase timing. Minimal overhead when disabled."""
        if not self._enabled or not ENABLE_PHASE_TIMING:
            yield
            return
        
        self.start_phase(phase_name)
        try:
            yield
        finally:
            self.end_phase(phase_name)
    
    def record_population(self, active: int, inactive: int, children: int) -> None:
        """Record population counts. No-op when disabled."""
        if not self._enabled or self._current_tick is None:
            return
        self._current_tick.active_agents = active
        self._current_tick.inactive_agents = inactive
        self._current_tick.child_pool = children
    
    def record_events(self, births: int = 0, deaths: int = 0, 
                     promotions: int = 0, conflicts: int = 0) -> None:
        """Record event counts. No-op when disabled."""
        if not self._enabled or self._current_tick is None:
            return
        self._current_tick.births = births
        self._current_tick.deaths = deaths
        self._current_tick.promotions = promotions
        self._current_tick.conflicts = conflicts
    
    def record_worker_utilization(self, utilization: float) -> None:
        """Record parallel worker utilization. No-op when disabled."""
        if not self._enabled or self._current_tick is None:
            return
        self._current_tick.worker_utilization = utilization
    
    def get_aggregates(self) -> AggregateMetrics:
        """Get aggregate metrics."""
        return self._aggregates
    
    def get_recent_history(self, n: int = 10) -> List[TickMetrics]:
        """Get recent tick history."""
        return self._history[-n:] if self._history else []
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary as dict."""
        if not self._enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "ticks_measured": self._aggregates.ticks_measured,
            "avg_duration_ms": round(self._aggregates.avg_duration_ms, 2),
            "max_duration_ms": round(self._aggregates.max_duration_ms, 2),
            "min_duration_ms": round(self._aggregates.min_duration_ms, 2) if self._aggregates.min_duration_ms != float('inf') else 0,
            "slow_ticks": self._aggregates.slow_tick_count,
            "phase_averages": {
                k: round(v / max(1, self._aggregates.ticks_measured), 2)
                for k, v in self._aggregates.phase_totals.items()
            }
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._aggregates = AggregateMetrics()
        self._history.clear()
        self._current_tick = None


# Global observer instance
_observer: Optional[PerformanceObserver] = None


def get_observer() -> PerformanceObserver:
    """Get or create the global performance observer."""
    global _observer
    if _observer is None:
        _observer = PerformanceObserver()
    return _observer


def timed_phase(phase_name: str):
    """Decorator for timing a function as a phase."""
    def decorator(func: Callable) -> Callable:
        if not ENABLE_METRICS or not ENABLE_PHASE_TIMING:
            # Return function unchanged when disabled
            return func
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            observer = get_observer()
            with observer.phase(phase_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
