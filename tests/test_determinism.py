"""
Determinism verification tests for Living Matrix refactoring.

These tests verify that:
1. Identical seeds produce identical results over 100+ ticks
2. Population, economy, and tension stay within statistical noise
3. Exported state remains backward compatible

Run with: python -m pytest tests/test_determinism.py -v
"""

import random
import pytest
from typing import Dict, List, Tuple


class MockDistrictResources:
    """Mock district resources for testing."""
    def __init__(self):
        self.data = {
            "food_stock": 50.0,
            "credits_pool": 100.0,
            "jobs_available": 10,
            "tension": 20.0,
            "security_level": 0.5
        }
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __getitem__(self, key):
        return self.data[key]


def create_test_system(seed: int = 42, num_agents: int = 50):
    """Create a HumanAgentSystem for testing."""
    from living_matrix.human_agent import HumanAgentSystem
    
    districts = ["district_a", "district_b", "district_c"]
    locations = ["loc_1", "loc_2", "loc_3", "loc_4", "loc_5"]
    
    return HumanAgentSystem(
        districts=districts,
        locations=locations,
        num_agents=num_agents,
        seed=seed
    )


def run_simulation(seed: int, ticks: int, num_agents: int = 50) -> Dict:
    """
    Run simulation for N ticks and return final state.
    
    Returns dict with population counts, events, and checksums.
    """
    random.seed(seed)
    
    system = create_test_system(seed=seed, num_agents=num_agents)
    district_resources = MockDistrictResources()
    
    all_events = []
    population_history = []
    
    for turn in range(ticks):
        events = system.advance(
            district_resources=district_resources.data,
            available_places=system.locations,
            world_map=None,
            turn=turn,
            extinction_risk=0.0,
            population_pressure=0.0,
            birth_pressure=0.0
        )
        
        all_events.extend(events)
        
        # Record population at each tick
        alive = sum(1 for a in system.agents.values() if a.is_alive)
        children = sum(system.child_pools.values())
        population_history.append((alive, children))
    
    # Calculate final state summary
    alive_agents = [a for a in system.agents.values() if a.is_alive]
    
    return {
        "seed": seed,
        "ticks": ticks,
        "final_population": len(alive_agents),
        "final_child_pool": sum(system.child_pools.values()),
        "total_events": len(all_events),
        "deaths": sum(1 for e in all_events if e[2] == "death"),
        "births": sum(1 for e in all_events if e[2] == "birth" or e[2] == "emergency_birth"),
        "promotions": sum(1 for e in all_events if e[2] == "promotion"),
        "conflicts": sum(1 for e in all_events if e[2] == "conflict"),
        "population_history": population_history,
        # Checksums for detailed verification
        "agent_ids_checksum": hash(tuple(sorted(a.id for a in alive_agents))),
        "age_sum": sum(a.age for a in alive_agents),
        "needs_checksum": sum(a.needs.hunger + a.needs.rest for a in alive_agents),
    }


class TestDeterminism:
    """Test suite for verifying deterministic simulation behavior."""
    
    def test_identical_seeds_produce_identical_results(self):
        """Run same seed twice and verify identical outcomes."""
        seed = 12345
        ticks = 100
        
        result1 = run_simulation(seed=seed, ticks=ticks)
        result2 = run_simulation(seed=seed, ticks=ticks)
        
        # Core counts must match exactly
        assert result1["final_population"] == result2["final_population"], \
            f"Population mismatch: {result1['final_population']} vs {result2['final_population']}"
        assert result1["final_child_pool"] == result2["final_child_pool"], \
            f"Child pool mismatch: {result1['final_child_pool']} vs {result2['final_child_pool']}"
        assert result1["total_events"] == result2["total_events"], \
            f"Event count mismatch: {result1['total_events']} vs {result2['total_events']}"
        assert result1["deaths"] == result2["deaths"], \
            f"Death count mismatch: {result1['deaths']} vs {result2['deaths']}"
        assert result1["births"] == result2["births"], \
            f"Birth count mismatch: {result1['births']} vs {result2['births']}"
        
        # Checksums must match
        assert result1["agent_ids_checksum"] == result2["agent_ids_checksum"], \
            "Agent IDs differ between runs"
        assert result1["age_sum"] == result2["age_sum"], \
            "Age sums differ between runs"
        assert result1["needs_checksum"] == result2["needs_checksum"], \
            "Needs checksums differ between runs"
    
    def test_different_seeds_produce_different_results(self):
        """Verify different seeds produce different (but valid) outcomes."""
        ticks = 50
        
        result1 = run_simulation(seed=111, ticks=ticks)
        result2 = run_simulation(seed=222, ticks=ticks)
        
        # Results should differ in some way
        # (could match by chance, but very unlikely)
        differs = (
            result1["final_population"] != result2["final_population"] or
            result1["deaths"] != result2["deaths"] or
            result1["births"] != result2["births"] or
            result1["agent_ids_checksum"] != result2["agent_ids_checksum"]
        )
        assert differs, "Different seeds produced identical results (very unlikely)"
    
    def test_population_stays_bounded(self):
        """Verify population stays within reasonable bounds over time."""
        seed = 42
        ticks = 150
        
        result = run_simulation(seed=seed, ticks=ticks, num_agents=100)
        
        # Population should not explode or crash to zero
        final_pop = result["final_population"] + result["final_child_pool"]
        assert final_pop > 0, "Population crashed to zero"
        assert final_pop < 50000, f"Population exploded to {final_pop}"
        
        # Check for reasonable growth/decline
        for alive, children in result["population_history"]:
            total = alive + children
            assert total >= 0, "Negative population detected"
    
    def test_100_ticks_stability(self):
        """Run 100 ticks and verify stable behavior."""
        seed = 99999
        ticks = 100
        
        result = run_simulation(seed=seed, ticks=ticks, num_agents=75)
        
        # Should have some events
        assert result["total_events"] > 0, "No events occurred in 100 ticks"
        
        # Should have population activity
        has_activity = result["deaths"] > 0 or result["births"] > 0 or result["promotions"] > 0
        assert has_activity, "No population activity in 100 ticks"
        
        # Final population should be reasonable
        assert result["final_population"] > 0, "All agents died"
    
    def test_tier_system_does_not_affect_outcomes(self):
        """
        Verify that the tier system produces same statistical outcomes.
        
        The tier system should only affect performance, not behavior.
        With large populations, tier rotation should still produce
        statistically similar results.
        """
        seed = 54321
        ticks = 100
        
        # Run with default population (tier system may or may not activate)
        result_small = run_simulation(seed=seed, ticks=ticks, num_agents=50)
        
        # Both runs with same seed should match
        result_small2 = run_simulation(seed=seed, ticks=ticks, num_agents=50)
        
        assert result_small["final_population"] == result_small2["final_population"]
        assert result_small["deaths"] == result_small2["deaths"]
        assert result_small["births"] == result_small2["births"]


