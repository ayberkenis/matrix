"""Background runner for Living Matrix world simulation."""

import asyncio
import threading
import time
from typing import Optional
from datetime import datetime
from living_matrix.core.ipc import MatrixStateStore, MatrixCommandQueue, MatrixState, MatrixCommand


class WorldRunner:
    """Runs Living Matrix world simulation in background."""
    
    def __init__(self, simulation, state_store: MatrixStateStore, command_queue: MatrixCommandQueue):
        """
        Initialize world runner.
        
        Args:
            simulation: Simulation instance
            state_store: State store for snapshots
            command_queue: Command queue for API commands
        """
        self.simulation = simulation
        self.state_store = state_store
        self.command_queue = command_queue
        
        self.running = False
        self.paused = False
        self.tick_rate_ms = 50  # Default 50ms per tick
        self._runner_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Initialize simulation
        self.simulation.initialize()
    
    def start(self):
        """Start the background runner."""
        if self.running:
            return
        
        self.running = True
        self.paused = False
        self._stop_event.clear()
        
        # Start runner thread
        self._runner_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._runner_thread.start()
    
    def stop(self):
        """Stop the background runner gracefully."""
        self.running = False
        self._stop_event.set()
        
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
        elif command.command == "inject_event":
            # Future: inject custom event
            pass
    
    def _tick(self):
        """Execute one simulation tick and update state store."""
        # Advance simulation
        self.simulation.step(autonomous=True)
        
        # Create state snapshot
        state = self._create_state_snapshot()
        
        # Update state store
        self.state_store.update(state)
    
    def _create_state_snapshot(self) -> MatrixState:
        """Create a read-only state snapshot."""
        sim = self.simulation
        
        # Get time
        day = 0
        time_str = "00:00"
        if sim.time_system:
            day = sim.time_system.day_index
            time_str = sim.time_system.format_time()
        
        # Get weather
        weather_str = "Unknown"
        if sim.weather_system:
            weather_str = sim.weather_system.format_weather_line()
        
        # Get districts
        districts = []
        if sim.world_map and sim.economy_system:
            for district_id, region in sim.world_map.regions.items():
                economy = sim.economy_system.get_district(district_id)
                if economy:
                    districts.append({
                        "id": district_id,
                        "name": economy.district_name,
                        "food_stock": economy.food_stock,
                        "tension": economy.tension,
                        "jobs_available": economy.jobs_available,
                        "scarcity": economy.scarcity
                    })
        
        # Get agents
        agents = []
        if sim.human_agent_system:
            for agent in sim.human_agent_system.agents.values():
                agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "district": agent.district,
                    "location": agent.location,
                    "role": agent.role,
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
                    "inventory": {
                        "food": agent.inventory.food,
                        "credits": agent.inventory.credits,
                        "tools": agent.inventory.tools
                    }
                })
        
        # Get events
        events = []
        if hasattr(sim, '_last_human_events'):
            for event_tuple in sim._last_human_events[-20:]:  # Last 20 events
                if len(event_tuple) >= 2:
                    events.append({
                        "agent_id": event_tuple[0] if len(event_tuple) > 0 else None,
                        "description": event_tuple[1] if len(event_tuple) > 1 else str(event_tuple[0]),
                        "type": event_tuple[2] if len(event_tuple) > 2 else None
                    })
        
        # Get economy summary
        economy = {}
        if sim.economy_system:
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
        
        return MatrixState(
            turn=sim.world.state.turn,
            day=day,
            time=time_str,
            weather=weather_str,
            districts=districts,
            agents=agents,
            events=events,
            economy=economy,
            timestamp=datetime.now().isoformat()
        )
