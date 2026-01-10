"""All dataclasses organized by domain."""

from .agent_dataclasses import (
    HumanNeeds, HumanTraits, HumanInventory, HumanAgent,
    AgentNeeds, AgentMood, Agent, Relationship as WorldSimRelationship
)
from .world_dataclasses import (
    Drives, AdvancedDistrict, DistrictPressure,
    DistrictPsychology, DistrictTension, WorldEvent
)
from .memory_dataclasses import (
    Episode, SemanticGraph, EmotionalTrace, LearnedRule
)
from .relationship_dataclasses import (
    Relationship, RelationshipData
)
from .belief_dataclasses import Belief
from .culture_dataclasses import Culture
from .flag_dataclasses import WorldFlag, FlagTrigger
from .intent_dataclasses import Intent
from .tension_dataclasses import Tension
from .causality_dataclasses import CausalRecord
from .economy_dataclasses import DistrictEconomy
from .event_dataclasses import Event
from .ipc_dataclasses import MatrixState, MatrixCommand
from .map_dataclasses import Location, Region

__all__ = [
    # Agent dataclasses
    'HumanNeeds', 'HumanTraits', 'HumanInventory', 'HumanAgent',
    'AgentNeeds', 'AgentMood', 'Agent', 'WorldSimRelationship',
    # World dataclasses
    'Drives', 'AdvancedDistrict', 'DistrictPressure',
    'DistrictPsychology', 'DistrictTension', 'WorldEvent',
    # Memory dataclasses
    'Episode', 'SemanticGraph', 'EmotionalTrace', 'LearnedRule',
    # Relationship dataclasses
    'Relationship', 'RelationshipData',
    # Other dataclasses
    'Belief', 'Culture', 'WorldFlag', 'FlagTrigger', 'Intent', 'Tension',
    'CausalRecord', 'DistrictEconomy', 'Event', 'MatrixState', 'MatrixCommand',
    'Location', 'Region'
]
