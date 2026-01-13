"""
Learning module for Living Matrix.

Provides safe, opt-in decision modulation based on learned patterns.

Key Principles:
- All learning is DISABLED by default
- When enabled, decisions are MODULATED, not replaced
- All learned values are CLIPPED to safe ranges
- Base logic always remains intact
- If learning disabled, decision path is BIT-FOR-BIT identical

Usage:
    from living_matrix.learning import get_decision_modulator
    
    modulator = get_decision_modulator()
    
    # Apply modulation to action scores (only if learning enabled)
    if modulator.is_active():
        scores = modulator.apply_modulation(scores, agent, district_id)
"""

from living_matrix.learning.modulator import (
    DecisionModulator,
    get_decision_modulator
)

__all__ = [
    'DecisionModulator',
    'get_decision_modulator'
]
