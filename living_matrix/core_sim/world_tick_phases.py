"""World Tick Phases - Decomposed world tick operations.

This module breaks down the monolithic _world_tick into discrete phases
that can be individually timed, skipped based on heartbeat, and run
with cached data where appropriate.

PHASES:
1. time_weather_advance - Time and weather updates
2. region_resources - Region resource updates
3. agent_actions - Agent action processing
4. events_advance - Event generation and processing
5. ai_systems - Entropy, pressure, causality
6. district_metrics - Per-district calculations
7. agent_updates - Human agent advances
8. decay_systems - Cleanup and decay

PERFORMANCE:
- Each phase is individually timed
- Phases can be skipped via heartbeat
- Expensive calculations are cached
"""

import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

from .world_heartbeat import WorldSystem, get_heartbeat
from .aggregate_cache import get_aggregate_cache, get_population_aggregates

if TYPE_CHECKING:
    from ..core import Simulation

logger = logging.getLogger(__name__)


@dataclass
class PhaseResult:
    """Result of running a phase."""
    name: str
    duration_ms: float
    skipped: bool = False
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldTickContext:
    """Shared context for world tick phases."""
    turn: int
    hour: int = 0
    weather_state: Dict[str, Any] = field(default_factory=dict)
    new_events: List[Any] = field(default_factory=list)
    all_human_events: List[Any] = field(default_factory=list)
    tensor_modifier: float = 0.0
    conditions: Any = None
    
    # Cached aggregates
    alive_count: int = 0
    global_child_pool: int = 0
    global_total_population: int = 0
    population_pressure: float = 0.0
    extinction_risk: float = 0.0
    
    # Phase timing
    phase_timings: Dict[str, float] = field(default_factory=dict)


