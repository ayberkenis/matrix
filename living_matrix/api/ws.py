"""WebSocket endpoint for real-time streaming."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Set, Optional
import json
import time
import hashlib
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
        
        # Track last sent data for new update types
        last_causality_count = 0
        last_emotions_hash = None
        last_rules_count = 0
        last_districts_hash = None
        last_agents_hash = None
        
        # Keep connection alive and stream updates
        import asyncio
        
        def hash_data(data):
            """Create a hash of data to detect changes."""
            if data is None:
                return None
            return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        
        # Create a task to periodically check for updates
        async def check_updates():
            """Periodically check for state updates and send them."""
            nonlocal last_turn, last_event_count
            nonlocal last_causality_count, last_emotions_hash, last_rules_count
            nonlocal last_districts_hash, last_agents_hash
            
            event_send_interval = 2.0  # Send events and other updates every 2 seconds (slower)
            state_check_interval = 0.5  # Check state every 500ms (keep responsive)
            last_update_send_time = time.time()
            
            while True:
                try:
                    await asyncio.sleep(state_check_interval)  # Check every 500ms
                    current_time = time.time()
                    
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
                    
                    # Send updates at slower rate (same as events)
                    time_since_last_update = current_time - last_update_send_time
                    if time_since_last_update >= event_send_interval:
                        try:
                            # 1. Send new events (matching API format)
                            new_events = _state_store.get_new_events_since(last_event_count)
                            if new_events:
                                # Send events matching API format: {"events": [...], "count": N}
                                await manager.send_personal_message({
                                    "type": "events",
                                    "payload": {
                                        "events": new_events,  # Send all new events
                                        "count": len(new_events)
                                    }
                                }, websocket)
                                last_event_count += len(new_events)
                            
                            # 2. Send causality updates (if new records)
                            causality_data = _state_store.get_causality_data()
                            if causality_data:
                                current_causality_count = causality_data.get('total_records', 0)
                                if current_causality_count > last_causality_count:
                                    recent = causality_data.get('records', [])[-5:]  # Last 5 new records
                                    if recent:
                                        await manager.send_personal_message({
                                            "type": "causality",
                                            "payload": {
                                                "new_records": recent,
                                                "total_records": current_causality_count
                                            }
                                        }, websocket)
                                    last_causality_count = current_causality_count
                            
                            # 3. Send emotional memory updates (if changed)
                            emotional_data = _state_store.get_emotional_data()
                            if emotional_data:
                                current_hash = hash_data(emotional_data.get('summary'))
                                if current_hash != last_emotions_hash:
                                    await manager.send_personal_message({
                                        "type": "emotions",
                                        "payload": {
                                            "summary": emotional_data.get('summary', {}),
                                            "recent_traces": emotional_data.get('recent_traces', [])[-3:]  # Last 3
                                        }
                                    }, websocket)
                                    last_emotions_hash = current_hash
                            
                            # 4. Send learned rules updates (if new rules)
                            rules_data = _state_store.get_learned_rules_data()
                            if rules_data:
                                current_rules_count = rules_data.get('total_rules', 0)
                                if current_rules_count > last_rules_count:
                                    new_rules = rules_data.get('rules', [])[-3:]  # Last 3 new rules
                                    if new_rules:
                                        await manager.send_personal_message({
                                            "type": "rules",
                                            "payload": {
                                                "new_rules": new_rules,
                                                "total_rules": current_rules_count
                                            }
                                        }, websocket)
                                    last_rules_count = current_rules_count
                            
                            # 5. Send district updates (if changed - includes tension, intent, pressure, resources, psychology)
                            current_state = _state_store.get_state()
                            if current_state and current_state.districts:
                                # Create hash from all district data to detect any changes
                                districts_data = {
                                    d.get('id'): {
                                        'tension_multi': d.get('tension_multi'),
                                        'intent': d.get('intent'),
                                        'pressure': d.get('pressure'),
                                        'resources': d.get('resources'),
                                        'psychology': d.get('psychology'),
                                        'tension_trend': d.get('tension_trend')
                                    }
                                    for d in current_state.districts
                                }
                                current_districts_hash = hash_data(districts_data)
                                if current_districts_hash != last_districts_hash:
                                    # Send districts matching exact API format
                                    districts_list = current_state.districts
                                    await manager.send_personal_message({
                                        "type": "districts",
                                        "payload": {
                                            "districts": districts_list,  # Send exact same format as API
                                            "count": len(districts_list)
                                        }
                                    }, websocket)
                                    last_districts_hash = current_districts_hash
                            
                            # 6. Send agent updates (if changed - full agent data matching API format)
                            if current_state and current_state.agents:
                                # Create hash from all agent data to detect any changes
                                agents_data = {
                                    a.get('id'): {
                                        'needs': a.get('needs'),
                                        'mood': a.get('mood'),
                                        'goals': a.get('goals'),
                                        'current_action': a.get('current_action'),
                                        'intent': a.get('intent'),
                                        'inventory': a.get('inventory'),
                                        'location': a.get('location'),
                                        'district': a.get('district')
                                    }
                                    for a in current_state.agents
                                }
                                current_agents_hash = hash_data(agents_data)
                                if current_agents_hash != last_agents_hash:
                                    # Send full agent payload matching API format
                                    await manager.send_personal_message({
                                        "type": "agents",
                                        "payload": {
                                            "agents": [
                                                {
                                                    "id": a.get('id'),
                                                    "name": a.get('name'),
                                                    "district": a.get('district'),
                                                    "location": a.get('location'),
                                                    "role": a.get('role'),
                                                    "sex": a.get('sex', 'unknown'),  # Add sex field
                                                    "needs": a.get('needs'),
                                                    "mood": a.get('mood'),
                                                    "goals": a.get('goals'),
                                                    "current_action": a.get('current_action'),
                                                    "intent": a.get('intent'),
                                                    "inventory": a.get('inventory'),
                                                    "relationships": a.get('relationships')  # Include if available
                                                }
                                                for a in current_state.agents  # Send all agents, not limited
                                            ],
                                            "count": len(current_state.agents)
                                        }
                                    }, websocket)
                                    last_agents_hash = current_agents_hash
                            
                            last_update_send_time = current_time
                            
                        except Exception as e:
                            # Connection closed or error, break out
                            print(f"WebSocket update error: {e}")
                            return
                
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
    """Broadcast a new event to all connected clients (matching API format)."""
    await manager.broadcast({
        "type": "events",
        "payload": {
            "events": [event],  # Wrap in events array matching API format
            "count": 1
        }
    })
