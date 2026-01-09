"""Consequence-driven world simulation logic."""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .agents import Agent
from .map import Region, WorldMap
from .weather import WeatherSystem, WeatherState


@dataclass
class WorkResult:
    """Result of a work action."""
    success: bool
    resource_gained: float  # Amount of resource produced
    stress_change: float  # Change in stress
    credits_earned: float  # Credits earned


class ConsequenceSystem:
    """Manages consequence-driven world simulation."""
    
    def __init__(self, seed: int = 42):
        """Initialize consequence system."""
        self.seed = seed
        random.seed(seed)
    
    def attempt_work(
        self,
        agent: Agent,
        region: Region,
        weather: WeatherState
    ) -> WorkResult:
        """
        Attempt work action with success/failure probability.
        
        Args:
            agent: Agent attempting work
            region: Region where work is attempted
            weather: Current weather state
            
        Returns:
            WorkResult with success status and consequences
        """
        # Base success probability
        p_success = 0.75
        
        # Modifiers
        p_success += agent.work_ethic * 0.15
        p_success += region.infrastructure * 0.10
        p_success -= agent.needs.hunger * 0.20
        p_success -= (1.0 - agent.energy) * 0.15
        
        # Weather penalty
        weather_penalty = 0.0
        if weather.precipitation > 0.5:
            weather_penalty += 0.15
        if weather.precipitation > 0.8:  # Storm
            weather_penalty += 0.10
        if weather.temperature < 0.3:  # Cold
            weather_penalty += 0.05
        p_success -= weather_penalty
        
        # Region shortage penalty
        shortage_penalty = 0.0
        if region.food < 20:
            shortage_penalty += 0.10
        if region.energy < 20:
            shortage_penalty += 0.05
        p_success -= shortage_penalty
        
        # Clamp probability
        p_success = max(0.1, min(0.95, p_success))
        
        # Roll for success
        success = random.random() < p_success
        
        if success:
            # Calculate resource production based on region tags
            resource_gained = 0.0
            if 'industrial' in region.tags:
                resource_gained = random.uniform(2.0, 5.0)
                region.materials = min(100.0, region.materials + resource_gained)
            elif 'garden' in region.tags:
                resource_gained = random.uniform(1.5, 4.0)
                region.food = min(100.0, region.food + resource_gained)
            else:
                resource_gained = random.uniform(1.0, 3.0)
                region.energy = min(100.0, region.energy + resource_gained)
            
            # Update memory
            agent.location_success[region.id] = agent.location_success.get(region.id, 0.0) + 1.0
            
            # Reduce stress, earn credits
            stress_change = -0.05
            credits_earned = random.uniform(1.0, 3.0)
            agent.credits += credits_earned
            
            return WorkResult(
                success=True,
                resource_gained=resource_gained,
                stress_change=stress_change,
                credits_earned=credits_earned
            )
        else:
            # Failure: increase stress, record failure
            agent.location_failure[region.id] = agent.location_failure.get(region.id, 0.0) + 1.0
            stress_change = 0.10
            
            return WorkResult(
                success=False,
                resource_gained=0.0,
                stress_change=stress_change,
                credits_earned=0.0
            )
    
    def attempt_trade(
        self,
        agent: Agent,
        region: Region
    ) -> Tuple[bool, str]:
        """
        Attempt trade action (buy food).
        
        Args:
            agent: Agent attempting trade
            region: Region where trade is attempted
            
        Returns:
            Tuple of (success, description)
        """
        if 'market' not in region.tags:
            return (False, f"{agent.name} cannot trade here (not a market)")
        
        # Calculate food price (increases with scarcity)
        base_price = 2.0
        scarcity_multiplier = 1.0
        if region.food < 30:
            scarcity_multiplier = 1.5
        if region.food < 15:
            scarcity_multiplier = 2.0
        
        price = base_price * scarcity_multiplier
        
        if agent.credits < price:
            return (False, f"{agent.name} cannot afford food (needs {price:.1f} credits)")
        
        if region.food < 1.0:
            return (False, f"{agent.name} finds no food available")
        
        # Execute trade
        agent.credits -= price
        food_amount = min(5.0, region.food)
        region.food -= food_amount
        agent.needs.hunger = max(0.0, agent.needs.hunger - 0.4)
        
        return (True, f"{agent.name} trades for food at {region.name}")
    
    def attempt_socialize(
        self,
        agent1: Agent,
        agent2: Agent,
        region: Region
    ) -> Tuple[bool, str]:
        """
        Attempt socialize action between two agents.
        
        Args:
            agent1: First agent
            agent2: Second agent
            region: Region where interaction occurs
            
        Returns:
            Tuple of (success, description)
        """
        # Check if tension causes disagreement
        if region.tension > 0.6 and random.random() < region.tension:
            # Disagreement
            agent1.stress = min(1.0, agent1.stress + 0.05)
            agent2.stress = min(1.0, agent2.stress + 0.05)
            
            # Update relationships (decrease trust)
            for rel in agent1.relationships:
                if rel.other_id == agent2.id:
                    rel.strength = max(0.0, rel.strength - 0.1)
            for rel in agent2.relationships:
                if rel.other_id == agent1.id:
                    rel.strength = max(0.0, rel.strength - 0.1)
            
            return (False, f"{agent1.name} and {agent2.name} have a brief disagreement at {region.name}")
        else:
            # Positive interaction
            agent1.stress = max(0.0, agent1.stress - 0.03)
            agent2.stress = max(0.0, agent2.stress - 0.03)
            agent1.needs.social = max(0.0, agent1.needs.social - 0.2)
            agent2.needs.social = max(0.0, agent2.needs.social - 0.2)
            
            # Update relationships (increase trust)
            for rel in agent1.relationships:
                if rel.other_id == agent2.id:
                    rel.strength = min(1.0, rel.strength + 0.05)
            for rel in agent2.relationships:
                if rel.other_id == agent1.id:
                    rel.strength = min(1.0, rel.strength + 0.05)
            
            return (True, f"{agent1.name} and {agent2.name} socialize at {region.name}")
    
    def update_region_resources(
        self,
        region: Region,
        num_agents: int,
        weather: WeatherState
    ):
        """
        Update region resources based on consumption and regeneration.
        
        Args:
            region: Region to update
            num_agents: Number of agents in region
            weather: Current weather state
        """
        # Consumption (agents consume food and energy)
        food_consumption = num_agents * 0.5
        energy_consumption = num_agents * 0.3
        
        # Weather affects consumption
        if weather.temperature < 0.3:  # Cold
            food_consumption *= 1.2  # More food needed
        
        region.food = max(0.0, region.food - food_consumption)
        region.energy = max(0.0, region.energy - energy_consumption)
        
        # Regeneration (depends on tags and weather)
        regen_rate = 0.1
        if 'garden' in region.tags:
            regen_rate = 0.3
        if weather.precipitation > 0.3 and weather.precipitation < 0.7:  # Moderate rain
            regen_rate *= 1.2  # Good for gardens
        if weather.precipitation > 0.7:  # Heavy rain/storm
            regen_rate *= 0.8  # Too much rain
        
        region.food = min(100.0, region.food + regen_rate)
        region.energy = min(100.0, region.energy + regen_rate * 0.5)
        
        # Update tension based on shortages
        if region.food < 20:
            region.tension = min(1.0, region.tension + 0.02)
        elif region.food > 50:
            region.tension = max(0.0, region.tension - 0.01)
        
        # Clamp resources
        region.food = max(0.0, min(100.0, region.food))
        region.materials = max(0.0, min(100.0, region.materials))
        region.energy = max(0.0, min(100.0, region.energy))
        region.tension = max(0.0, min(1.0, region.tension))
    
    def get_memory_bias(self, agent: Agent, region_id: str) -> float:
        """
        Get memory bias for a region (positive = prefer, negative = avoid).
        
        Args:
            agent: Agent
            region_id: Region ID
            
        Returns:
            Bias value (-1.0 to 1.0)
        """
        success = agent.location_success.get(region_id, 0.0)
        failure = agent.location_failure.get(region_id, 0.0)
        
        if success + failure == 0:
            return 0.0
        
        # Calculate bias: more successes = positive, more failures = negative
        total = success + failure
        bias = (success - failure) / max(1.0, total)
        
        return max(-1.0, min(1.0, bias))
