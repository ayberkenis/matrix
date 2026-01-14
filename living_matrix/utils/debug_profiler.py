"""Debug profiling utilities for simulation performance analysis.

This module provides lightweight, toggleable timing and measurement utilities
to identify performance bottlenecks in the Living Matrix simulation.

USAGE:
    Enable via environment variable: LM_DEBUG_PROFILE=true
    
    Or programmatically:
        from living_matrix.utils.debug_profiler import enable_profiling
        enable_profiling()

All instrumentation has ZERO overhead when disabled.
"""

import os
import time
import sys
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
from collections import deque

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Enable debug profiling via environment variable
DEBUG_PROFILE_ENABLED = os.environ.get("LM_DEBUG_PROFILE", "false").lower() in ("true", "1", "yes", "on")

# Print detailed per-turn breakdown
DEBUG_VERBOSE = os.environ.get("LM_DEBUG_VERBOSE", "false").lower() in ("true", "1", "yes", "on")

# Log every N turns (to reduce output spam)
DEBUG_LOG_INTERVAL = int(os.environ.get("LM_DEBUG_LOG_INTERVAL", "1"))

# Memory estimation (requires psutil, optional)
DEBUG_TRACK_MEMORY = os.environ.get("LM_DEBUG_MEMORY", "false").lower() in ("true", "1", "yes", "on")


def enable_profiling():
    """Enable debug profiling programmatically."""
    global DEBUG_PROFILE_ENABLED
    DEBUG_PROFILE_ENABLED = True


def disable_profiling():
    """Disable debug profiling programmatically."""
    global DEBUG_PROFILE_ENABLED
    DEBUG_PROFILE_ENABLED = False


def is_profiling_enabled() -> bool:
    """Check if profiling is enabled."""
    return DEBUG_PROFILE_ENABLED


# ============================================================================
# TIMING DATA STRUCTURES
# ============================================================================

@dataclass
class PhaseTimer:
    """Timing data for a single phase."""
    name: str
    total_ms: float = 0.0
    count: int = 0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    last_ms: float = 0.0
    
    def record(self, duration_ms: float):
        """Record a timing measurement."""
        self.total_ms += duration_ms
        self.count += 1
        self.last_ms = duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
    
    @property
    def avg_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def reset(self):
        """Reset all measurements."""
        self.total_ms = 0.0
        self.count = 0
        self.min_ms = float('inf')
        self.max_ms = 0.0
        self.last_ms = 0.0


@dataclass
class TurnMetrics:
    """Metrics collected for a single simulation turn."""
    turn: int
    total_duration_ms: float = 0.0
    
    # Population metrics
    active_agents: int = 0
    inactive_agents: int = 0
    child_pool: int = 0
    total_entities: int = 0
    
    # Collection sizes
    relationships_count: int = 0
    beliefs_count: int = 0
    memory_entries: int = 0
    dead_agents_count: int = 0
    
    # Event counts
    births: int = 0
    deaths: int = 0
    promotions: int = 0
    conflicts: int = 0
    
    # Phase durations
    phase_durations: Dict[str, float] = field(default_factory=dict)
    
    # Memory estimate (bytes, if available)
    memory_estimate_bytes: int = 0
    
    # Per-agent statistics
    agents_processed: int = 0
    avg_time_per_agent_ms: float = 0.0
    max_agent_time_ms: float = 0.0


@dataclass
class GrowthPattern:
    """Tracks growth over time to detect O(n), O(n²), etc."""
    metric_name: str
    values: deque = field(default_factory=lambda: deque(maxlen=100))
    turn_numbers: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record(self, turn: int, value: float):
        """Record a value at a turn."""
        self.values.append(value)
        self.turn_numbers.append(turn)
    
    def get_growth_rate(self) -> str:
        """Estimate growth pattern: linear, quadratic, exponential, or stable."""
        if len(self.values) < 10:
            return "insufficient_data"
        
        values = list(self.values)
        
        # Check if stable (less than 10% change)
        if len(values) >= 2:
            first_val = values[0]
            last_val = values[-1]
            if first_val > 0:
                change_ratio = abs(last_val - first_val) / first_val
                if change_ratio < 0.1:
                    return "stable"
        
        # Check for growth pattern by comparing intervals
        if len(values) >= 20:
            # Compare early, middle, and late growth rates
            early_growth = values[9] - values[0] if values[0] != 0 else 0
            late_growth = values[-1] - values[-10] if values[-10] != 0 else 0
            
            if early_growth > 0:
                ratio = late_growth / early_growth if early_growth != 0 else 0
                if ratio > 3.0:
                    return "exponential"  # Growth accelerating rapidly
                elif ratio > 1.5:
                    return "quadratic"  # Growth accelerating
                elif ratio > 0.8:
                    return "linear"  # Steady growth
                else:
                    return "decelerating"  # Growth slowing
        
        return "undetermined"


