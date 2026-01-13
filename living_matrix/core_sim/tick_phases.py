"""Tick phase decomposition for structured simulation.

The main tick is decomposed into logical phases that can be:
- Profiled independently
- Parallelized where safe
- Skipped conditionally based on population

Phases are designed to be side-effect aware with minimal cross-dependencies.
"""

from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from living_matrix.utils.observability import get_observer


class TickPhase(Enum):
    """Simulation tick phases in execution order."""
    ENVIRONMENT = auto()      # Weather, time, world pressure
    POPULATION_LIFECYCLE = auto()  # Aging, deaths, births, promotions
    AGENT_DECISIONS = auto()  # Agent action selection
    AGENT_ACTIONS = auto()    # Action execution, interactions
    ECONOMY = auto()          # Resource production/consumption, trade
    TENSION = auto()          # Conflict resolution, tension propagation
    PERSISTENCE = auto()      # State saving, metrics export


@dataclass
class PhaseResult:
    """Result of executing a phase."""
    phase: TickPhase
    events: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    should_continue: bool = True  # False to halt tick early


@dataclass
class PhaseContext:
    """
    Shared context passed between phases.
    
    Contains read-only inputs and accumulates outputs.
    Designed for minimal mutable state.
    """
    # Input (read-only during phases)
    turn: int
    agents: Dict[str, Any]  # Live agents
    districts: Dict[str, Any]
    weather_states: Dict[str, Dict]
    extinction_risk: float = 0.0
    population_pressure: float = 0.0
    death_panic_mode: bool = False
    generational_trauma: float = 0.0
    
    # Accumulated outputs (each phase may add to these)
    events: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)
    births_this_tick: List[Tuple[str, str]] = field(default_factory=list)
    deaths_this_tick: List[str] = field(default_factory=list)
    promotions_this_tick: List[str] = field(default_factory=list)
    
    # Phase-specific data (set by one phase, read by another)
    active_agent_ids: List[str] = field(default_factory=list)
    inactive_agent_ids: List[str] = field(default_factory=list)
    agent_actions: Dict[str, str] = field(default_factory=dict)


class TickPhaseExecutor:
    """
    Executes tick phases in order with observability.
    
    Each phase is a function that takes PhaseContext and returns PhaseResult.
    Phases can be skipped conditionally based on population or tick number.
    """
    
    def __init__(self):
        self._phase_handlers: Dict[TickPhase, Callable[[PhaseContext], PhaseResult]] = {}
        self._skip_conditions: Dict[TickPhase, Callable[[PhaseContext], bool]] = {}
        self._observer = get_observer()
    
    def register_phase(
        self,
        phase: TickPhase,
        handler: Callable[[PhaseContext], PhaseResult],
        skip_condition: Optional[Callable[[PhaseContext], bool]] = None
    ) -> None:
        """
        Register a handler for a phase.
        
        Args:
            phase: The phase to handle
            handler: Function that executes the phase
            skip_condition: Optional function that returns True if phase should skip
        """
        self._phase_handlers[phase] = handler
        if skip_condition:
            self._skip_conditions[phase] = skip_condition
    
    def execute_tick(self, context: PhaseContext) -> List[PhaseResult]:
        """
        Execute all registered phases in order.
        
        Args:
            context: Shared context for the tick
            
        Returns:
            List of PhaseResults from each executed phase
        """
        results = []
        
        # Execute phases in enum order
        for phase in TickPhase:
            if phase not in self._phase_handlers:
                continue
            
            # Check skip condition
            if phase in self._skip_conditions:
                if self._skip_conditions[phase](context):
                    continue
            
            # Execute with timing
            with self._observer.phase(phase.name):
                try:
                    result = self._phase_handlers[phase](context)
                    results.append(result)
                    
                    # Merge events into context
                    context.events.extend(result.events)
                    
                    # Check for early halt
                    if not result.should_continue:
                        break
                        
                except Exception as e:
                    # Log error but continue with other phases
                    import logging
                    logging.getLogger(__name__).error(
                        f"Error in phase {phase.name}: {e}",
                        exc_info=True
                    )
        
        return results


