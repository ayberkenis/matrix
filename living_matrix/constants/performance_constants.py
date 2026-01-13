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
