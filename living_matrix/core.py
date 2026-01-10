"""Main simulation loop and command processing."""

import sys
import json
import time
import threading
import random
from pathlib import Path
from typing import Optional, Tuple, List

from .world import World
from .agents import Coordinator
from .metrics import MetricsTracker
from .ui import (
    format_status_line, format_output, print_help, print_drives,
    print_inspect_token, print_inspect_cluster, print_prompt,
    print_tensor_stats, print_world_state, print_embed_neighbors
)
from .grammar import tokenize
from .world_sim import (
    TimeSystem, WorldMap, WeatherSystem, AgentSystem, EventSystem, WorldSimState
)
from .world_sim.bulletin import format_world_bulletin
from .world_sim.consequence import ConsequenceSystem
from .human_agent import HumanAgentSystem
from .economy import EconomySystem
from .camera import Camera, CameraMode
from .ui_panels import UIPanels, UISettings


class Simulation:
    """Main simulation controller."""
    
    def __init__(self, data_dir: str = "data", autopilot_enabled: bool = True):
        self.world = World(data_dir)
        self.coordinator = Coordinator()
        self.metrics = MetricsTracker()
        self.auto_save_interval = 10  # Save every N turns
        self.running = True
        self.debug_mode = False
        self._low_diversity_turns = 0  # Track consecutive low diversity turns
        
        # World simulation components
        self.world_sim_state = WorldSimState(data_dir)
        self.time_system: Optional[TimeSystem] = None
        self.world_map: Optional[WorldMap] = None
        self.weather_system: Optional[WeatherSystem] = None
        self.agent_system: Optional[AgentSystem] = None
        self.event_system: Optional[EventSystem] = None
        self.consequence_system: Optional[ConsequenceSystem] = None
        
        # New systems
        self.human_agent_system: Optional[HumanAgentSystem] = None
        self.economy_system: Optional[EconomySystem] = None
        self.world_dynamics_system = None  # Advanced world dynamics (replaces economy for tension/pressure)
        self.camera = Camera()
        self.ui_panels = UIPanels()
        
        # Advanced AI systems
        from living_matrix.causality import CausalitySystem
        from living_matrix.memory import EmotionalMemory, LearnedRulesSystem
        from living_matrix.entropy import EntropySystem
        from living_matrix.world_pressure import WorldPressureSystem
        
        self.causality_system = CausalitySystem()
        self.emotional_memory = EmotionalMemory()
        self.learned_rules = LearnedRulesSystem()
        self.entropy_system = EntropySystem(seed=self.world.state.seed if self.world.state else 42)
        self.world_pressure_system = WorldPressureSystem()
        
        # Observation effect tracking
        self.observation_count = 0
        self.last_observation_turn = 0
        
        # Autopilot settings
        self.autopilot = autopilot_enabled
        self.tick_delay_ms = 50  # milliseconds between autonomous ticks (default 50ms)
        self.bulletin_interval = 5  # Print bulletin every N turns
        self.follow_agent_id: Optional[str] = None  # Agent to follow
        self.world_turn_counter = 0  # Track world turns for bulletin
        self._last_human_events: List = []  # Store human agent events for rendering
    
    def initialize(self):
        """Initialize simulation state."""
        self.world.load()
        
        # Initialize world simulation
        self._initialize_world_simulation()
        
        print("Living Matrix initialized.")
        if self.autopilot:
            print("Autonomous mode: ON (world simulation running)")
        else:
            print("Autonomous mode: OFF (use /run to start)")
        print("Type /help for commands, or enter text as stimulus.")
        print()
    
    def _initialize_world_simulation(self):
        """Initialize or load world simulation components."""
        # Try to load existing state
        loaded = self.world_sim_state.load(seed=self.world.state.seed)
        
        if loaded:
            self.time_system, self.world_map, self.weather_system, \
                self.agent_system, self.event_system = loaded
            self.consequence_system = ConsequenceSystem(seed=self.world.state.seed)
            
            # Initialize new systems (even if loaded, we need them)
            district_ids = list(self.world_map.regions.keys())
            location_ids = list(self.world_map.locations.keys())
            if not self.human_agent_system:
                self.human_agent_system = HumanAgentSystem(
                    districts=district_ids,
                    locations=location_ids,
                    num_agents=random.randint(12, 30),
                    seed=self.world.state.seed
                )
            if not self.economy_system:
                self.economy_system = EconomySystem(districts=district_ids, seed=self.world.state.seed)
        else:
            # Create new world simulation
            self.time_system = TimeSystem(seed=self.world.state.seed)
            self.world_map = WorldMap(seed=self.world.state.seed)
            
            region_ids = list(self.world_map.regions.keys())
            self.weather_system = WeatherSystem(region_ids, seed=self.world.state.seed)
            
            location_ids = list(self.world_map.locations.keys())
            num_agents = random.randint(8, 24)  # 8-24 agents as specified
            self.agent_system = AgentSystem(location_ids, num_agents=num_agents, seed=self.world.state.seed)
            
            self.event_system = EventSystem(seed=self.world.state.seed)
            self.consequence_system = ConsequenceSystem(seed=self.world.state.seed)
            
            # Initialize new systems
            district_ids = list(self.world_map.regions.keys())
            location_ids = list(self.world_map.locations.keys())
            self.human_agent_system = HumanAgentSystem(
                districts=district_ids,
                locations=location_ids,
                num_agents=random.randint(12, 30),
                seed=self.world.state.seed
            )
            self.economy_system = EconomySystem(districts=district_ids, seed=self.world.state.seed)
    
    def process_command(self, line: str) -> bool:
        """
        Process a command. Returns True if command was handled.
        
        Args:
            line: Input line
            
        Returns:
            True if command was handled, False if should be treated as stimulus
        """
        line = line.strip()
        
        if not line.startswith("/"):
            return False
        
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            print_help()
            return True
        
        elif cmd == "/seed":
            try:
                seed = int(args)
                self.world.set_seed(seed)
                print(f"Seed set to {seed}")
            except ValueError:
                print("Error: /seed requires an integer argument")
            return True
        
        elif cmd == "/reset":
            confirm = input("Are you sure you want to reset? (yes/no): ").strip().lower()
            if confirm == "yes":
                self.world.reset()
                self.metrics.reset()
                print("World reset.")
            else:
                print("Reset cancelled.")
            return True
        
        elif cmd == "/save":
            self.world.save()
            print("State saved.")
            return True
        
        elif cmd == "/load":
            self.world.load()
            self.metrics.reset()
            print("State reloaded.")
            return True
        
        elif cmd == "/inspect":
            parts2 = args.split(None, 1)
            if len(parts2) < 2:
                print("Usage: /inspect token <word> or /inspect cluster <word>")
                return True
            
            subcmd = parts2[0].lower()
            word = parts2[1].strip()
            
            if subcmd == "token":
                print_inspect_token(word, self.world.state.semantic_graph)
            elif subcmd == "cluster":
                print_inspect_cluster(word, self.world.state.semantic_graph)
            else:
                print("Usage: /inspect token <word> or /inspect cluster <word>")
            return True
        
        elif cmd == "/drives":
            print_drives(self.world.state.drives)
            return True
        
        elif cmd == "/debug":
            if args.lower() == "on":
                self.debug_mode = True
                print("Debug mode ON")
            elif args.lower() == "off":
                self.debug_mode = False
                print("Debug mode OFF")
            else:
                print("Usage: /debug on|off")
            return True
        
        elif cmd == "/step":
            try:
                n = int(args) if args else 1
                for _ in range(n):
                    self.step(autonomous=True)
            except ValueError:
                print("Error: /step requires an integer argument")
            return True
        
        elif cmd == "/tensor":
            if not self.world.state.tensor_cognition:
                print("Tensor cognition not initialized.")
                return True
            # Calculate current temperature for display
            diversity = self.metrics.get_diversity()
            coherence = self.metrics.get_coherence(self.world.state.semantic_graph.edges)
            temp_novelty = 0.0  # Approximate for display
            base_temp = 1.0
            if temp_novelty < 0.15:
                base_temp += 0.2
            if diversity < 0.2:
                base_temp += 0.2
            if coherence < 0.25:
                base_temp -= 0.1
            temperature = max(0.7, min(1.6, base_temp))
            print_tensor_stats(self.world.state.tensor_cognition, temperature=temperature)
            return True
        
        elif cmd == "/state":
            if not self.world.state.tensor_cognition:
                print("Tensor cognition not initialized.")
                return True
            stability = self.world.state.drives.stability
            print_world_state(self.world.state.tensor_cognition, stability=stability)
            return True
        
        elif cmd == "/embed":
            if not args:
                print("Usage: /embed <token>")
            else:
                print_embed_neighbors(self.world.state.tensor_cognition, args.strip())
            return True
        
        elif cmd == "/freeze":
            if self.world.state.tensor_cognition:
                self.world.state.tensor_cognition.learning_frozen = True
                print("Tensor learning frozen.")
            else:
                print("Tensor cognition not initialized.")
            return True
        
        elif cmd == "/thaw":
            if self.world.state.tensor_cognition:
                self.world.state.tensor_cognition.learning_frozen = False
                print("Tensor learning resumed.")
            else:
                print("Tensor cognition not initialized.")
            return True
        
        elif cmd == "/export":
            self.export_graph()
            return True
        
        elif cmd == "/silent":
            self.world.state.silence_mode = True
            print("Silence mode enabled. System will continue thinking but suppress output.")
            return True
        
        elif cmd == "/speak":
            self.world.state.silence_mode = False
            print("Silence mode disabled. System will resume visible output.")
            return True
        
        elif cmd == "/pulse":
            # Force world bulletin and one visible output now
            if self.time_system and self.world_map and self.weather_system and \
               self.event_system and self.agent_system:
                print("\n" + "="*50)
                print(format_world_bulletin(
                    self.time_system, self.world_map, self.weather_system,
                    self.event_system, self.follow_agent_id, self.agent_system
                ))
                print("="*50 + "\n")
            self.step(autonomous=True, force_speak=True)
            return True
        
        elif cmd == "/status":
            # Show drives + tensor stats without generating text
            state = self.world.state
            diversity = self.metrics.get_diversity()
            coherence = self.metrics.get_coherence(state.semantic_graph.edges)
            print(f"Turn: {state.turn}")
            print_drives(state.drives)
            print(f"Diversity: {diversity:.3f}, Coherence: {coherence:.3f}")
            if state.tensor_cognition:
                temp_diversity = self.metrics.get_diversity()
                temp_coherence = self.metrics.get_coherence(state.semantic_graph.edges)
                base_temp = 1.0
                if temp_diversity < 0.2:
                    base_temp += 0.2
                if temp_coherence < 0.25:
                    base_temp -= 0.1
                temperature = max(0.7, min(1.6, base_temp))
                print_tensor_stats(state.tensor_cognition, temperature=temperature)
            print(f"Silence mode: {state.silence_mode}")
            if state.last_stimulus_turn > 0:
                turns_since_stimulus = state.turn - state.last_stimulus_turn
                print(f"Last stimulus: {turns_since_stimulus} turns ago")
            return True
        
        elif cmd == "/run":
            self.autopilot = True
            print("Autonomous mode ON")
            return True
        
        elif cmd == "/pause":
            self.autopilot = False
            print("Autonomous mode PAUSED")
            return True
        
        elif cmd == "/auto":
            if args and args.strip().lower() == "off":
                self.autopilot = False
                print("Autonomous mode OFF")
            else:
                self.autopilot = True
                print("Autonomous mode ON")
            return True
        
        elif cmd == "/sanity":
            """Run sanity checks: 200 steps headless, assert no NaNs, resources bounded, events occurred."""
            print("Running sanity checks (200 steps)...")
            original_autopilot = self.autopilot
            self.autopilot = False  # Disable autopilot for testing
            
            try:
                for i in range(200):
                    self.step(autonomous=True)
                    if i % 20 == 0:
                        print(f"  Step {i}...")
                
                # Check resources
                if self.world_map:
                    for region in self.world_map.regions.values():
                        assert 0 <= region.food <= 100, f"Region {region.name} food out of bounds: {region.food}"
                        assert 0 <= region.materials <= 100, f"Region {region.name} materials out of bounds: {region.materials}"
                        assert 0 <= region.energy <= 100, f"Region {region.name} energy out of bounds: {region.energy}"
                        assert 0 <= region.tension <= 1, f"Region {region.name} tension out of bounds: {region.tension}"
                
                # Check events occurred
                if self.event_system:
                    recent = self.event_system.get_recent_events(n=10)
                    assert len(recent) > 0, "No events occurred during sanity check"
                
                # Check diversity
                diversity = self.metrics.get_diversity()
                assert diversity > 0.05, f"Diversity too low: {diversity}"
                
                print("✓ All sanity checks passed!")
                print(f"  Final diversity: {diversity:.3f}")
                print(f"  Events: {len(self.event_system.get_recent_events(n=100))}")
                
            except AssertionError as e:
                print(f"✗ Sanity check failed: {e}")
            finally:
                self.autopilot = original_autopilot
            
            return True
        
        elif cmd == "/speed":
            if args:
                try:
                    delay_ms = int(args.strip())
                    if delay_ms < 0:
                        print("Delay must be >= 0 milliseconds")
                    else:
                        self.tick_delay_ms = delay_ms
                        print(f"Tick delay set to {self.tick_delay_ms}ms")
                except ValueError:
                    print("Usage: /speed <milliseconds>")
            else:
                print(f"Current tick delay: {self.tick_delay_ms}ms")
            return True
        
        elif cmd == "/device":
            """Show current PyTorch device (CPU/CUDA)."""
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                print(f"Device: CUDA ({device_name})")
            else:
                print("Device: CPU")
            return True
        
        elif cmd == "/tick" or cmd == "/step":
            # Advance world simulation by N turns
            num_turns = 1
            if args:
                try:
                    num_turns = int(args.strip())
                except ValueError:
                    print("Usage: /tick <n> or /step <n>")
                    return True
            
            for _ in range(num_turns):
                self.step(autonomous=True)
            return True
        
        elif cmd == "/time":
            if self.time_system:
                print(self.time_system.format_time())
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/weather":
            if self.weather_system:
                print(self.weather_system.format_weather_line())
                # Show per-region if requested
                if args and args.strip().lower() == "all":
                    for region_id, weather in self.weather_system.region_weather.items():
                        region = self.world_map.get_region(region_id) if self.world_map else None
                        region_name = region.name if region else region_id
                        print(f"{region_name}: {self.weather_system.format_weather_line(region_id)}")
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/map":
            if self.world_map:
                for region_id, region in self.world_map.regions.items():
                    print(f"\n{region.name}:")
                    for loc in region.locations:
                        print(f"  - {loc.name} ({loc.type_tag})")
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/where":
            if self.world_map:
                hotspots = self.world_map.get_hotspots(top_n=10)
                if hotspots:
                    print("Current hotspots:")
                    for loc, density in hotspots:
                        crowd_size = int(density * 15)
                        print(f"  {loc.name}: {crowd_size} people")
                else:
                    print("No active hotspots.")
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/events":
            if self.event_system:
                recent = self.event_system.get_recent_events(n=10)
                if recent:
                    print("Recent events:")
                    for event in recent:
                        print(f"  [{event.turn}] {event.description}")
                else:
                    print("No events yet.")
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/agents":
            # Show human agents (new system)
            if self.human_agent_system:
                agents = list(self.human_agent_system.agents.values())
                print(f"Human Agents ({len(agents)}):")
                print(f"{'ID':<12} {'Name':<12} {'District':<12} {'Role':<10} {'Hunger':<8} {'Mood':<8}")
                print("-" * 70)
                for agent in agents[:20]:  # Show first 20
                    needs = agent.needs
                    print(f"{agent.id:<12} {agent.name:<12} {agent.district[:11]:<12} {agent.role:<10} {needs.hunger:<8} {agent.mood:+.2f}")
                if len(agents) > 20:
                    print(f"... and {len(agents) - 20} more")
            elif self.agent_system:
                # Fallback to old system
                role_counts = {}
                for agent in self.agent_system.agents.values():
                    role_counts[agent.role] = role_counts.get(agent.role, 0) + 1
                
                print("Agents by role:")
                for role, count in sorted(role_counts.items()):
                    print(f"  {role}: {count}")
                
                # Top crowded locations
                if self.world_map:
                    hotspots = self.world_map.get_hotspots(top_n=5)
                    if hotspots:
                        print("\nTop crowded locations:")
                        for loc, density in hotspots:
                            agents_at = self.agent_system.get_agents_at_location(loc.id)
                            print(f"  {loc.name}: {len(agents_at)} agents")
            else:
                print("World simulation not initialized.")
            return True
        
        elif cmd == "/agent":
            if not args:
                print("Usage: /agent <id|name>")
                return True
            
            # Try human agent system first
            if self.human_agent_system:
                agent = self.human_agent_system.get_agent(args.strip())
                if not agent:
                    agent = self.human_agent_system.get_agent_by_name(args.strip())
                
                if agent:
                    # Print detailed agent info
                    print(f"\nAgent: {agent.name} ({agent.id})")
                    print(f"Role: {agent.role} | District: {agent.district} | Location: {agent.location}")
                    print(f"\nNeeds:")
                    print(f"  Hunger: {agent.needs.hunger}/100")
                    print(f"  Rest: {agent.needs.rest}/100")
                    print(f"  Safety: {agent.needs.safety}/100")
                    print(f"  Belonging: {agent.needs.belonging}/100")
                    print(f"  Purpose: {agent.needs.purpose}/100")
                    print(f"\nTraits:")
                    print(f"  Risk: {agent.traits.risk:.2f}")
                    print(f"  Empathy: {agent.traits.empathy:.2f}")
                    print(f"  Ambition: {agent.traits.ambition:.2f}")
                    print(f"  Patience: {agent.traits.patience:.2f}")
                    print(f"\nInventory:")
                    print(f"  Food: {agent.inventory.food}")
                    print(f"  Credits: {agent.inventory.credits}")
                    print(f"  Tools: {agent.inventory.tools}")
                    print(f"\nMood: {agent.mood:+.2f}")
                    print(f"Current Action: {agent.current_action}")
                    print(f"Goals: {', '.join(agent.goals)}")
                    if agent.memory:
                        print(f"\nRecent Memory:")
                        for mem in list(agent.memory)[-5:]:
                            print(f"  • {mem}")
                    return True
            
            # Fallback to old agent system
            if not self.agent_system:
                print("World simulation not initialized.")
                return True
            
            # Try to find agent
            agent = self.agent_system.get_agent(args.strip())
            if not agent:
                agent = self.agent_system.get_agent_by_name(args.strip())
            
            if agent:
                loc = self.world_map.get_location(agent.current_location) if self.world_map else None
                home_loc = self.world_map.get_location(agent.home_location) if self.world_map else None
                
                print(f"\nAgent: {agent.name} ({agent.id})")
                print(f"Role: {agent.role}")
                print(f"Location: {loc.name if loc else agent.current_location}")
                print(f"Home: {home_loc.name if home_loc else agent.home_location}")
                print(f"Schedule: {agent.schedule}")
                print(f"\nNeeds:")
                print(f"  Rest: {agent.needs.rest:.2f}, Food: {agent.needs.food:.2f}")
                print(f"  Safety: {agent.needs.safety:.2f}, Social: {agent.needs.social:.2f}, Purpose: {agent.needs.purpose:.2f}")
                print(f"\nMood:")
                print(f"  Calm: {agent.mood.calm:.2f}, Tense: {agent.mood.tense:.2f}, Curious: {agent.mood.curious:.2f}")
                print(f"\nRelationships: {len(agent.relationships)}")
                print(f"\nRecent memory:")
                for mem in list(agent.memory)[-5:]:
                    print(f"  - {mem}")
            else:
                print(f"Agent not found: {args.strip()}")
            return True
        
        elif cmd == "/follow":
            if not args:
                print("Usage: /follow <id|name>")
                return True
            
            if not self.agent_system:
                print("World simulation not initialized.")
                return True
            
            # Try to find agent
            agent = self.agent_system.get_agent(args.strip())
            if not agent:
                agent = self.agent_system.get_agent_by_name(args.strip())
            
            if agent:
                self.follow_agent_id = agent.id
                print(f"Now following: {agent.name} ({agent.role})")
            else:
                print(f"Agent not found: {args.strip()}")
            return True
        
        elif cmd == "/unfollow":
            self.follow_agent_id = None
            print("Stopped following.")
            return True
        
        elif cmd == "/districts":
            """List district stats (food_stock, tension, jobs)."""
            if not self.economy_system or not self.world_map:
                print("Economy system not initialized.")
                return True
            
            print("Districts:")
            print(f"{'District':<15} {'Food':<8} {'Tension':<10} {'Jobs':<8} {'Scarcity':<10}")
            print("-" * 60)
            for district in self.economy_system.get_all_districts():
                scarcity_str = "YES" if district.scarcity else "NO"
                print(f"{district.district_name:<15} {district.food_stock:<8} {district.tension:<10} {district.jobs_available:<8} {scarcity_str:<10}")
            return True
        
        elif cmd == "/economy":
            """Global economy snapshot."""
            if not self.economy_system:
                print("Economy system not initialized.")
                return True
            
            districts = self.economy_system.get_all_districts()
            total_food = sum(d.food_stock for d in districts)
            total_credits = sum(d.credits_pool for d in districts)
            avg_tension = sum(d.tension for d in districts) / len(districts) if districts else 0
            scarcity_count = sum(1 for d in districts if d.scarcity)
            
            print("Global Economy:")
            print(f"  Total Food Stock: {total_food}")
            print(f"  Total Credits Pool: {total_credits}")
            print(f"  Average Tension: {avg_tension:.1f}")
            print(f"  Districts with Scarcity: {scarcity_count}/{len(districts)}")
            return True
        
        elif cmd == "/cam" or cmd == "/camera":
            """Camera controls."""
            if not args:
                print(f"Current camera mode: {self.camera.get_mode_string()}")
                return True
            
            parts = args.strip().split(None, 1)
            mode = parts[0].lower()
            target = parts[1] if len(parts) > 1 else None
            
            if self.camera.set_mode(mode, target):
                print(f"Camera mode: {self.camera.get_mode_string()}")
            else:
                print("Usage: /cam [god|district <name>|agent <id|name>|place <name>]")
            return True
        
        elif cmd == "/ui":
            """UI controls."""
            if not args:
                print(f"UI enabled: {self.ui_panels.settings.enabled}")
                print(f"Clear screen: {self.ui_panels.settings.clear_screen}")
                print(f"Mode: {self.ui_panels.settings.mode}")
                print(f"FPS limit: {self.ui_panels.settings.fps_limit}")
                return True
            
            parts = args.strip().split()
            subcmd = parts[0].lower()
            
            if subcmd == "on":
                self.ui_panels.settings.enabled = True
                print("UI enabled")
            elif subcmd == "off":
                self.ui_panels.settings.enabled = False
                print("UI disabled")
            elif subcmd == "clear":
                if len(parts) > 1:
                    clear_val = parts[1].lower()
                    self.ui_panels.settings.clear_screen = (clear_val == "on")
                    print(f"Clear screen: {self.ui_panels.settings.clear_screen}")
                else:
                    print("Usage: /ui clear [on|off]")
            elif subcmd == "mode":
                if len(parts) > 1:
                    mode_val = parts[1].lower()
                    if mode_val in ["compact", "full"]:
                        self.ui_panels.settings.mode = mode_val
                        print(f"UI mode: {mode_val}")
                    else:
                        print("Usage: /ui mode [compact|full]")
                else:
                    print("Usage: /ui mode [compact|full]")
            elif subcmd == "fps":
                if len(parts) > 1:
                    try:
                        fps = int(parts[1])
                        self.ui_panels.settings.fps_limit = max(0, fps)
                        print(f"FPS limit: {self.ui_panels.settings.fps_limit}")
                    except ValueError:
                        print("Usage: /ui fps <number>")
                else:
                    print("Usage: /ui fps <number>")
            else:
                print("Usage: /ui [on|off|clear|mode|fps]")
            return True
        
        elif cmd == "/quit":
            self.running = False
            return True
        
        else:
            print(f"Unknown command: {cmd}. Type /help for available commands.")
            return True
    
    def export_graph(self):
        """Export semantic graph to JSON file."""
        graph_data = self.world.state.semantic_graph.to_dict()
        export_path = Path(self.world.data_dir) / "graph.json"
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            print(f"Graph exported to {export_path}")
        except Exception as e:
            print(f"Error exporting graph: {e}")
    
    def _generate_minimum_utterance(self, state, vocab_size: int) -> Tuple[str, List[str]]:
        """
        Generate a minimum-length utterance (6+ tokens).
        Uses graph expansion, nearest neighbors, or templates.
        """
        MIN_SAY_TOKENS = 6
        if not state.tensor_cognition or not state.tensor_cognition.primordial_lexicon:
            return ("", [])
        
        import random
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            # Strategy 1: Sample from lexicon and expand via graph
            if state.semantic_graph.nodes:
                seed_tokens = random.sample(
                    state.tensor_cognition.primordial_lexicon,
                    min(2, len(state.tensor_cognition.primordial_lexicon))
                )
                # Try to expand via graph random walk
                expanded = self._expand_via_graph(seed_tokens, MIN_SAY_TOKENS, state)
                if len(expanded) >= MIN_SAY_TOKENS:
                    return (" ".join(expanded), expanded)
            
            # Strategy 2: Use nearest neighbors from embedding space
            if state.tensor_cognition and len(state.tensor_cognition.token_to_id) >= MIN_SAY_TOKENS:
                seed = random.choice(state.tensor_cognition.primordial_lexicon)
                expanded = self._expand_via_neighbors(seed, MIN_SAY_TOKENS, state)
                if len(expanded) >= MIN_SAY_TOKENS:
                    return (" ".join(expanded), expanded)
            
            attempts += 1
        
        # Strategy 3: Force template output
        return self._generate_template_utterance(MIN_SAY_TOKENS, state)
    
    def _expand_to_minimum_utterance(
        self, output_text: str, output_tokens: List[str], state
    ) -> Tuple[str, List[str]]:
        """Expand a short utterance to minimum length (6 tokens)."""
        MIN_SAY_TOKENS = 6
        if len(output_tokens) >= MIN_SAY_TOKENS:
            return (output_text, output_tokens)
        
        # Try graph expansion first
        expanded = self._expand_via_graph(output_tokens, MIN_SAY_TOKENS, state)
        if len(expanded) >= MIN_SAY_TOKENS:
            return (" ".join(expanded), expanded)
        
        # Try nearest neighbors
        if output_tokens:
            seed = output_tokens[-1]
            expanded = self._expand_via_neighbors(seed, MIN_SAY_TOKENS, state)
            if len(expanded) >= MIN_SAY_TOKENS:
                return (" ".join(expanded), expanded)
        
        # Fallback: append distinct tokens from lexicon
        if state.tensor_cognition and state.tensor_cognition.primordial_lexicon:
            remaining = MIN_SAY_TOKENS - len(output_tokens)
            available = [t for t in state.tensor_cognition.primordial_lexicon 
                        if t not in output_tokens]
            if available:
                import random
                additional = random.sample(available, min(remaining, len(available)))
                expanded = output_tokens + additional
                return (" ".join(expanded), expanded)
        
        return (output_text, output_tokens)  # Return as-is if can't expand
    
    def _expand_via_graph(
        self, seed_tokens: List[str], target_length: int, state
    ) -> List[str]:
        """Expand tokens via graph random walk."""
        result = seed_tokens.copy()
        graph = state.semantic_graph
        
        while len(result) < target_length:
            last_token = result[-1]
            if last_token in graph.edges and graph.edges[last_token]:
                # Pick random neighbor
                neighbors = list(graph.edges[last_token].keys())
                import random
                next_token = random.choice(neighbors)
                if next_token not in result:  # Avoid immediate repetition
                    result.append(next_token)
                else:
                    break
            else:
                break
        
        return result
    
    def _expand_via_neighbors(
        self, seed_token: str, target_length: int, state
    ) -> List[str]:
        """Expand via nearest neighbors in embedding space."""
        if not state.tensor_cognition:
            return [seed_token]
        
        result = [seed_token]
        neighbors = state.tensor_cognition.get_nearest_neighbors(seed_token, top_k=10)
        
        for neighbor, _ in neighbors:
            if neighbor not in result and len(result) < target_length:
                result.append(neighbor)
            if len(result) >= target_length:
                break
        
        return result
    
    def _generate_template_utterance(self, min_tokens: int, state) -> Tuple[str, List[str]]:
        """Generate a template-based utterance with minimum tokens."""
        from .grammar import GRAMMAR_TEMPLATES, apply_grammar_template
        import random
        
        if not GRAMMAR_TEMPLATES:
            # Fallback: just repeat distinct tokens
            if state.tensor_cognition and state.tensor_cognition.primordial_lexicon:
                tokens = random.sample(
                    state.tensor_cognition.primordial_lexicon,
                    min(min_tokens, len(state.tensor_cognition.primordial_lexicon))
                )
                return (" ".join(tokens), tokens)
            return ("", [])
        
        # Try templates until we get enough tokens
        for _ in range(5):
            template = random.choice(GRAMMAR_TEMPLATES)
            if state.semantic_graph.nodes:
                result = apply_grammar_template(template, state.semantic_graph)
                tokens = tokenize(result)
                if len(tokens) >= min_tokens:
                    return (result, tokens)
        
        # Last resort: sample distinct tokens
        if state.tensor_cognition and state.tensor_cognition.primordial_lexicon:
            tokens = random.sample(
                state.tensor_cognition.primordial_lexicon,
                min(min_tokens, len(state.tensor_cognition.primordial_lexicon))
            )
            return (" ".join(tokens), tokens)
        
        return ("", [])
    
    def step(self, user_input: Optional[str] = None, autonomous: bool = False, force_speak: bool = False):
        """Execute one simulation step."""
        state = self.world.state
        
        # ===== PHASE A: THINKING (always happens) =====
        
        # Process user input if provided (high-weight stimulus)
        interaction_intensity = 0.0
        stimulus_tokens = []
        stimulus_motif = None
        if user_input:
            stimulus_tokens = tokenize(user_input)
            self.world.process_input(user_input)
            interaction_intensity = min(1.0, len(user_input) / 100.0)  # Normalize
            
            # Encode stimulus as motif tensor
            if state.tensor_cognition and stimulus_tokens:
                stimulus_motif = state.tensor_cognition.encode_motif(stimulus_tokens)
                state.last_stimulus_tensor = stimulus_motif.tolist()
                state.last_stimulus_turn = state.turn
                # High-weight update from user input
                drives_list = [state.drives.stability, state.drives.novelty, 
                              state.drives.cohesion, state.drives.expression]
                state.tensor_cognition.update_from_interaction(
                    stimulus_tokens, weight=1.0, drives=drives_list
                )
        
        # Apply stimulus decay (if there was a previous stimulus)
        if state.last_stimulus_tensor and state.last_stimulus_turn > 0:
            turns_since = state.turn - state.last_stimulus_turn
            if turns_since > 0:
                decay_weight = (state.stimulus_decay_factor ** turns_since)
                if decay_weight > 0.01 and state.tensor_cognition:  # Only if still significant
                    import torch
                    device = state.tensor_cognition.device if state.tensor_cognition else torch.device("cpu")
                    decayed_motif = torch.tensor(state.last_stimulus_tensor, dtype=torch.float32, device=device)
                    drives_list = [state.drives.stability, state.drives.novelty,
                                  state.drives.cohesion, state.drives.expression]
                    state.tensor_cognition.update_from_internal_motif(
                        decayed_motif, weight=decay_weight * 0.3, drives=drives_list
                    )
                elif decay_weight <= 0.01:
                    # Stimulus has decayed away
                    state.last_stimulus_tensor = None
        
        # Internal thought cycle (if no user input or autonomous)
        if not user_input and state.tensor_cognition:
            # Generate internal motif
            drives_list = [state.drives.stability, state.drives.novelty,
                          state.drives.cohesion, state.drives.expression]
            internal_motif = state.tensor_cognition.generate_internal_motif(
                novelty_drive=state.drives.novelty,
                stability=state.drives.stability
            )
            # Update from internal thought (smaller weight)
            state.tensor_cognition.update_from_internal_motif(
                internal_motif, weight=0.1, drives=drives_list
            )
            # Create weak graph edges between internal thought tokens
            internal_tokens = getattr(state.tensor_cognition, '_last_internal_tokens', [])
            if len(internal_tokens) >= 2:
                # Create weak edges (weight 0.5) between distinct tokens
                for i in range(len(internal_tokens) - 1):
                    token1 = internal_tokens[i]
                    token2 = internal_tokens[i + 1]
                    if token1 != token2:
                        # Add weak bidirectional edge
                        state.semantic_graph.add_edge(token1, token2, weight=0.5)
                        state.semantic_graph.add_edge(token2, token1, weight=0.5)
        
        # Lexicon sprout for sparse graphs (autonomous steps)
        if autonomous:
            self.world.lexicon_sprout(state.drives.novelty)
        
        # Get current metrics
        temp_diversity = self.metrics.get_diversity()
        temp_coherence = self.metrics.get_coherence(state.semantic_graph.edges)
        temp_novelty = 0.0  # Will be computed after generation if we speak
        
        # Internal novelty injection (if novelty is low and no user input)
        if not user_input and state.tensor_cognition:
            # We'll check novelty after potential generation, but inject proactively
            if temp_diversity < 0.2:
                state.tensor_cognition.inject_latent_novelty(novelty_drive=state.drives.novelty)
        
        # Update metrics and drives (even without speaking)
        # Use previous output tokens if available, otherwise empty
        prev_output_tokens = getattr(self, '_last_output_tokens', [])
        if prev_output_tokens:
            diversity = self.metrics.get_diversity()
            coherence = self.metrics.get_coherence(state.semantic_graph.edges)
            novelty = self.metrics.get_novelty(prev_output_tokens)
        else:
            diversity = temp_diversity
            coherence = temp_coherence
            novelty = 0.0
        
        # Update drives (always, even in silence)
        self.world.update_drives(diversity, coherence, novelty, interaction_intensity)
        
        # ===== PHASE B: SPEAKING (conditional) =====
        
        # Determine if we should generate visible output
        vocab_size = len(state.tensor_cognition.token_to_id) if state.tensor_cognition else 0
        should_speak = (
            force_speak or
            user_input is not None or  # Always speak when user provides input
            (not state.silence_mode and (
                # Adjusted conditions: expression threshold + vocabulary requirement
                (state.drives.expression > 0.30 and vocab_size >= 8) or
                state.turn % 10 == 0  # Heartbeat every 10 turns
            ))
        )
        
        output_text = None
        output_tokens = []
        agent_name = None
        
        if should_speak:
            # Generate output
            output_text, output_tokens, agent_name = self.coordinator.select_output(
                state.semantic_graph,
                state.episodic_memory,
                state.drives,
                state.turn,
                tensor_cognition=state.tensor_cognition,
                diversity=temp_diversity,
                coherence=temp_coherence,
                novelty_score=temp_novelty
            )
            
            # Force generation if expression is high and vocabulary exists
            # but no output was generated
            if not output_text and state.drives.expression > 0.30 and vocab_size >= 8:
                # Generate a minimum-length artifact (6+ tokens)
                output_text, output_tokens = self._generate_minimum_utterance(
                    state, vocab_size
                )
                if output_text:
                    agent_name = "Weaver"
            
            # Enforce minimum utterance length (6 tokens)
            if output_tokens and len(output_tokens) < 6:
                output_text, output_tokens = self._expand_to_minimum_utterance(
                    output_text, output_tokens, state
                )
            
            # Feed artifact back into graph (closed loop learning)
            if output_tokens:
                self.world.process_artifact(output_tokens)
            
            # Update metrics
            if output_tokens:
                self.metrics.add_tokens(output_tokens)
                # Add artifact tokens for novelty calculation
                self.metrics.add_artifact_tokens(output_tokens)
            
            # Recalculate metrics with actual output
            diversity = self.metrics.get_diversity()
            coherence = self.metrics.get_coherence(state.semantic_graph.edges)
            novelty = self.metrics.get_novelty(output_tokens)
            
            # Novelty floor: if diversity < 0.15 for 30 turns, inject new tokens
            if diversity < 0.15:
                self._low_diversity_turns += 1
                if self._low_diversity_turns >= 30:
                    # Force lexicon sprout with world-specific tokens
                    if self.world_map and self.agent_system and state.tensor_cognition:
                        # Inject region names, agent names, professions, weather terms
                        new_tokens = []
                        for region in list(self.world_map.regions.values())[:3]:
                            new_tokens.append(region.name.lower())
                        for agent in list(self.agent_system.agents.values())[:3]:
                            new_tokens.append(agent.name.lower())
                            new_tokens.append(agent.role.lower())
                        new_tokens.extend(['rain', 'wind', 'clear', 'cloud'])
                        
                        for token in new_tokens:
                            # get_token_id automatically adds the token if it doesn't exist
                            state.tensor_cognition.get_token_id(token)
                        
                        self._low_diversity_turns = 0  # Reset counter
            else:
                self._low_diversity_turns = 0  # Reset if diversity recovers
            
            # Debug output for novel tokens
            if self.debug_mode:
                novel_tokens = self.metrics.get_novel_tokens(output_tokens)
                if novel_tokens:
                    print(f"[DEBUG] novel tokens this turn: {novel_tokens}")
            
            # Store for next turn's thinking phase
            self._last_output_tokens = output_tokens
        
        # Increment turn (always, even in silence)
        state.turn += 1
        
        # Render UI if enabled and should render
        if self.ui_panels.should_render(state.turn) or should_speak:
            self._render_ui(state.turn)
        
        # Debug output
        if self.debug_mode and should_speak:
            num_nodes = len(state.semantic_graph.nodes)
            num_edges = sum(len(neighbors) for neighbors in state.semantic_graph.edges.values())
            top_nodes = sorted(
                state.semantic_graph.nodes.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            print(f"[DEBUG] Stimulus tokens: {stimulus_tokens}")
            print(f"[DEBUG] Artifact tokens: {output_tokens}")
            print(f"[DEBUG] Graph: {num_nodes} nodes, {num_edges} edges")
            print(f"[DEBUG] Top nodes: {', '.join(f'{t}({w:.1f})' for t, w in top_nodes)}")
            print()
        
        # Display status and output (only if speaking)
        if should_speak:
            print(format_status_line(
                state.turn - 1,  # Use previous turn number (before increment)
                state.drives,
                diversity,
                coherence,
                novelty
            ))
            
            if output_text:
                print(format_output(output_text, agent_name))
            else:
                # Honest silence message
                vocab_size = len(state.tensor_cognition.token_to_id) if state.tensor_cognition else 0
                if vocab_size < 8:
                    print("  (silence — internal motion without symbols)")
                else:
                    print("  (silence — no output generated)")
            
            print()
            
            # Store in episodic memory (only if we spoke)
            user_input_str = user_input if user_input else ""
            notable = interaction_intensity > 0.5 or len(output_tokens) > 10
            state.episodic_memory.add(
                state.turn - 1,  # Use previous turn number
                user_input_str,
                output_text,
                notable=notable
            )
        
        # Advance turn
        self.world.advance_turn()
        
        # Render UI if enabled and should render
        if self.ui_panels.should_render(state.turn) or should_speak:
            self._render_ui(state.turn)
        
        # Advance world simulation if initialized
        if self.time_system and self.world_map and self.weather_system and \
           self.agent_system and self.event_system:
            self._world_tick()
        
        # Auto-save
        if state.turn % self.auto_save_interval == 0:
            self.world.save()
            # Also save world simulation state
            if self.time_system and self.world_map:
                self.world_sim_state.save(
                    self.time_system, self.world_map, self.weather_system,
                    self.agent_system, self.event_system
                )
    
    def _world_tick(self):
        """Advance world simulation by one turn with consequences."""
        if not all([self.time_system, self.world_map, self.weather_system,
                   self.agent_system, self.event_system]):
            return
        
        if not self.consequence_system:
            self.consequence_system = ConsequenceSystem(seed=self.world.state.seed)
        
        # Advance time
        self.time_system.advance(turns=1)
        hour = self.time_system.get_hour()
        
        # Advance weather
        self.weather_system.advance()
        
        # Update region resources (consumption and regeneration)
        for region in self.world_map.regions.values():
            agents_in_region = sum(1 for a in self.agent_system.agents.values()
                                  if self.world_map.get_region_by_location_id(a.current_location) == region)
            weather_state = self.weather_system.snapshot(region.id)
            self.consequence_system.update_region_resources(region, agents_in_region, weather_state)
        
        # Advance agents with consequence-driven decisions
        agent_actions = self._advance_agents_with_consequences(hour)
        self.agent_system.update_crowd_densities(self.world_map)
        
        # Get tensor modifier (subtle influence, 10% max)
        state = self.world.state
        if state.tensor_cognition:
            world_state = state.tensor_cognition.get_world_state(state.drives.stability)
            # Use state_flux norm as a small modifier (-0.1 to 0.1)
            tensor_modifier = (state.tensor_cognition.state_flux.norm().item() - 1.0) * 0.1
        else:
            tensor_modifier = 0.0
        
        # Advance events
        new_events = self.event_system.advance(
            self.world_map, self.agent_system, agent_actions, tensor_modifier
        )
        
        # ===== INTEGRATE NEW AI SYSTEMS =====
        turn = self.world.state.turn
        
        # 1. Check for entropy/anomalies
        anomaly = self.entropy_system.check_anomaly(turn)
        if anomaly:
            # Apply anomaly effects
            if self.world_dynamics_system:
                for district_id in self.world_map.regions.keys():
                    district = self.world_dynamics_system.get_district(district_id)
                    if district:
                        # Apply anomaly effects to tension
                        if 'social_tension' in anomaly.effects:
                            district.tension_state.multi_tension.social += anomaly.effects['social_tension']
                        if 'economic_tension' in anomaly.effects:
                            district.tension_state.multi_tension.economic += anomaly.effects['economic_tension']
                        if 'existential_tension' in anomaly.effects:
                            district.tension_state.multi_tension.existential += anomaly.effects['existential_tension']
                        district.tension_state.multi_tension.normalize()
        
        # 2. Apply world pressure to districts and agents
        if self.world_dynamics_system and self.weather_system and self.time_system:
            conditions = self.world_pressure_system.get_conditions_from_world(
                self.weather_system, self.time_system
            )
            
            for district_id in self.world_map.regions.keys():
                district = self.world_dynamics_system.get_district(district_id)
                if district:
                    # Apply world pressure to district intent and tension
                    self.world_pressure_system.apply_pressure(
                        conditions, district.intent, district.tension_state.multi_tension, turn
                    )
        
        # 3. Update agent intents based on events and tension
        if self.agent_system and self.world_dynamics_system:
            for agent in self.agent_system.agents.values():
                # Get district tension if agent is in a district
                region = self.world_map.get_region_by_location_id(agent.current_location)
                if region and self.world_dynamics_system:
                    district = self.world_dynamics_system.get_district(region.id)
                    if district:
                        # Apply tension to agent intent
                        agent.intent.apply_tension(
                            district.tension_state.multi_tension.economic,
                            district.tension_state.multi_tension.social,
                            district.tension_state.multi_tension.political,
                            district.tension_state.multi_tension.existential
                        )
                        
                        # Apply pressure (food, scarcity, weather)
                        weather_bad = conditions.weather in ['rain', 'storm', 'extreme_heat', 'extreme_cold']
                        agent.intent.apply_pressure(
                            district.pressure.food,
                            district.pressure.food > 0.7,
                            weather_bad
                        )
        
        # 4. Record causality for major events
        if new_events:
            for event in new_events:
                # Record cause-effect
                # Handle event_type - could be Enum or string
                event_type_str = 'unknown'
                if hasattr(event, 'event_type'):
                    if hasattr(event.event_type, 'value'):
                        # It's an Enum
                        event_type_str = event.event_type.value
                    else:
                        # It's already a string
                        event_type_str = str(event.event_type)
                
                cause = f"event:{event_type_str}"
                effect = event.description if hasattr(event, 'description') else str(event)
                self.causality_system.record(
                    cause=cause,
                    effect=effect,
                    source=event.district_id if hasattr(event, 'district_id') else 'world',
                    confidence=0.5,
                    duration=event.duration if hasattr(event, 'duration') else 1,
                    turn=turn
                )
                
                # Add emotional trace
                event_desc = effect
                # Determine emotions based on event type
                event_type_lower = event_type_str.lower()
                if 'conflict' in event_type_lower or 'riot' in event_type_lower:
                    self.emotional_memory.add(event_desc, turn, fear=0.3, anger=0.4, sadness=0.2)
                elif 'aid' in event_type_lower or 'cooperation' in event_type_lower:
                    self.emotional_memory.add(event_desc, turn, hope=0.4, joy=0.3)
                elif 'shortage' in event_type_lower or 'scarcity' in event_type_lower:
                    self.emotional_memory.add(event_desc, turn, fear=0.5, sadness=0.3)
        
        # 5. Decay systems
        self.causality_system.decay_all()
        self.emotional_memory.decay_all()
        
        # 6. Learn rules from patterns (simplified - check if conditions match effects)
        if self.world_dynamics_system:
            for district_id in self.world_map.regions.keys():
                district = self.world_dynamics_system.get_district(district_id)
                if district:
                    # Example: learn rule about food scarcity
                    if district.pressure.food > 0.7 and district.tension_state.multi_tension.social > 50:
                        condition = f"food_pressure > 0.7"
                        effect = "social_tension += 0.3"
                        self.learned_rules.learn_rule(condition, effect, turn)
        
        # 7. Cleanup learned rules
        self.learned_rules.cleanup(turn)
        
        # 8. Adjust entropy based on tension (higher tension = more anomalies)
        if self.world_dynamics_system:
            total_tension = 0.0
            count = 0
            for district_id in self.world_map.regions.keys():
                district = self.world_dynamics_system.get_district(district_id)
                if district:
                    total_tension += district.tension_state.multi_tension.get_average()
                    count += 1
            if count > 0:
                avg_tension = total_tension / count
                # Higher tension increases entropy rate (up to 3x)
                tension_factor = 1.0 + (avg_tension / 100.0) * 2.0
                self.entropy_system.adjust_entropy_rate(tension_factor)
            else:
                self.entropy_system.reset_entropy_rate()
        
        # Advance economy and human agents per district
        # Use world_dynamics_system if available, otherwise fallback to economy_system
        if self.human_agent_system and self.world_map:
            all_human_events = []
            use_advanced = self.world_dynamics_system is not None
            
            for district_id, region in self.world_map.regions.items():
                # Get agents in this district
                district_agents = [a for a in self.human_agent_system.agents.values() 
                                 if a.district == district_id]
                agent_count = len(district_agents)
                
                # Get neighboring districts
                neighbor_ids = [r_id for r_id in self.world_map.regions.keys() if r_id != district_id]
                
                if use_advanced:
                    # Use advanced world dynamics
                    # Get weather state
                    weather_state = {}
                    if self.weather_system:
                        weather_snap = self.weather_system.snapshot(district_id)
                        if weather_snap:
                            weather_state = {
                                "precipitation": getattr(weather_snap, 'precipitation', 0),
                                "wind": getattr(weather_snap, 'wind', 0),
                                "temperature": getattr(weather_snap, 'temperature', 0)
                            }
                    
                    # Advance world dynamics
                    self.world_dynamics_system.advance(
                        district_id, agent_count, weather_state, neighbor_ids, self.world.state.turn
                    )
                    
                    # Get district resources from world dynamics
                    district = self.world_dynamics_system.get_district(district_id)
                    if district:
                        district_resources = {
                            "food_stock": district.food_stock,
                            "credits_pool": district.credits_pool,
                            "jobs_available": district.jobs_available,
                            "security_level": district.security_level,
                            "tension": district.tension_state.tension,
                            "scarcity": district.pressure.food > 0.7  # Derived from pressure
                        }
                        
                        # Collect events from active events
                        for event in district.active_events:
                            # Handle event_type - could be Enum or string
                            event_type_str = 'unknown'
                            if hasattr(event, 'event_type'):
                                if hasattr(event.event_type, 'value'):
                                    # It's an Enum
                                    event_type_str = event.event_type.value
                                else:
                                    # It's already a string
                                    event_type_str = str(event.event_type)
                            
                            all_human_events.append(("world", 
                                f"{event_type_str} in {district.district_name}", 
                                event_type_str))
                    else:
                        district_resources = {"food_stock": 50, "credits_pool": 100, "jobs_available": 5, 
                                            "security_level": 70, "tension": 20, "scarcity": False}
                else:
                    # Fallback to old economy system
                    if self.economy_system:
                        district_resources = self.economy_system.get_district_resources(district_id)
                        self.economy_system.advance(district_id, agent_count, [])
                    else:
                        district_resources = {"food_stock": 50, "credits_pool": 100, "jobs_available": 5, 
                                            "security_level": 70, "tension": 20, "scarcity": False}
                
                # Advance human agents
                location_ids = [loc.id for loc in region.locations]
                human_events = self.human_agent_system.advance(
                    district_resources, location_ids, self.world_map, self.world.state.turn
                )
                all_human_events.extend(human_events)
                
                if not use_advanced and self.economy_system:
                    # Update economy tension with human events
                    event_descriptions = [e[1] for e in human_events]
                    self.economy_system.update_tension(district_id, event_descriptions)
                    
                    # Generate economy events
                    economy_events = self.economy_system.generate_events(district_id)
                    for evt in economy_events:
                        all_human_events.append(("economy", evt, "economy"))
            
            # Store human events for UI rendering
            self._last_human_events = all_human_events
    
    def _advance_agents_with_consequences(self, hour: int) -> List[Tuple[str, str]]:
        """Advance agents with consequence-driven decision making."""
        actions = []
        
        for agent in self.agent_system.agents.values():
            # Update needs and energy/stress
            agent.needs.food += random.uniform(0.01, 0.02)  # Hunger increases
            agent.needs.rest += random.uniform(0.01, 0.02)  # Rest need increases
            agent.energy = max(0.0, min(1.0, agent.energy - 0.01))
            agent.stress = max(0.0, min(1.0, agent.stress + 0.005))
            
            # Clamp needs
            agent.needs.food = min(1.0, agent.needs.food)
            agent.needs.rest = min(1.0, agent.needs.rest)
            
            # Determine action with memory bias
            action = self._determine_agent_action_with_consequences(agent, hour)
            actions.append((agent.id, action))
            agent.memory.append(action)
        
        return actions
    
    def _determine_agent_action_with_consequences(self, agent, hour: int) -> str:
        """Determine agent action using needs, memory bias, and consequences."""
        import random
        
        # Get current location and region
        current_loc = self.world_map.get_location(agent.current_location)
        if not current_loc:
            return f"{agent.name} is lost"
        
        region = self.world_map.get_region_by_location_id(agent.current_location)
        if not region:
            return f"{agent.name} is at {current_loc.name}"
        
        weather = self.weather_system.snapshot(region.id)
        
        # Update schedule
        if 22 <= hour or hour < 6:
            agent.schedule = "sleep"
        elif 6 <= hour < 9 or 17 <= hour < 22:
            agent.schedule = "free"
        else:
            agent.schedule = "work"
        
        # Priority 1: Sleep if schedule says so
        if agent.schedule == "sleep":
            if agent.current_location != agent.home_location:
                agent.current_location = agent.home_location
                return f"{agent.name} returns home to rest"
            agent.needs.rest = max(0.0, agent.needs.rest - 0.15)
            agent.energy = min(1.0, agent.energy + 0.1)
            return f"{agent.name} rests at {current_loc.name}"
        
        # Priority 2: High hunger -> trade
        if agent.needs.hunger > 0.7:
            # Check memory bias for market regions
            market_regions = [r for r in self.world_map.regions.values() if 'market' in r.tags]
            if market_regions:
                # Prefer regions with positive memory
                scored_regions = []
                for r in market_regions:
                    bias = self.consequence_system.get_memory_bias(agent, r.id)
                    score = r.food / 100.0 + bias * 0.3  # Prefer regions with food and good memory
                    scored_regions.append((r, score))
                
                scored_regions.sort(key=lambda x: x[1], reverse=True)
                target_region = scored_regions[0][0]
                
                # Find a location in target region
                target_locs = [loc for loc in self.world_map.locations.values()
                              if loc.region_id == target_region.id and loc.type_tag == 'market']
                if target_locs:
                    agent.current_location = target_locs[0].id
                    success, desc = self.consequence_system.attempt_trade(agent, target_region)
                    if success:
                        agent.stress = max(0.0, agent.stress - 0.02)
                    return desc
        
        # Priority 3: Low energy -> rest
        if agent.energy < 0.3:
            if agent.current_location != agent.home_location:
                agent.current_location = agent.home_location
                return f"{agent.name} returns home to rest"
            agent.needs.rest = max(0.0, agent.needs.rest - 0.1)
            agent.energy = min(1.0, agent.energy + 0.05)
            return f"{agent.name} rests at {current_loc.name}"
        
        # Priority 4: Work if schedule says so
        if agent.schedule == "work" and agent.work_ethic > 0.4:
            work_locations = [loc for loc in self.world_map.locations.values()
                            if loc.type_tag in ['industrial', 'civic', 'market']]
            if work_locations:
                # Use memory bias to choose work location
                scored_locs = []
                for loc in work_locations:
                    work_region = self.world_map.get_region_by_location_id(loc.id)
                    if work_region:
                        bias = self.consequence_system.get_memory_bias(agent, work_region.id)
                        score = work_region.infrastructure + bias * 0.2
                        scored_locs.append((loc, work_region, score))
                
                scored_locs.sort(key=lambda x: x[2], reverse=True)
                target_loc, target_region, _ = scored_locs[0]
                
                if agent.current_location != target_loc.id:
                    # Check weather for movement cost
                    if weather.precipitation > 0.5:
                        # High precip makes movement less likely
                        if random.random() > 0.7:
                            agent.current_location = target_loc.id
                            return f"{agent.name} moves to {target_loc.name} despite weather"
                        else:
                            return f"{agent.name} stays put due to weather"
                    else:
                        agent.current_location = target_loc.id
                        return f"{agent.name} goes to work at {target_loc.name}"
                else:
                    # Already at work location, attempt work
                    work_result = self.consequence_system.attempt_work(agent, target_region, weather)
                    agent.stress = max(0.0, min(1.0, agent.stress + work_result.stress_change))
                    agent.energy = max(0.0, agent.energy - 0.05)
                    
                    if work_result.success:
                        return f"{agent.name} works successfully at {target_loc.name}"
                    else:
                        return f"{agent.name} struggles with work at {target_loc.name}"
        
        # Priority 5: High stress -> socialize
        if agent.stress > 0.6 and agent.social_trait > 0.4:
            # Find other agents at same location
            other_agents = [a for a in self.agent_system.agents.values()
                          if a.id != agent.id and a.current_location == agent.current_location]
            if other_agents:
                other = random.choice(other_agents)
                success, desc = self.consequence_system.attempt_socialize(agent, other, region)
                return desc
        
        # Default: stay or move randomly (with memory bias)
        if random.random() < 0.2:
            transit_locations = [loc for loc in self.world_map.locations.values()
                               if loc.type_tag == 'transit']
            if transit_locations:
                loc = random.choice(transit_locations)
                agent.current_location = loc.id
                return f"{agent.name} moves to {loc.name}"
        
        return f"{agent.name} is at {current_loc.name}"
    
    def _render_ui(self, turn: int):
        """Render UI panels based on camera mode."""
        if not self.ui_panels.settings.enabled:
            return
        
        # Get header
        if self.time_system and self.weather_system:
            header = f"{self.time_system.format_time()} | {self.weather_system.format_weather_line()}"
        else:
            header = f"Turn {turn}"
        
        # Get districts for minimap/heatmap
        districts = list(self.world_map.regions.values()) if self.world_map else []
        district_names = [d.name for d in districts]
        
        # Get agents for minimap
        agents = list(self.human_agent_system.agents.values()) if self.human_agent_system else []
        
        # Render minimap
        focused_agent_id = None
        if self.camera.mode == CameraMode.AGENT and self.camera.target_agent_id:
            focused_agent_id = self.camera.target_agent_id
        minimap_lines = self.ui_panels.render_minimap(district_names, agents, focused_agent_id)
        
        # Render heatmap
        heatmap_lines = self.ui_panels.render_heatmap(districts, self.economy_system)
        
        # Get events
        events = self._last_human_events if hasattr(self, '_last_human_events') else []
        if self.event_system:
            recent_events = self.event_system.get_recent_events(n=10)
            events.extend([e.description for e in recent_events])
        event_feed_lines = self.ui_panels.render_event_feed(events)
        
        # Render based on camera mode
        agent_list_lines = None
        agent_panel_lines = None
        
        if self.camera.mode == CameraMode.AGENT and self.camera.target_agent_id:
            # AGENT mode: show agent panel
            agent = None
            if self.human_agent_system:
                agent = self.human_agent_system.get_agent(self.camera.target_agent_id)
                if not agent:
                    agent = self.human_agent_system.get_agent_by_name(self.camera.target_agent_id)
            if agent:
                agent_panel_lines = self.ui_panels.render_agent_panel(agent)
        elif self.camera.mode == CameraMode.DISTRICT and self.camera.target_district:
            # DISTRICT mode: show agents in district
            if self.human_agent_system:
                district_agents = self.human_agent_system.get_agents_in_district(self.camera.target_district)
                agent_list_lines = self.ui_panels.render_agent_list(district_agents, max_agents=10)
        else:
            # GOD mode or default: show top agents
            if self.human_agent_system:
                all_agents = list(self.human_agent_system.agents.values())
                agent_list_lines = self.ui_panels.render_agent_list(all_agents, max_agents=8)
        
        # Render screen
        self.ui_panels.render_screen(
            header, minimap_lines, heatmap_lines, event_feed_lines,
            agent_list_lines, agent_panel_lines, self.ui_panels.settings.mode
        )
    
    def run(self):
        """
        Main simulation loop - input-driven.
        - Always waits for user input using input()
        - Empty input = one autonomous tick (if autopilot enabled)
        - Non-empty input = command or stimulus
        """
        self.initialize()
        
        try:
            while self.running:
                # Always wait for user input (this is the clock)
                print_prompt()
                try:
                    line = input().strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting...")
                    break
                
                # Empty input = autonomous tick (if autopilot enabled)
                if not line:
                    if self.autopilot:
                        # Perform one autonomous step
                        self.step(autonomous=True)
                        self.world_turn_counter += 1
                        
                        # Print bulletin every N turns
                        if self.world_turn_counter % self.bulletin_interval == 0:
                            if self.time_system and self.world_map and self.weather_system and \
                               self.event_system and self.agent_system:
                                print("\n" + "="*50)
                                print(format_world_bulletin(
                                    self.time_system, self.world_map, self.weather_system,
                                    self.event_system, self.follow_agent_id, self.agent_system
                                ))
                                print("="*50 + "\n")
                        
                        # Sleep for tick delay (only for autonomous ticks)
                        if self.tick_delay_ms > 0:
                            time.sleep(self.tick_delay_ms / 1000.0)
                    else:
                        # Autopilot off, empty input does nothing
                        print("(Autopilot is OFF. Use /auto on to enable, or enter a command.)")
                    continue
                
                # Non-empty input: process as command or stimulus
                if self.process_command(line):
                    continue
                
                # Treat as user input stimulus
                self.step(user_input=line)
        
        except KeyboardInterrupt:
            print("\nExiting...")
        
        finally:
            # Save on exit
            self.world.save()
            if self.time_system and self.world_map:
                self.world_sim_state.save(
                    self.time_system, self.world_map, self.weather_system,
                    self.agent_system, self.event_system
                )
            print("State saved. Goodbye.")
