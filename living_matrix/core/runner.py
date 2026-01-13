"""Background runner for Living Matrix world simulation."""

import asyncio
import threading
import time
import logging
import os
from typing import Optional
from datetime import datetime
from living_matrix.core.ipc import MatrixStateStore, MatrixCommandQueue, MatrixState, MatrixCommand

logger = logging.getLogger(__name__)


class WorldRunner:
    """Runs Living Matrix world simulation in background."""
    
    def __init__(self, simulation, state_store: MatrixStateStore, command_queue: MatrixCommandQueue, version_manager=None):
        """
        Initialize world runner.
        
        Args:
            simulation: Simulation instance
            state_store: State store for snapshots
            command_queue: Command queue for API commands
            version_manager: Optional version manager for tracking resets
        """
        self.simulation = simulation
        self.state_store = state_store
        self.command_queue = command_queue
        self.version_manager = version_manager
        
        self.running = False
        self.paused = False
        self.tick_rate_ms = 50  # Default 50ms per tick
        self._runner_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Periodic logging (every 10 seconds)
        self._last_log_time = time.time()
        self._log_interval_seconds = 10.0
        
        # Gemini Visual Intelligence (observational only)
        self._gemini_worker = None
        self._gemini_enabled = os.getenv("GEMINI_ENABLED", "true").lower() not in ("false", "0", "no", "off")
        self._last_gemini_submit_time = 0.0  # Wall-clock time of last snapshot submission
        self._gemini_submit_interval = 60  # Submit snapshot every 60 seconds (worker decides when to generate)
        
        # Initialize simulation
        self.simulation.initialize()
        
        # Initialize Gemini worker if enabled and API key present
        self._init_gemini_worker()
    
    def _init_gemini_worker(self):
        """
        Initialize Gemini Visual Intelligence worker.
        
        The worker is OBSERVATIONAL ONLY - it reads state snapshots
        and generates Matrix-style images but never modifies simulation.
        
        Fails gracefully if Gemini is unavailable.
        """
        if not self._gemini_enabled:
            logger.info("Gemini Visual Intelligence disabled (GEMINI_ENABLED=false)")
            return
        
        if not os.getenv("GEMINI_API_KEY"):
            logger.info("Gemini Visual Intelligence disabled (no GEMINI_API_KEY)")
            return
        
        try:
            from living_matrix.gemini.worker import get_worker
            self._gemini_worker = get_worker()
            logger.info("Gemini Visual Intelligence initialized")
        except ImportError as e:
            logger.warning(f"Gemini module not available: {e}")
            self._gemini_worker = None
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini worker: {e}")
            self._gemini_worker = None
    
    def start(self):
        """Start the background runner."""
        if self.running:
            return
        
        self.running = True
        self.paused = False
        self._stop_event.clear()
        
        # Start Gemini worker if available
        if self._gemini_worker:
            try:
                self._gemini_worker.start()
                logger.info("Gemini image worker started")
            except Exception as e:
                logger.warning(f"Failed to start Gemini worker: {e}")
        
        # Start runner thread
        self._runner_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._runner_thread.start()
    
    def stop(self):
        """Stop the background runner gracefully."""
        self.running = False
        self._stop_event.set()
        
        # Stop Gemini worker if running
        if self._gemini_worker:
            try:
                self._gemini_worker.stop()
                logger.info("Gemini image worker stopped")
            except Exception as e:
                logger.warning(f"Error stopping Gemini worker: {e}")
        
        if self._runner_thread:
            self._runner_thread.join(timeout=5.0)
    
    def pause(self):
        """Pause the simulation."""
        self.paused = True
    
    def resume(self):
        """Resume the simulation."""
        self.paused = False
    
    def set_speed(self, tick_rate_ms: int):
        """Set tick rate in milliseconds."""
        self.tick_rate_ms = max(10, min(1000, tick_rate_ms))  # Clamp 10-1000ms
    
    def _run_loop(self):
        """Main runner loop (runs in background thread)."""
        try:
            while self.running and not self._stop_event.is_set():
                # Process commands (non-blocking)
                try:
                    command = self.command_queue.get_nowait()
                    if command:
                        self._process_command(command)
                except Exception:
                    pass  # Queue empty or error, continue
                
                # Run simulation step if not paused
                if not self.paused:
                    try:
                        self._tick()
                    except Exception as e:
                        print(f"Error in simulation tick: {e}")
                
                # Periodic logging every 10 seconds
                current_time = time.time()
                if current_time - self._last_log_time >= self._log_interval_seconds:
                    self._log_statistics()
                    self._last_log_time = current_time
                
                # Sleep for tick rate
                time.sleep(self.tick_rate_ms / 1000.0)
        
        except Exception as e:
            print(f"Error in world runner: {e}")
    
    def _process_command(self, command: MatrixCommand):
        """Process a command from the queue."""
        if command.command == "pause":
            self.pause()
        elif command.command == "resume":
            self.resume()
        elif command.command == "set_speed":
            if command.params and "ms" in command.params:
                self.set_speed(command.params["ms"])
        elif command.command == "reset":
            # Reset simulation (reinitialize)
            self.simulation.initialize()
            # Mark reset in version manager if available
            if self.version_manager:
                self.version_manager.mark_reset()
        elif command.command == "inject_event":
            # Future: inject custom event
            pass
    
    def _tick(self):
        """Execute one simulation tick and update state store."""
        # Advance simulation
        self.simulation.step(autonomous=True)
        
        # Apply observation effect if recently observed
        obs_info = self.state_store.get_observation_info()
        current_turn = self.simulation.world.state.turn if self.simulation.world.state else 0
        if obs_info['last_turn'] == current_turn or (current_turn - obs_info['last_turn']) < 5:
            # Recently observed - temporarily boost expression drive
            if self.simulation.world.state:
                # Temporarily increase expression drive
                original_expression = self.simulation.world.state.drives.expression
                self.simulation.world.state.drives.expression = min(1.0, original_expression + 0.1)
        
        # Create state snapshot
        state = self._create_state_snapshot()
        
        # Update state store
        self.state_store.update(state)
        
        # Update advanced AI systems data (every tick, but lightweight)
        self._update_ai_systems_data()
        
        # Submit snapshot to Gemini worker (hourly, observational only)
        self._submit_gemini_snapshot()
    
    def _create_state_snapshot(self) -> MatrixState:
        """Create a read-only state snapshot."""
        sim = self.simulation
        
        # Get time
        day = 0
        time_str = "00:00"
        if sim.time_system:
            day = sim.time_system.day_index
            time_str = sim.time_system.format_time()
        
        # Get weather (detailed)
        weather_str = "Unknown"
        weather_detail = None
        if sim.weather_system:
            weather_str = sim.weather_system.format_weather_line()
            # Get detailed weather for first region
            if sim.world_map and sim.world_map.regions:
                first_region_id = list(sim.world_map.regions.keys())[0]
                weather_snapshot = sim.weather_system.snapshot(first_region_id)
                if weather_snapshot:
                    weather_detail = {
                        "sky": weather_snapshot.sky if hasattr(weather_snapshot, 'sky') else "unknown",
                        "wind": weather_snapshot.wind if hasattr(weather_snapshot, 'wind') else "unknown",
                        "precipitation": weather_snapshot.precipitation if hasattr(weather_snapshot, 'precipitation') else "unknown",
                        "temperature": weather_snapshot.temperature if hasattr(weather_snapshot, 'temperature') else "unknown"
                    }
        
        # Get districts (use world_dynamics if available, fallback to economy)
        districts = []
        if sim.world_map:
            # Check if world_dynamics_system exists
            world_dynamics = getattr(sim, 'world_dynamics_system', None)
            
            if world_dynamics:
                # Use advanced world dynamics
                for district_id, region in sim.world_map.regions.items():
                    district = world_dynamics.get_district(district_id)
                    if district:
                        # Get neighboring districts
                        neighbor_ids = [r_id for r_id in sim.world_map.regions.keys() if r_id != district_id]
                        
                        # Get multi-dimensional tension
                        multi_tension = None
                        if hasattr(district.tension_state, 'multi_tension'):
                            multi_tension = district.tension_state.multi_tension.to_dict()
                        else:
                            # Fallback to single tension
                            multi_tension = {
                                'economic': district.tension_state.tension,
                                'social': district.tension_state.tension,
                                'political': district.tension_state.tension * 0.75,
                                'existential': district.tension_state.tension * 0.5
                            }
                        
                        # Get district intent
                        district_intent = None
                        if hasattr(district, 'intent'):
                            district_intent = district.intent.to_dict()
                        
                        # Get district culture
                        district_culture = None
                        if hasattr(district, 'culture') and district.culture:
                            district_culture = district.culture.to_dict()
                        
                        district_dict = {
                            "id": district_id,
                            "name": district.district_name,
                            "tension": round(district.tension_state.tension, 1),  # Legacy
                            "tension_multi": multi_tension,  # New multi-dimensional
                            "intent": district_intent,  # New intent
                            "culture": district_culture,  # New culture
                            "tension_trend": world_dynamics.get_tension_trend(district_id),
                            "pressure": {
                                "food": round(district.pressure.food, 2),
                                "jobs": round(district.pressure.jobs, 2),
                                "weather": round(district.pressure.weather, 2),
                                "migration": round(district.pressure.migration, 2),
                                "rumor": round(district.pressure.rumor, 2),
                                "inequality": round(district.pressure.inequality, 2)
                            },
                            "resources": {
                                "food_stock": round(district.food_stock, 1),
                                "jobs_available": district.jobs_available
                            },
                            "psychology": {
                                "trust": round(district.psychology.trust_score, 2),
                                "trauma": round(district.psychology.trauma_score, 2),
                                "fatigue": round(district.psychology.fatigue_score, 2)
                            },
                            "recent_events": [
                                {
                                    "type": e.get("type", "unknown"),
                                    "severity": e.get("severity", 0.0),
                                    "turn": e.get("turn", 0)
                                }
                                for e in list(district.psychology.recent_events)[-5:]
                            ],
                            "risk_flags": world_dynamics.get_risk_flags(district_id)
                        }
                        # Add birth_pressure if available (SYSTEM 13)
                        if hasattr(district, 'birth_pressure'):
                            district_dict["birth_pressure"] = round(district.birth_pressure, 2)
                        # POPULATION COMPRESSION: Add population metrics
                        if hasattr(district, 'child_pool'):
                            district_dict["child_pool"] = district.child_pool
                        if hasattr(district, 'active_agents'):
                            district_dict["active_agents"] = district.active_agents
                        if hasattr(district, 'total_population'):
                            district_dict["total_population"] = district.total_population
                        if hasattr(district, 'population_pressure'):
                            district_dict["population_pressure"] = round(district.population_pressure, 3)
                        districts.append(district_dict)
            elif sim.economy_system:
                # Fallback to old economy system
                # Try to get culture from culture system if available
                culture_system = None
                if hasattr(sim, 'world_dynamics_system') and hasattr(sim.world_dynamics_system, 'culture_system'):
                    culture_system = sim.world_dynamics_system.culture_system
                
                for district_id, region in sim.world_map.regions.items():
                    economy = sim.economy_system.get_district(district_id)
                    if economy:
                        district_dict = {
                            "id": district_id,
                            "name": economy.district_name,
                            "food_stock": economy.food_stock,
                            "tension": economy.tension,
                            "jobs_available": economy.jobs_available,
                            "scarcity": economy.scarcity
                        }
                        # Add culture if available
                        if culture_system:
                            culture = culture_system.get_culture(district_id)
                            if culture:
                                district_dict["culture"] = culture.to_dict()
                        districts.append(district_dict)
        
        # Get agents (alive agents only for main state)
        agents = []
        if sim.human_agent_system:
            # Check if agents dict exists (even if empty)
            if not hasattr(sim.human_agent_system, 'agents'):
                # System exists but agents dict missing - this shouldn't happen
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("human_agent_system exists but has no 'agents' attribute")
            elif sim.human_agent_system.agents:
                # Include all agents from agents dict (alive agents)
                # The agents dict only contains alive agents (dead ones are moved to dead_agents)
                for agent in sim.human_agent_system.agents.values():
                    # Include agent (all in agents dict should be alive, but check for safety)
                    if not hasattr(agent, 'is_alive') or getattr(agent, 'is_alive', True):
                        # Get agent intent
                        agent_intent = None
                        if hasattr(agent, 'intent'):
                            agent_intent = agent.intent.to_dict()
                        elif hasattr(sim, 'agent_system') and sim.agent_system:
                            # Try to get from agent_system
                            world_agent = sim.agent_system.get_agent(agent.id)
                            if world_agent and hasattr(world_agent, 'intent'):
                                agent_intent = world_agent.intent.to_dict()
                        
                        # Get agent beliefs
                        agent_beliefs = {}
                        if hasattr(agent, 'beliefs'):
                            agent_beliefs = {
                                topic: belief.to_dict() 
                                for topic, belief in agent.beliefs.items()
                            }
                        
                        # Get agent relationships
                        agent_relationships = {}
                        if hasattr(agent, 'relationships'):
                            agent_relationships = {
                                target_id: rel.to_dict() 
                                for target_id, rel in agent.relationships.items()
                            }
                        
                        agents.append({
                            "id": agent.id,
                            "name": agent.name,
                            "district": agent.district,
                            "location": agent.location,
                            "role": agent.role,
                            "sex": getattr(agent, 'sex', 'unknown'),  # Add sex field
                            "age": getattr(agent, 'age', 0),
                            "lifespan": getattr(agent, 'lifespan', 1000),
                            "is_alive": getattr(agent, 'is_alive', True),
                            "children_ids": getattr(agent, 'children_ids', []),
                            "parents_ids": getattr(agent, 'parents_ids', []),
                            "needs": {
                                "hunger": agent.needs.hunger,
                                "rest": agent.needs.rest,
                                "safety": agent.needs.safety,
                                "belonging": agent.needs.belonging,
                                "purpose": agent.needs.purpose
                            },
                            "mood": agent.mood,
                            "goals": agent.goals,
                            "current_action": agent.current_action,
                            "intent": agent_intent,  # New intent
                            "beliefs": agent_beliefs,  # New beliefs
                            "relationships": agent_relationships,  # New relationships
                            "inventory": {
                                "food": agent.inventory.food,
                                "credits": agent.inventory.credits,
                                "tools": agent.inventory.tools
                            },
                            # Survival drives (SYSTEM 10)
                            "survival_drive": getattr(agent, 'survival_drive', 0.8),
                            "reproduction_drive": getattr(agent, 'reproduction_drive', 0.5),
                            "legacy_drive": getattr(agent, 'legacy_drive', 0.3),
                            "must_attempt_reproduction": getattr(agent, 'must_attempt_reproduction', False),
                            "future_resource_bonus": getattr(agent, 'future_resource_bonus', 0.0)
                        })
        
        # Get events
        events = []
        if hasattr(sim, '_last_human_events'):
            for event_tuple in sim._last_human_events[-20:]:  # Last 20 events
                if len(event_tuple) >= 2:
                    events.append({
                        "agent_id": event_tuple[0] if len(event_tuple) > 0 else None,
                        "description": event_tuple[1] if len(event_tuple) > 1 else str(event_tuple[0]),
                        "type": event_tuple[2] if len(event_tuple) > 2 else None,
                        "turn": sim.world.state.turn  # Add turn number for tracking
                    })
        
        # Get economy/world summary
        economy = {}
        world_dynamics = getattr(sim, 'world_dynamics_system', None)
        
        if world_dynamics:
            districts_list = world_dynamics.get_all_districts()
            total_food = sum(d.food_stock for d in districts_list)
            total_credits = sum(d.credits_pool for d in districts_list)
            avg_tension = sum(d.tension_state.tension for d in districts_list) / len(districts_list) if districts_list else 0
            
            # Get hotspots (top 3 by tension)
            hotspots = sorted(
                [(d.district_name, d.tension_state.tension) for d in districts_list],
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            # Get active events
            active_event_types = set()
            for d in districts_list:
                for event in d.active_events:
                    active_event_types.add(event.event_type.value)
            
            # System health
            high_tension_count = sum(1 for d in districts_list if d.tension_state.tension > 85)
            if high_tension_count >= len(districts_list) * 0.7:
                stability = "degrading"
                risk_level = "critical"
            elif high_tension_count >= len(districts_list) * 0.4:
                stability = "degrading"
                risk_level = "high"
            elif high_tension_count > 0:
                stability = "stable"
                risk_level = "moderate"
            else:
                stability = "recovering"
                risk_level = "low"
            
            # POPULATION COMPRESSION: Get global population metrics
            global_active_agents = len([a for a in sim.human_agent_system.agents.values() if a.is_alive]) if sim.human_agent_system else 0
            global_child_pool = sum(sim.human_agent_system.child_pools.values()) if sim.human_agent_system else 0
            global_total_population = global_active_agents + global_child_pool
            global_population_pressure = sim.world.state.population_pressure if hasattr(sim.world.state, 'population_pressure') else 0.0
            civilization_phase = sim.world.state.civilization_phase if hasattr(sim.world.state, 'civilization_phase') else "unknown"
            
            economy = {
                "total_food": round(total_food, 1),
                "total_credits": round(total_credits, 1),
                "average_tension": round(avg_tension, 1),
                "global_tension_index": round(avg_tension / 100.0, 2),
                "district_count": len(districts_list),
                "hotspots": [{"district": name, "tension": round(t, 1)} for name, t in hotspots],
                "active_events": list(active_event_types),
                "system_health": {
                    "stability": stability,
                    "risk_level": risk_level
                },
                # POPULATION COMPRESSION: Add global population metrics
                "active_agents": global_active_agents,
                "child_pool": global_child_pool,
                "total_population": global_total_population,
                "population_pressure": round(global_population_pressure, 3),
                "civilization_phase": civilization_phase
            }
        elif sim.economy_system:
            # Fallback to old economy system
            districts_list = sim.economy_system.get_all_districts()
            total_food = sum(d.food_stock for d in districts_list)
            total_credits = sum(d.credits_pool for d in districts_list)
            avg_tension = sum(d.tension for d in districts_list) / len(districts_list) if districts_list else 0
            scarcity_count = sum(1 for d in districts_list if d.scarcity)
            
            economy = {
                "total_food": total_food,
                "total_credits": total_credits,
                "average_tension": avg_tension,
                "scarcity_count": scarcity_count,
                "district_count": len(districts_list)
            }
        
        # Build state with enhanced data
        state_data = {
            "turn": sim.world.state.turn,
            "day": day,
            "time": time_str,
            "weather": weather_str,
            "districts": districts,
            "agents": agents,
            "events": events,
            "economy": economy,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add detailed weather if available
        if weather_detail:
            state_data["weather_detail"] = weather_detail
        
        # Create MatrixState (handle optional weather_detail)
        return MatrixState(
            turn=state_data["turn"],
            day=state_data["day"],
            time=state_data["time"],
            weather=state_data["weather"],
            districts=state_data["districts"],
            agents=state_data["agents"],
            events=state_data["events"],
            economy=state_data["economy"],
            timestamp=state_data["timestamp"],
            weather_detail=state_data.get("weather_detail")
        )
    
    def _log_statistics(self):
        """Log simulation statistics to console every 10 seconds."""
        sim = self.simulation
        try:
            # Get turn
            turn = sim.world.state.turn if sim.world.state else 0
            
            # Get day
            day = 0
            if sim.time_system:
                day = sim.time_system.day_index
            
            # Get agent count
            agent_count = 0
            child_pool = 0
            if sim.human_agent_system:
                agent_count = len([a for a in sim.human_agent_system.agents.values() if a.is_alive])
                child_pool = sum(sim.human_agent_system.child_pools.values())
            
            # Get district count
            district_count = 0
            if sim.world_map:
                district_count = len(sim.world_map.regions)
            
            # Get total population
            total_population = agent_count + child_pool
            
            # Get current timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Format and print
            print(f"[STATS] Turn: {turn} | Day: {day} | Agents: {agent_count} | Children: {child_pool} | Total Pop: {total_population} | Districts: {district_count} | {timestamp}")
        except Exception as e:
            # Don't crash on logging errors
            print(f"[STATS] Error logging statistics: {e}")
    
    def _update_ai_systems_data(self):
        """Update AI systems data in state store (causality, emotions, rules)."""
        sim = self.simulation
        
        # Update causality data
        if hasattr(sim, 'causality_system'):
            recent_records = sim.causality_system.get_recent(limit=100)
            causality_data = {
                'records': [r.to_dict() for r in recent_records],
                'total_records': len(sim.causality_system.records)
            }
            self.state_store.set_causality_data(causality_data)
        
        # Update emotional memory data
        if hasattr(sim, 'emotional_memory'):
            emotional_data = {
                'summary': sim.emotional_memory.get_emotion_summary(),
                'recent_traces': [t.to_dict() for t in sim.emotional_memory.get_recent(limit=50)],
                'total_traces': len(sim.emotional_memory.traces)
            }
            self.state_store.set_emotional_data(emotional_data)
        
        # Update learned rules data
        if hasattr(sim, 'learned_rules'):
            rules_data = {
                'rules': [r.to_dict() for r in sim.learned_rules.rules],
                'total_rules': len(sim.learned_rules.rules)
            }
            self.state_store.set_learned_rules_data(rules_data)
        
        # Update world flags data
        if hasattr(sim, 'world_flags_system'):
            flags = sim.world_flags_system.get_all_flags()
            flags_data = {
                'flags': [f.to_dict() for f in flags],
                'count': len(flags)
            }
            self.state_store.set_world_flags_data(flags_data)
        
        # Update escalation chains data
        if hasattr(sim, 'escalation_system'):
            active_chains = sim.escalation_system.get_active_chains()
            all_chains = list(sim.escalation_system.chains.values())
            escalation_data = {
                'chains': [c.to_dict() for c in active_chains],
                'active_count': len(active_chains),
                'total_chains': len(all_chains)
            }
            self.state_store.set_escalation_data(escalation_data)
        
        # Update culture data
        if hasattr(sim, 'world_dynamics_system') and hasattr(sim.world_dynamics_system, 'culture_system'):
            cultures = {}
            for district_id in sim.world_map.regions.keys() if sim.world_map else []:
                culture = sim.world_dynamics_system.culture_system.get_culture(district_id)
                if culture:
                    cultures[district_id] = culture.to_dict()
            culture_data = {
                'cultures': cultures
            }
            self.state_store.set_culture_data(culture_data)
        
        # Update death counts
        if hasattr(sim, 'human_agent_system') and sim.human_agent_system:
            death_counts = sim.human_agent_system.death_counts.copy() if hasattr(sim.human_agent_system, 'death_counts') else {}
            self.state_store.set_death_counts(death_counts)
    
    def _submit_gemini_snapshot(self):
        """
        Submit state snapshot to Gemini worker for image generation.
        
        Submits snapshots periodically (every 60 seconds wall-clock time).
        The worker decides when to actually generate images based on
        REAL-WORLD hours, not simulation time.
        
        IMPORTANT: This is OBSERVATIONAL ONLY - it reads simulation state
        but never modifies it. Image generation happens in background.
        """
        if self._gemini_worker is None:
            return
        
        # Only submit every N seconds (wall-clock time)
        current_time = time.time()
        if current_time - self._last_gemini_submit_time < self._gemini_submit_interval:
            return
        
        sim = self.simulation
        
        try:
            # Create lightweight snapshot for Gemini (different from full state)
            from living_matrix.gemini.snapshot import create_state_snapshot
            snapshot = create_state_snapshot(sim, self.state_store)
            
            if snapshot:
                # Submit to worker (non-blocking) - worker decides when to generate
                submitted = self._gemini_worker.submit_snapshot(snapshot)
                if submitted:
                    self._last_gemini_submit_time = current_time
                    # Log at info level to confirm snapshots are being sent
                    print(f"[GEMINI] Snapshot submitted (Turn {snapshot.simulation_turn}, Day {snapshot.simulation_day}, Pop {snapshot.global_population})")
            else:
                print("[GEMINI] Failed to create snapshot")
        except Exception as e:
            # Gemini is optional - don't crash simulation
            print(f"[GEMINI] Error submitting snapshot: {e}")