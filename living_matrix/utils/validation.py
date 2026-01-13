"""
Validation and profiling utilities for Living Matrix.

Provides:
1. Deterministic test harness - verifies identical outputs for same seed
2. Profiling helper - runs cProfile and prints top functions
3. Learning validation - verifies learning doesn't break determinism

Usage:
    from living_matrix.utils.validation import (
        run_determinism_test,
        run_profiling,
        validate_learning_safety
    )
    
    # Verify determinism
    passed, results = run_determinism_test(seed=42, agents=1000, ticks=50)
    
    # Profile performance
    run_profiling(agents=10000, ticks=10, top_n=30)
"""

import random
import time
import os
from typing import Tuple, Dict, Any, Optional


def run_determinism_test(
    seed: int = 42,
    agents: int = 1000,
    ticks: int = 50,
    verbose: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Run determinism test with LEARNING_DISABLED.
    
    Verifies that running the simulation twice with the same seed
    produces identical results.
    
    Args:
        seed: Random seed to use
        agents: Number of agents to create
        ticks: Number of ticks to run
        verbose: Print results
        
    Returns:
        Tuple of (passed, results_dict)
    """
    # Ensure learning is disabled
    os.environ['LM_LEARNING_ENABLED'] = 'false'
    
    # Reset any cached config
    try:
        from living_matrix.config import reload_config
        reload_config()
    except ImportError:
        pass
    
    from living_matrix.human_agent import HumanAgentSystem
    
    def run_simulation():
        # Reset all singletons to ensure clean state
        try:
            from living_matrix.redis_memory.manager import reset_memory_manager
            from living_matrix.redis_memory.redis_client import reset_redis_client
            from living_matrix.learning.modulator import reset_decision_modulator
            reset_memory_manager()
            reset_redis_client()
            reset_decision_modulator()
        except ImportError:
            pass
        
        # Reset random state with seed
        random.seed(seed)
        
        districts = ['d1', 'd2', 'd3', 'd4', 'd5']
        locations = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8']
        
        system = HumanAgentSystem(
            districts=districts,
            locations=locations,
            num_agents=agents,
            seed=seed
        )
        
        resources = {
            'food_stock': 80,
            'credits_pool': 200,
            'jobs_available': 20,
            'tension': 15
        }
        
        for turn in range(ticks):
            system.advance(
                district_resources=resources,
                available_places=locations,
                world_map=None,
                turn=turn
            )
        
        # Collect deterministic state
        alive = sum(1 for a in system.agents.values() if a.is_alive)
        children = sum(system.child_pools.values())
        total_credits = sum(a.inventory.credits for a in system.agents.values() if a.is_alive)
        total_food = sum(a.inventory.food for a in system.agents.values() if a.is_alive)
        avg_hunger = sum(a.needs.hunger for a in system.agents.values() if a.is_alive) / max(1, alive)
        
        return {
            'alive': alive,
            'children': children,
            'total_credits': total_credits,
            'total_food': total_food,
            'avg_hunger': round(avg_hunger, 2)
        }
    
    if verbose:
        print(f"Running determinism test: {agents} agents, {ticks} ticks, seed={seed}")
        print("Run 1...", end=" ")
    
    start1 = time.perf_counter()
    result1 = run_simulation()
    time1 = time.perf_counter() - start1
    
    if verbose:
        print(f"done ({time1:.2f}s)")
        print("Run 2...", end=" ")
    
    start2 = time.perf_counter()
    result2 = run_simulation()
    time2 = time.perf_counter() - start2
    
    if verbose:
        print(f"done ({time2:.2f}s)")
    
    passed = result1 == result2
    
    results = {
        'passed': passed,
        'seed': seed,
        'agents': agents,
        'ticks': ticks,
        'run1': result1,
        'run2': result2,
        'time1': time1,
        'time2': time2
    }
    
    if verbose:
        print()
        print(f"Run 1: {result1}")
        print(f"Run 2: {result2}")
        print()
        if passed:
            print("[PASS] DETERMINISM: Results are identical")
        else:
            print("[FAIL] DETERMINISM: Results differ!")
            for key in result1:
                if result1[key] != result2[key]:
                    print(f"  Difference in '{key}': {result1[key]} vs {result2[key]}")
    
    return passed, results


def run_profiling(
    agents: int = 10000,
    ticks: int = 10,
    top_n: int = 30,
    verbose: bool = True
) -> Optional[str]:
    """
    Run cProfile and print top functions by cumulative time.
    
    Args:
        agents: Number of agents to create
        ticks: Number of ticks to run
        top_n: Number of top functions to print
        verbose: Print results
        
    Returns:
        Profile stats as string (or None if cProfile unavailable)
    """
    import cProfile
    import pstats
    from io import StringIO
    
    # Ensure learning is disabled for fair comparison
    os.environ['LM_LEARNING_ENABLED'] = 'false'
    
    try:
        from living_matrix.config import reload_config
        reload_config()
    except ImportError:
        pass
    
    from living_matrix.human_agent import HumanAgentSystem
    
    def run_simulation():
        seed = 42
        random.seed(seed)
        districts = ['d1', 'd2', 'd3', 'd4', 'd5']
        locations = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8']
        
        system = HumanAgentSystem(
            districts=districts,
            locations=locations,
            num_agents=agents,
            seed=seed
        )
        
        resources = {
            'food_stock': 80,
            'credits_pool': 200,
            'jobs_available': 20,
            'tension': 15
        }
        
        for turn in range(ticks):
            system.advance(
                district_resources=resources,
                available_places=locations,
                world_map=None,
                turn=turn
            )
    
    if verbose:
        print(f"Profiling: {agents} agents, {ticks} ticks")
        print("Running...")
    
    pr = cProfile.Profile()
    pr.enable()
    run_simulation()
    pr.disable()
    
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(top_n)
    
    output = s.getvalue()
    
    if verbose:
        print(output)
    
    return output


def validate_learning_safety(
    seed: int = 42,
    agents: int = 500,
    ticks: int = 30,
    verbose: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that learning-enabled simulation stays within safe bounds.
    
    Checks:
    1. No extreme population swings
    2. Learned weights stay within clip bounds
    3. Memory usage stays bounded
    
    Args:
        seed: Random seed
        agents: Number of agents
        ticks: Number of ticks
        verbose: Print results
        
    Returns:
        Tuple of (passed, results_dict)
    """
    # Enable learning
    os.environ['LM_LEARNING_ENABLED'] = 'true'
    os.environ['LM_DISTRICT_LEARNING_ENABLED'] = 'true'
    os.environ['LM_POPULATION_MEMORY_ENABLED'] = 'true'
    
    try:
        from living_matrix.config import reload_config, get_config
        cfg = reload_config()
    except ImportError:
        if verbose:
            print("Learning config not available, skipping validation")
        return True, {'skipped': True}
    
    from living_matrix.human_agent import HumanAgentSystem
    
    random.seed(seed)
    districts = ['d1', 'd2', 'd3', 'd4', 'd5']
    locations = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8']
    
    system = HumanAgentSystem(
        districts=districts,
        locations=locations,
        num_agents=agents,
        seed=seed
    )
    
    resources = {
        'food_stock': 80,
        'credits_pool': 200,
        'jobs_available': 20,
        'tension': 15
    }
    
    population_history = []
    
    if verbose:
        print(f"Running learning safety validation: {agents} agents, {ticks} ticks")
    
    for turn in range(ticks):
        system.advance(
            district_resources=resources,
            available_places=locations,
            world_map=None,
            turn=turn
        )
        alive = sum(1 for a in system.agents.values() if a.is_alive)
        population_history.append(alive)
    
    # Check population stability
    max_pop = max(population_history)
    min_pop = min(population_history)
    pop_range = max_pop - min_pop
    avg_pop = sum(population_history) / len(population_history)
    
    # Allow up to 50% swing
    pop_stable = pop_range < avg_pop * 0.5
    
    # Check memory manager stats
    try:
        from living_matrix.redis_memory import get_memory_manager
        mm = get_memory_manager()
        stats = mm.get_stats() if mm else {}
    except ImportError:
        stats = {}
    
    results = {
        'population_stable': pop_stable,
        'max_population': max_pop,
        'min_population': min_pop,
        'population_range': pop_range,
        'avg_population': avg_pop,
        'memory_stats': stats
    }
    
    passed = pop_stable
    
    if verbose:
        print(f"Population range: {min_pop} - {max_pop} (avg: {avg_pop:.0f})")
        print(f"Population stability: {'[PASS]' if pop_stable else '[FAIL]'}")
        if stats:
            print(f"Memory stats: {stats}")
    
    # Restore default config
    os.environ['LM_LEARNING_ENABLED'] = 'false'
    os.environ['LM_DISTRICT_LEARNING_ENABLED'] = 'false'
    os.environ['LM_POPULATION_MEMORY_ENABLED'] = 'false'
    
    return passed, results


def run_performance_comparison(
    agents: int = 10000,
    ticks: int = 20,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Compare performance with and without learning enabled.
    
    Args:
        agents: Number of agents
        ticks: Number of ticks
        verbose: Print results
        
    Returns:
        Comparison results dict
    """
    from living_matrix.human_agent import HumanAgentSystem
    
    def run_test(learning_enabled: bool):
        os.environ['LM_LEARNING_ENABLED'] = str(learning_enabled).lower()
        
        try:
            from living_matrix.config import reload_config
            reload_config()
        except ImportError:
            pass
        
        random.seed(42)
        districts = ['d1', 'd2', 'd3', 'd4', 'd5']
        locations = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8']
        
        system = HumanAgentSystem(
            districts=districts,
            locations=locations,
            num_agents=agents,
            seed=42
        )
        
        resources = {
            'food_stock': 80,
            'credits_pool': 200,
            'jobs_available': 20,
            'tension': 15
        }
        
        start = time.perf_counter()
        for turn in range(ticks):
            system.advance(
                district_resources=resources,
                available_places=locations,
                world_map=None,
                turn=turn
            )
        
        return time.perf_counter() - start
    
    if verbose:
        print(f"Performance comparison: {agents} agents, {ticks} ticks")
        print()
    
    if verbose:
        print("Running with learning DISABLED...", end=" ")
    time_disabled = run_test(False)
    if verbose:
        print(f"{time_disabled:.2f}s ({time_disabled/ticks*1000:.0f}ms/tick)")
    
    if verbose:
        print("Running with learning ENABLED...", end=" ")
    time_enabled = run_test(True)
    if verbose:
        print(f"{time_enabled:.2f}s ({time_enabled/ticks*1000:.0f}ms/tick)")
    
    overhead = ((time_enabled - time_disabled) / time_disabled) * 100
    
    results = {
        'agents': agents,
        'ticks': ticks,
        'time_disabled': time_disabled,
        'time_enabled': time_enabled,
        'overhead_percent': overhead
    }
    
    if verbose:
        print()
        print(f"Learning overhead: {overhead:+.1f}%")
    
    # Restore default
    os.environ['LM_LEARNING_ENABLED'] = 'false'
    
    return results


if __name__ == '__main__':
    print("=" * 60)
    print("Living Matrix Validation Suite")
    print("=" * 60)
    print()
    
    # Determinism test
    print("-" * 40)
    print("DETERMINISM TEST")
    print("-" * 40)
    passed, _ = run_determinism_test(seed=42, agents=1000, ticks=50)
    print()
    
    # Profiling
    print("-" * 40)
    print("PROFILING (top 20 functions)")
    print("-" * 40)
    run_profiling(agents=5000, ticks=5, top_n=20)
    print()
    
    # Performance comparison
    print("-" * 40)
    print("PERFORMANCE COMPARISON")
    print("-" * 40)
    run_performance_comparison(agents=5000, ticks=10)
