"""REST API routes for Living Matrix."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from living_matrix.core.ipc import MatrixStateStore, MatrixCommandQueue, MatrixCommand


router = APIRouter()

# These will be set by app.py after initialization
_state_store: MatrixStateStore = None
_command_queue: MatrixCommandQueue = None
_version_manager = None
_simulation = None  # Reference to the simulation for advanced queries


def set_dependencies(state_store: MatrixStateStore, command_queue: MatrixCommandQueue, version_manager=None, simulation=None):
    """Set the state store and command queue (called from app.py after initialization)."""
    global _state_store, _command_queue, _version_manager, _simulation
    _state_store = state_store
    _command_queue = command_queue
    _version_manager = version_manager
    _simulation = simulation


def get_simulation():
    """Get the simulation reference."""
    return _simulation


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
        
        # Add death counts to economy (world state data)
        death_counts = _state_store.get_death_counts()
        if death_counts and isinstance(response.get("economy"), dict):
            response["economy"]["death_counts"] = death_counts
        
        return response
    
    @router.get("/agents")
    async def get_agents(
        limit: int = 100,
        offset: int = 0,
        district: str = None,
        role: str = None,
        alive_only: bool = True
    ):
        """
        Get agents with pagination and filtering.
        
        Args:
            limit: Maximum number of agents to return (default 100, max 1000)
            offset: Number of agents to skip (default 0)
            district: Filter by district ID (optional)
            role: Filter by role (optional)
            alive_only: Only return alive agents (default True)
        
        Returns:
            Paginated list of agents with metadata
        """
        if _state_store is None:
            raise HTTPException(status_code=503, detail="World not initialized")
        
        # Clamp limit
        limit = max(1, min(1000, limit))
        offset = max(0, offset)
        
        # Get all agents
        all_agents = _state_store.get_agents()
        
        # Apply filters
        filtered_agents = all_agents
        
        if alive_only:
            filtered_agents = [a for a in filtered_agents if a.get('is_alive', True)]
        
        if district:
            filtered_agents = [a for a in filtered_agents if a.get('district') == district]
        
        if role:
            filtered_agents = [a for a in filtered_agents if a.get('role') == role]
        
        # Get total count before pagination
        total_count = len(filtered_agents)
        
        # Apply pagination
        paginated_agents = filtered_agents[offset:offset + limit]
        
        return {
            "agents": paginated_agents,
            "count": len(paginated_agents),
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(paginated_agents) < total_count
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
        
        response = {
            "alive": len(alive),
            "total": len(agents),
            "age_groups": age_groups,
            "average_age": sum(a.get('age', 0) for a in alive) / len(alive) if alive else 0
        }
        
        # Add death counts
        death_counts = _state_store.get_death_counts()
        if death_counts:
            response["death_counts"] = death_counts
        
        return response
    
    # =========================================================================
    # GEMINI VISUAL INTELLIGENCE ROUTES
    # =========================================================================
    
    @router.get("/state/image")
    async def get_state_image():
        """
        Get the latest Matrix-style visualization of the simulation state.
        
        This endpoint returns the most recently generated image from the
        Gemini Visual Intelligence layer. Images are generated hourly
        (simulation time) based on aggregated state snapshots.
        
        The image is served from disk: gemini/generations/last.jpg
        
        Returns:
            - 200: Image data (image/jpeg)
            - 204: No image generated yet
            - 503: Gemini worker not available
        
        Headers:
            - X-Simulation-Day: The simulation day when image was generated
            - X-Simulation-Hour: The simulation hour when image was generated
            - X-State-Hash: Hash of the state snapshot used
            - X-Prompt-Hash: Hash of the prompt used for generation
        
        Note: This endpoint is READ-ONLY and serves cached images from disk.
        It NEVER triggers Gemini API calls directly.
        """
        from fastapi.responses import FileResponse, Response
        import json
        
        try:
            from living_matrix.gemini.worker import GeminiImageWorker
            
            image_path = GeminiImageWorker.get_image_path()
            metadata_path = GeminiImageWorker.get_metadata_path()
            
            # Check if image exists on disk
            if not image_path.exists():
                return Response(
                    status_code=204,
                    headers={
                        "X-Message": "No image generated yet. Images are generated hourly."
                    }
                )
            
            # Load metadata for headers
            headers = {}
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    headers = {
                        "X-Simulation-Day": str(metadata.get('generated_at_day', 0)),
                        "X-Simulation-Hour": str(metadata.get('generated_at_hour', 0)),
                        "X-Simulation-Turn": str(metadata.get('generated_at_turn', 0)),
                        "X-State-Hash": metadata.get('state_hash', ''),
                        "X-Prompt-Hash": metadata.get('prompt_hash', ''),
                        "X-Generated-At": metadata.get('generated_at_timestamp', ''),
                        "X-Generation-Time-Ms": str(metadata.get('generation_time_ms', 0)),
                        "X-Image-Size-Bytes": str(metadata.get('image_size_bytes', 0)),
                    }
                except Exception:
                    pass
            
            # Serve the file directly
            return FileResponse(
                path=str(image_path),
                media_type="image/jpeg",
                headers=headers
            )
            
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Gemini module not available"
            )
    
    @router.get("/state/image/info")
    async def get_state_image_info():
        """
        Get metadata about the latest generated image without the image data.
        
        Useful for checking if a new image is available without downloading it.
        Also provides debug information about the worker state.
        """
        try:
            from living_matrix.gemini.worker import get_worker
            from living_matrix.gemini.client import get_client
            
            worker = get_worker()
            client = get_client()
            
            stats = worker.get_stats()
            image = worker.get_latest_image()
            
            response = {
                "worker_running": stats.get("running", False),
                "images_generated": stats.get("images_generated", 0),
                "generation_failures": stats.get("generation_failures", 0),
                "rate_limit_hits": stats.get("rate_limit_hits", 0),
                "snapshots_received": stats.get("snapshots_received", 0),
                "snapshots_skipped": stats.get("snapshots_skipped", 0),
                "has_image": image is not None,
                "client_available": client.is_available if client else False,
                "client_model": client.IMAGE_MODEL if client else None,
                "current_wall_hour": stats.get("current_wall_hour"),
                "last_generation_wall_hour": stats.get("last_generation_wall_hour"),
                "next_generation_in_seconds": stats.get("next_generation_in_seconds", 0),
                "rate_limited": stats.get("rate_limited", False),
                "rate_limit_remaining_seconds": stats.get("rate_limit_remaining_seconds", 0),
            }
            
            if image:
                response["latest_image"] = image.to_dict()
            
            return response
            
        except ImportError as e:
            return {
                "worker_running": False,
                "error": f"Gemini module not available: {e}"
            }
        except Exception as e:
            return {
                "worker_running": False,
                "error": str(e)
            }
    
    # =========================================================================
    # DISTRICT DYNAMICS ENDPOINTS
    # =========================================================================
    
    @router.get("/districts/dynamics")
    async def get_district_dynamics():
        """
        Get global district dynamics status including wars, merges, and collapses.
        
        Returns:
            - active_districts: Number of active districts
            - struggling_districts: Number of struggling districts
            - districts_at_war: Number of districts at war
            - collapsed_districts: Number of collapsed districts
            - active_wars: Number of active wars
            - total_wars: Total wars in history
            - total_merges: Total merges in history
            - total_collapses: Total collapses in history
            - recent_events: Last 10 district dynamics events
        """
        sim = get_simulation()
        if not sim or not hasattr(sim, 'world_dynamics_system'):
            raise HTTPException(status_code=503, detail="Simulation not running")
        
        if not sim.world_dynamics_system:
            return {"error": "World dynamics system not initialized"}
        
        return sim.world_dynamics_system.get_global_dynamics_status()
    
    @router.get("/districts/wars")
    async def get_active_wars():
        """
        Get list of all active wars between districts.
        
        Returns list of wars with:
            - war_id: Unique war identifier
            - attacker: Attacking district ID
            - attacker_name: Attacking district name
            - defender: Defending district ID
            - defender_name: Defending district name
            - war_type: Type of war (food_raid, territory, resource_war, ideological, retaliation)
            - duration: How many turns the war has lasted
            - intensity: How intense the fighting is (0-1)
            - casualties_attacker: Attacker casualties
            - casualties_defender: Defender casualties
            - status: Current war status description
        """
        sim = get_simulation()
        if not sim or not hasattr(sim, 'world_dynamics_system'):
            raise HTTPException(status_code=503, detail="Simulation not running")
        
        if not sim.world_dynamics_system:
            return {"wars": []}
        
        return {"wars": sim.world_dynamics_system.get_active_wars()}
    
    @router.get("/districts/{district_id}/dynamics")
    async def get_district_dynamics_detail(district_id: str):
        """
        Get dynamics detail for a specific district.
        
        Returns:
            - state: Current district state (active, struggling, collapsing, collapsed, at_war, merging)
            - struggling_turns: Number of consecutive turns in struggling state
            - war_weariness: Current war weariness (0-1)
            - defensive_strength: Defensive military strength (0-1)
            - offensive_strength: Offensive military strength (0-1)
            - allies: List of allied district IDs
            - enemies: List of enemy district IDs
            - current_war: Current war details if in war
        """
        sim = get_simulation()
        if not sim or not hasattr(sim, 'world_dynamics_system'):
            raise HTTPException(status_code=503, detail="Simulation not running")
        
        if not sim.world_dynamics_system:
            raise HTTPException(status_code=404, detail="World dynamics system not initialized")
        
        summary = sim.world_dynamics_system.get_district_dynamics_summary(district_id)
        if not summary:
            raise HTTPException(status_code=404, detail=f"District {district_id} not found")
        
        return summary
    
    @router.get("/districts/collapsed")
    async def get_collapsed_districts():
        """
        Get list of collapsed district IDs.
        
        Collapsed districts are no longer active in the simulation.
        """
        sim = get_simulation()
        if not sim or not hasattr(sim, 'world_dynamics_system'):
            raise HTTPException(status_code=503, detail="Simulation not running")
        
        if not sim.world_dynamics_system:
            return {"collapsed": []}
        
        return {"collapsed": sim.world_dynamics_system.get_collapsed_districts()}
    
    return router
