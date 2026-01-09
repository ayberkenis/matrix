# Consequence-Driven World Simulation - Implementation Summary

## Overview
Implemented a consequence-driven world simulation with food scarcity, work success/failure, weather effects, and memory bias affecting agent decisions. The system runs autonomously without user stimulus and remains stable.

## Key Changes

### A) Persistent State Fields (Backward Compatible)
- **Regions**: Extended `Region` class in `world_sim/map.py` with:
  - `food`, `materials`, `energy` (0-100 floats)
  - `infrastructure` (0-1 float)
  - `tension` (0-1 float)
  - `tags` (list of region types)
- **Agents**: Extended `Agent` class in `world_sim/agents.py` with:
  - `energy`, `stress` (0-1 floats)
  - `credits` (float for trade)
  - `risk`, `social_trait`, `work_ethic` (0-1 floats)
  - `location_success`, `location_failure` (dicts for memory bias)
- **Serialization**: Updated `to_dict`/`from_dict` methods to persist new fields with defaults

### B) Regions (Districts)
- Created 6-12 fictional regions with resources, infrastructure, and tension
- Resources regenerate based on tags and weather
- Consumption based on agent count per region
- Shortages increase tension and reduce work success

### C) Agents (Humans)
- Created 8-24 agents (configurable, default 8-24)
- Decision policy based on:
  - Needs (hunger, energy, stress)
  - Weather conditions
  - Region resources
  - Memory bias (success/failure per region)
- Actions: rest, work, trade, socialize, move

### D) Weather System
- Weather affects:
  - Movement cost (precipitation)
  - Work success probability (precipitation, temperature)
  - Food consumption (cold increases hunger)
  - Stress (storms increase stress)

### E) Work Success/Failure
- Success probability formula:
  ```
  p = 0.75 + work_ethic*0.15 + infrastructure*0.10 
      - hunger*0.20 - (1-energy)*0.15 
      - weather_penalty - shortage_penalty
  ```
- Success: produces resources, reduces stress, earns credits, updates memory
- Failure: increases stress, records failure in memory

### F) Trade System
- Agents use credits (earned from work) to buy food
- Price increases with scarcity (multiplier 1.0-2.0)
- Only works in market regions

### G) Socialize/Relationships
- Two agents in same region can socialize
- Positive: reduces stress, increases trust
- Negative (if tension high): increases stress, decreases trust

### H) Rumors and Event Log
- Rumors generated from:
  - Event types (tensions, cooperation, discovery)
  - Average region tension
  - Food shortages across regions
- Displayed in world bulletin

### I) Enhanced Output
- World bulletin shows:
  - Time, weather, hotspots
  - Recent events (1-2)
  - Resource warnings (if food < 20)
  - Rumors
  - Follow section (if following agent)

### J) Autonomous Mode Default
- Autopilot ON by default
- `/auto on|off` command to toggle
- `/run` and `/pause` commands still work
- System advances continuously when autopilot is on

### K) Novelty Floor (Anti-Collapse)
- Tracks consecutive turns with diversity < 0.15
- After 30 turns, injects new tokens:
  - Region names
  - Agent names
  - Professions
  - Weather terms
- Resets counter when diversity recovers

### L) Sanity Checks
- `/sanity` command runs 200 steps headless
- Checks:
  - No NaNs
  - Resources bounded [0, 100]
  - Tension bounded [0, 1]
  - Events occurred
  - Diversity > 0.05

## New Files

1. **`living_matrix/world_sim/consequence.py`**
   - `ConsequenceSystem` class
   - `WorkResult` dataclass
   - Methods: `attempt_work`, `attempt_trade`, `attempt_socialize`, `update_region_resources`, `get_memory_bias`

## Modified Files

1. **`living_matrix/world_sim/map.py`**
   - Extended `Region` dataclass
   - Updated `_generate_map` to initialize resources
   - Added `get_region_by_location_id`, `update_region_resources`

2. **`living_matrix/world_sim/agents.py`**
   - Extended `Agent` dataclass with new fields
   - Updated serialization to include new fields

3. **`living_matrix/world_sim/bulletin.py`**
   - Added resource warnings
   - Enhanced rumor generation

4. **`living_matrix/core.py`**
   - Added `ConsequenceSystem` integration
   - New method: `_advance_agents_with_consequences`
   - New method: `_determine_agent_action_with_consequences`
   - Updated `_world_tick` to use consequence system
   - Added novelty floor tracking
   - Added `/auto` and `/sanity` commands

5. **`living_matrix/world_sim/__init__.py`**
   - Added `ConsequenceSystem` export

## Commands

### New Commands
- `/auto [on|off]` - Toggle autonomous mode (default: ON)
- `/sanity` - Run sanity checks (200 steps, assert resources bounded, events occurred, diversity > 0.05)

### Existing Commands (Preserved)
- `/run` - Start autonomous mode
- `/pause` - Pause autonomous mode
- `/speed <seconds>` - Set tick delay
- `/time`, `/weather`, `/map`, `/events`, `/agents`, `/agent <id|name>`, `/follow <id|name>`, etc.

## Example Usage

```bash
# Start simulation (autopilot ON by default)
python -m living_matrix

# Run without autopilot
python -m living_matrix --no-run

# Commands while running:
/auto off      # Disable autopilot
/auto on       # Enable autopilot
/sanity        # Run sanity checks
/pause         # Pause
/run           # Resume
```

## Expected Output

The system will:
1. Run autonomously, advancing world simulation every 0.3 seconds
2. Print world bulletin every 5 turns showing:
   - Time, weather, hotspots
   - Recent events
   - Resource warnings (if any)
   - Rumors
3. Agents make decisions based on needs, memory, and weather
4. Resources fluctuate based on consumption and regeneration
5. Work can succeed or fail, affecting agent memory and stress
6. Trade occurs when agents need food and have credits
7. Social interactions affect relationships and stress

## Determinism

- All random operations use `seed` from world state
- Fixed seed → same sequence of events
- Save/load preserves state exactly

## Stability

- Resources clamped to [0, 100]
- Tension clamped to [0, 1]
- Agent needs/energy/stress clamped to [0, 1]
- Novelty floor prevents token collapse
- No infinite loops (bounded operations)
