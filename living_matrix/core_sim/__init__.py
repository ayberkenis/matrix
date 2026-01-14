"""Core simulation step functions and performance optimizations."""

from .simulation_step_helpers import *
from .agent_tiers import (
    AgentTier,
    AgentTierManager,
    TierAssignment,
    TierState
)
from .tick_phases import (
    TickPhase,
    PhaseResult,
    PhaseContext,
    TickPhaseExecutor,
    skip_reproduction_for_large_pop,
    skip_conflicts_for_large_pop
)
from .parallel import (
    ParallelExecutor,
    AgentBatch,
    BatchResult,
    get_parallel_executor,
    partition_agents_deterministic
)
from .statistics import (
    RunningStats,
    PopulationStats,
    CohortManager,
    StatisticalSampler,
    get_population_stats,
    get_cohort_manager,
    get_sampler
)

# New optimization modules
from .world_heartbeat import (
    WorldHeartbeat,
    WorldSystem,
    get_heartbeat,
    reset_heartbeat,
)
from .async_snapshot import (
    AsyncSnapshotBuilder,
    DirtyTracker,
    SnapshotPriority,
    get_snapshot_builder,
    init_snapshot_builder,
    shutdown_snapshot_builder,
)
from .aggregate_cache import (
    AggregateCache,
    PopulationAggregates,
    DistrictAggregates,
    get_aggregate_cache,
    get_population_aggregates,
    get_district_aggregates,
)
from .agent_scheduler import (
    AgentScheduler,
    AgentSleepState,
    get_agent_scheduler,
)
from .cleanup import (
    CleanupManager,
    DeadAgentManager,
    RelationshipPruner,
    get_cleanup_manager,
)
from .population_compression import (
    PopulationCompressor,
    CohortStats,
    get_population_compressor,
)
from .watchdog import (
    TurnTimeWatchdog,
    TurnTiming,
    get_watchdog,
)
from .optimization import (
    OptimizationOrchestrator,
    OptimizationConfig,
    get_optimizer,
    reset_optimizer,
)