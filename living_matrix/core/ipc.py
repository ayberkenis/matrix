"""Inter-process communication: state store and command queue."""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from collections import deque


@dataclass
class MatrixState:
    """Read-only snapshot of world state."""
    turn: int
    day: int
    time: str
    weather: str
    districts: List[Dict[str, Any]]
    agents: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    economy: Dict[str, Any]
    timestamp: str
    weather_detail: Optional[Dict[str, Any]] = None  # Detailed weather info


@dataclass
class MatrixCommand:
    """Command to send to world runner."""
    command: str  # pause, resume, set_speed, reset, inject_event
    params: Dict[str, Any] = None


class MatrixStateStore:
    """Thread-safe read-only state store."""
    
    def __init__(self):
        """Initialize state store."""
        self._lock = threading.Lock()
        self._state: Optional[MatrixState] = None
        self._event_history: deque = deque(maxlen=200)  # Last 200 events
        self._last_turn: int = 0  # Track last turn for change detection
        self._last_event_ids: set = set()  # Track event IDs to detect new events
        self._observation_count: int = 0  # Track API observations (for observation effect)
        self._last_observation_turn: int = 0
    
    def update(self, state: MatrixState):
        """Update the state snapshot (called by runner)."""
        with self._lock:
            self._state = state
            self._last_turn = state.turn
            # Add new events to history
            for event in state.events:
                # Create a unique ID for the event (using description + turn if available)
                event_id = self._get_event_id(event)
                if event_id not in self._last_event_ids:
                    self._event_history.append(event)
                    self._last_event_ids.add(event_id)
                    # Keep only last 200 event IDs to prevent memory growth
                    if len(self._last_event_ids) > 200:
                        # Remove oldest event IDs (simple approach: clear and rebuild)
                        recent_ids = {self._get_event_id(e) for e in list(self._event_history)[-200:]}
                        self._last_event_ids = recent_ids
    
    def _get_event_id(self, event: Dict[str, Any]) -> str:
        """Generate a unique ID for an event."""
        desc = event.get("description", "") if isinstance(event, dict) else str(event)
        agent_id = event.get("agent_id", "") if isinstance(event, dict) else ""
        turn = event.get("turn", 0) if isinstance(event, dict) else 0
        return f"{turn}:{agent_id}:{desc}"
    
    def has_new_state(self, last_seen_turn: int) -> bool:
        """Check if state has been updated since last_seen_turn."""
        with self._lock:
            return self._last_turn > last_seen_turn
    
    def get_state(self) -> Optional[MatrixState]:
        """Get current state snapshot (thread-safe)."""
        with self._lock:
            return self._state
    
    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events (thread-safe)."""
        with self._lock:
            return list(self._event_history)[-limit:]
    
    def get_new_events_since(self, last_count: int) -> List[Dict[str, Any]]:
        """Get new events since last_count (thread-safe)."""
        with self._lock:
            current_count = len(self._event_history)
            if current_count > last_count:
                return list(self._event_history)[last_count:]
            return []
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents (thread-safe)."""
        with self._lock:
            if self._state:
                return self._state.agents
            return []
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get specific agent (thread-safe)."""
        with self._lock:
            if self._state:
                for agent in self._state.agents:
                    if agent.get("id") == agent_id:
                        return agent
            return None
    
    def get_districts(self) -> List[Dict[str, Any]]:
        """Get all districts (thread-safe)."""
        with self._lock:
            if self._state:
                return self._state.districts
            return []
    
    def get_economy(self) -> Optional[Dict[str, Any]]:
        """Get economy summary (thread-safe)."""
        with self._lock:
            if self._state:
                return self._state.economy
            return None
    
    def record_observation(self, turn: int):
        """
        Record that the world was observed (for observation effect).
        This temporarily increases expression and narrative richness.
        """
        with self._lock:
            self._observation_count += 1
            self._last_observation_turn = turn
    
    def get_observation_info(self) -> Dict[str, Any]:
        """Get observation tracking info."""
        with self._lock:
            return {
                'count': self._observation_count,
                'last_turn': self._last_observation_turn
            }
    
    # Advanced AI systems data
    def set_causality_data(self, causality_data: Dict[str, Any]):
        """Set causality system data (thread-safe)."""
        with self._lock:
            self._causality_data = causality_data
    
    def get_causality_data(self) -> Optional[Dict[str, Any]]:
        """Get causality system data (thread-safe)."""
        with self._lock:
            return getattr(self, '_causality_data', None)
    
    def set_emotional_data(self, emotional_data: Dict[str, Any]):
        """Set emotional memory data (thread-safe)."""
        with self._lock:
            self._emotional_data = emotional_data
    
    def get_emotional_data(self) -> Optional[Dict[str, Any]]:
        """Get emotional memory data (thread-safe)."""
        with self._lock:
            return getattr(self, '_emotional_data', None)
    
    def set_learned_rules_data(self, rules_data: Dict[str, Any]):
        """Set learned rules data (thread-safe)."""
        with self._lock:
            self._learned_rules_data = rules_data
    
    def get_learned_rules_data(self) -> Optional[Dict[str, Any]]:
        """Get learned rules data (thread-safe)."""
        with self._lock:
            return getattr(self, '_learned_rules_data', None)
    
    # New systems data
    def set_world_flags_data(self, flags_data: Dict[str, Any]):
        """Set world flags data (thread-safe)."""
        with self._lock:
            self._world_flags_data = flags_data
    
    def get_world_flags_data(self) -> Optional[Dict[str, Any]]:
        """Get world flags data (thread-safe)."""
        with self._lock:
            return getattr(self, '_world_flags_data', None)
    
    def set_escalation_data(self, escalation_data: Dict[str, Any]):
        """Set escalation chains data (thread-safe)."""
        with self._lock:
            self._escalation_data = escalation_data
    
    def get_escalation_data(self) -> Optional[Dict[str, Any]]:
        """Get escalation chains data (thread-safe)."""
        with self._lock:
            return getattr(self, '_escalation_data', None)
    
    def set_culture_data(self, culture_data: Dict[str, Any]):
        """Set culture data (thread-safe)."""
        with self._lock:
            self._culture_data = culture_data
    
    def get_culture_data(self) -> Optional[Dict[str, Any]]:
        """Get culture data (thread-safe)."""
        with self._lock:
            return getattr(self, '_culture_data', None)
    
    def set_death_counts(self, death_counts: Dict[str, int]):
        """Set death counts by cause (thread-safe)."""
        with self._lock:
            self._death_counts = death_counts
    
    def get_death_counts(self) -> Dict[str, int]:
        """Get death counts by cause (thread-safe)."""
        with self._lock:
            return getattr(self, '_death_counts', {})


class MatrixCommandQueue:
    """Thread-safe command queue for API -> Runner communication."""
    
    def __init__(self):
        """Initialize command queue."""
        self._queue = asyncio.Queue()
        self._lock = threading.Lock()
    
    async def put(self, command: MatrixCommand):
        """Put a command in the queue (async)."""
        await self._queue.put(command)
    
    def put_sync(self, command: MatrixCommand):
        """Put a command in the queue (sync, for non-async code)."""
        # Create a new event loop if needed (for background thread)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is running, schedule the put
            asyncio.run_coroutine_threadsafe(self._queue.put(command), loop)
        else:
            # If loop is not running, we can run it
            loop.run_until_complete(self._queue.put(command))
    
    async def get(self) -> MatrixCommand:
        """Get a command from the queue (async)."""
        return await self._queue.get()
    
    def get_nowait(self) -> Optional[MatrixCommand]:
        """Get a command from the queue without waiting (sync)."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
