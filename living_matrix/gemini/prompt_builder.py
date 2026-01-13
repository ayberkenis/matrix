"""
Gemini Prompt Builder for Matrix-style Image Generation.

This module creates deterministic prompts for Gemini image generation
based on simulation state snapshots. The prompts produce realistic
world visualizations with Matrix-inspired overlay elements.

Style: Real-world cityscape/map with subtle Matrix vibes
- District names as white text labels
- HUD overlay showing stats (population, tension, resources)
- Realistic buildings and landscapes with digital enhancement
- Green/cyan data streams as atmospheric effect, not dominant
"""

from typing import Optional, List
from .snapshot import StateSnapshot


# =============================================================================
# SYSTEM PROMPT (STATIC, HARD-CODED)
# =============================================================================

SYSTEM_PROMPT = """You are an autonomous visual intelligence observing a living simulation.
You must render a single image that represents the CURRENT STATE of the world.

STYLE REQUIREMENTS:
- Realistic aerial/isometric view of a city or world map
- Subtle Matrix-inspired digital overlay (NOT full Matrix green code aesthetic)
- Real buildings, streets, districts visible beneath translucent data layers
- Glowing data streams and neural connections as atmospheric accents
- Color palette: Dark blues, teals, with green/cyan digital accents

HUD OVERLAY REQUIREMENTS:
- Include a translucent HUD panel in one corner showing key stats
- District names must appear as WHITE TEXT labels on their locations
- Stats display: Population count, Tension level, Resource status
- Clean, futuristic UI elements with soft glow effects

MOOD:
- Blend of real-world urbanism with cyberpunk/Matrix undertones
- Should feel like observing a living city through an advanced AI interface
- Tension and crisis should affect the color temperature (warmer = more danger)
- Stability should feel calm with cool blue tones"""


# =============================================================================
# VISUAL VOCABULARY MAPPINGS
# =============================================================================

# Tension level descriptors - more realistic
TENSION_DESCRIPTORS = {
    "critical": [
        "red warning indicators flashing across multiple districts",
        "emergency response patterns visible in street activity",
        "heat signatures concentrated in conflict zones",
        "infrastructure strain visible as flickering lights"
    ],
    "high": [
        "amber alert indicators on several sectors",
        "elevated activity patterns in population centers",
        "stressed infrastructure showing orange highlights",
        "crowd density increasing in key areas"
    ],
    "medium": [
        "normal urban activity with routine data flows",
        "balanced traffic patterns across districts",
        "steady state indicators showing green/blue",
        "moderate population movement between zones"
    ],
    "low": [
        "calm blue-green indicators across all sectors",
        "peaceful urban landscape with minimal alerts",
        "optimal flow patterns in all systems",
        "serene cityscape with gentle data streams"
    ]
}

# Population density descriptors - realistic city
POPULATION_DESCRIPTORS = {
    "sparse": "scattered buildings with empty streets between",
    "low": "small town feel with modest building density",
    "medium": "suburban sprawl transitioning to urban centers",
    "high": "dense metropolitan area with towering structures",
    "overcrowded": "mega-city density with overwhelming vertical development"
}

# Resource state descriptors
RESOURCE_DESCRIPTORS = {
    "abundant": "bright city lights and active commerce zones",
    "sufficient": "normal power distribution with lit districts",
    "strained": "some sectors showing dimmed lighting",
    "scarce": "darkened zones with sporadic power",
    "critical": "widespread blackout areas with emergency lighting only"
}

# Civilization phase descriptors
PHASE_DESCRIPTORS = {
    "survival": "rugged frontier settlement with basic structures",
    "growth": "construction cranes and expanding city borders",
    "stable": "established metropolis with mature infrastructure",
    "strain": "overcrowded districts with visible wear",
    "decline": "abandoned sectors and crumbling outer zones"
}

# Weather effects on the scene
WEATHER_EFFECTS = {
    "clear": "crisp visibility with sharp shadows",
    "cloudy": "diffused lighting through overcast sky",
    "rain": "wet streets reflecting city lights, rain streaks visible",
    "storm": "dramatic lightning illuminating the skyline",
    "unknown": "atmospheric haze"
}


def _get_tension_descriptor(unrest_level: str, index: int = 0) -> str:
    """Get a deterministic tension descriptor based on level."""
    descriptors = TENSION_DESCRIPTORS.get(unrest_level, TENSION_DESCRIPTORS["medium"])
    return descriptors[index % len(descriptors)]


