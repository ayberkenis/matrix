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
    
    def update(self, state: MatrixState):
        """Update the state snapshot (called by runner)."""
        with self._lock:
            self._state = state
            self._last_turn = state.turn
            # Add new events to history
            for event in state.events:
                # Check if event is already in history (by description)
                event_desc = event.get("description", "") if isinstance(event, dict) else str(event)
                if not any(e.get("description", "") == event_desc if isinstance(e, dict) else str(e) == event_desc 
                          for e in self._event_history):
                    self._event_history.append(event)
    
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
