"""Optimization Orchestrator - Integrates all performance optimizations.

This module provides a single integration point for all optimization
systems, making it easy to enable/disable and configure optimizations.

COMPONENTS:
- World Heartbeat: Tick frequency control
- Async Snapshot: Non-blocking serialization
- Aggregate Cache: Cached global computations
- Agent Scheduler: Sleep/wake system
- Cleanup Manager: Dead agent and relationship pruning
- Population Compressor: Statistical agent compression
- Watchdog: Turn time monitoring and emergency mode

USAGE:
    from living_matrix.core_sim.optimization import get_optimizer
    
    opt = get_optimizer()
    opt.initialize(simulation)
    
    # In step():
    opt.pre_turn(turn)
    ... run simulation ...
    opt.post_turn(turn, phase_timings)
"""

import logging
import os
from typing import Dict, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

from .world_heartbeat import WorldHeartbeat, WorldSystem, get_heartbeat, reset_heartbeat
from .async_snapshot import AsyncSnapshotBuilder, get_snapshot_builder, init_snapshot_builder, shutdown_snapshot_builder
from .aggregate_cache import get_aggregate_cache, get_population_aggregates, reset_aggregate_cache
from .agent_scheduler import AgentScheduler, get_agent_scheduler, reset_agent_scheduler
from .cleanup import CleanupManager, get_cleanup_manager, reset_cleanup_manager
from .population_compression import PopulationCompressor, get_population_compressor, reset_population_compressor
from .watchdog import TurnTimeWatchdog, get_watchdog, reset_watchdog

if TYPE_CHECKING:
    from ..core import Simulation
    from ..human_agent import HumanAgentSystem

logger = logging.getLogger(__name__)


# Environment variable to disable all optimizations (for debugging)
DISABLE_OPTIMIZATIONS = os.environ.get("LM_DISABLE_OPTIMIZATIONS", "false").lower() == "true"


@dataclass
class OptimizationConfig:
    """Configuration for optimization systems."""
    # Master switches
    enable_heartbeat: bool = True
    enable_async_snapshot: bool = True
    enable_caching: bool = True
    enable_agent_scheduler: bool = True
    enable_cleanup: bool = True
    enable_compression: bool = True
    enable_watchdog: bool = True
    
    # Heartbeat intervals (overrides defaults)
    economy_interval: Optional[int] = None
    district_interval: Optional[int] = None
    tension_interval: Optional[int] = None
    
    # Compression settings
    max_active_agents: int = 1000
    compression_threshold: int = 800
    
    # Cleanup settings
    max_dead_agents: int = 500
    cleanup_interval: int = 20
    
    # Watchdog settings
    emergency_threshold_ms: float = 5000
    slow_turns_before_emergency: int = 3