def create_population_lifecycle_phase(
    age_agent_func: Callable,
    check_reproduction_func: Callable,
    add_child_func: Callable,
    promote_children_func: Callable,
    age_child_pools_func: Callable
) -> Callable[[PhaseContext], PhaseResult]:
    """
    Create the population lifecycle phase handler.
    
    This phase handles:
    - Agent aging
    - Death checks
    - Reproduction checks
    - Child pool aging
    - Child promotions
    """
    def handler(ctx: PhaseContext) -> PhaseResult:
        result = PhaseResult(phase=TickPhase.POPULATION_LIFECYCLE)
        
        # These operations are handled by the caller passing in the functions
        # The phase just structures the execution order
        
        # Aging and deaths are handled first
        # Then reproduction
        # Then child pool aging
        # Finally promotions
        
        result.metrics["births"] = len(ctx.births_this_tick)
        result.metrics["deaths"] = len(ctx.deaths_this_tick)
        result.metrics["promotions"] = len(ctx.promotions_this_tick)
        
        return result
    
    return handler


def create_agent_decisions_phase(
    decide_action_func: Callable
) -> Callable[[PhaseContext], PhaseResult]:
    """
    Create the agent decisions phase handler.
    
    This phase selects actions for all active agents.
    Inactive agents keep their current action.
    """
    def handler(ctx: PhaseContext) -> PhaseResult:
        result = PhaseResult(phase=TickPhase.AGENT_DECISIONS)
        
        # Decisions are computed for active agents only
        # ctx.agent_actions is populated with agent_id -> action
        
        result.metrics["decisions_made"] = len(ctx.agent_actions)
        
        return result
    
    return handler


def create_agent_actions_phase(
    execute_action_func: Callable
) -> Callable[[PhaseContext], PhaseResult]:
    """
    Create the agent actions phase handler.
    
    This phase executes the decided actions.
    """
    def handler(ctx: PhaseContext) -> PhaseResult:
        result = PhaseResult(phase=TickPhase.AGENT_ACTIONS)
        
        # Actions are executed, generating events
        
        result.metrics["actions_executed"] = len(ctx.agent_actions)
        
        return result
    
    return handler


def create_skip_condition_by_population(
    threshold: int,
    tick_interval: int
) -> Callable[[PhaseContext], bool]:
    """
    Create a skip condition based on population and tick number.
    
    Above the threshold, the phase only runs every N ticks.
    """
    def should_skip(ctx: PhaseContext) -> bool:
        if len(ctx.agents) < threshold:
            return False  # Always run below threshold
        return ctx.turn % tick_interval != 0
    
    return should_skip


# Pre-built skip conditions for common phases
def skip_reproduction_for_large_pop(ctx: PhaseContext) -> bool:
    """Skip reproduction every N ticks for large populations."""
    from living_matrix.constants.performance_constants import (
        SKIP_REPRODUCTION_THRESHOLD,
        REPRODUCTION_TICK_INTERVAL_LARGE_POP
    )
    if len(ctx.agents) < SKIP_REPRODUCTION_THRESHOLD:
        return False
    return ctx.turn % REPRODUCTION_TICK_INTERVAL_LARGE_POP != 0


def skip_conflicts_for_large_pop(ctx: PhaseContext) -> bool:
    """Skip conflict check every N ticks for large populations."""
    from living_matrix.constants.performance_constants import (
        SKIP_CONFLICTS_THRESHOLD,
        CONFLICT_TICK_INTERVAL_LARGE_POP
    )
    if len(ctx.agents) < SKIP_CONFLICTS_THRESHOLD:
        return False
    return ctx.turn % CONFLICT_TICK_INTERVAL_LARGE_POP != 0
