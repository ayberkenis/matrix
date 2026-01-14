"""Enhanced Food System - Scalable resource management.

This module provides a food system that properly scales with population,
supporting 10,000+ agents while maintaining meaningful scarcity/abundance.

KEY CONCEPTS:

1. **Food Capacity Scales with Infrastructure**
   - Base capacity per district
   - Scales with workplace count and population
   - Can be upgraded through development

2. **Multiple Production Sources**
   - Farming (worker-based, seasonal)
   - Hunting/Gathering (location-based)
   - Trade (inter-district)
   - Reserves (storage from surplus)

3. **Per-Capita Consumption**
   - Base consumption per agent
   - Modified by needs (hungry agents consume more)
   - Modified by activity (working agents need more)

4. **Surplus/Shortage Mechanics**
   - Surplus builds reserves
   - Reserves buffer shortages
   - Prolonged shortage causes starvation

5. **Population-Proportional Scaling**
   - Food per capita is the key metric
   - Target: ~2-3 food per capita for healthy population
   - Below 1.0 = scarcity, above 3.0 = abundance
"""

import random
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from enum import Enum


class FoodSufficiency(Enum):
    """Food sufficiency levels."""
    STARVATION = "starvation"    # < 0.5 per capita
    SCARCITY = "scarcity"        # 0.5 - 1.0 per capita  
    ADEQUATE = "adequate"        # 1.0 - 2.0 per capita
    ABUNDANT = "abundant"        # 2.0 - 3.0 per capita
    SURPLUS = "surplus"          # > 3.0 per capita


@dataclass
class FoodProductionSource:
    """A source of food production."""
    source_type: str  # 'farming', 'hunting', 'trade', 'reserves'
    base_output: float  # Base food per turn
    efficiency: float = 1.0  # Current efficiency (0.0 - 1.5)
    workers_assigned: int = 0  # Workers for this source
    output_per_worker: float = 2.0  # Food per worker per turn
    max_workers: int = 100  # Maximum workers this source can use
    
    def get_output(self, weather_modifier: float = 1.0) -> float:
        """Calculate food output this turn."""
        worker_output = self.workers_assigned * self.output_per_worker
        total = (self.base_output + worker_output) * self.efficiency * weather_modifier
        return max(0, total * random.uniform(0.9, 1.1))  # Small variance


@dataclass
class DistrictFoodState:
    """Enhanced food state for a district."""
    district_id: str
    
    # Current stocks
    food_stock: float = 100.0  # Current available food
    food_reserves: float = 50.0  # Long-term reserves
    
    # Capacity (scales with population and infrastructure)
    base_capacity: float = 200.0  # Base food capacity
    infrastructure_level: int = 1  # 1-5, increases capacity
    
    # Production sources
    farming: FoodProductionSource = field(default_factory=lambda: FoodProductionSource(
        source_type='farming',
        base_output=20.0,
        output_per_worker=2.5,
        max_workers=50
    ))
    hunting: FoodProductionSource = field(default_factory=lambda: FoodProductionSource(
        source_type='hunting',
        base_output=10.0,
        output_per_worker=1.5,
        max_workers=20
    ))
    trade_income: float = 0.0  # Food from inter-district trade
    
    # Consumption tracking
    consumption_last_turn: float = 0.0
    production_last_turn: float = 0.0
    
    # History for trends (last 10 turns)
    food_history: List[float] = field(default_factory=list)
    
    @property
    def total_capacity(self) -> float:
        """Total food storage capacity."""
        return self.base_capacity * (1 + 0.5 * (self.infrastructure_level - 1))
    
    @property
    def reserve_capacity(self) -> float:
        """Reserve storage capacity (30% of total)."""
        return self.total_capacity * 0.3
    
    def get_food_per_capita(self, population: int) -> float:
        """Get food per capita (key metric)."""
        if population <= 0:
            return float('inf')
        return (self.food_stock + self.food_reserves) / population
    
    def get_sufficiency(self, population: int) -> FoodSufficiency:
        """Get food sufficiency level."""
        per_capita = self.get_food_per_capita(population)
        
        if per_capita < 0.5:
            return FoodSufficiency.STARVATION
        elif per_capita < 1.0:
            return FoodSufficiency.SCARCITY
        elif per_capita < 2.0:
            return FoodSufficiency.ADEQUATE
        elif per_capita < 3.0:
            return FoodSufficiency.ABUNDANT
        else:
            return FoodSufficiency.SURPLUS


