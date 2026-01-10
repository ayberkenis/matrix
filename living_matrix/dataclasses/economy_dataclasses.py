"""Economy-related dataclasses."""

from dataclasses import dataclass


@dataclass
class DistrictEconomy:
    """Economy state for a district."""
    district_id: str
    district_name: str
    
    # Resources
    food_stock: int = 50  # 0-100
    credits_pool: int = 100  # Shared credits pool
    jobs_available: int = 5  # Available jobs
    security_level: int = 70  # 0-100, affects safety
    
    # Production capacity
    production_rate: float = 1.0  # Multiplier for production
    workplace_count: int = 2  # Number of workplaces
    
    # Tension
    tension: int = 20  # 0-100
    
    # Flags
    scarcity: bool = False  # Food scarcity flag
    unemployment: bool = False  # High unemployment flag