def _get_population_descriptor(population: int, active_agents: int) -> str:
    """Get population density descriptor."""
    if population < 10:
        return POPULATION_DESCRIPTORS["sparse"]
    elif population < 30:
        return POPULATION_DESCRIPTORS["low"]
    elif population < 100:
        return POPULATION_DESCRIPTORS["medium"]
    elif population < 300:
        return POPULATION_DESCRIPTORS["high"]
    else:
        return POPULATION_DESCRIPTORS["overcrowded"]


def _get_resource_descriptor(food_stock: float, population: int) -> str:
    """Get resource state descriptor based on food per capita."""
    if population == 0:
        return RESOURCE_DESCRIPTORS["abundant"]
    
    food_per_capita = food_stock / population
    
    if food_per_capita > 5.0:
        return RESOURCE_DESCRIPTORS["abundant"]
    elif food_per_capita > 2.0:
        return RESOURCE_DESCRIPTORS["sufficient"]
    elif food_per_capita > 1.0:
        return RESOURCE_DESCRIPTORS["strained"]
    elif food_per_capita > 0.3:
        return RESOURCE_DESCRIPTORS["scarce"]
    else:
        return RESOURCE_DESCRIPTORS["critical"]


def _get_weather_effect(weather_condition: str) -> str:
    """Extract weather effect from condition string."""
    weather_lower = weather_condition.lower()
    
    if "storm" in weather_lower or "thunder" in weather_lower:
        return WEATHER_EFFECTS["storm"]
    elif "rain" in weather_lower:
        return WEATHER_EFFECTS["rain"]
    elif "cloud" in weather_lower or "overcast" in weather_lower:
        return WEATHER_EFFECTS["cloudy"]
    elif "clear" in weather_lower or "sun" in weather_lower:
        return WEATHER_EFFECTS["clear"]
    else:
        return WEATHER_EFFECTS["unknown"]


def _build_district_labels(dominant_districts: List[dict]) -> str:
    """Build district label instructions for the image."""
    if not dominant_districts:
        return "Label visible districts with white text"
    
    labels = []
    for district in dominant_districts[:5]:  # Up to 5 districts
        name = district.get("name", "Unknown")
        tension = district.get("tension", 0)
        pop = district.get("population", 0)
        
        # Determine district visual state
        if tension >= 80:
            state = "red warning glow"
        elif tension >= 60:
            state = "amber caution highlight"
        elif tension >= 40:
            state = "yellow-green normal"
        else:
            state = "cool blue stable"
        
        labels.append(f'"{name}" ({state}, pop: {pop})')
    
    return "District labels in WHITE TEXT: " + ", ".join(labels)


def _build_hud_content(snapshot: StateSnapshot) -> str:
    """Build HUD panel content description."""
    # Status indicator
    if snapshot.collapse_risk:
        status = "CRITICAL - COLLAPSE IMMINENT"
        status_color = "red"
    elif snapshot.crisis_active:
        status = "ALERT - CRISIS ACTIVE"
        status_color = "orange"
    elif snapshot.famine_risk:
        status = "WARNING - RESOURCE SHORTAGE"
        status_color = "yellow"
    elif snapshot.unrest_level == "high":
        status = "ELEVATED - HIGH TENSION"
        status_color = "amber"
    else:
        status = "NOMINAL - STABLE"
        status_color = "green"
    
    hud_lines = [
        "HUD PANEL (translucent, corner overlay):",
        f"  STATUS: {status} ({status_color} indicator)",
        f"  DAY {snapshot.simulation_day} | HOUR {snapshot.simulation_hour:02d}:00",
        f"  POPULATION: {snapshot.global_population:,} ({snapshot.active_agents} active)",
        f"  TENSION: {snapshot.average_tension:.0f}% (economic: {snapshot.tension_economic:.0f}, social: {snapshot.tension_social:.0f})",
        f"  RESOURCES: {snapshot.food_stock:.0f} food | {snapshot.credits_pool:.0f} credits",
        f"  PHASE: {snapshot.civilization_phase.upper()}",
    ]
    
    if snapshot.birth_rate > 0 or snapshot.death_rate > 0:
        hud_lines.append(f"  RATES: +{snapshot.birth_rate:.1%} births | -{snapshot.death_rate:.1%} deaths")
    
    return "\n".join(hud_lines)


def _build_special_conditions(snapshot: StateSnapshot) -> str:
    """Build special condition visual effects."""
    conditions = []
    
    if snapshot.collapse_risk:
        conditions.append("red emergency beacons pulsing across the city")
    
    if snapshot.famine_risk:
        conditions.append("darkened commercial zones with closed facilities")
    
    if snapshot.crisis_active:
        conditions.append("emergency response vehicles visible on main routes")
    
    if snapshot.conflict_rate > 0.3:
        conditions.append("crowd gatherings visible in several districts")
    
    if snapshot.world_state == "dead_world":
        conditions.append("abandoned cityscape with no activity")
    
    return "; ".join(conditions) if conditions else ""