class OptimizationOrchestrator:
    """
    Main orchestrator for all optimization systems.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self._sim: Optional['Simulation'] = None
        self._initialized = False
        
        # Component references (lazy initialized)
        self._heartbeat: Optional[WorldHeartbeat] = None
        self._snapshot_builder: Optional[AsyncSnapshotBuilder] = None
        self._scheduler: Optional[AgentScheduler] = None
        self._cleanup: Optional[CleanupManager] = None
        self._compressor: Optional[PopulationCompressor] = None
        self._watchdog: Optional[TurnTimeWatchdog] = None
    
    def initialize(self, sim: 'Simulation'):
        """
        Initialize all optimization systems with the simulation.
        
        Call this once after simulation is created.
        """
        if DISABLE_OPTIMIZATIONS:
            logger.warning("All optimizations DISABLED via LM_DISABLE_OPTIMIZATIONS")
            return
        
        self._sim = sim
        
        # Initialize components
        if self.config.enable_heartbeat:
            self._heartbeat = get_heartbeat()
            logger.debug("World heartbeat initialized")
        
        if self.config.enable_async_snapshot:
            # Snapshot builder needs a build function
            # This will be provided when first snapshot is requested
            pass
        
        if self.config.enable_caching:
            get_aggregate_cache()  # Initialize
            logger.debug("Aggregate cache initialized")
        
        if self.config.enable_agent_scheduler:
            self._scheduler = get_agent_scheduler()
            logger.debug("Agent scheduler initialized")
        
        if self.config.enable_cleanup:
            self._cleanup = get_cleanup_manager()
            logger.debug("Cleanup manager initialized")
        
        if self.config.enable_compression:
            self._compressor = get_population_compressor()
            logger.debug("Population compressor initialized")
        
        if self.config.enable_watchdog:
            self._watchdog = get_watchdog()
            logger.debug("Turn time watchdog initialized")
        
        self._initialized = True
        logger.info("Optimization systems initialized")
    
    def shutdown(self):
        """Shutdown all optimization systems."""
        shutdown_snapshot_builder()
        self._initialized = False
        logger.info("Optimization systems shut down")
    
    def pre_turn(self, turn: int, agent_count: int = 0):
        """
        Called at the start of each turn.
        
        - Starts watchdog timing
        - Updates heartbeat population
        - Checks emergency mode settings
        """
        if not self._initialized or DISABLE_OPTIMIZATIONS:
            return
        
        # Start watchdog
        if self._watchdog:
            self._watchdog.start_turn(turn)
        
        # Update heartbeat population for interval scaling
        if self._heartbeat:
            self._heartbeat.set_population(agent_count)
        
        # Check for emergency mode adjustments
        self._apply_emergency_settings()
    
    def post_turn(
        self,
        turn: int,
        phase_timings: Dict[str, float] = None,
        agent_count: int = 0
    ):
        """
        Called at the end of each turn.
        
        - Ends watchdog timing
        - Runs cleanup if needed
        - Checks for compression needs
        - Enqueues snapshot
        """
        if not self._initialized or DISABLE_OPTIMIZATIONS:
            return
        
        # End watchdog timing
        if self._watchdog:
            self._watchdog.end_turn(turn, phase_timings, agent_count)
        
        # Run cleanup if needed
        if self._cleanup and self._sim and self._sim.human_agent_system:
            if self._cleanup.should_run_cleanup(turn):
                self._cleanup.run_cleanup(self._sim.human_agent_system, turn)
        
        # Check for compression
        if self._compressor and self._sim and self._sim.human_agent_system:
            if self._compressor.should_compress(self._sim.human_agent_system):
                self._compressor.compress_excess(self._sim.human_agent_system, turn)
    
    def _apply_emergency_settings(self):
        """Apply emergency mode settings if active."""
        if not self._watchdog or not self._watchdog.is_emergency_mode:
            return
        
        settings = self._watchdog.get_emergency_settings()
        
        # Increase heartbeat intervals
        if self._heartbeat and settings.get('interval_multiplier', 1) > 1:
            multiplier = settings['interval_multiplier']
            for system in WorldSystem:
                current = self._heartbeat.get_interval(system)
                self._heartbeat.set_interval(system, current * multiplier)
        
        # Reduce max active agents
        if self._compressor and settings.get('max_active_agents'):
            self._compressor.max_active = settings['max_active_agents']
    
    # ========================================================================
    # HEARTBEAT HELPERS
    # ========================================================================
    
    def should_update_system(self, system: WorldSystem, turn: int) -> bool:
        """Check if a world system should update this turn."""
        if not self._heartbeat or DISABLE_OPTIMIZATIONS:
            return True
        return self._heartbeat.should_update(system, turn)
    
    def record_system_update(self, system: WorldSystem, turn: int, duration_ms: float = 0.0):
        """Record that a system was updated."""
        if self._heartbeat:
            self._heartbeat.record_update(system, turn, duration_ms)
    
    def mark_system_dirty(self, system: WorldSystem):
        """Mark a system for forced update."""
        if self._heartbeat:
            self._heartbeat.mark_dirty(system)
    
    # ========================================================================
    # CACHING HELPERS
    # ========================================================================
    
    def get_cached_or_compute(
        self,
        key: str,
        turn: int,
        compute_func,
        max_age: int = 5
    ) -> Any:
        """Get cached value or compute it."""
        if DISABLE_OPTIMIZATIONS:
            return compute_func()
        
        cache = get_aggregate_cache()
        return cache.get_or_compute(key, turn, compute_func, max_age)
    
    def invalidate_cache(self, key: str):
        """Invalidate a cache entry."""
        cache = get_aggregate_cache()
        cache.invalidate(key)
    
    def invalidate_population_caches(self):
        """Invalidate all population-related caches."""
        pop_agg = get_population_aggregates()
        pop_agg.invalidate_all()
    
    # ========================================================================
    # AGENT SCHEDULING HELPERS
    # ========================================================================
    
    def update_agent_activity(
        self,
        agents: Dict,
        turn: int,
        events: list = None,
        active_districts: set = None
    ):
        """Update agent activity scores and sleep states."""
        if not self._scheduler or DISABLE_OPTIMIZATIONS:
            return
        self._scheduler.update_activity_scores(agents, turn, events, active_districts)
    
    def get_active_agents(self, agents: Dict) -> list:
        """Get list of agents that should be fully processed."""
        if not self._scheduler or DISABLE_OPTIMIZATIONS:
            return list(agents.values())
        return self._scheduler.get_active_agents(agents)
    
    def get_sleeping_agents(self, agents: Dict) -> list:
        """Get list of sleeping agents."""
        if not self._scheduler or DISABLE_OPTIMIZATIONS:
            return []
        return self._scheduler.get_sleeping_agents(agents)
    
    def advance_sleeping_agent(self, agent, turn: int):
        """Minimal advancement for sleeping agent."""
        if self._scheduler:
            self._scheduler.advance_sleeping_agent(agent, turn)
    
    # ========================================================================
    # COMPRESSION HELPERS
    # ========================================================================
    
    def advance_cohorts(self, turn: int, district_resources: Dict) -> tuple:
        """Advance statistical cohorts."""
        if not self._compressor or DISABLE_OPTIMIZATIONS:
            return 0, 0
        return self._compressor.advance_cohorts(turn, district_resources)
    
    def get_cohort_contribution(self, district_id: str) -> Dict:
        """Get economic/tension contribution from cohort."""
        if not self._compressor:
            return {'economic': 0, 'tension': 0, 'population': 0}
        
        cohort = self._compressor.cohorts.get(district_id)
        if not cohort:
            return {'economic': 0, 'tension': 0, 'population': 0}
        
        return {
            'economic': cohort.get_economic_contribution(),
            'tension': cohort.get_tension_contribution(),
            'population': cohort.count,
        }
    
    def get_effective_population(self) -> int:
        """Get total effective population (active + compressed)."""
        active = 0
        if self._sim and self._sim.human_agent_system:
            active = len([a for a in self._sim.human_agent_system.agents.values() if a.is_alive])
        
        compressed = 0
        if self._compressor:
            compressed = self._compressor.get_total_compressed_population()
        
        return active + compressed
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """Get comprehensive optimization statistics."""
        stats = {
            'enabled': not DISABLE_OPTIMIZATIONS and self._initialized,
        }
        
        if self._heartbeat:
            stats['heartbeat'] = self._heartbeat.get_statistics()
        
        if self._watchdog:
            stats['watchdog'] = self._watchdog.get_statistics()
        
        if self._scheduler:
            stats['scheduler'] = self._scheduler.get_statistics()
        
        if self._cleanup:
            stats['cleanup'] = self._cleanup.get_statistics()
        
        if self._compressor:
            stats['compression'] = self._compressor.get_statistics()
        
        cache = get_aggregate_cache()
        stats['cache'] = cache.get_statistics()
        
        return stats


# Global instance
_optimizer: Optional[OptimizationOrchestrator] = None


def get_optimizer(config: Optional[OptimizationConfig] = None) -> OptimizationOrchestrator:
    """Get or create the global optimization orchestrator."""
    global _optimizer
    if _optimizer is None:
        _optimizer = OptimizationOrchestrator(config)
    return _optimizer


def reset_optimizer():
    """Reset all optimization systems (for testing)."""
    global _optimizer
    
    if _optimizer:
        _optimizer.shutdown()
    
    _optimizer = None
    reset_heartbeat()
    reset_aggregate_cache()
    reset_agent_scheduler()
    reset_cleanup_manager()
    reset_population_compressor()
    reset_watchdog()
