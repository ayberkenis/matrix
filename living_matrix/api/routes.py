"""REST API routes for Living Matrix."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from living_matrix.core.ipc import MatrixStateStore, MatrixCommandQueue, MatrixCommand


router = APIRouter()

# These will be set by app.py after initialization
_state_store: MatrixStateStore = None
_command_queue: MatrixCommandQueue = None
_version_manager = None


def set_dependencies(state_store: MatrixStateStore, command_queue: MatrixCommandQueue, version_manager=None):
    """Set the state store and command queue (called from app.py after initialization)."""
    global _state_store, _command_queue, _version_manager
    _state_store = state_store
    _command_queue = command_queue
    _version_manager = version_manager


def setup_routes():
    """Setup routes (uses global state_store and command_queue)."""
    
    @router.get("/version")
    async def get_version():
        """Get version information."""
        global _version_manager
        if _version_manager is None:
            # Fallback if version manager not initialized
            from living_matrix.version import VersionManager
            _version_manager = VersionManager(data_dir="data")
            _version_manager.load()
        return _version_manager.get_info()
    
    @router.get("/health")
    async def health():
        """Health check endpoint."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        state = _state_store.get_state()
        return {
            "status": "ok",
            "running": state is not None,
            "turn": state.turn if state else 0
        }
    
    @router.get("/state")
    async def get_state():
        """Get world state summary with enhanced data."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        state = _state_store.get_state()
        if not state:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        # Record observation (for observation effect)
        _state_store.record_observation(state.turn)
        
        response = {
            "turn": state.turn,
            "day": state.day,
            "time": state.time,
            "weather": state.weather,
            "economy": state.economy,
            "timestamp": state.timestamp
        }
        
        # Add detailed weather if available
        if hasattr(state, 'weather_detail') and state.weather_detail:
            response["weather"] = state.weather_detail
        
        return response
    
    @router.get("/agents")
    async def get_agents():
        """Get all agents."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        agents = _state_store.get_agents()
        return {
            "agents": agents,
            "count": len(agents)
        }
    
    @router.get("/agents/{agent_id}")
    async def get_agent(agent_id: str):
        """Get specific agent by ID."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        agent = _state_store.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return agent
    
    @router.get("/districts")
    async def get_districts():
        """Get all districts with economy stats."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        state = _state_store.get_state()
        if state:
            _state_store.record_observation(state.turn)
        districts = _state_store.get_districts()
        return {
            "districts": districts,
            "count": len(districts)
        }
    
    @router.get("/events")
    async def get_events(limit: int = 50):
        """Get recent events."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        events = _state_store.get_events(limit=limit)
        return {
            "events": events,
            "count": len(events)
        }
    
    @router.post("/control/pause")
    async def pause():
        """Pause the simulation."""
        if _command_queue is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        command = MatrixCommand(command="pause")
        await _command_queue.put(command)
        return {"status": "paused"}
    
    @router.post("/control/resume")
    async def resume():
        """Resume the simulation."""
        if _command_queue is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        command = MatrixCommand(command="resume")
        await _command_queue.put(command)
        return {"status": "resumed"}
    
    @router.post("/control/speed")
    async def set_speed(data: Dict[str, Any]):
        """Set simulation speed."""
        if _command_queue is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        ms = data.get("ms")
        if ms is None or not isinstance(ms, (int, float)):
            raise HTTPException(status_code=400, detail="Missing or invalid 'ms' parameter")
        
        command = MatrixCommand(command="set_speed", params={"ms": int(ms)})
        await _command_queue.put(command)
        return {"status": "speed_set", "ms": int(ms)}
    
    @router.get("/world/causality")
    async def get_causality(limit: int = 50):
        """Get recent causal records."""
        # Note: This requires access to simulation's causality_system
        # For now, return placeholder - full implementation would need simulation reference
        return {
            "message": "Causality system integrated - records available in simulation",
            "note": "Full API access requires simulation reference integration"
        }
    
    @router.get("/world/emotions")
    async def get_emotions():
        """Get emotional memory summary."""
        # Note: This requires access to simulation's emotional_memory
        return {
            "message": "Emotional memory system integrated",
            "note": "Full API access requires simulation reference integration"
        }
    
    @router.get("/world/rules")
    async def get_learned_rules():
        """Get learned rules."""
        # Note: This requires access to simulation's learned_rules
        return {
            "message": "Learned rules system integrated",
            "note": "Full API access requires simulation reference integration"
        }
    
    return router
