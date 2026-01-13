"""
Decision Modulator for Living Matrix.

Provides safe learning-based modulation of agent decisions.

CRITICAL SAFETY GUARANTEES:
1. Decisions are MODULATED, not replaced
2. Base logic always executes first
3. Modulation is multiplicative with clipping [0.75, 1.25]
4. When learning disabled, code path is BIT-FOR-BIT identical
5. All random behavior preserved (deterministic with seed)

Modulation is applied by scaling action scores:
    modulated_score = base_score * (1.0 + clipped_bias)

Where clipped_bias is in range [-0.25, +0.25] (from clip range 0.75-1.25).
"""

import logging
from typing import Dict, Optional, TYPE_CHECKING

from living_matrix.config import get_config
from living_matrix.redis_memory import get_memory_manager

if TYPE_CHECKING:
    from living_matrix.dataclasses import HumanAgent

logger = logging.getLogger(__name__)


class DecisionModulator:
    """
    Applies learned modulation to agent decisions.
    
    When active:
    - Fetches district modifiers from memory
    - Applies multiplicative bias to action scores
    - All biases are strictly clipped
    
    When inactive:
    - Returns scores unchanged
    - Zero overhead in decision path
    """
    
    __slots__ = ('_config', '_memory', '_active', '_cache', '_cache_tick')
    
    def __init__(self):
        self._config = get_config()
        self._memory = None
        self._active = False
        self._cache: Dict[str, Dict[str, float]] = {}
        self._cache_tick = -1
    
    def _ensure_initialized(self):
        """Lazy initialization of memory manager."""
        if self._memory is None:
            self._memory = get_memory_manager()
            self._active = (
                self._config.LEARNING_ENABLED and
                self._config.DISTRICT_LEARNING_ENABLED and
                self._memory is not None and
                self._memory.is_available()
            )
    
    def is_active(self) -> bool:
        """
        Check if modulation is active.
        
        Returns False if:
        - Learning disabled in config
        - District learning disabled
        - Redis unavailable
        """
        self._ensure_initialized()
        return self._active
    
    def apply_modulation(
        self,
        action_scores: Dict[str, float],
        agent: 'HumanAgent',
        district_id: str,
        turn: int
    ) -> Dict[str, float]:
        """
        Apply learned modulation to action scores.
        
        HOT PATH - CALLED PER AGENT PER TICK (when learning enabled)
        
        Args:
            action_scores: Base action scores from decide_action
            agent: The agent making the decision
            district_id: Agent's district for policy lookup
            turn: Current turn number
            
        Returns:
            Modulated action scores (or unchanged if learning disabled)
        """
        if not self.is_active():
            return action_scores
        
        # Get district modifiers (cached per tick)
        modifiers = self._get_cached_modifiers(district_id, turn)
        if not modifiers:
            return action_scores
        
        # Apply multiplicative modulation with clipping
        clip = self._config.clip_weight
        
        modulated = {}
        for action, score in action_scores.items():
            modifier = 1.0
            
            # Map actions to modifier types
            if action in ('socialize', 'help'):
                modifier = clip(modifiers.get('cooperation_bias', 1.0))
            elif action == 'theft':
                modifier = clip(modifiers.get('aggression_bias', 1.0))
            elif action == 'work':
                modifier = clip(modifiers.get('work_bias', 1.0))
            elif action == 'move':
                modifier = clip(modifiers.get('migration_bias', 1.0))
            elif action in ('trade', 'rest'):
                # Trade/rest modulated by risk aversion (inverse)
                risk = modifiers.get('risk_aversion', 1.0)
                modifier = clip(2.0 - risk)  # Inverted
            
            # Apply multiplicative modulation
            modulated[action] = score * modifier
        
        return modulated
    
    def _get_cached_modifiers(self, district_id: str, turn: int) -> Optional[Dict[str, float]]:
        """
        Get modifiers with per-tick caching.
        
        Minimizes Redis reads by caching per district per tick.
        """
        # Clear cache on new tick
        if self._cache_tick != turn:
            self._cache.clear()
            self._cache_tick = turn
        
        # Check cache
        if district_id in self._cache:
            return self._cache[district_id]
        
        # Load from memory manager
        if self._memory:
            mods = self._memory.get_district_modifiers(district_id)
            self._cache[district_id] = mods.to_dict()
            return self._cache[district_id]
        
        return None
    
    def record_action_outcome(
        self,
        agent_id: str,
        action: str,
        success: bool,
        district_id: str
    ):
        """
        Record action outcome for learning.
        
        Called after action execution to update learning signals.
        
        Args:
            agent_id: Agent identifier
            action: Action that was taken
            success: Whether the action succeeded
            district_id: Agent's district
        """
        if not self.is_active() or not self._memory:
            return
        
        # Record to agent micro-memory
        self._memory.record_agent_action(agent_id, action, success)
    
    def compute_district_learning_signal(
        self,
        district_id: str,
        cooperation_successes: int,
        cooperation_attempts: int,
        aggression_outcomes: int,
        aggression_attempts: int,
        work_productivity: float,
        migration_count: int,
        total_agents: int
    ):
        """
        Compute and apply learning signal for a district.
        
        Called once per tick per district (O(1) per district).
        
        Learning signals are in range [-1, +1]:
        - Positive = behavior was successful, increase bias
        - Negative = behavior failed, decrease bias
        """
        if not self.is_active() or not self._memory:
            return
        
        # Compute signals (normalized to [-1, +1])
        cooperation_signal = 0.0
        if cooperation_attempts > 0:
            success_rate = cooperation_successes / cooperation_attempts
            cooperation_signal = (success_rate - 0.5) * 2.0  # Map [0,1] to [-1,1]
        
        aggression_signal = 0.0
        if aggression_attempts > 0:
            success_rate = aggression_outcomes / aggression_attempts
            aggression_signal = (success_rate - 0.5) * 2.0
        
        # Productivity signal based on deviation from expected
        productivity_signal = (work_productivity - 0.5) * 2.0
        
        # Migration signal (positive if migration was beneficial)
        migration_signal = 0.0
        if total_agents > 0:
            migration_rate = migration_count / total_agents
            # Slight penalty for high migration (stability preference)
            migration_signal = (0.3 - migration_rate) * 2.0
        
        # Risk signal (neutral for now, could be based on deaths/survival)
        risk_signal = 0.0
        
        # Apply learning update
        self._memory.update_district_policy(
            district_id,
            cooperation_signal=cooperation_signal,
            aggression_signal=aggression_signal,
            productivity_signal=productivity_signal,
            migration_signal=migration_signal,
            risk_signal=risk_signal
        )


# Global singleton
_modulator: Optional[DecisionModulator] = None


def get_decision_modulator() -> DecisionModulator:
    """Get the singleton decision modulator."""
    global _modulator
    if _modulator is None:
        _modulator = DecisionModulator()
    return _modulator


def reset_decision_modulator():
    """Reset the decision modulator (for testing)."""
    global _modulator
    _modulator = None