def build_image_prompt(snapshot: StateSnapshot) -> str:
    """
    Build a deterministic image generation prompt from state snapshot.
    
    The prompt is deterministic given the same state - no random adjectives.
    Uses consistent visual vocabulary mapped to state values.
    
    Args:
        snapshot: StateSnapshot containing aggregated simulation state
    
    Returns:
        String prompt for Gemini image generation
    """
    # Core visual elements based on state
    tension_visual = _get_tension_descriptor(
        snapshot.unrest_level, 
        snapshot.simulation_turn % 4
    )
    population_visual = _get_population_descriptor(
        snapshot.global_population,
        snapshot.active_agents
    )
    resource_visual = _get_resource_descriptor(
        snapshot.food_stock,
        snapshot.global_population
    )
    phase_visual = PHASE_DESCRIPTORS.get(
        snapshot.civilization_phase, 
        PHASE_DESCRIPTORS["survival"]
    )
    weather_effect = _get_weather_effect(snapshot.weather_condition)
    district_labels = _build_district_labels(snapshot.dominant_districts)
    hud_content = _build_hud_content(snapshot)
    
    # Build the main prompt
    prompt_parts = [
        "Generate an aerial/isometric view of a living city simulation.",
        "",
        "SCENE DESCRIPTION:",
        f"- City type: {population_visual}",
        f"- Infrastructure: {phase_visual}",
        f"- Power/resources: {resource_visual}",
        f"- Current conditions: {tension_visual}",
        f"- Weather: {weather_effect}",
        "",
        "DISTRICT LAYOUT:",
        district_labels,
        "",
        hud_content,
    ]
    
    # Add special conditions
    special = _build_special_conditions(snapshot)
    if special:
        prompt_parts.append("")
        prompt_parts.append(f"SPECIAL EFFECTS: {special}")
    
    # Style instructions
    prompt_parts.extend([
        "",
        "STYLE:",
        "- Realistic cityscape with subtle Matrix/cyberpunk digital overlay",
        "- Green and cyan data streams flowing between buildings (subtle, not dominant)",
        "- White text labels for district names positioned over their areas",
        "- Translucent HUD panel with stats in corner (dark background, glowing text)",
        "- Color temperature based on tension (cool blues = stable, warm reds = crisis)",
        "- Night scene with city lights and digital augmented reality elements",
        "- Think: Google Earth meets Blade Runner meets The Matrix",
    ])
    
    return "\n".join(prompt_parts)


def build_daily_summary(
    snapshots: List[StateSnapshot],
    day: int
) -> str:
    """
    Build a compressed textual summary of a day for context memory.
    
    This is used for the daily context feed to Gemini, providing
    visual continuity day-to-day. The summary is capped in size.
    
    Args:
        snapshots: List of hourly snapshots from the day
        day: The simulation day number
    
    Returns:
        Compressed summary string (max ~500 chars)
    """
    if not snapshots:
        return f"Day {day}: No data recorded."
    
    # Use last snapshot for final state
    final = snapshots[-1]
    
    # Calculate day's trajectory
    if len(snapshots) >= 2:
        first = snapshots[0]
        tension_delta = final.average_tension - first.average_tension
        pop_delta = final.global_population - first.global_population
        
        if tension_delta > 10:
            tension_trend = "escalating"
        elif tension_delta < -10:
            tension_trend = "calming"
        else:
            tension_trend = "stable"
        
        if pop_delta > 5:
            pop_trend = "growing"
        elif pop_delta < -5:
            pop_trend = "declining"
        else:
            pop_trend = "steady"
    else:
        tension_trend = "unknown"
        pop_trend = "unknown"
    
    # Count significant events
    crisis_hours = sum(1 for s in snapshots if s.crisis_active)
    
    # Build summary
    parts = [
        f"Day {day}:",
        f"Pop {final.global_population} ({pop_trend}),",
        f"Tension {tension_trend} (avg {final.average_tension:.0f}),",
        f"Phase: {final.civilization_phase}.",
    ]
    
    if crisis_hours > 0:
        parts.append(f"Crisis active {crisis_hours}h.")
    
    if final.collapse_risk:
        parts.append("Collapse risk detected.")
    
    if final.famine_risk:
        parts.append("Famine conditions.")
    
    summary = " ".join(parts)
    
    # Cap at 500 characters
    if len(summary) > 500:
        summary = summary[:497] + "..."
    
    return summary


def get_system_prompt() -> str:
    """Return the static system prompt for Gemini."""
    return SYSTEM_PROMPT
