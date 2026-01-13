"""
Memory Manager for Living Matrix.

Orchestrates all memory layers and provides a unified interface for:
- Agent micro-memory
- District policy learning
- Population memory

The manager handles:
- Batching Redis writes for efficiency
- Caching reads to minimize Redis calls
- Graceful degradation when Redis unavailable
- Instability detection and learning dampening

Usage:
    from living_matrix.memory import get_memory_manager
    
    mm = get_memory_manager()
    
    # During tick
    mm.begin_tick(turn)
    
    # Record agent actions (batched)
    mm.record_agent_action(agent_id, action, success)
    
    # Get district policy modifiers
    modifiers = mm.get_district_modifiers(district_id)
    
    # End tick (flushes batches)
    mm.end_tick()
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from living_matrix.config import get_config
from living_matrix.redis_memory.redis_client import get_redis_client, is_redis_available

logger = logging.getLogger(__name__)


@dataclass
class DistrictModifiers:
    """
    Learned modifiers for a district.
    
    All modifiers are multiplicative (default 1.0) and clipped
    to safe ranges [0.75, 1.25].
    """
    aggression_bias: float = 1.0
    cooperation_bias: float = 1.0
    work_bias: float = 1.0
    migration_bias: float = 1.0
    risk_aversion: float = 1.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'aggression_bias': self.aggression_bias,
            'cooperation_bias': self.cooperation_bias,
            'work_bias': self.work_bias,
            'migration_bias': self.migration_bias,
            'risk_aversion': self.risk_aversion
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'DistrictModifiers':
        return cls(
            aggression_bias=data.get('aggression_bias', 1.0),
            cooperation_bias=data.get('cooperation_bias', 1.0),
            work_bias=data.get('work_bias', 1.0),
            migration_bias=data.get('migration_bias', 1.0),
            risk_aversion=data.get('risk_aversion', 1.0)
        )


@dataclass
class PopulationSignals:
    """
    Coarse signals derived from population memory.
    
    These are simple, cheap-to-compute signals that can
    modulate decisions slightly.
    """
    food_trend: str = "stable"  # "up", "down", "stable"
    tension_trend: str = "stable"
    tension_volatility: str = "low"  # "low", "medium", "high"
    death_rate_trend: str = "stable"
    productivity_trend: str = "stable"


class MemoryManager:
    """
    Unified memory manager for all learning features.
    
    Safety Guarantees:
    - All operations fail gracefully
    - All learned values are clipped
    - Batched writes minimize Redis calls
    - Instability detection dampens learning
    - Never blocks the simulation
    """
    
    def __init__(self):
        self._config = get_config()
        self._client = None
        self._available = False
        
        # Per-tick state
        self._current_tick = 0
        self._pending_agent_writes: List[Tuple[str, str, int]] = []
        self._pending_pop_writes: List[Tuple[str, str, float, int]] = []
        
        # Cached district modifiers (refreshed per tick)
        self._district_modifiers_cache: Dict[str, DistrictModifiers] = {}
        self._cache_tick = -1
        
        # Instability tracking
        self._last_population = 0
        self._instability_factor = 1.0  # 1.0 = normal, <1.0 = dampened
        
        # Stats
        self._stats = {
            'agent_memory_writes': 0,
            'district_policy_updates': 0,
            'population_memory_writes': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _ensure_client(self) -> bool:
        """Ensure Redis client is initialized."""
        if self._client is None:
            self._client = get_redis_client()
            self._available = self._client is not None and self._client.is_connected()
        return self._available
    
    def is_available(self) -> bool:
        """Check if memory features are available."""
        return self._ensure_client()
    
    def is_learning_enabled(self) -> bool:
        """Check if learning is enabled and Redis is available."""
        return self._config.LEARNING_ENABLED and self.is_available()
    
    # ========================================
    # TICK LIFECYCLE
    # ========================================
    
    def begin_tick(self, turn: int, population: int = 0):
        """
        Begin a new tick.
        
        Args:
            turn: Current turn number
            population: Current population count (for instability detection)
        """
        self._current_tick = turn
        self._pending_agent_writes.clear()
        self._pending_pop_writes.clear()
        
        # Detect instability
        if population > 0 and self._last_population > 0:
            change_rate = abs(population - self._last_population) / self._last_population
            if change_rate > self._config.INSTABILITY_THRESHOLD:
                self._instability_factor = self._config.INSTABILITY_DAMPENING
                logger.debug(f"Instability detected: {change_rate:.2%}, dampening learning")
            else:
                self._instability_factor = min(1.0, self._instability_factor + 0.1)
        
        self._last_population = population
    
    def end_tick(self):
        """
        End the current tick - flush all pending writes.
        """
        if not self.is_available():
            return
        
        # Flush pending agent memory writes
        if self._pending_agent_writes and self._config.MICRO_MEMORY_ENABLED:
            count = self._client.push_batch_agent_memory(self._pending_agent_writes)
            self._stats['agent_memory_writes'] += count
        
        # Flush pending population memory writes
        if self._pending_pop_writes and self._config.POPULATION_MEMORY_ENABLED:
            count = self._client.push_batch_population_stats(self._pending_pop_writes)
            self._stats['population_memory_writes'] += count
        
        self._pending_agent_writes.clear()
        self._pending_pop_writes.clear()
    
    # ========================================
    # AGENT MICRO-MEMORY
    # ========================================
    
    def record_agent_action(self, agent_id: str, action: str, success: bool):
        """
        Record an agent's action to micro-memory.
        
        Only records for active agents.
        Batched for efficiency - writes happen at end_tick().
        
        Args:
            agent_id: Agent identifier
            action: Action taken
            success: Whether action succeeded
        """
        if not self._config.MICRO_MEMORY_ENABLED:
            return
        
        # Encode action compactly
        data = f"{action}:{1 if success else 0}"
        max_size = self._config.AGENT_MEMORY_SIZE
        
        self._pending_agent_writes.append((agent_id, data, max_size))
    
    def get_agent_action_history(self, agent_id: str) -> List[Tuple[str, bool]]:
        """
        Get agent's recent action history.
        
        Returns:
            List of (action, success) tuples, most recent first
        """
        if not self.is_available() or not self._config.MICRO_MEMORY_ENABLED:
            return []
        
        entries = self._client.get_agent_memory(agent_id, self._config.AGENT_MEMORY_SIZE)
        result = []
        for entry in entries:
            parts = entry.split(':')
            if len(parts) == 2:
                result.append((parts[0], parts[1] == '1'))
        return result
    
    # ========================================
    # DISTRICT POLICY LEARNING
    # ========================================
    
    def get_district_modifiers(self, district_id: str) -> DistrictModifiers:
        """
        Get learned modifiers for a district.
        
        Cached per tick for efficiency.
        
        Args:
            district_id: District identifier
            
        Returns:
            DistrictModifiers with learned values (or defaults)
        """
        if not self._config.DISTRICT_LEARNING_ENABLED:
            return DistrictModifiers()
        
        # Check cache
        if self._cache_tick == self._current_tick and district_id in self._district_modifiers_cache:
            self._stats['cache_hits'] += 1
            return self._district_modifiers_cache[district_id]
        
        # Clear cache if new tick
        if self._cache_tick != self._current_tick:
            self._district_modifiers_cache.clear()
            self._cache_tick = self._current_tick
        
        self._stats['cache_misses'] += 1
        
        # Load from Redis
        if self.is_available():
            data = self._client.get_district_policy(district_id)
            if data:
                modifiers = DistrictModifiers.from_dict(data)
            else:
                modifiers = DistrictModifiers()
        else:
            modifiers = DistrictModifiers()
        
        self._district_modifiers_cache[district_id] = modifiers
        return modifiers
    
    def update_district_policy(self, district_id: str, 
                               cooperation_signal: float,
                               aggression_signal: float,
                               productivity_signal: float,
                               migration_signal: float,
                               risk_signal: float):
        """
        Update district policy based on observed signals.
        
        Uses exponential moving average with very small learning rate.
        All values are clipped to safe ranges.
        
        Args:
            district_id: District identifier
            cooperation_signal: [-1, 1] cooperation success
            aggression_signal: [-1, 1] aggression success
            productivity_signal: [-1, 1] work productivity
            migration_signal: [-1, 1] migration success
            risk_signal: [-1, 1] risk outcome
        """
        if not self._config.DISTRICT_LEARNING_ENABLED or not self.is_available():
            return
        
        current = self.get_district_modifiers(district_id)
        
        # Apply learning with instability dampening
        lr = self._config.LEARNING_RATE_DISTRICT * self._instability_factor
        clip = self._config.clip_weight
        
        # Update each bias
        new_modifiers = DistrictModifiers(
            cooperation_bias=clip(current.cooperation_bias + lr * cooperation_signal),
            aggression_bias=clip(current.aggression_bias + lr * aggression_signal),
            work_bias=clip(current.work_bias + lr * productivity_signal),
            migration_bias=clip(current.migration_bias + lr * migration_signal),
            risk_aversion=clip(current.risk_aversion + lr * risk_signal)
        )
        
        # Save to Redis
        self._client.set_district_policy(district_id, new_modifiers.to_dict())
        self._stats['district_policy_updates'] += 1
        
        # Update cache
        self._district_modifiers_cache[district_id] = new_modifiers
    
    # ========================================
    # POPULATION MEMORY
    # ========================================
    
    def record_population_stats(self, district_id: str,
                                hunger_avg: float,
                                tension: float,
                                death_count: int,
                                productivity: float):
        """
        Record population statistics for a district.
        
        Batched for efficiency.
        
        Args:
            district_id: District identifier
            hunger_avg: Average hunger level
            tension: District tension
            death_count: Deaths this tick
            productivity: Work productivity
        """
        if not self._config.POPULATION_MEMORY_ENABLED:
            return
        
        max_size = self._config.POPULATION_MEMORY_SIZE
        
        self._pending_pop_writes.append((district_id, "hunger", hunger_avg, max_size))
        self._pending_pop_writes.append((district_id, "tension", tension, max_size))
        self._pending_pop_writes.append((district_id, "deaths", float(death_count), max_size))
        self._pending_pop_writes.append((district_id, "productivity", productivity, max_size))
    
    def get_population_signals(self, district_id: str) -> PopulationSignals:
        """
        Get coarse population signals for a district.
        
        Computes trends from stored history.
        
        Args:
            district_id: District identifier
            
        Returns:
            PopulationSignals with trend information
        """
        if not self._config.POPULATION_MEMORY_ENABLED or not self.is_available():
            return PopulationSignals()
        
        signals = PopulationSignals()
        
        # Get recent stats
        hunger = self._client.get_population_stats(district_id, "hunger", 10)
        tension = self._client.get_population_stats(district_id, "tension", 10)
        deaths = self._client.get_population_stats(district_id, "deaths", 10)
        productivity = self._client.get_population_stats(district_id, "productivity", 10)
        
        # Compute trends (simple: compare recent average to older average)
        def compute_trend(values: List[float]) -> str:
            if len(values) < 4:
                return "stable"
            recent = sum(values[:len(values)//2]) / (len(values)//2)
            older = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            diff = recent - older
            if diff > 0.1:
                return "up"
            elif diff < -0.1:
                return "down"
            return "stable"
        
        def compute_volatility(values: List[float]) -> str:
            if len(values) < 2:
                return "low"
            avg = sum(values) / len(values)
            if avg == 0:
                return "low"
            variance = sum((v - avg) ** 2 for v in values) / len(values)
            cv = (variance ** 0.5) / avg if avg > 0 else 0
            if cv > 0.5:
                return "high"
            elif cv > 0.2:
                return "medium"
            return "low"
        
        signals.food_trend = "down" if compute_trend(hunger) == "up" else (
            "up" if compute_trend(hunger) == "down" else "stable"
        )  # Inverted: higher hunger = lower food
        signals.tension_trend = compute_trend(tension)
        signals.tension_volatility = compute_volatility(tension)
        signals.death_rate_trend = compute_trend(deaths)
        signals.productivity_trend = compute_trend(productivity)
        
        return signals
    
    # ========================================
    # STATS & DIAGNOSTICS
    # ========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics."""
        return {
            **self._stats,
            'available': self.is_available(),
            'learning_enabled': self.is_learning_enabled(),
            'instability_factor': self._instability_factor,
            'current_tick': self._current_tick
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0


# Global singleton
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the singleton memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def reset_memory_manager():
    """Reset the memory manager (for testing)."""
    global _memory_manager
    _memory_manager = None
