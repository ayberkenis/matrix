"""Population system constants."""

# Population compression constants
MAX_ACTIVE_AGENTS = 500  # Hard cap on active agents
ADULTHOOD_AGE = 3  # Age when children become adults (turns) - very low for fast promotion (6 simulation turns)
MAX_CHILD_POOL_PER_DISTRICT = 1000  # Soft cap on child pool per district

# Population continuity guards
MIN_ADULT_SURVIVORS = 2  # Minimum viable population guard (hard rule)
MAX_ADULT_DEATH_RATE = 0.25  # Never allow > 25% adult death per turn

# Agent roles
ROLES = ['worker', 'trader', 'guard', 'medic', 'student', 'builder', 'scout', 'keeper']

# Agent name parts
NAME_PARTS = ['Eli', 'Noa', 'Leo', 'Sam', 'Theo', 'Max', 'Alex', 'Luca', 'Ezra', 'Milo',
              'Ryan', 'Owen', 'Finn', 'Cole', 'Nate', 'Jude']

# Age distribution for initial population
# Ages adjusted for slower aging - start much younger to ensure reproduction time
INITIAL_AGE_YOUNG_PROBABILITY = 0.8  # 80% young (increased from 60%)
INITIAL_AGE_MIDDLE_PROBABILITY = 0.95  # 15% middle-aged (cumulative)
INITIAL_AGE_YOUNG_MIN = 0
INITIAL_AGE_YOUNG_MAX = 50  # Much younger - start in reproductive prime
INITIAL_AGE_MIDDLE_MIN = 50
INITIAL_AGE_MIDDLE_MAX = 150
INITIAL_AGE_ELDERLY_MIN = 150
INITIAL_AGE_ELDERLY_MAX = 200

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
INITIAL_FOOD_MIN = 2
INITIAL_FOOD_MAX = 8
INITIAL_CREDITS_MIN = 10
INITIAL_CREDITS_MAX = 30
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
# High promotion chance to ensure population growth over time
BASE_PROMOTION_CHANCE = 0.80  # 80% base chance per eligible child per turn (very high for steady growth)
PROMOTION_FOOD_FACTOR_DIVISOR = 50.0
PROMOTION_JOB_FACTOR_DIVISOR = 8.0