# ============================================================================
# MAIN PROFILER CLASS
# ============================================================================

class SimulationProfiler:
    """
    Main profiler for simulation performance analysis.
    
    All methods are no-ops when DEBUG_PROFILE_ENABLED is False.
    """
    
    __slots__ = (
        '_enabled', '_phase_timers', '_current_turn', '_turn_history',
        '_growth_trackers', '_phase_stack', '_phase_start_times',
        '_agent_times', '_current_agent_start'
    )
    
    def __init__(self):
        self._enabled = DEBUG_PROFILE_ENABLED
        self._phase_timers: Dict[str, PhaseTimer] = {}
        self._current_turn: Optional[TurnMetrics] = None
        self._turn_history: deque = deque(maxlen=1000)  # Keep last 1000 turns
        self._growth_trackers: Dict[str, GrowthPattern] = {}
        self._phase_stack: List[str] = []
        self._phase_start_times: Dict[str, float] = {}
        self._agent_times: List[float] = []
        self._current_agent_start: float = 0.0
    
    def is_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled and DEBUG_PROFILE_ENABLED
    
    # ========================================================================
    # TURN LIFECYCLE
    # ========================================================================
    
    def start_turn(self, turn: int) -> None:
        """Start profiling a new turn."""
        if not self.is_enabled():
            return
        
        self._current_turn = TurnMetrics(turn=turn)
        self._current_turn.total_duration_ms = -time.perf_counter() * 1000
        self._agent_times.clear()
    
    def end_turn(self) -> Optional[TurnMetrics]:
        """End turn profiling and return metrics."""
        if not self.is_enabled() or self._current_turn is None:
            return None
        
        self._current_turn.total_duration_ms += time.perf_counter() * 1000
        
        # Calculate agent statistics
        if self._agent_times:
            self._current_turn.agents_processed = len(self._agent_times)
            self._current_turn.avg_time_per_agent_ms = sum(self._agent_times) / len(self._agent_times)
            self._current_turn.max_agent_time_ms = max(self._agent_times)
        
        # Store in history
        self._turn_history.append(self._current_turn)
        
        # Update growth trackers
        self._track_growth("turn_duration_ms", self._current_turn.turn, self._current_turn.total_duration_ms)
        self._track_growth("active_agents", self._current_turn.turn, self._current_turn.active_agents)
        self._track_growth("total_entities", self._current_turn.turn, self._current_turn.total_entities)
        self._track_growth("relationships", self._current_turn.turn, self._current_turn.relationships_count)
        
        # Log if interval matches
        if self._current_turn.turn % DEBUG_LOG_INTERVAL == 0:
            self._log_turn_summary()
        
        result = self._current_turn
        self._current_turn = None
        return result
    
    # ========================================================================
    # PHASE TIMING
    # ========================================================================
    
    def start_phase(self, phase_name: str) -> None:
        """Start timing a phase."""
        if not self.is_enabled():
            return
        self._phase_start_times[phase_name] = time.perf_counter()
        self._phase_stack.append(phase_name)
    
    def end_phase(self, phase_name: str) -> float:
        """End timing a phase and return duration in ms."""
        if not self.is_enabled():
            return 0.0
        
        if phase_name not in self._phase_start_times:
            return 0.0
        
        duration_ms = (time.perf_counter() - self._phase_start_times[phase_name]) * 1000
        
        # Record in phase timer
        if phase_name not in self._phase_timers:
            self._phase_timers[phase_name] = PhaseTimer(name=phase_name)
        self._phase_timers[phase_name].record(duration_ms)
        
        # Record in current turn
        if self._current_turn is not None:
            self._current_turn.phase_durations[phase_name] = duration_ms
        
        # Clean up
        del self._phase_start_times[phase_name]
        if self._phase_stack and self._phase_stack[-1] == phase_name:
            self._phase_stack.pop()
        
        return duration_ms
    
    @contextmanager
    def phase(self, phase_name: str):
        """Context manager for timing a phase."""
        if not self.is_enabled():
            yield
            return
        
        self.start_phase(phase_name)
        try:
            yield
        finally:
            self.end_phase(phase_name)
    
    # ========================================================================
    # AGENT TIMING
    # ========================================================================
    
    def start_agent(self) -> None:
        """Start timing an agent update."""
        if not self.is_enabled():
            return
        self._current_agent_start = time.perf_counter()
    
    def end_agent(self) -> None:
        """End timing an agent update."""
        if not self.is_enabled():
            return
        duration_ms = (time.perf_counter() - self._current_agent_start) * 1000
        self._agent_times.append(duration_ms)
    
    # ========================================================================
    # POPULATION TRACKING
    # ========================================================================
    
    def record_population(
        self,
        active_agents: int,
        inactive_agents: int = 0,
        child_pool: int = 0,
        dead_agents: int = 0
    ) -> None:
        """Record population counts."""
        if not self.is_enabled() or self._current_turn is None:
            return
        
        self._current_turn.active_agents = active_agents
        self._current_turn.inactive_agents = inactive_agents
        self._current_turn.child_pool = child_pool
        self._current_turn.dead_agents_count = dead_agents
        self._current_turn.total_entities = active_agents + inactive_agents + child_pool
    
    def record_collections(
        self,
        relationships: int = 0,
        beliefs: int = 0,
        memory_entries: int = 0
    ) -> None:
        """Record collection sizes."""
        if not self.is_enabled() or self._current_turn is None:
            return
        
        self._current_turn.relationships_count = relationships
        self._current_turn.beliefs_count = beliefs
        self._current_turn.memory_entries = memory_entries
    
    def record_events(
        self,
        births: int = 0,
        deaths: int = 0,
        promotions: int = 0,
        conflicts: int = 0
    ) -> None:
        """Record event counts."""
        if not self.is_enabled() or self._current_turn is None:
            return
        
        self._current_turn.births = births
        self._current_turn.deaths = deaths
        self._current_turn.promotions = promotions
        self._current_turn.conflicts = conflicts
    
    # ========================================================================
    # MEMORY ESTIMATION
    # ========================================================================
    
    def estimate_memory(self, simulation) -> int:
        """Estimate memory usage of simulation objects."""
        if not self.is_enabled() or not DEBUG_TRACK_MEMORY:
            return 0
        
        try:
            import psutil
            process = psutil.Process()
            mem_bytes = process.memory_info().rss
            if self._current_turn is not None:
                self._current_turn.memory_estimate_bytes = mem_bytes
            return mem_bytes
        except ImportError:
            # psutil not available, use sys.getsizeof as fallback
            try:
                total = 0
                if hasattr(simulation, 'human_agent_system') and simulation.human_agent_system:
                    total += sys.getsizeof(simulation.human_agent_system.agents)
                    total += sys.getsizeof(simulation.human_agent_system.dead_agents)
                    total += sys.getsizeof(simulation.human_agent_system.child_pools)
                if self._current_turn is not None:
                    self._current_turn.memory_estimate_bytes = total
                return total
            except Exception:
                return 0
        except Exception:
            return 0
    
    # ========================================================================
    # GROWTH TRACKING
    # ========================================================================
    
    def _track_growth(self, metric_name: str, turn: int, value: float) -> None:
        """Track a metric over time for growth analysis."""
        if metric_name not in self._growth_trackers:
            self._growth_trackers[metric_name] = GrowthPattern(metric_name=metric_name)
        self._growth_trackers[metric_name].record(turn, value)
    
    def get_growth_analysis(self) -> Dict[str, str]:
        """Get growth pattern analysis for all tracked metrics."""
        return {
            name: tracker.get_growth_rate()
            for name, tracker in self._growth_trackers.items()
        }
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def _log_turn_summary(self) -> None:
        """Log summary for current turn."""
        if self._current_turn is None:
            return
        
        t = self._current_turn
        
        # Basic summary line
        summary = (
            f"[PROFILE] Turn {t.turn}: {t.total_duration_ms:.1f}ms | "
            f"Agents: {t.active_agents} active, {t.inactive_agents} inactive | "
            f"Children: {t.child_pool} | "
            f"Total: {t.total_entities}"
        )
        print(summary)
        
        # Verbose mode: print phase breakdown
        if DEBUG_VERBOSE and t.phase_durations:
            phase_str = " | ".join(
                f"{name}: {dur:.1f}ms" 
                for name, dur in sorted(t.phase_durations.items(), key=lambda x: -x[1])
            )
            print(f"  Phases: {phase_str}")
        
        # Verbose mode: print agent timing
        if DEBUG_VERBOSE and t.agents_processed > 0:
            print(f"  Agents: {t.agents_processed} processed, "
                  f"avg {t.avg_time_per_agent_ms:.3f}ms/agent, "
                  f"max {t.max_agent_time_ms:.3f}ms")
        
        # Verbose mode: print events
        if DEBUG_VERBOSE:
            print(f"  Events: {t.births} births, {t.deaths} deaths, "
                  f"{t.promotions} promotions, {t.conflicts} conflicts")
        
        # Verbose mode: print collections
        if DEBUG_VERBOSE and (t.relationships_count > 0 or t.beliefs_count > 0):
            print(f"  Collections: {t.relationships_count} relationships, "
                  f"{t.beliefs_count} beliefs, {t.memory_entries} memories")
        
        # Warning for slow turns
        if t.total_duration_ms > 1000:  # > 1 second
            print(f"  ⚠ SLOW TURN: {t.total_duration_ms:.0f}ms exceeds 1000ms threshold")
        
        # Memory warning
        if t.memory_estimate_bytes > 0:
            mem_mb = t.memory_estimate_bytes / (1024 * 1024)
            print(f"  Memory: {mem_mb:.1f}MB")
            if mem_mb > 500:
                print(f"  ⚠ HIGH MEMORY: {mem_mb:.0f}MB")
    
    def get_phase_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all phase timings."""
        return {
            name: {
                "total_ms": timer.total_ms,
                "count": timer.count,
                "avg_ms": timer.avg_ms,
                "min_ms": timer.min_ms if timer.min_ms != float('inf') else 0,
                "max_ms": timer.max_ms,
                "last_ms": timer.last_ms
            }
            for name, timer in self._phase_timers.items()
        }
    
    def get_turn_history(self, n: int = 10) -> List[TurnMetrics]:
        """Get last N turn metrics."""
        return list(self._turn_history)[-n:]
    
    def print_full_report(self) -> None:
        """Print a comprehensive profiling report."""
        if not self._turn_history:
            print("[PROFILE] No data collected yet.")
            return
        
        print("\n" + "=" * 70)
        print("SIMULATION PROFILING REPORT")
        print("=" * 70)
        
        # Turn statistics
        turns = list(self._turn_history)
        if turns:
            durations = [t.total_duration_ms for t in turns]
            print(f"\nTURN STATISTICS ({len(turns)} turns)")
            print(f"  Average duration: {sum(durations)/len(durations):.1f}ms")
            print(f"  Min duration: {min(durations):.1f}ms")
            print(f"  Max duration: {max(durations):.1f}ms")
            print(f"  Latest duration: {durations[-1]:.1f}ms")
            
            slow_turns = sum(1 for d in durations if d > 1000)
            if slow_turns > 0:
                print(f"  ⚠ Slow turns (>1s): {slow_turns} ({100*slow_turns/len(durations):.1f}%)")
        
        # Phase breakdown
        print(f"\nPHASE BREAKDOWN (cumulative)")
        sorted_phases = sorted(
            self._phase_timers.items(),
            key=lambda x: x[1].total_ms,
            reverse=True
        )
        total_phase_time = sum(p.total_ms for _, p in sorted_phases)
        for name, timer in sorted_phases:
            pct = 100 * timer.total_ms / total_phase_time if total_phase_time > 0 else 0
            print(f"  {name}: {timer.total_ms:.0f}ms total ({pct:.1f}%), "
                  f"avg {timer.avg_ms:.2f}ms, max {timer.max_ms:.1f}ms")
        
        # Growth analysis
        print(f"\nGROWTH PATTERNS")
        for name, pattern in self._growth_trackers.items():
            growth_type = pattern.get_growth_rate()
            if pattern.values:
                latest = pattern.values[-1]
                earliest = pattern.values[0] if pattern.values else 0
                print(f"  {name}: {growth_type} (from {earliest:.0f} to {latest:.0f})")
        
        # Population trend
        if turns:
            first_agents = turns[0].active_agents
            last_agents = turns[-1].active_agents
            first_total = turns[0].total_entities
            last_total = turns[-1].total_entities
            print(f"\nPOPULATION TREND")
            print(f"  Active agents: {first_agents} → {last_agents} ({last_agents - first_agents:+d})")
            print(f"  Total entities: {first_total} → {last_total} ({last_total - first_total:+d})")
        
        print("\n" + "=" * 70)
    
    def reset(self) -> None:
        """Reset all profiling data."""
        self._phase_timers.clear()
        self._turn_history.clear()
        self._growth_trackers.clear()
        self._current_turn = None


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_profiler: Optional[SimulationProfiler] = None


def get_profiler() -> SimulationProfiler:
    """Get or create the global simulation profiler."""
    global _profiler
    if _profiler is None:
        _profiler = SimulationProfiler()
    return _profiler


# ============================================================================
# DECORATORS
# ============================================================================

def profile_phase(phase_name: str):
    """Decorator to profile a function as a phase."""
    def decorator(func: Callable) -> Callable:
        if not DEBUG_PROFILE_ENABLED:
            return func
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.phase(phase_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# DETECTION UTILITIES
# ============================================================================

def detect_stall(
    turn_durations: List[float],
    threshold_multiplier: float = 5.0
) -> bool:
    """
    Detect if simulation is stalling (turn duration spiking abnormally).
    
    Returns True if latest turn took more than threshold_multiplier times
    the average of previous turns.
    """
    if len(turn_durations) < 10:
        return False
    
    previous = turn_durations[:-1]
    avg_previous = sum(previous) / len(previous)
    latest = turn_durations[-1]
    
    return latest > avg_previous * threshold_multiplier


def detect_population_explosion(
    population_history: List[int],
    growth_threshold: float = 0.1
) -> bool:
    """
    Detect if population is growing explosively (>10% per turn).
    """
    if len(population_history) < 5:
        return False
    
    recent = population_history[-5:]
    for i in range(1, len(recent)):
        if recent[i-1] > 0:
            growth = (recent[i] - recent[i-1]) / recent[i-1]
            if growth > growth_threshold:
                return True
    return False


def detect_queue_growth(
    queue_sizes: List[int],
    growth_threshold: float = 0.05
) -> bool:
    """
    Detect if queues/lists are growing unbounded.
    """
    if len(queue_sizes) < 20:
        return False
    
    # Compare first half to second half
    first_half = queue_sizes[:len(queue_sizes)//2]
    second_half = queue_sizes[len(queue_sizes)//2:]
    
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    
    if avg_first > 0:
        growth = (avg_second - avg_first) / avg_first
        return growth > growth_threshold
    
    return avg_second > 0


# ============================================================================
# QUICK HELPERS
# ============================================================================

def log_if_slow(duration_ms: float, threshold_ms: float, message: str) -> None:
    """Log a warning if duration exceeds threshold."""
    if duration_ms > threshold_ms:
        logger.warning(f"[SLOW] {message}: {duration_ms:.1f}ms (threshold: {threshold_ms:.0f}ms)")


def format_duration(ms: float) -> str:
    """Format a duration nicely."""
    if ms < 1:
        return f"{ms*1000:.0f}µs"
    elif ms < 1000:
        return f"{ms:.1f}ms"
    else:
        return f"{ms/1000:.2f}s"
