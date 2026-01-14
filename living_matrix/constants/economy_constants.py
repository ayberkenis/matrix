"""Economy system constants."""

# ============================================================================
# DISTRICT RESOURCE DEFAULTS
# ============================================================================

# Food capacity scales with population: base + (population * FOOD_PER_CAPITA_CAPACITY)
DEFAULT_FOOD_STOCK = 100.0  # Starting food per district
FOOD_PER_CAPITA_CAPACITY = 3.0  # Max food storage per person
MIN_FOOD_CAPACITY = 200.0  # Minimum food capacity per district
MAX_FOOD_CAPACITY = 50000.0  # Maximum food capacity (prevents overflow)

DEFAULT_CREDITS_POOL = 100.0
DEFAULT_JOBS_AVAILABLE = 5
DEFAULT_SECURITY_LEVEL = 70.0

# Production defaults
DEFAULT_PRODUCTION_RATE = 1.0
DEFAULT_WORKPLACE_COUNT = 2

# Ideal levels (for pressure calculation)
IDEAL_FOOD = 50.0  # Legacy - pressure uses per-capita now
IDEAL_JOBS = 8

# Tension normalization
TENSION_NORMALIZATION_DIVISOR = 100.0

# ============================================================================
# AGENT-DRIVEN FOOD SYSTEM
# ============================================================================

# Food produced per farming action
FOOD_PER_FARM_ACTION = 3  # Base food produced when a farmer farms
FOOD_PER_HUNT_ACTION = 2  # Base food produced when a hunter hunts
FOOD_GATHER_BASE = 1  # Any agent can gather small amounts when hungry

# Food consumption per agent per turn
FOOD_CONSUMPTION_PER_AGENT = 0.3  # Reduced - agents eat when hungry via actions
FOOD_CONSUMPTION_CHILD = 0.15  # Children in pool consume less

# Skill bonuses for food production roles
FARMER_SKILL_BONUS = 1.5  # Farmers produce 1.5x more
HUNTER_SKILL_BONUS = 1.3  # Hunters produce 1.3x more

# Weather modifiers on food production
WEATHER_FARM_GOOD = 1.3  # Good weather boosts farming
WEATHER_FARM_NORMAL = 1.0
WEATHER_FARM_BAD = 0.6
WEATHER_FARM_EXTREME = 0.3

WEATHER_HUNT_GOOD = 1.1  # Hunting less affected by weather
WEATHER_HUNT_NORMAL = 1.0
WEATHER_HUNT_BAD = 0.8
WEATHER_HUNT_EXTREME = 0.5

# Natural food regeneration per district per turn (environment)
NATURAL_FOOD_REGEN_BASE = 5.0  # Base food that regenerates naturally
NATURAL_FOOD_REGEN_MAX = 20.0  # Max natural regen (rich districts)

# Food spoilage (prevents infinite accumulation)
FOOD_SPOILAGE_RATE = 0.02  # 2% of food stock spoils per turn
FOOD_SPOILAGE_THRESHOLD = 500  # Only spoils above this amount

# ============================================================================
# FOOD PRESSURE THRESHOLDS
# ============================================================================

# Food per capita thresholds
STARVATION_THRESHOLD = 0.3  # Below = starvation (agents die)
SCARCITY_THRESHOLD = 0.7  # Below = scarcity (agents prioritize food)
ABUNDANCE_THRESHOLD = 2.0  # Above = surplus (agents relax about food)

# ============================================================================
# ROLE TRANSITION
# ============================================================================

# Chance per turn for an agent to consider changing role based on district needs
ROLE_CHANGE_CHANCE = 0.05  # 5% chance per turn to evaluate role change
ROLE_CHANGE_FOOD_CRISIS = 0.3  # 30% if district is in food scarcity
