"""Event system constants."""

# Event types
EVENT_TYPES = [
    'commute', 'market_trade', 'shift_start', 'shift_end',
    'meal', 'rest', 'meeting', 'minor_conflict', 'helping', 'discovery'
]

# Event generation
SPONTANEOUS_EVENT_CHANCE = 0.1  # 10% chance per turn

# Tensor modifier thresholds
TENSOR_MODIFIER_POSITIVE_THRESHOLD = 0.05
TENSOR_MODIFIER_NEGATIVE_THRESHOLD = -0.05
TENSOR_MODIFIER_MAX = 0.1  # 10% max influence

# Event log size
EVENT_LOG_MAX_SIZE = 200
