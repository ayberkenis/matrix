"""
Redis client for Living Matrix memory architecture.

Provides a lightweight, singleton Redis client that:
- Reads connection URL from REDIS_URL environment variable
- Fails gracefully if Redis is unavailable
- Auto-disables memory features on connection failure
- Uses connection pooling for efficiency

IMPORTANT: Redis is used ONLY for memory, not for core simulation state.
"""

import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

from living_matrix.config import get_config

logger = logging.getLogger(__name__)

# Global state
_redis_client: Optional['RedisMemoryClient'] = None
_redis_available: bool = False
_redis_checked: bool = False


class RedisMemoryClient:
    """
    Lightweight Redis client wrapper for memory operations.
    
    All operations fail gracefully and return None/empty on error.
    Never blocks the simulation on Redis I/O.
    
    Key Prefixing:
        All keys are prefixed with config.REDIS_KEY_PREFIX (default: "lm")
        Example keys:
        - lm:agent:{agent_id}:mem
        - lm:district:{district_id}:policy
        - lm:district:{district_id}:popmem
    """
    
    def __init__(self, redis_url: str, timeout: float = 1.0):
        """
        Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL
            timeout: Connection timeout in seconds
        """
        self._url = redis_url
        self._timeout = timeout
        self._client = None
        self._prefix = get_config().REDIS_KEY_PREFIX
        self._connected = False
        
        self._try_connect()
    
    def _try_connect(self) -> bool:
        """Attempt to connect to Redis."""
        try:
            import redis
            self._client = redis.from_url(
                self._url,
                socket_timeout=self._timeout,
                socket_connect_timeout=self._timeout,
                decode_responses=True
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self._url}")
            return True
        except ImportError:
            logger.warning("redis-py not installed, memory features disabled")
            self._connected = False
            return False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, memory features disabled")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    def _key(self, *parts: str) -> str:
        """Build a prefixed key."""
        return f"{self._prefix}:{':'.join(parts)}"
    
    # ========================================
    # AGENT MICRO-MEMORY OPERATIONS
    # ========================================
    
    def push_agent_memory(self, agent_id: str, data: str, max_size: int = 16) -> bool:
        """
        Push data to agent's memory ring buffer.
        
        Uses LPUSH + LTRIM to maintain fixed size.
        
        Args:
            agent_id: Agent identifier
            data: Data to push (should be small, encoded string)
            max_size: Maximum buffer size
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            key = self._key("agent", agent_id, "mem")
            pipe = self._client.pipeline()
            pipe.lpush(key, data)
            pipe.ltrim(key, 0, max_size - 1)
            pipe.execute()
            return True
        except Exception as e:
            logger.debug(f"Redis push_agent_memory failed: {e}")
            return False
    
    def get_agent_memory(self, agent_id: str, count: int = 16) -> List[str]:
        """
        Get agent's recent memory entries.
        
        Args:
            agent_id: Agent identifier
            count: Number of recent entries to retrieve
            
        Returns:
            List of memory entries (most recent first)
        """
        if not self._connected:
            return []
        
        try:
            key = self._key("agent", agent_id, "mem")
            return self._client.lrange(key, 0, count - 1)
        except Exception as e:
            logger.debug(f"Redis get_agent_memory failed: {e}")
            return []
    
    # ========================================
    # DISTRICT POLICY OPERATIONS
    # ========================================
    
    def set_district_policy(self, district_id: str, policy: Dict[str, float]) -> bool:
        """
        Set district policy weights.
        
        Args:
            district_id: District identifier
            policy: Dict of policy weights
            
        Returns:
            True if successful
        """
        if not self._connected:
            return False
        
        try:
            key = self._key("district", district_id, "policy")
            # Convert floats to strings for Redis
            str_policy = {k: str(v) for k, v in policy.items()}
            self._client.hset(key, mapping=str_policy)
            return True
        except Exception as e:
            logger.debug(f"Redis set_district_policy failed: {e}")
            return False
    
    def get_district_policy(self, district_id: str) -> Dict[str, float]:
        """
        Get district policy weights.
        
        Args:
            district_id: District identifier
            
        Returns:
            Dict of policy weights (empty if not found)
        """
        if not self._connected:
            return {}
        
        try:
            key = self._key("district", district_id, "policy")
            data = self._client.hgetall(key)
            return {k: float(v) for k, v in data.items()}
        except Exception as e:
            logger.debug(f"Redis get_district_policy failed: {e}")
            return {}
    
    def update_district_policy_field(self, district_id: str, field: str, value: float) -> bool:
        """
        Update a single policy field.
        
        Args:
            district_id: District identifier
            field: Policy field name
            value: New value
            
        Returns:
            True if successful
        """
        if not self._connected:
            return False
        
        try:
            key = self._key("district", district_id, "policy")
            self._client.hset(key, field, str(value))
            return True
        except Exception as e:
            logger.debug(f"Redis update_district_policy_field failed: {e}")
            return False
    
    # ========================================
    # POPULATION MEMORY OPERATIONS
    # ========================================
    
    def push_population_stat(self, district_id: str, stat_type: str, 
                            value: float, max_size: int = 128) -> bool:
        """
        Push a population statistic to district memory.
        
        Args:
            district_id: District identifier
            stat_type: Type of stat (e.g., "hunger", "tension")
            value: Statistic value
            max_size: Maximum buffer size
            
        Returns:
            True if successful
        """
        if not self._connected:
            return False
        
        try:
            key = self._key("district", district_id, "popmem", stat_type)
            pipe = self._client.pipeline()
            pipe.lpush(key, str(value))
            pipe.ltrim(key, 0, max_size - 1)
            pipe.execute()
            return True
        except Exception as e:
            logger.debug(f"Redis push_population_stat failed: {e}")
            return False
    
    def get_population_stats(self, district_id: str, stat_type: str, 
                            count: int = 128) -> List[float]:
        """
        Get recent population statistics.
        
        Args:
            district_id: District identifier
            stat_type: Type of stat
            count: Number of recent entries
            
        Returns:
            List of stat values (most recent first)
        """
        if not self._connected:
            return []
        
        try:
            key = self._key("district", district_id, "popmem", stat_type)
            data = self._client.lrange(key, 0, count - 1)
            return [float(v) for v in data]
        except Exception as e:
            logger.debug(f"Redis get_population_stats failed: {e}")
            return []
    
    # ========================================
    # BATCH OPERATIONS
    # ========================================
    
    def push_batch_agent_memory(self, updates: List[tuple]) -> int:
        """
        Push multiple agent memory updates in a pipeline.
        
        Args:
            updates: List of (agent_id, data, max_size) tuples
            
        Returns:
            Number of successful pushes
        """
        if not self._connected or not updates:
            return 0
        
        try:
            pipe = self._client.pipeline()
            for agent_id, data, max_size in updates:
                key = self._key("agent", agent_id, "mem")
                pipe.lpush(key, data)
                pipe.ltrim(key, 0, max_size - 1)
            pipe.execute()
            return len(updates)
        except Exception as e:
            logger.debug(f"Redis push_batch_agent_memory failed: {e}")
            return 0
    
    def push_batch_population_stats(self, updates: List[tuple]) -> int:
        """
        Push multiple population stats in a pipeline.
        
        Args:
            updates: List of (district_id, stat_type, value, max_size) tuples
            
        Returns:
            Number of successful pushes
        """
        if not self._connected or not updates:
            return 0
        
        try:
            pipe = self._client.pipeline()
            for district_id, stat_type, value, max_size in updates:
                key = self._key("district", district_id, "popmem", stat_type)
                pipe.lpush(key, str(value))
                pipe.ltrim(key, 0, max_size - 1)
            pipe.execute()
            return len(updates)
        except Exception as e:
            logger.debug(f"Redis push_batch_population_stats failed: {e}")
            return 0
    
    def close(self):
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._connected = False


def get_redis_client() -> Optional[RedisMemoryClient]:
    """
    Get the singleton Redis client.
    
    Returns None if Redis is not available.
    """
    global _redis_client, _redis_available, _redis_checked
    
    if not _redis_checked:
        _redis_checked = True
        cfg = get_config()
        
        # Only create client if some memory feature is enabled
        if cfg.is_any_learning_active():
            _redis_client = RedisMemoryClient(cfg.REDIS_URL, cfg.REDIS_TIMEOUT)
            _redis_available = _redis_client.is_connected()
        else:
            _redis_available = False
    
    return _redis_client if _redis_available else None


def is_redis_available() -> bool:
    """Check if Redis is available and connected."""
    get_redis_client()  # Ensure we've checked
    return _redis_available


def reset_redis_client():
    """Reset the Redis client (for testing)."""
    global _redis_client, _redis_available, _redis_checked
    if _redis_client:
        _redis_client.close()
    _redis_client = None
    _redis_available = False
    _redis_checked = False
