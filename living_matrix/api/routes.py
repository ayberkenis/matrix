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


def setup_routes(debug_mode: bool = False):
    """
    Setup routes (uses global state_store and command_queue).
    
    Args:
        debug_mode: If True, enables control endpoints (pause, resume, speed)
    """
    
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
    
    # Control endpoints - only available in debug mode
    if debug_mode:
        @router.post("/control/pause")
        async def pause():
            """Pause the simulation (debug mode only)."""
            if _command_queue is None:
                raise HTTPException(status_code=503, detail="World not initialized")
            command = MatrixCommand(command="pause")
            await _command_queue.put(command)
            return {"status": "paused"}
        
        @router.post("/control/resume")
        async def resume():
            """Resume the simulation (debug mode only)."""
            if _command_queue is None:
                raise HTTPException(status_code=503, detail="World not initialized")
            command = MatrixCommand(command="resume")
            await _command_queue.put(command)
            return {"status": "resumed"}
        
        @router.post("/control/speed")
        async def set_speed(data: Dict[str, Any]):
            """Set simulation speed (debug mode only)."""
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
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        causality_data = _state_store.get_causality_data()
        if not causality_data:
            return {
                "records": [],
                "total_records": 0,
                "message": "Causality system not yet initialized"
            }
        
        # Limit records if requested
        records = causality_data.get('records', [])
        if limit < len(records):
            records = records[-limit:]
        
        return {
            "records": records,
            "total_records": causality_data.get('total_records', 0),
            "returned": len(records)
        }
    
    @router.get("/world/emotions")
    async def get_emotions():
        """Get emotional memory summary."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        emotional_data = _state_store.get_emotional_data()
        if not emotional_data:
            return {
                "summary": {
                    "fear": 0.0,
                    "anger": 0.0,
                    "hope": 0.0,
                    "joy": 0.0,
                    "sadness": 0.0,
                    "surprise": 0.0
                },
                "recent_traces": [],
                "total_traces": 0,
                "message": "Emotional memory not yet initialized"
            }
        
        return {
            "summary": emotional_data.get('summary', {}),
            "recent_traces": emotional_data.get('recent_traces', []),
            "total_traces": emotional_data.get('total_traces', 0)
        }
    
    @router.get("/world/rules")
    async def get_learned_rules():
        """Get learned rules."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        rules_data = _state_store.get_learned_rules_data()
        if not rules_data:
            return {
                "rules": [],
                "total_rules": 0,
                "message": "Learned rules system not yet initialized"
            }
        
        # Sort by confidence (highest first)
        rules = rules_data.get('rules', [])
        rules_sorted = sorted(rules, key=lambda r: r.get('confidence', 0.0), reverse=True)
        
        return {
            "rules": rules_sorted,
            "total_rules": rules_data.get('total_rules', 0),
            "returned": len(rules_sorted)
        }
    
    # New endpoints for World Flags, Escalation, Beliefs, Culture
    @router.get("/world/flags")
    async def get_world_flags():
        """Get all triggered world flags."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        flags_data = _state_store.get_world_flags_data()
        if not flags_data:
            return {
                "flags": [],
                "count": 0,
                "message": "World flags system not yet initialized"
            }
        
        return {
            "flags": flags_data.get('flags', []),
            "count": flags_data.get('count', 0)
        }
    
    @router.get("/escalations")
    async def get_escalations():
        """Get all active escalation chains."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        escalation_data = _state_store.get_escalation_data()
        if not escalation_data:
            return {
                "chains": [],
                "active_count": 0,
                "message": "Escalation system not yet initialized"
            }
        
        return {
            "chains": escalation_data.get('chains', []),
            "active_count": escalation_data.get('active_count', 0),
            "total_chains": escalation_data.get('total_chains', 0)
        }
    
    @router.get("/districts/{district_id}/culture")
    async def get_district_culture(district_id: str):
        """Get culture for a specific district."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        culture_data = _state_store.get_culture_data()
        if not culture_data:
            # Return default culture if system not yet initialized
            return {
                "district_id": district_id,
                "culture": {
                    "collectivism": 0.5,
                    "obedience": 0.5,
                    "aggression": 0.5,
                    "risk_tolerance": 0.5
                },
                "message": "Culture system not yet initialized, returning default values"
            }
        
        culture = culture_data.get('cultures', {}).get(district_id)
        if not culture:
            # Return default culture if district not found
            return {
                "district_id": district_id,
                "culture": {
                    "collectivism": 0.5,
                    "obedience": 0.5,
                    "aggression": 0.5,
                    "risk_tolerance": 0.5
                },
                "message": f"Culture not found for district {district_id}, returning default values"
            }
        
        return {
            "district_id": district_id,
            "culture": culture
        }
    
    @router.get("/agents/{agent_id}/beliefs")
    async def get_agent_beliefs(agent_id: str):
        """Get beliefs for a specific agent."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        agent = _state_store.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        beliefs = agent.get('beliefs', {})
        return {
            "agent_id": agent_id,
            "beliefs": beliefs,
            "count": len(beliefs)
        }
    
    @router.get("/agents/{agent_id}/relationships")
    async def get_agent_relationships(agent_id: str):
        """Get relationships for a specific agent."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        agent = _state_store.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        relationships = agent.get('relationships', {})
        return {
            "agent_id": agent_id,
            "relationships": relationships,
            "count": len(relationships)
        }
    
    @router.get("/population/stats")
    async def get_population_stats():
        """Get population statistics (alive, dead, age groups, births, deaths)."""
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        # Get population stats from simulation (would need to expose this)
        # For now, calculate from agents
        agents = _state_store.get_agents()
        alive = [a for a in agents if a.get('is_alive', True)]
        age_groups = {
            "children": sum(1 for a in alive if a.get('age', 0) < 100),
            "adults": sum(1 for a in alive if 100 <= a.get('age', 0) < 800),
            "elderly": sum(1 for a in alive if a.get('age', 0) >= 800)
        }
        
        return {
            "alive": len(alive),
            "total": len(agents),
            "age_groups": age_groups,
            "average_age": sum(a.get('age', 0) for a in alive) / len(alive) if alive else 0
        }
    
    return router