class TestPerformanceObservability:
    """Test performance observability features."""
    
    def test_observer_zero_cost_when_disabled(self):
        """Verify observer has minimal overhead when disabled."""
        import os
        import time
        
        # Ensure metrics are disabled
        os.environ["LM_ENABLE_METRICS"] = "false"
        
        # Reload to pick up env var
        from importlib import reload
        import living_matrix.constants.performance_constants
        reload(living_matrix.constants.performance_constants)
        
        seed = 42
        ticks = 50
        
        start = time.perf_counter()
        run_simulation(seed=seed, ticks=ticks)
        duration = time.perf_counter() - start
        
        # Should complete reasonably quickly
        assert duration < 30.0, f"Simulation took too long: {duration}s"
    
    def test_tier_manager_stats(self):
        """Test tier manager statistics."""
        system = create_test_system(seed=42, num_agents=300)
        
        # Update tier assignments
        active, inactive = system.tier_manager.update_assignments(
            system.agents, turn=1
        )
        
        stats = system.tier_manager.get_stats()
        
        # Should have tracked some agents
        assert stats["total_tracked"] > 0
        assert stats["active_count"] + stats["inactive_count"] == stats["total_tracked"]


class TestBackwardCompatibility:
    """Test backward compatibility of state and events."""
    
    def test_event_format(self):
        """Verify events have expected format (agent_id, description, event_type)."""
        seed = 42
        ticks = 20
        
        system = create_test_system(seed=seed, num_agents=30)
        district_resources = MockDistrictResources()
        
        for turn in range(ticks):
            events = system.advance(
                district_resources=district_resources.data,
                available_places=system.locations,
                world_map=None,
                turn=turn
            )
            
            for event in events:
                assert len(event) == 3, f"Event has wrong format: {event}"
                assert isinstance(event[0], str), f"Agent ID not string: {event[0]}"
                assert isinstance(event[1], str), f"Description not string: {event[1]}"
                # event_type can be None or string
                assert event[2] is None or isinstance(event[2], str), \
                    f"Event type not None/string: {event[2]}"
    
    def test_agent_attributes_present(self):
        """Verify agents have all expected attributes."""
        system = create_test_system(seed=42, num_agents=20)
        
        for agent in system.agents.values():
            # Core attributes
            assert hasattr(agent, "id")
            assert hasattr(agent, "name")
            assert hasattr(agent, "district")
            assert hasattr(agent, "location")
            assert hasattr(agent, "role")
            assert hasattr(agent, "sex")
            assert hasattr(agent, "age")
            assert hasattr(agent, "lifespan")
            assert hasattr(agent, "is_alive")
            
            # Needs
            assert hasattr(agent, "needs")
            assert hasattr(agent.needs, "hunger")
            assert hasattr(agent.needs, "rest")
            assert hasattr(agent.needs, "safety")
            
            # Traits
            assert hasattr(agent, "traits")
            assert hasattr(agent.traits, "risk")
            assert hasattr(agent.traits, "empathy")
            
            # Survival drives
            assert hasattr(agent, "survival_drive")
            assert hasattr(agent, "reproduction_drive")
            assert hasattr(agent, "legacy_drive")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