class EnhancedFoodSystem:
    """
    Manages food production, consumption, and distribution.
    
    Usage:
        food_system = EnhancedFoodSystem()
        food_system.initialize_district('region_1', population=100)
        
        # Each turn:
        result = food_system.advance_district(
            'region_1',
            population=150,
            worker_allocation={'farming': 30, 'hunting': 10},
            weather_modifier=0.9
        )
        
        print(f"Food per capita: {result['food_per_capita']}")
        print(f"Sufficiency: {result['sufficiency']}")
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.districts: Dict[str, DistrictFoodState] = {}
        
        # Global configuration
        self.base_consumption_per_agent = 0.5  # Base food consumed per agent per turn
        self.hunger_consumption_bonus = 0.3  # Extra consumption when hungry
        self.target_food_per_capita = 2.0  # Target for healthy population
        self.starvation_threshold = 0.5  # Below this = starvation
        
        # Production modifiers
        self.tension_production_penalty = 0.5  # Max penalty from tension
        self.weather_impact = {
            'good': 1.2,
            'normal': 1.0,
            'bad': 0.7,
            'extreme': 0.4
        }
    
    def initialize_district(
        self,
        district_id: str,
        population: int = 50,
        infrastructure_level: int = 1
    ) -> DistrictFoodState:
        """Initialize food state for a district."""
        # Scale base capacity with expected population
        base_capacity = max(200, population * 3)
        
        state = DistrictFoodState(
            district_id=district_id,
            food_stock=population * self.target_food_per_capita,
            food_reserves=population * 1.0,
            base_capacity=base_capacity,
            infrastructure_level=infrastructure_level,
        )
        
        # Scale production sources based on population
        state.farming.base_output = 10 + population * 0.3
        state.farming.max_workers = max(50, population // 2)
        state.hunting.base_output = 5 + population * 0.1
        state.hunting.max_workers = max(20, population // 5)
        
        self.districts[district_id] = state
        return state
    
    def get_or_create_state(
        self,
        district_id: str,
        population: int = 50
    ) -> DistrictFoodState:
        """Get existing state or create new one."""
        if district_id not in self.districts:
            return self.initialize_district(district_id, population)
        return self.districts[district_id]
    
    def calculate_production(
        self,
        state: DistrictFoodState,
        population: int,
        worker_allocation: Dict[str, int],
        tension: float = 0.0,
        weather: str = 'normal'
    ) -> float:
        """Calculate total food production for a turn."""
        # Tension penalty (high tension reduces production)
        tension_modifier = 1.0 - (tension / 100.0) * self.tension_production_penalty
        tension_modifier = max(0.3, tension_modifier)
        
        # Weather modifier
        weather_mod = self.weather_impact.get(weather, 1.0)
        
        # Auto-allocate workers if not specified
        if not worker_allocation:
            # Default: 60% farming, 20% hunting, 20% other
            farming_workers = int(population * 0.3)
            hunting_workers = int(population * 0.1)
            worker_allocation = {
                'farming': min(farming_workers, state.farming.max_workers),
                'hunting': min(hunting_workers, state.hunting.max_workers)
            }
        
        # Assign workers
        state.farming.workers_assigned = min(
            worker_allocation.get('farming', 0),
            state.farming.max_workers
        )
        state.hunting.workers_assigned = min(
            worker_allocation.get('hunting', 0),
            state.hunting.max_workers
        )
        
        # Calculate outputs
        farming_output = state.farming.get_output(weather_mod) * tension_modifier
        hunting_output = state.hunting.get_output(weather_mod * 0.8) * tension_modifier  # Less weather dependent
        trade_output = state.trade_income
        
        total_production = farming_output + hunting_output + trade_output
        
        # Population scaling bonus (larger populations have some economy of scale)
        if population > 100:
            scale_bonus = 1.0 + math.log10(population / 100) * 0.2
            total_production *= min(scale_bonus, 1.5)
        
        return total_production
    
    def calculate_consumption(
        self,
        population: int,
        avg_hunger: float = 0.3,
        child_fraction: float = 0.2
    ) -> float:
        """Calculate total food consumption for a turn."""
        # Base consumption
        base = population * self.base_consumption_per_agent
        
        # Hunger bonus (hungry agents consume more when food is available)
        hunger_bonus = population * avg_hunger * self.hunger_consumption_bonus
        
        # Children consume less
        child_reduction = population * child_fraction * 0.3
        
        total = base + hunger_bonus - child_reduction
        
        # Add small variance
        total *= random.uniform(0.95, 1.05)
        
        return max(0, total)
    
    def advance_district(
        self,
        district_id: str,
        population: int,
        worker_allocation: Dict[str, int] = None,
        tension: float = 0.0,
        weather: str = 'normal',
        avg_hunger: float = 0.3,
        child_fraction: float = 0.2
    ) -> Dict:
        """
        Advance food system for a district by one turn.
        
        Returns dict with:
        - food_stock: Current food available
        - food_reserves: Current reserves
        - production: Food produced this turn
        - consumption: Food consumed this turn
        - net_change: Production - Consumption
        - food_per_capita: Food per person
        - sufficiency: FoodSufficiency level
        - pressure: Food pressure (0.0 = abundant, 1.0 = starvation)
        """
        state = self.get_or_create_state(district_id, population)
        
        # Scale capacity if population has grown significantly
        if population > state.base_capacity / 2:
            state.base_capacity = max(state.base_capacity, population * 3)
            state.farming.max_workers = max(state.farming.max_workers, population // 2)
            state.hunting.max_workers = max(state.hunting.max_workers, population // 5)
        
        # Calculate production
        production = self.calculate_production(
            state, population, worker_allocation or {},
            tension, weather
        )
        
        # Calculate consumption
        consumption = self.calculate_consumption(
            population, avg_hunger, child_fraction
        )
        
        # Apply production (add to stock)
        state.food_stock += production
        
        # Apply consumption
        if state.food_stock >= consumption:
            # Enough food in stock
            state.food_stock -= consumption
        else:
            # Need to dip into reserves
            shortfall = consumption - state.food_stock
            state.food_stock = 0
            
            if state.food_reserves >= shortfall:
                state.food_reserves -= shortfall
            else:
                # True shortage - not enough food
                state.food_reserves = 0
                # Remaining shortfall causes starvation
        
        # Surplus goes to reserves
        surplus = state.food_stock - (state.total_capacity * 0.7)
        if surplus > 0:
            transfer = min(surplus * 0.3, state.reserve_capacity - state.food_reserves)
            if transfer > 0:
                state.food_stock -= transfer
                state.food_reserves += transfer
        
        # Cap stocks to capacity
        state.food_stock = min(state.food_stock, state.total_capacity)
        state.food_reserves = min(state.food_reserves, state.reserve_capacity)
        
        # Track history
        state.production_last_turn = production
        state.consumption_last_turn = consumption
        state.food_history.append(state.food_stock)
        if len(state.food_history) > 10:
            state.food_history.pop(0)
        
        # Calculate metrics
        food_per_capita = state.get_food_per_capita(population)
        sufficiency = state.get_sufficiency(population)
        
        # Calculate pressure (inverse of per-capita scaled to 0-1)
        # 0.0 = abundant (3+ per capita), 1.0 = starvation (<0.5 per capita)
        pressure = max(0.0, min(1.0, 1.0 - (food_per_capita - 0.5) / 2.5))
        
        return {
            'food_stock': state.food_stock,
            'food_reserves': state.food_reserves,
            'total_food': state.food_stock + state.food_reserves,
            'capacity': state.total_capacity,
            'production': production,
            'consumption': consumption,
            'net_change': production - consumption,
            'food_per_capita': food_per_capita,
            'sufficiency': sufficiency.value,
            'pressure': pressure,
            'trend': self._get_trend(state),
        }
    
    def _get_trend(self, state: DistrictFoodState) -> str:
        """Get food trend from history."""
        if len(state.food_history) < 3:
            return 'stable'
        
        recent = state.food_history[-3:]
        avg_change = (recent[-1] - recent[0]) / len(recent)
        
        if avg_change > 5:
            return 'rising'
        elif avg_change < -5:
            return 'falling'
        else:
            return 'stable'
    
    def transfer_food(
        self,
        from_district: str,
        to_district: str,
        amount: float
    ) -> float:
        """Transfer food between districts (trade)."""
        if from_district not in self.districts or to_district not in self.districts:
            return 0.0
        
        from_state = self.districts[from_district]
        to_state = self.districts[to_district]
        
        # Can only transfer available surplus
        available = max(0, from_state.food_stock - from_state.total_capacity * 0.3)
        actual_transfer = min(amount, available)
        
        if actual_transfer > 0:
            from_state.food_stock -= actual_transfer
            to_state.food_stock = min(
                to_state.total_capacity,
                to_state.food_stock + actual_transfer * 0.9  # 10% transport loss
            )
        
        return actual_transfer
    
    def upgrade_infrastructure(self, district_id: str) -> bool:
        """Upgrade district infrastructure (increases capacity)."""
        if district_id not in self.districts:
            return False
        
        state = self.districts[district_id]
        if state.infrastructure_level >= 5:
            return False
        
        state.infrastructure_level += 1
        state.farming.base_output *= 1.2
        state.farming.output_per_worker *= 1.1
        state.farming.max_workers = int(state.farming.max_workers * 1.2)
        
        return True
    
    def get_global_stats(self) -> Dict:
        """Get global food statistics across all districts."""
        if not self.districts:
            return {}
        
        total_food = sum(s.food_stock + s.food_reserves for s in self.districts.values())
        total_capacity = sum(s.total_capacity + s.reserve_capacity for s in self.districts.values())
        total_production = sum(s.production_last_turn for s in self.districts.values())
        total_consumption = sum(s.consumption_last_turn for s in self.districts.values())
        
        return {
            'total_food': total_food,
            'total_capacity': total_capacity,
            'utilization': total_food / total_capacity if total_capacity > 0 else 0,
            'total_production': total_production,
            'total_consumption': total_consumption,
            'net_production': total_production - total_consumption,
            'districts_in_scarcity': sum(
                1 for s in self.districts.values()
                if s.food_stock < s.base_capacity * 0.3
            ),
        }
    
    def sync_with_legacy(
        self,
        district_id: str,
        legacy_food_stock: float,
        population: int
    ) -> Tuple[float, float]:
        """
        Sync enhanced food system with legacy food_stock value.
        
        Scales the legacy 0-100 food_stock to the enhanced system.
        
        Returns (new_food_stock, food_pressure)
        """
        state = self.get_or_create_state(district_id, population)
        
        # Legacy system uses 0-100 scale
        # Convert to enhanced system scale
        legacy_ratio = legacy_food_stock / 100.0
        
        # Set food stock proportionally to capacity
        target_food = state.total_capacity * legacy_ratio
        state.food_stock = target_food * 0.7
        state.food_reserves = target_food * 0.3
        
        # Calculate pressure
        food_per_capita = state.get_food_per_capita(population)
        pressure = max(0.0, min(1.0, 1.0 - (food_per_capita - 0.5) / 2.5))
        
        return state.food_stock + state.food_reserves, pressure


# Global instance
_enhanced_food_system: Optional[EnhancedFoodSystem] = None


def get_enhanced_food_system(seed: int = 42) -> EnhancedFoodSystem:
    """Get or create the global enhanced food system."""
    global _enhanced_food_system
    if _enhanced_food_system is None:
        _enhanced_food_system = EnhancedFoodSystem(seed)
    return _enhanced_food_system


def reset_enhanced_food_system():
    """Reset the global food system (for testing)."""
    global _enhanced_food_system
    _enhanced_food_system = None
