"""Constants for beliefs system."""

# BeliefSystem defaults
DEFAULT_BELIEF_DECAY_RATE = 0.01  # Confidence decays by this per turn
DEFAULT_BELIEF_SPREAD_PROBABILITY = 0.15  # Probability of spreading belief during interaction

# Belief confidence ranges by source
RUMOR_CONFIDENCE_MIN = 0.3
RUMOR_CONFIDENCE_MAX = 0.6
EVENT_CONFIDENCE_MIN = 0.6
EVENT_CONFIDENCE_MAX = 0.9
INTERACTION_CONFIDENCE_MIN = 0.4
INTERACTION_CONFIDENCE_MAX = 0.7
EXPERIENCE_CONFIDENCE_MIN = 0.7
EXPERIENCE_CONFIDENCE_MAX = 1.0

# Belief spread confidence reduction
SPREAD_CONFIDENCE_MULTIPLIER = 0.7

# Belief merge confidence decay
MERGE_CONFIDENCE_DECAY = 0.9

# Movement bias weights
SAFETY_BELIEF_WEIGHT = 0.6
FOOD_BELIEF_WEIGHT = 0.4

# Conflict/cooperation likelihood modifiers
# Reduced from 0.5 to 0.15 to reduce conflict event spam
CONFLICT_LIKELIHOOD_MULTIPLIER = 0.15
CONFLICT_LIKELIHOOD_BASE = 0.7  # Reduced from 1.0
COOPERATION_LIKELIHOOD_MULTIPLIER = 0.5
COOPERATION_LIKELIHOOD_BASE = 1.0
COOPERATION_LIKELIHOOD_REDUCTION = 0.3
