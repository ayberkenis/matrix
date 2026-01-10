"""Simulation system constants."""

# Auto-save interval
AUTO_SAVE_INTERVAL = 10  # Save every N turns

# Low diversity tracking
LOW_DIVERSITY_THRESHOLD = 0.15
LOW_DIVERSITY_TURNS_THRESHOLD = 30

# Expression drive thresholds
EXPRESSION_SPEAK_THRESHOLD = 0.30
MIN_VOCABULARY_SIZE = 8

# Heartbeat interval
HEARTBEAT_INTERVAL = 10  # Every 10 turns

# Stimulus decay
STIMULUS_DECAY_FACTOR = 0.85  # Decay per turn
STIMULUS_DECAY_MIN_WEIGHT = 0.01  # Only apply if still significant

# Internal thought weights
INTERNAL_MOTIF_WEIGHT = 0.1
INTERNAL_EDGE_WEIGHT = 0.5

# Lexicon sprout thresholds
LEXICON_SPROUT_NOVELTY_THRESHOLD = 0.6
LEXICON_SPROUT_MAX_EDGES = 10
LEXICON_SPROUT_MIN_TOKENS = 1
LEXICON_SPROUT_MAX_TOKENS = 3

# Minimum utterance length
MIN_UTTERANCE_LENGTH = 6

# Agent system initialization
INITIAL_AGENTS_MIN = 8
INITIAL_AGENTS_MAX = 24
HUMAN_AGENTS_MIN = 12
HUMAN_AGENTS_MAX = 30
HUMAN_AGENTS_FLOOR = 20  # At least 20 agents

# Bulletin interval
BULLETIN_INTERVAL = 5  # Print bulletin every N turns

# Tick delay
DEFAULT_TICK_DELAY_MS = 50  # milliseconds between autonomous ticks
