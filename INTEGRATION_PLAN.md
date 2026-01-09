# Integration Plan for Four Feature Groups

## Status: Core modules created, integration in progress

### Created Files:
1. ✅ `living_matrix/human_agent.py` - HumanAgent with needs/goals/conflict
2. ✅ `living_matrix/economy.py` - Economy system with production/consumption/tension
3. ✅ `living_matrix/camera.py` - Camera/POV modes
4. ✅ `living_matrix/ui_panels.py` - Terminal UI panels

### Remaining Integration Tasks:

1. **Add commands to `core.py`**:
   - `/agents` - list human agents
   - `/agent <id|name>` - detailed agent info
   - `/districts` - list district stats
   - `/economy` - global economy snapshot
   - `/cam god|district|agent|place [target]` - camera controls
   - `/ui on|off|clear|mode|fps` - UI controls

2. **Integrate into `_world_tick()`**:
   - Advance economy system per district
   - Advance human agent system per district
   - Collect events from both systems
   - Update tension based on events

3. **Integrate rendering**:
   - Call UI panels render based on camera mode
   - Render appropriate view (GOD/DISTRICT/AGENT/PLACE)
   - Only render when UI enabled and should_render() returns True

4. **Fix district/location mapping**:
   - Map human agents to world_map regions/locations
   - Ensure district_ids match between systems