class WorldTickPhases:
    """
    Manages world tick phase execution.
    
    Usage:
        phases = WorldTickPhases(simulation)
        ctx = phases.execute_all(turn)
        # ctx.phase_timings contains per-phase timing
    """
    
    def __init__(self, sim: 'Simulation'):
        self.sim = sim
        self._heartbeat = get_heartbeat()
        self._cache = get_aggregate_cache()
        self._pop_agg = get_population_aggregates()
    
    def execute_all(self, turn: int) -> WorldTickContext:
        """Execute all world tick phases."""
        ctx = WorldTickContext(turn=turn)
        
        # Phase 1: Time and Weather
        self._run_phase(ctx, "time_weather", self._phase_time_weather)
        
        # Phase 2: Region Resources
        self._run_phase(ctx, "region_resources", self._phase_region_resources)
        
        # Phase 3: Agent Actions (consequence-driven)
        self._run_phase(ctx, "agent_actions", self._phase_agent_actions)
        
        # Phase 4: Events
        self._run_phase(ctx, "events", self._phase_events)
        
        # Phase 5: AI Systems (entropy, pressure, causality)
        self._run_phase(ctx, "ai_systems", self._phase_ai_systems)
        
        # Phase 6: District Metrics (can be throttled)
        self._run_phase(ctx, "district_metrics", self._phase_district_metrics)
        
        # Phase 7: Agent Updates (human agents)
        self._run_phase(ctx, "agent_updates", self._phase_agent_updates)
        
        # Phase 8: Decay and Cleanup
        self._run_phase(ctx, "decay_cleanup", self._phase_decay_cleanup)
        
        return ctx
    
    def _run_phase(self, ctx: WorldTickContext, name: str, phase_func):
        """Run a single phase with timing."""
        start = time.perf_counter()
        try:
            phase_func(ctx)
        except Exception as e:
            logger.error(f"Phase {name} error: {e}")
        duration_ms = (time.perf_counter() - start) * 1000
        ctx.phase_timings[name] = duration_ms
    
    # ========================================================================
    # PHASE IMPLEMENTATIONS
    # ========================================================================
    
    def _phase_time_weather(self, ctx: WorldTickContext):
        """Phase 1: Advance time and weather."""
        sim = self.sim
        
        if not sim.time_system:
            return
        
        # Advance time (always runs)
        sim.time_system.advance(turns=1)
        ctx.hour = sim.time_system.get_hour()
        
        # Advance weather
        if sim.weather_system:
            sim.weather_system.advance()
    
    def _phase_region_resources(self, ctx: WorldTickContext):
        """Phase 2: Update region resources."""
        sim = self.sim
        
        if not all([sim.world_map, sim.consequence_system, sim.weather_system]):
            return
        
        # Only run if heartbeat says so
        if not self._heartbeat.should_update(WorldSystem.ECONOMY, ctx.turn):
            return
        
        for region in sim.world_map.regions.values():
            # Use cached agent count if available
            cache_key = f"agents_in_region_{region.id}"
            agents_in_region = self._cache.get(cache_key, ctx.turn, max_age=5)
            
            if agents_in_region is None:
                agents_in_region = sum(
                    1 for a in sim.agent_system.agents.values()
                    if sim.world_map.get_region_by_location_id(a.current_location) == region
                )
                self._cache.set(cache_key, agents_in_region, ctx.turn)
            
            weather_state = sim.weather_system.snapshot(region.id)
            sim.consequence_system.update_region_resources(
                region, agents_in_region, weather_state
            )
        
        self._heartbeat.record_update(WorldSystem.ECONOMY, ctx.turn)
    
    def _phase_agent_actions(self, ctx: WorldTickContext):
        """Phase 3: Process agent actions with consequences."""
        sim = self.sim
        
        if not all([sim.agent_system, sim.world_map, sim.consequence_system]):
            return
        
        # This phase always runs (agents need updates)
        agent_actions = sim._advance_agents_with_consequences(ctx.hour)
        sim.agent_system.update_crowd_densities(sim.world_map)
        
        # Get tensor modifier
        state = sim.world.state
        if state.tensor_cognition:
            world_state = state.tensor_cognition.get_world_state(state.drives.stability)
            ctx.tensor_modifier = (state.tensor_cognition.state_flux.norm().item() - 1.0) * 0.1
    
    def _phase_events(self, ctx: WorldTickContext):
        """Phase 4: Event generation and processing."""
        sim = self.sim
        
        # Events always run (they're important for simulation)
        if not sim.event_system:
            return
        
        ctx.new_events = sim.event_system.advance(
            sim.world_map, sim.agent_system, 
            [], ctx.tensor_modifier  # agent_actions not needed here
        )
    
    def _phase_ai_systems(self, ctx: WorldTickContext):
        """Phase 5: AI systems - entropy, pressure, causality."""
        sim = self.sim
        turn = ctx.turn
        
        # Entropy check
        if sim.entropy_system:
            anomaly = sim.entropy_system.check_anomaly(turn)
            if anomaly and sim.world_dynamics_system:
                self._apply_anomaly_effects(anomaly)
        
        # World pressure (throttled)
        if self._heartbeat.should_update(WorldSystem.TENSION_UPDATE, turn):
            self._apply_world_pressure(ctx)
            self._heartbeat.record_update(WorldSystem.TENSION_UPDATE, turn)
        
        # Agent intent updates (throttled for large populations)
        self._update_agent_intents(ctx)
        
        # Causality recording for events
        self._record_event_causality(ctx)
    
    def _phase_district_metrics(self, ctx: WorldTickContext):
        """Phase 6: District metrics and calculations."""
        sim = self.sim
        turn = ctx.turn
        
        if not self._heartbeat.should_update(WorldSystem.DISTRICT_STATS, turn):
            return
        
        # Calculate population aggregates (cached)
        self._calculate_population_aggregates(ctx)
        
        # Tension entropy adjustment
        if sim.world_dynamics_system:
            self._adjust_entropy_from_tension(ctx)
        
        self._heartbeat.record_update(WorldSystem.DISTRICT_STATS, turn)
    
    def _phase_agent_updates(self, ctx: WorldTickContext):
        """Phase 7: Human agent system advances."""
        sim = self.sim
        
        if not sim.human_agent_system or not sim.world_map:
            return
        
        # This is the core agent update - always runs
        self._advance_human_agents(ctx)
    
    def _phase_decay_cleanup(self, ctx: WorldTickContext):
        """Phase 8: Decay and cleanup systems."""
        sim = self.sim
        turn = ctx.turn
        
        # Causality decay (throttled)
        if self._heartbeat.should_update(WorldSystem.CAUSALITY_DECAY, turn):
            if sim.causality_system:
                sim.causality_system.decay_all()
            if sim.emotional_memory:
                sim.emotional_memory.decay_all()
            self._heartbeat.record_update(WorldSystem.CAUSALITY_DECAY, turn)
        
        # Learned rules cleanup (throttled)
        if sim.learned_rules and turn % 10 == 0:
            sim.learned_rules.cleanup(turn)
        
        # Culture drift (heavily throttled)
        if self._heartbeat.should_update(WorldSystem.CULTURE_DRIFT, turn):
            self._drift_cultures(ctx)
            self._heartbeat.record_update(WorldSystem.CULTURE_DRIFT, turn)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _apply_anomaly_effects(self, anomaly):
        """Apply entropy anomaly effects to districts."""
        sim = self.sim
        
        if not sim.world_dynamics_system or not sim.world_map:
            return
        
        for district_id in sim.world_map.regions.keys():
            district = sim.world_dynamics_system.get_district(district_id)
            if district:
                effects = anomaly.effects
                if 'social_tension' in effects:
                    district.tension_state.multi_tension.social += effects['social_tension']
                if 'economic_tension' in effects:
                    district.tension_state.multi_tension.economic += effects['economic_tension']
                if 'existential_tension' in effects:
                    district.tension_state.multi_tension.existential += effects['existential_tension']
                district.tension_state.multi_tension.normalize()
    
    def _apply_world_pressure(self, ctx: WorldTickContext):
        """Apply world pressure to districts."""
        sim = self.sim
        
        if not all([sim.world_dynamics_system, sim.weather_system, 
                   sim.time_system, sim.world_pressure_system]):
            return
        
        ctx.conditions = sim.world_pressure_system.get_conditions_from_world(
            sim.weather_system, sim.time_system
        )
        
        for district_id in sim.world_map.regions.keys():
            district = sim.world_dynamics_system.get_district(district_id)
            if district:
                sim.world_pressure_system.apply_pressure(
                    ctx.conditions, district.intent, 
                    district.tension_state.multi_tension, ctx.turn
                )
    
    def _update_agent_intents(self, ctx: WorldTickContext):
        """Update agent intents based on district conditions."""
        sim = self.sim
        
        if not all([sim.agent_system, sim.world_dynamics_system, sim.world_map]):
            return
        
        # Sample agents for large populations
        agents_list = list(sim.agent_system.agents.values())
        if len(agents_list) > 200:
            agents_to_update = random.sample(agents_list, 200)
        else:
            agents_to_update = agents_list
        
        for agent in agents_to_update:
            region = sim.world_map.get_region_by_location_id(agent.current_location)
            if not region:
                continue
            
            district = sim.world_dynamics_system.get_district(region.id)
            if not district:
                continue
            
            # Apply tension
            agent.intent.apply_tension(
                district.tension_state.multi_tension.economic,
                district.tension_state.multi_tension.social,
                district.tension_state.multi_tension.political,
                district.tension_state.multi_tension.existential
            )
            
            # Apply pressure
            if ctx.conditions:
                weather_bad = ctx.conditions.weather in ['rain', 'storm', 'extreme_heat', 'extreme_cold']
                agent.intent.apply_pressure(
                    district.pressure.food,
                    district.pressure.food > 0.7,
                    weather_bad
                )
    
    def _record_event_causality(self, ctx: WorldTickContext):
        """Record causality for new events."""
        sim = self.sim
        
        if not ctx.new_events or not sim.causality_system:
            return
        
        for event in ctx.new_events:
            event_type_str = self._get_event_type_str(event)
            cause = f"event:{event_type_str}"
            effect = getattr(event, 'description', str(event))
            
            sim.causality_system.record(
                cause=cause,
                effect=effect,
                source=getattr(event, 'district_id', 'world'),
                confidence=0.5,
                duration=getattr(event, 'duration', 1),
                turn=ctx.turn
            )
            
            # Emotional trace
            self._add_emotional_trace(event, event_type_str, ctx.turn)
    
    def _add_emotional_trace(self, event, event_type_str: str, turn: int):
        """Add emotional trace for an event."""
        sim = self.sim
        
        if not sim.emotional_memory:
            return
        
        event_desc = getattr(event, 'description', str(event))
        event_type_lower = event_type_str.lower()
        
        if 'conflict' in event_type_lower or 'riot' in event_type_lower:
            sim.emotional_memory.add(event_desc, turn, fear=0.3, anger=0.4, sadness=0.2)
        elif 'aid' in event_type_lower or 'cooperation' in event_type_lower:
            sim.emotional_memory.add(event_desc, turn, hope=0.4, joy=0.3)
        elif 'shortage' in event_type_lower or 'scarcity' in event_type_lower:
            sim.emotional_memory.add(event_desc, turn, fear=0.5, sadness=0.3)
    
    def _calculate_population_aggregates(self, ctx: WorldTickContext):
        """Calculate and cache population aggregates."""
        sim = self.sim
        turn = ctx.turn
        
        if not sim.human_agent_system:
            return
        
        # Use cached values if available
        cache = self._cache
        
        ctx.alive_count = cache.get_or_compute(
            "alive_count", turn,
            lambda: len([a for a in sim.human_agent_system.agents.values() if a.is_alive]),
            max_age=1
        )
        
        ctx.global_child_pool = cache.get_or_compute(
            "global_child_pool", turn,
            lambda: sum(sim.human_agent_system.child_pools.values()),
            max_age=1
        )
        
        ctx.global_total_population = ctx.alive_count + ctx.global_child_pool
        
        # Population pressure
        safe_threshold = 30
        ctx.population_pressure = max(0.0, min(1.0, 1.0 - (ctx.alive_count / safe_threshold)))
        
        # Extinction risk
        if ctx.alive_count < 10:
            ctx.extinction_risk = 1.0 - (ctx.alive_count / 10.0)
        elif sim.world.state.turns_since_last_birth > 50:
            ctx.extinction_risk = min(0.9, sim.world.state.turns_since_last_birth / 100.0)
        else:
            ctx.extinction_risk = 0.0
        
        # Update world state
        sim.world.state.active_agents = ctx.alive_count
        sim.world.state.total_child_pool = ctx.global_child_pool
        sim.world.state.total_population = ctx.global_total_population
        sim.world.state.population_pressure = ctx.population_pressure
        sim.world.state.extinction_risk = ctx.extinction_risk
    
    def _adjust_entropy_from_tension(self, ctx: WorldTickContext):
        """Adjust entropy rate based on tension."""
        sim = self.sim
        
        if not sim.world_dynamics_system or not sim.entropy_system or not sim.world_map:
            return
        
        # Use cached average tension
        avg_tension = self._cache.get_or_compute(
            "avg_district_tension", ctx.turn,
            lambda: self._compute_avg_tension(),
            max_age=5
        )
        
        if avg_tension is not None and avg_tension > 0:
            tension_factor = 1.0 + (avg_tension / 100.0) * 2.0
            sim.entropy_system.adjust_entropy_rate(tension_factor)
        else:
            sim.entropy_system.reset_entropy_rate()
    
    def _compute_avg_tension(self) -> float:
        """Compute average tension across districts."""
        sim = self.sim
        
        total_tension = 0.0
        count = 0
        
        for district_id in sim.world_map.regions.keys():
            district = sim.world_dynamics_system.get_district(district_id)
            if district:
                total_tension += district.tension_state.multi_tension.get_average()
                count += 1
        
        return total_tension / count if count > 0 else 0.0
    
    def _advance_human_agents(self, ctx: WorldTickContext):
        """Advance human agents for all districts."""
        sim = self.sim
        turn = ctx.turn
        
        use_advanced = sim.world_dynamics_system is not None
        
        for district_id, region in sim.world_map.regions.items():
            # Get or compute district resources
            district_resources = self._get_district_resources(district_id, ctx)
            
            # Get location IDs
            location_ids = [loc.id for loc in region.locations]
            
            # Link systems
            if hasattr(sim, 'world_flags_system'):
                sim.human_agent_system._world_flags_system = sim.world_flags_system
            
            # Advance agents
            human_events = sim.human_agent_system.advance(
                district_resources, location_ids, sim.world_map, turn,
                ctx.extinction_risk, ctx.population_pressure, 0.0,
                weather_system=sim.weather_system
            )
            ctx.all_human_events.extend(human_events)
    
    def _get_district_resources(self, district_id: str, ctx: WorldTickContext) -> Dict[str, Any]:
        """Get district resources, using cache where possible."""
        sim = self.sim
        
        if sim.world_dynamics_system:
            district = sim.world_dynamics_system.get_district(district_id)
            if district:
                return {
                    "food_stock": district.food_stock,
                    "credits_pool": district.credits_pool,
                    "jobs_available": district.jobs_available,
                    "security_level": district.security_level,
                    "tension": district.tension_state.tension,
                    "scarcity": district.pressure.food > 0.7
                }
        
        # Fallback
        return {
            "food_stock": 50, "credits_pool": 100, "jobs_available": 5,
            "security_level": 70, "tension": 20, "scarcity": False
        }
    
    def _drift_cultures(self, ctx: WorldTickContext):
        """Apply culture drift to districts."""
        sim = self.sim
        
        if not sim.world_dynamics_system or not sim.world_map:
            return
        
        for district_id in sim.world_map.regions.keys():
            district = sim.world_dynamics_system.get_district(district_id)
            if district and district.culture:
                sim.world_dynamics_system.culture_system.drift_culture(district_id)
    
    @staticmethod
    def _get_event_type_str(event) -> str:
        """Extract event type as string."""
        if hasattr(event, 'event_type'):
            if hasattr(event.event_type, 'value'):
                return event.event_type.value
            return str(event.event_type)
        return 'unknown'


# Global instance for easy access
_world_tick_phases: Optional[WorldTickPhases] = None


def get_world_tick_phases(sim: 'Simulation') -> WorldTickPhases:
    """Get or create world tick phases instance."""
    global _world_tick_phases
    if _world_tick_phases is None or _world_tick_phases.sim != sim:
        _world_tick_phases = WorldTickPhases(sim)
    return _world_tick_phases
