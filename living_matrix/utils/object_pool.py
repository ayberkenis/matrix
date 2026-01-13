"""Object pooling and memory optimization utilities.

Provides object reuse to avoid per-tick allocation overhead.
All pools are bounded to prevent unbounded memory growth.
"""

from typing import TypeVar, Generic, Callable, List, Optional, Dict, Any
from collections import deque
from dataclasses import dataclass

from living_matrix.constants.performance_constants import MAX_POOL_SIZE, EVENT_BUFFER_SIZE

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """
    Generic object pool for reusing objects.
    
    Objects are acquired from the pool and returned when done.
    If the pool is empty, a new object is created.
    Pool has a maximum size to prevent unbounded growth.
    """
    
    __slots__ = ('_factory', '_pool', '_max_size', '_reset_func')
    
    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = MAX_POOL_SIZE,
        reset_func: Optional[Callable[[T], None]] = None
    ):
        """
        Initialize object pool.
        
        Args:
            factory: Function to create new objects
            max_size: Maximum pool size
            reset_func: Optional function to reset object state before reuse
        """
        self._factory = factory
        self._pool: deque = deque()
        self._max_size = max_size
        self._reset_func = reset_func
    
    def acquire(self) -> T:
        """
        Acquire an object from the pool.
        
        Returns a recycled object if available, otherwise creates new.
        """
        if self._pool:
            obj = self._pool.popleft()
            if self._reset_func:
                self._reset_func(obj)
            return obj
        return self._factory()
    
    def release(self, obj: T) -> None:
        """
        Return an object to the pool.
        
        Object is discarded if pool is at max size.
        """
        if len(self._pool) < self._max_size:
            self._pool.append(obj)
    
    def clear(self) -> None:
        """Clear all pooled objects."""
        self._pool.clear()
    
    @property
    def size(self) -> int:
        """Current number of pooled objects."""
        return len(self._pool)


@dataclass(slots=True)
class EventRecord:
    """
    Lightweight event record using slots for memory efficiency.
    
    Uses __slots__ to avoid per-instance __dict__.
    """
    agent_id: str = ""
    description: str = ""
    event_type: Optional[str] = None
    turn: int = 0
    
    def reset(self) -> None:
        """Reset for reuse."""
        self.agent_id = ""
        self.description = ""
        self.event_type = None
        self.turn = 0
    
    def set(
        self,
        agent_id: str,
        description: str,
        event_type: Optional[str],
        turn: int
    ) -> 'EventRecord':
        """Set values and return self for chaining."""
        self.agent_id = agent_id
        self.description = description
        self.event_type = event_type
        self.turn = turn
        return self
    
    def to_tuple(self) -> tuple:
        """Convert to tuple format for compatibility."""
        return (self.agent_id, self.description, self.event_type)


class EventBuffer:
    """
    Pre-allocated buffer for events to avoid per-tick list creation.
    
    Uses a circular buffer approach with pre-allocated EventRecord objects.
    """
    
    __slots__ = ('_records', '_size', '_write_idx', '_count', '_pool')
    
    def __init__(self, size: int = EVENT_BUFFER_SIZE):
        self._size = size
        self._write_idx = 0
        self._count = 0
        self._pool = ObjectPool(
            factory=EventRecord,
            max_size=size,
            reset_func=lambda r: r.reset()
        )
        # Pre-allocate all records
        self._records: List[EventRecord] = [EventRecord() for _ in range(size)]
    
    def add(
        self,
        agent_id: str,
        description: str,
        event_type: Optional[str],
        turn: int
    ) -> None:
        """Add an event to the buffer."""
        record = self._records[self._write_idx]
        record.set(agent_id, description, event_type, turn)
        
        self._write_idx = (self._write_idx + 1) % self._size
        self._count = min(self._count + 1, self._size)
    
    def get_recent(self, n: int) -> List[EventRecord]:
        """Get the N most recent events."""
        n = min(n, self._count)
        if n == 0:
            return []
        
        result = []
        idx = (self._write_idx - n) % self._size
        for _ in range(n):
            result.append(self._records[idx])
            idx = (idx + 1) % self._size
        return result
    
    def to_tuples(self, n: Optional[int] = None) -> List[tuple]:
        """Convert recent events to tuple format."""
        if n is None:
            n = self._count
        return [r.to_tuple() for r in self.get_recent(n)]
    
    def clear(self) -> None:
        """Clear the buffer."""
        self._write_idx = 0
        self._count = 0
        for record in self._records:
            record.reset()
    
    @property
    def count(self) -> int:
        """Number of events in buffer."""
        return self._count


# Lightweight tuple-based containers for hot paths
# These avoid dict overhead while maintaining readability

@dataclass(slots=True, frozen=True)
class NeedsSnapshot:
    """Immutable snapshot of agent needs (more efficient than dict)."""
    hunger: int
    rest: int
    safety: int
    belonging: int
    purpose: int


@dataclass(slots=True, frozen=True)
class TraitsSnapshot:
    """Immutable snapshot of agent traits."""
    risk: float
    empathy: float
    ambition: float
    patience: float


@dataclass(slots=True)
class ResourceState:
    """Mutable resource state for districts."""
    food_stock: float = 50.0
    credits_pool: float = 100.0
    jobs_available: int = 10
    tension: float = 0.0
    
    def update_from_dict(self, d: Dict[str, Any]) -> None:
        """Update from dictionary."""
        if "food_stock" in d:
            self.food_stock = d["food_stock"]
        if "credits_pool" in d:
            self.credits_pool = d["credits_pool"]
        if "jobs_available" in d:
            self.jobs_available = d["jobs_available"]
        if "tension" in d:
            self.tension = d["tension"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "food_stock": self.food_stock,
            "credits_pool": self.credits_pool,
            "jobs_available": self.jobs_available,
            "tension": self.tension
        }


class LookupCache:
    """
    Simple cache for repeated lookups.
    
    Automatically invalidates on tick boundary.
    """
    
    __slots__ = ('_cache', '_current_turn', '_max_size')
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._current_turn: int = -1
        self._max_size = max_size
    
    def get(self, key: str, turn: int) -> Optional[Any]:
        """Get cached value if same turn."""
        if turn != self._current_turn:
            self._cache.clear()
            self._current_turn = turn
            return None
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, turn: int) -> None:
        """Cache a value for the current turn."""
        if turn != self._current_turn:
            self._cache.clear()
            self._current_turn = turn
        if len(self._cache) < self._max_size:
            self._cache[key] = value
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._current_turn = -1


# Pre-instantiated pools for common objects
_event_pool: Optional[ObjectPool[EventRecord]] = None
_event_buffer: Optional[EventBuffer] = None
_lookup_cache: Optional[LookupCache] = None


def get_event_pool() -> ObjectPool[EventRecord]:
    """Get global event record pool."""
    global _event_pool
    if _event_pool is None:
        _event_pool = ObjectPool(
            factory=EventRecord,
            max_size=MAX_POOL_SIZE,
            reset_func=lambda r: r.reset()
        )
    return _event_pool


def get_event_buffer() -> EventBuffer:
    """Get global event buffer."""
    global _event_buffer
    if _event_buffer is None:
        _event_buffer = EventBuffer(EVENT_BUFFER_SIZE)
    return _event_buffer


def get_lookup_cache() -> LookupCache:
    """Get global lookup cache."""
    global _lookup_cache
    if _lookup_cache is None:
        _lookup_cache = LookupCache()
    return _lookup_cache
