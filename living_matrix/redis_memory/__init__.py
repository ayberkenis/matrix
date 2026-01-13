"""
Redis-backed memory architecture for Living Matrix.

This module provides optional, opt-in memory layers that enable
learning and adaptation without affecting core simulation behavior.

NOTE: This is named 'redis_memory' to avoid shadowing the existing
'memory.py' which contains SemanticGraph, EpisodicMemory, etc.

Memory Layers:
1. Agent Micro-Memory - Small per-agent ring buffers (last actions/outcomes)
2. District Policy - Learned policy weights per district
3. Population Memory - Compressed rolling statistics

All memory features:
- Are DISABLED by default
- Fail gracefully if Redis unavailable
- Use bounded, fixed-size buffers
- Never block the simulation

Usage:
    from living_matrix.redis_memory import get_memory_manager
    
    mm = get_memory_manager()
    if mm.is_available():
        mm.record_agent_action(agent_id, action, success)
"""

from living_matrix.redis_memory.redis_client import (
    RedisMemoryClient,
    get_redis_client,
    is_redis_available
)
from living_matrix.redis_memory.manager import (
    MemoryManager,
    get_memory_manager
)

__all__ = [
    'RedisMemoryClient',
    'get_redis_client',
    'is_redis_available',
    'MemoryManager',
    'get_memory_manager'
]
