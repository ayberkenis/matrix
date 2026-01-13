"""
Central configuration module for Living Matrix.

All feature flags and configuration values are read from environment variables
or use sensible defaults. Learning features are strictly opt-in.

Usage:
    from living_matrix.config import config
    
    if config.LEARNING_ENABLED:
        # Apply learning modulation
        pass

Environment Variables:
    REDIS_URL - Redis connection URL (default: redis://localhost:6379)
    LM_LEARNING_ENABLED - Enable learning features (default: false)
    LM_MICRO_MEMORY_ENABLED - Enable agent micro-memory (default: false)
    LM_DISTRICT_LEARNING_ENABLED - Enable district policy learning (default: false)
    LM_POPULATION_MEMORY_ENABLED - Enable population memory (default: false)
    LM_ACTIVE_SET_ENABLED - Enable active set limiting (default: false)
    LM_MAX_ACTIVE_AGENTS - Maximum active agents when active set enabled (default: 500)
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


def _env_bool(key: str, default: bool = False) -> bool:
    """Read boolean from environment variable."""
    val = os.environ.get(key, str(default)).lower()
    return val in ('true', '1', 'yes', 'on')


def _env_int(key: str, default: int) -> int:
    """Read integer from environment variable."""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Read float from environment variable."""
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


@dataclass
class LearningConfig:
    """
    Configuration for learning and memory features.
    
    All learning features are DISABLED by default to preserve
    deterministic behavior with the same seed.
    
    Safety Guarantees:
    - All learned weights are clipped to CLIP_RANGES
    - All memory buffers are bounded
    - Learning rates are very small to prevent instability
    """
    
    # ========================================
    # FEATURE FLAGS (all default False)
    # ========================================
    
    # Master learning switch - must be True for any learning
    LEARNING_ENABLED: bool = field(default_factory=lambda: _env_bool('LM_LEARNING_ENABLED', False))
    
    # Enable agent micro-memory (small per-agent ring buffers in Redis)
    MICRO_MEMORY_ENABLED: bool = field(default_factory=lambda: _env_bool('LM_MICRO_MEMORY_ENABLED', False))
    
    # Enable district-level policy learning
    DISTRICT_LEARNING_ENABLED: bool = field(default_factory=lambda: _env_bool('LM_DISTRICT_LEARNING_ENABLED', False))
    
    # Enable population memory (compressed rolling stats)
    POPULATION_MEMORY_ENABLED: bool = field(default_factory=lambda: _env_bool('LM_POPULATION_MEMORY_ENABLED', False))
    
    # Enable active set limiting (LLM context window analog)
    ACTIVE_SET_ENABLED: bool = field(default_factory=lambda: _env_bool('LM_ACTIVE_SET_ENABLED', False))
    
    # ========================================
    # ACTIVE SET CONFIGURATION
    # ========================================
    
    # Maximum agents to fully simulate per tick (when ACTIVE_SET_ENABLED)
    MAX_ACTIVE_AGENTS: int = field(default_factory=lambda: _env_int('LM_MAX_ACTIVE_AGENTS', 500))
    
    # Minimum agents to always fully simulate
    MIN_ACTIVE_AGENTS: int = field(default_factory=lambda: _env_int('LM_MIN_ACTIVE_AGENTS', 100))
    
    # How often to rotate active set (ticks)
    ACTIVE_SET_ROTATION_INTERVAL: int = field(default_factory=lambda: _env_int('LM_ACTIVE_SET_ROTATION', 5))
    
    # ========================================
    # LEARNING SAFETY PARAMETERS
    # ========================================
    
    # Learning rates (very small for stability)
    LEARNING_RATE_DISTRICT: float = field(default_factory=lambda: _env_float('LM_LR_DISTRICT', 0.005))
    LEARNING_RATE_AGENT: float = field(default_factory=lambda: _env_float('LM_LR_AGENT', 0.001))
    
    # Clip ranges for learned weights [min_multiplier, max_multiplier]
    WEIGHT_CLIP_MIN: float = field(default_factory=lambda: _env_float('LM_WEIGHT_CLIP_MIN', 0.75))
    WEIGHT_CLIP_MAX: float = field(default_factory=lambda: _env_float('LM_WEIGHT_CLIP_MAX', 1.25))
    
    # Additive bias clip range
    BIAS_CLIP_MIN: float = field(default_factory=lambda: _env_float('LM_BIAS_CLIP_MIN', -10.0))
    BIAS_CLIP_MAX: float = field(default_factory=lambda: _env_float('LM_BIAS_CLIP_MAX', 10.0))
    
    # ========================================
    # MEMORY WINDOW SIZES (fixed, small)
    # ========================================
    
    # Agent micro-memory ring buffer size
    AGENT_MEMORY_SIZE: int = field(default_factory=lambda: _env_int('LM_AGENT_MEMORY_SIZE', 16))
    
    # District memory window size
    DISTRICT_MEMORY_SIZE: int = field(default_factory=lambda: _env_int('LM_DISTRICT_MEMORY_SIZE', 64))
    
    # Population memory window size
    POPULATION_MEMORY_SIZE: int = field(default_factory=lambda: _env_int('LM_POPULATION_MEMORY_SIZE', 128))
    
    # ========================================
    # REDIS CONFIGURATION
    # ========================================
    
    REDIS_URL: str = field(default_factory=lambda: os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    
    # Redis key prefix
    REDIS_KEY_PREFIX: str = field(default_factory=lambda: os.environ.get('LM_REDIS_PREFIX', 'lm'))
    
    # Redis connection timeout (seconds)
    REDIS_TIMEOUT: float = field(default_factory=lambda: _env_float('LM_REDIS_TIMEOUT', 1.0))
    
    # ========================================
    # STABILITY DETECTION
    # ========================================
    
    # If population changes by more than this % in one tick, dampen learning
    INSTABILITY_THRESHOLD: float = field(default_factory=lambda: _env_float('LM_INSTABILITY_THRESHOLD', 0.1))
    
    # Learning rate dampening factor when instability detected
    INSTABILITY_DAMPENING: float = field(default_factory=lambda: _env_float('LM_INSTABILITY_DAMPENING', 0.1))
    
    def is_any_learning_active(self) -> bool:
        """Check if any learning feature is actually active."""
        return (
            self.LEARNING_ENABLED and
            (self.MICRO_MEMORY_ENABLED or 
             self.DISTRICT_LEARNING_ENABLED or 
             self.POPULATION_MEMORY_ENABLED)
        )
    
    def clip_weight(self, value: float) -> float:
        """Clip a learned weight to safe range."""
        return max(self.WEIGHT_CLIP_MIN, min(self.WEIGHT_CLIP_MAX, value))
    
    def clip_bias(self, value: float) -> float:
        """Clip an additive bias to safe range."""
        return max(self.BIAS_CLIP_MIN, min(self.BIAS_CLIP_MAX, value))


# Global singleton config instance
config = LearningConfig()


def reload_config() -> LearningConfig:
    """
    Reload configuration from environment.
    
    Useful for testing or runtime reconfiguration.
    """
    global config
    config = LearningConfig()
    return config


def get_config() -> LearningConfig:
    """Get the current configuration instance."""
    return config
