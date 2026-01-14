"""Performance and scaling constants for Living Matrix simulation.

These constants control parallel execution, memory optimization, and
performance observability without affecting simulation behavior.
"""

import os

# ============================================================================
# PARALLEL EXECUTION SETTINGS
# ============================================================================

# Enable/disable parallel processing (can be overridden by environment)
# Default to FALSE - serialization overhead outweighs benefit for small active sets
# The tier system already limits active agents to ~400, making parallel less effective
# Set LM_ENABLE_PARALLEL=true to enable if you have very heavy per-agent processing
ENABLE_PARALLEL = os.environ.get("LM_ENABLE_PARALLEL", "false").lower() == "true"

# Number of worker processes (0 = auto-detect based on CPU count)
# Default to 4 cores for good performance when enabled
WORKER_COUNT = int(os.environ.get("LM_WORKER_COUNT", "4"))

# Minimum agents before parallelization kicks in (below this, sequential is faster)
PARALLEL_THRESHOLD_AGENTS = 500

# Batch size for parallel agent processing
AGENT_BATCH_SIZE = 100

# ============================================================================
# AGENT TIER THRESHOLDS
# ============================================================================

# Population threshold for enabling tiered simulation
TIER_POPULATION_THRESHOLD = 200

# Fraction of agents to fully simulate each tick when population > threshold
# Lower fraction = faster ticks but less granular simulation
FULL_SIMULATION_FRACTION = 0.10  # Only 10% of agents fully simulated per tick

# Minimum number of fully-simulated agents regardless of population
MIN_FULL_SIMULATION_COUNT = 100

# Maximum number of active agents (hard cap for performance)
MAX_ACTIVE_SIMULATION_COUNT = 500

# Ticks between full updates for inactive agents
INACTIVE_AGENT_UPDATE_INTERVAL = 10  # Update inactive every 10 ticks

# For very large populations, use even more aggressive optimization
VERY_LARGE_POP_THRESHOLD = 3000
VERY_LARGE_POP_SIMULATION_FRACTION = 0.05  # Only 5% at very large populations
VERY_LARGE_MAX_ACTIVE = 400  # Hard cap for very large populations

# ============================================================================
# MEMORY OPTIMIZATION
# ============================================================================

# Maximum size of object pools (prevents unbounded memory growth)
MAX_POOL_SIZE = 10000

# Pre-allocated event buffer size
EVENT_BUFFER_SIZE = 1000

# Maximum memory entries per agent
MAX_AGENT_MEMORY_SIZE = 20

# Maximum relationships per agent before pruning weak ones
MAX_RELATIONSHIPS_PER_AGENT = 50

# Relationship pruning threshold (affection + trust below this gets pruned)
RELATIONSHIP_PRUNE_THRESHOLD = 0.15

# ============================================================================
# TICK OPTIMIZATION
# ============================================================================

# Population thresholds for skipping expensive operations
SKIP_REPRODUCTION_THRESHOLD = 3000  # Skip reproduction check every N ticks above this
SKIP_CONFLICTS_THRESHOLD = 2500  # Skip conflict check every N ticks above this
SKIP_NEEDS_UPDATE_THRESHOLD = 2000  # Skip needs update every N ticks above this

# Tick intervals for skipped operations (higher = more skipping)
REPRODUCTION_TICK_INTERVAL_LARGE_POP = 5
CONFLICT_TICK_INTERVAL_LARGE_POP = 3
NEEDS_TICK_INTERVAL_LARGE_POP = 2

# ============================================================================
# STATISTICAL COMPRESSION
# ============================================================================

# Use running averages instead of per-tick recalculation above this population
RUNNING_AVERAGE_THRESHOLD = 1000

# Sample size for statistical approximations (percentage of population)
STATISTICAL_SAMPLE_PERCENTAGE = 0.1

# Minimum sample size for statistical operations
MIN_STATISTICAL_SAMPLE = 50

# ============================================================================
# WORLD HEARTBEAT (Tick Frequency Control)
# ============================================================================

# Default tick intervals for world systems (turns between updates)
# Lower = more frequent updates, Higher = less computation
ECONOMY_TICK_INTERVAL = int(os.environ.get("LM_ECONOMY_INTERVAL", "3"))
DISTRICT_STATS_TICK_INTERVAL = int(os.environ.get("LM_DISTRICT_INTERVAL", "5"))
GLOBAL_METRICS_TICK_INTERVAL = int(os.environ.get("LM_METRICS_INTERVAL", "10"))
TENSION_UPDATE_TICK_INTERVAL = int(os.environ.get("LM_TENSION_INTERVAL", "2"))
CULTURE_DRIFT_TICK_INTERVAL = int(os.environ.get("LM_CULTURE_INTERVAL", "20"))
CAUSALITY_DECAY_TICK_INTERVAL = int(os.environ.get("LM_CAUSALITY_INTERVAL", "5"))
SNAPSHOT_TICK_INTERVAL = int(os.environ.get("LM_SNAPSHOT_INTERVAL", "1"))
PERSISTENCE_TICK_INTERVAL = int(os.environ.get("LM_PERSISTENCE_INTERVAL", "10"))

