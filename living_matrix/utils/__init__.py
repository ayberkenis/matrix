"""Utility modules for Living Matrix simulation."""

from .random_utils import *
from .math_utils import *
from .time_utils import *
from .logging_utils import *
from .guards import *
from .spatial_index import SpatialIndex
from .observability import (
    get_observer,
    PerformanceObserver,
    TickMetrics,
    AggregateMetrics,
    timed_phase
)
from .object_pool import (
    ObjectPool,
    EventBuffer,
    EventRecord,
    LookupCache,
    NeedsSnapshot,
    TraitsSnapshot,
    ResourceState,
    get_event_pool,
    get_event_buffer,
    get_lookup_cache
)