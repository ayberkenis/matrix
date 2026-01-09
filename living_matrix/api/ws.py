"""WebSocket endpoint for real-time streaming."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Set, Optional
import json
from living_matrix.core.ipc import MatrixStateStore

# Global state store (set by app.py)
_state_store: Optional[MatrixStateStore] = None


def set_state_store(state_store: MatrixStateStore):
    """Set the state store (called from app.py)."""
    global _state_store
    _state_store = state_store


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    On connect: sends initial full snapshot
    Then streams: state updates and events
    """
    if _state_store is None:
        await websocket.close(code=503, reason="World not initialized")
        return
    
    await manager.connect(websocket)
    
    try:
        # Send initial snapshot
        state = _state_store.get_state()
        if state:
            await manager.send_personal_message({
                "type": "state",
                "payload": {
                    "turn": state.turn,
                    "day": state.day,
                    "time": state.time,
                    "weather": state.weather,
                    "economy": state.economy,
                    "districts": state.districts,
                    "agents": state.agents,
                    "events": state.events
                }
            }, websocket)
        
        # Track last sent turn and events to detect updates
        last_turn = state.turn if state else 0
        last_event_count = len(_state_store.get_events()) if _state_store else 0
        
        # Keep connection alive and stream updates
        import asyncio
        
        # Create a task to periodically check for updates
        async def check_updates():
            """Periodically check for state updates and send them."""
            nonlocal last_turn, last_event_count
            while True:
                try:
                    await asyncio.sleep(0.5)  # Check every 500ms
                    
                    if _state_store is None:
                        continue
                    
                    # Check if state has been updated
                    if _state_store.has_new_state(last_turn):
                        current_state = _state_store.get_state()
                        if current_state:
                            # Send state update
                            last_turn = current_state.turn
                            await manager.send_personal_message({
                                "type": "state",
                                "payload": {
                                    "turn": current_state.turn,
                                    "day": current_state.day,
                                    "time": current_state.time,
                                    "weather": current_state.weather,
                                    "economy": current_state.economy
                                }
                            }, websocket)
                    
                    # Check for new events using get_events() method
                    current_events = _state_store.get_events(limit=200)
                    if len(current_events) > last_event_count:
                        new_events = current_events[last_event_count:]
                        for event in new_events:
                            await manager.send_personal_message({
                                "type": "event",
                                "payload": event
                            }, websocket)
                        last_event_count = len(current_events)
                
                except Exception as e:
                    # Continue on error (connection might be closed)
                    break
        
        # Start update checker task
        update_task = asyncio.create_task(check_updates())
        
        try:
            # Main loop: handle client messages
            while True:
                try:
                    # Wait for client messages (with timeout to allow task switching)
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                    # Handle client commands
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                except asyncio.TimeoutError:
                    # Timeout is expected, continue to allow update task to run
                    continue
                except WebSocketDisconnect:
                    break
        finally:
            # Cancel update task
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


async def broadcast_state_update(state_store: MatrixStateStore):
    """Broadcast state update to all connected clients."""
    state = state_store.get_state()
    if state:
        await manager.broadcast({
            "type": "state",
            "payload": {
                "turn": state.turn,
                "day": state.day,
                "time": state.time,
                "weather": state.weather,
                "economy": state.economy
            }
        })


async def broadcast_event(event: dict, state_store: MatrixStateStore):
    """Broadcast a new event to all connected clients."""
    await manager.broadcast({
        "type": "event",
        "payload": event
    })
