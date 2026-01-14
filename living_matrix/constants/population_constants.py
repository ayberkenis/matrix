"""Population system constants."""

# Population compression constants
MAX_ACTIVE_AGENTS = 10000  # Very high cap (effectively unlimited) - birth/death rates manage population
ADULTHOOD_AGE = 3  # Age when children become adults (turns) - very low for fast promotion (6 simulation turns)
MAX_CHILD_POOL_PER_DISTRICT = 1000  # Soft cap on child pool per district
MAX_CHILDREN_PER_COUPLE = 5  # Maximum children a couple can have

# Population density controls (to prevent explosive growth)
IDEAL_POPULATION = 500  # Target population for balanced growth
POPULATION_DENSITY_FACTOR = 4.0  # How much population density affects reproduction (increased from 2.0 for much stronger control)
# When population > IDEAL_POPULATION, reproduction is reduced exponentially
# Formula: reproduction_multiplier = 1.0 / (1.0 + (population - IDEAL_POPULATION) / IDEAL_POPULATION * POPULATION_DENSITY_FACTOR)
# At 2000 agents (4x ideal): penalty = 1/(1+3*2) = 1/7 = 0.14 (86% reduction)
# At 5000 agents (10x ideal): penalty = 1/(1+9*2) = 1/19 = 0.05 (95% reduction)

# Population continuity guards
MIN_ADULT_SURVIVORS = 2  # Minimum viable population guard (hard rule)
MAX_ADULT_DEATH_RATE = 0.25  # Never allow > 25% adult death per turn

# Agent roles (with food production roles)
ROLES = ['worker', 'trader', 'guard', 'medic', 'student', 'builder', 'scout', 'keeper', 'farmer', 'hunter']

# Food production roles - higher weight for spawning to ensure food production
FOOD_PRODUCTION_ROLES = ['farmer', 'hunter']
FOOD_ROLE_SPAWN_WEIGHT = 3  # 3x more likely to spawn as farmer/hunter when food is low

# Agent name parts
NAME_PARTS = ['Eli', 'Noa', 'Leo', 'Sam', 'Theo', 'Max', 'Alex', 'Luca', 'Ezra', 'Milo',
              'Ryan', 'Owen', 'Finn', 'Cole', 'Nate', 'Jude']

# Age distribution for initial population
# Ages adjusted so agents START in reproductive window (20+)
INITIAL_AGE_YOUNG_PROBABILITY = 0.8  # 80% young
INITIAL_AGE_MIDDLE_PROBABILITY = 0.95  # 15% middle-aged (cumulative)
INITIAL_AGE_YOUNG_MIN = 25  # Start at 25 - already in reproductive window
INITIAL_AGE_YOUNG_MAX = 150  # Young adults in reproductive prime
INITIAL_AGE_MIDDLE_MIN = 150
INITIAL_AGE_MIDDLE_MAX = 400  # Still well within reproductive window
INITIAL_AGE_ELDERLY_MIN = 400
INITIAL_AGE_ELDERLY_MAX = 600  # Still below typical lifespan - 20

# Lifespan constants
# Increased for slower aging - agents now effectively live twice as long
MIN_REMAINING_LIFESPAN = 1600  # At least 1600 turns of life remaining (doubled)
LIFESPAN_VARIANCE = 2400  # Additional variance for lifespan (doubled)

# Initial needs ranges
INITIAL_HUNGER_MIN = 20
INITIAL_HUNGER_MAX = 60
INITIAL_REST_MIN = 30
INITIAL_REST_MAX = 70
INITIAL_SAFETY_MIN = 50
INITIAL_SAFETY_MAX = 90
INITIAL_BELONGING_MIN = 40
INITIAL_BELONGING_MAX = 70
INITIAL_PURPOSE_MIN = 40
INITIAL_PURPOSE_MAX = 80

# Initial trait ranges
INITIAL_RISK_MIN = 0.2
INITIAL_RISK_MAX = 0.8
INITIAL_EMPATHY_MIN = 0.3
INITIAL_EMPATHY_MAX = 0.9
INITIAL_AMBITION_MIN = 0.2
INITIAL_AMBITION_MAX = 0.8
INITIAL_PATIENCE_MIN = 0.3
INITIAL_PATIENCE_MAX = 0.9

# Initial inventory ranges
# Increased food to prevent early starvation before reproduction kicks in
INITIAL_FOOD_MIN = 10
INITIAL_FOOD_MAX = 100
INITIAL_CREDITS_MIN = 10
INITIAL_CREDITS_MAX = 50
INITIAL_TOOLS_MAX = 2

# Survival drive constants
INITIAL_SURVIVAL_DRIVE_MIN = 0.7
INITIAL_SURVIVAL_DRIVE_MAX = 1.0
INITIAL_LEGACY_DRIVE_MIN = 0.2
INITIAL_LEGACY_DRIVE_MAX = 0.4

# Reproduction drive by age
REPRODUCTION_DRIVE_TOO_YOUNG_MIN = 0.3
REPRODUCTION_DRIVE_TOO_YOUNG_MAX = 0.5
REPRODUCTION_DRIVE_PEAK_MIN = 0.6
REPRODUCTION_DRIVE_PEAK_MAX = 0.9
REPRODUCTION_DRIVE_DECLINING_MIN = 0.4
REPRODUCTION_DRIVE_DECLINING_MAX = 0.7
REPRODUCTION_DRIVE_ELDERLY_MIN = 0.2
REPRODUCTION_DRIVE_ELDERLY_MAX = 0.5

# Relationship formation
INITIAL_RELATIONSHIP_CHANCE = 0.3  # 30% chance to form initial relationship
INITIAL_RELATIONSHIP_POSITIVE_CHANCE = 0.7  # 70% positive, 30% neutral
INITIAL_AFFECTION_MIN = 0.3
INITIAL_AFFECTION_MAX = 0.6
INITIAL_TRUST_MIN = 0.3
INITIAL_TRUST_MAX = 0.5
INITIAL_FAMILIARITY_MIN = 0.2
INITIAL_FAMILIARITY_MAX = 0.4

# Child pool mortality rates (extremely low to allow children to reach adulthood)
# Mortality is applied every 2 turns (when children age), so rates are per aging event
# With ADULTHOOD_AGE=5, children need 10 simulation turns (5 aging events) to reach adulthood
CHILD_MORTALITY_RATE_UNDER_10 = 0.0001  # 0.01% per aging event (extremely low)
CHILD_MORTALITY_RATE_UNDER_50 = 0.00005  # 0.005% per aging event
CHILD_MORTALITY_RATE_OVER_50 = 0.00001   # 0.001% per aging event

# Emergency birth constants
EMERGENCY_BIRTH_MULTIPLIER = 0.5  # 50% of alive_count per district

# Promotion constants
# Reduced promotion chance to slow down population growth
BASE_PROMOTION_CHANCE = 0.30  # 30% base chance per eligible child per turn (reduced from 80% for controlled growth)
PROMOTION_FOOD_FACTOR_DIVISOR = 50.0
PROMOTION_JOB_FACTOR_DIVISOR = 8.0
