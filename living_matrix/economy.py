"""Economy system: production, consumption, scarcity, tension."""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field


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


class EconomySystem:
    """Manages economy across all districts."""
    
    def __init__(self, districts: List[str], seed: int = 42):
        """Initialize economy system."""
        self.seed = seed
        random.seed(seed)
        self.districts: Dict[str, DistrictEconomy] = {}
        
        # Initialize district economies
        for district_id in districts:
            district_name = district_id.replace("region_", "").title()
            economy = DistrictEconomy(
                district_id=district_id,
                district_name=district_name,
                food_stock=random.randint(30, 70),
                credits_pool=random.randint(50, 150),
                jobs_available=random.randint(3, 8),
                security_level=random.randint(60, 90),
                production_rate=random.uniform(0.8, 1.2),
                workplace_count=random.randint(1, 4)
            )
            self.districts[district_id] = economy
    
    def produce(self, district_id: str, agent_count: int):
        """
        Produce resources in a district.
        Production depends on workplace count, production rate, and agent workers.
        """
        if district_id not in self.districts:
            return
        
        economy = self.districts[district_id]
        
        # Food production (from gardens/agriculture)
        if "garden" in district_id.lower() or economy.workplace_count > 0:
            workers = min(agent_count, economy.workplace_count * 2)
            food_produced = int(workers * economy.production_rate * random.uniform(0.8, 1.2))
            economy.food_stock = min(100, economy.food_stock + food_produced)
        
        # Credits production (from work)
        if economy.jobs_available > 0:
            credits_produced = int(economy.jobs_available * economy.production_rate * 2)
            economy.credits_pool = min(200, economy.credits_pool + credits_produced)
        
        # Jobs regenerate slowly
        if economy.jobs_available < 5:
            economy.jobs_available = min(10, economy.jobs_available + 1)
    
    def consume(self, district_id: str, agent_count: int):
        """
        Consume resources in a district.
        Agents consume food daily.
        """
        if district_id not in self.districts:
            return
        
        economy = self.districts[district_id]
        
        # Food consumption (each agent consumes ~1 food per day, approximated per tick)
        food_consumed = agent_count
        economy.food_stock = max(0, economy.food_stock - food_consumed)
    
    def update_tension(self, district_id: str, events: List[str]):
        """
        Update district tension based on scarcity, unemployment, and events.
        """
        if district_id not in self.districts:
            return
        
        economy = self.districts[district_id]
        
        # Scarcity increases tension
        if economy.food_stock < 20:
            economy.scarcity = True
            economy.tension = min(100, economy.tension + 2)
        else:
            economy.scarcity = False
            economy.tension = max(0, economy.tension - 1)
        
        # Unemployment increases tension
        if economy.jobs_available < 2:
            economy.unemployment = True
            economy.tension = min(100, economy.tension + 1)
        else:
            economy.unemployment = False
        
        # Events affect tension
        for event in events:
            if "conflict" in event.lower() or "theft" in event.lower():
                economy.tension = min(100, economy.tension + 3)
            elif "help" in event.lower() or "aid" in event.lower():
                economy.tension = max(0, economy.tension - 2)
            elif "strike" in event.lower() or "protest" in event.lower():
                economy.tension = min(100, economy.tension + 5)
        
        # Natural decay (slow)
        economy.tension = max(0, economy.tension - 0.5)
    
    def get_price_multiplier(self, district_id: str) -> float:
        """Get price multiplier based on scarcity."""
        if district_id not in self.districts:
            return 1.0
        
        economy = self.districts[district_id]
        if economy.scarcity:
            return 1.5 + (20 - economy.food_stock) / 20.0  # 1.5 to 2.5x
        return 1.0
    
    def generate_events(self, district_id: str) -> List[str]:
        """
        Generate economy-related events based on state.
        """
        if district_id not in self.districts:
            return []
        
        economy = self.districts[district_id]
        events = []
        
        # Shortage event
        if economy.scarcity and random.random() < 0.3:
            events.append(f"Food shortage reported in {economy.district_name}")
        
        # Price spike
        if economy.scarcity and random.random() < 0.2:
            events.append(f"Price spike in {economy.district_name} market")
        
        # Strike
        if economy.unemployment and economy.tension > 60 and random.random() < 0.15:
            events.append(f"Workers strike in {economy.district_name}")
        
        # Aid shipment (positive event)
        if economy.scarcity and economy.tension > 70 and random.random() < 0.1:
            economy.food_stock = min(100, economy.food_stock + 10)
            events.append(f"Aid shipment arrives in {economy.district_name}")
        
        return events
    
    def advance(self, district_id: str, agent_count: int, events: List[str]):
        """
        Advance economy one tick for a district.
        """
        self.produce(district_id, agent_count)
        self.consume(district_id, agent_count)
        self.update_tension(district_id, events)
    
    def get_district_resources(self, district_id: str) -> Dict:
        """Get district resources as dict for agent system."""
        if district_id not in self.districts:
            return {
                "food_stock": 50,
                "credits_pool": 100,
                "jobs_available": 5,
                "security_level": 70,
                "tension": 20,
                "scarcity": False
            }
        
        economy = self.districts[district_id]
        return {
            "food_stock": economy.food_stock,
            "credits_pool": economy.credits_pool,
            "jobs_available": economy.jobs_available,
            "security_level": economy.security_level,
            "tension": economy.tension,
            "scarcity": economy.scarcity
        }
    
    def get_district(self, district_id: str) -> Optional[DistrictEconomy]:
        """Get district economy by ID."""
        return self.districts.get(district_id)
    
    def get_all_districts(self) -> List[DistrictEconomy]:
        """Get all district economies."""
        return list(self.districts.values())