# Population thresholds for interval scaling
HEARTBEAT_SCALE_THRESHOLD = 500  # Scale intervals above this population
HEARTBEAT_SCALE_FACTOR = 2  # Multiply intervals by this when population > threshold

# ============================================================================
# DEAD AGENT CLEANUP
# ============================================================================

# Maximum number of dead agents to keep in memory
MAX_DEAD_AGENTS = int(os.environ.get("LM_MAX_DEAD_AGENTS", "500"))

# Number of dead agents to prune when cap is reached
DEAD_AGENT_PRUNE_COUNT = 100

# Interval for dead agent cleanup (turns)
DEAD_AGENT_CLEANUP_INTERVAL = 50

# ============================================================================
# AGGREGATE CACHING
# ============================================================================

# Maximum age (in turns) for cached aggregates before recomputation
CACHE_MAX_AGE_POPULATION = 1  # Population counts are critical
CACHE_MAX_AGE_TENSION = 5  # Tension can be slightly stale
CACHE_MAX_AGE_METRICS = 10  # Metrics can be more stale
CACHE_MAX_AGE_DISTRICT = 5  # District summaries

# ============================================================================
# ASYNC SNAPSHOT
# ============================================================================

# Enable async snapshot building
ENABLE_ASYNC_SNAPSHOT = os.environ.get("LM_ASYNC_SNAPSHOT", "true").lower() == "true"

# Maximum pending snapshot requests before dropping
MAX_SNAPSHOT_QUEUE_SIZE = 10

# ============================================================================
# AGENT SLEEP/WAKE SYSTEM
# ============================================================================

# Threshold for agent activity score (below this, agent sleeps)
AGENT_SLEEP_THRESHOLD = 0.3

# Needs stability threshold (needs below this delta = stable)
NEEDS_STABILITY_DELTA = 0.05

# Minimum turns before agent can sleep again after waking
WAKE_COOLDOWN_TURNS = 5

# Maximum fraction of agents that can sleep at once
MAX_SLEEPING_FRACTION = 0.6

# ============================================================================
# POPULATION COMPRESSION
# ============================================================================

# Maximum active (fully simulated) agents
MAX_ACTIVE_AGENTS = int(os.environ.get("LM_MAX_ACTIVE_AGENTS", "1000"))

# Compression kicks in above this population
COMPRESSION_THRESHOLD = 800

# Minimum agents to keep active regardless of compression
MIN_ACTIVE_AGENTS = 200

# ============================================================================
# OBSERVABILITY (Zero-cost when disabled)
# ============================================================================

# Enable performance metrics collection (can be enabled via environment)
ENABLE_METRICS = os.environ.get("LM_ENABLE_METRICS", "false").lower() == "true"

# Metrics collection interval (ticks between metric snapshots)
METRICS_INTERVAL = 10

# Log performance warnings when tick takes longer than this (milliseconds)
SLOW_TICK_THRESHOLD_MS = 100

# Enable detailed phase timing (more overhead)
ENABLE_PHASE_TIMING = os.environ.get("LM_PHASE_TIMING", "false").lower() == "true"

# ============================================================================
# TURN TIME WATCHDOG
# ============================================================================

# Maximum turn time before emergency mode (milliseconds)
EMERGENCY_TURN_TIME_MS = int(os.environ.get("LM_EMERGENCY_TIME_MS", "5000"))

# Number of slow turns before emergency mode activates
SLOW_TURNS_BEFORE_EMERGENCY = 3

# Emergency mode interval multiplier (increases all intervals)
EMERGENCY_INTERVAL_MULTIPLIER = 3

# Emergency mode maximum active agents
EMERGENCY_MAX_ACTIVE_AGENTS = 200


def get_worker_count() -> int:
    """Get optimal worker count based on CPU cores."""
    if WORKER_COUNT > 0:
        return WORKER_COUNT
    # Leave one core for main thread
    cpu_count = os.cpu_count() or 4
    return max(1, cpu_count - 1)


def should_use_parallel(agent_count: int) -> bool:
    """Determine if parallel processing should be used."""
    return ENABLE_PARALLEL and agent_count >= PARALLEL_THRESHOLD_AGENTS


def get_batch_count(agent_count: int) -> int:
    """Calculate number of batches for parallel processing."""
    if agent_count <= AGENT_BATCH_SIZE:
        return 1
    return (agent_count + AGENT_BATCH_SIZE - 1) // AGENT_BATCH_SIZE
