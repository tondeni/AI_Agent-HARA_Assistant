# ==============================================================================
# code/tools/scenario_builder.py
# Tool for building complete driving scenarios from basic situations
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import json
import os
import sys
from typing import List, Dict

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder)
plugin_folder = os.path.dirname(code_folder)
sys.path.insert(0, code_folder)


class ScenarioBuilder:
    """
    Build complete driving scenarios for HARA by combining basic operational situations.
    Maps driving_scenarios.json conditions to operational_situations.json exposures.
    """
    
    def __init__(self, plugin_folder: str):
        self.plugin_folder = plugin_folder
        # Simplified scenario mapping - key conditions to operational situation IDs
        self.condition_to_scenario_map = {
            # Speed-based
            "speed_<150_kmh": ["URB-001", "URB-004"],
            "speed_150-210_kmh": ["HWY-001"],
            "speed_210-300_kmh": ["HWY-001"],  # But exposure adjusted to E2
            
            # Visibility
            "poor_visibility_<50m_fog_blinding": ["ENV-005"],
            "dark_no_residual_light": ["ENV-006"],
            
            # Road conditions
            "reduced_friction_coefficient_<0.8": ["ENV-001", "ENV-002"],
            "low_friction_coefficient_<0.5_snow_ice": ["ENV-003", "ENV-004"],
            
            # Dynamic
            "emergency_brake": ["CRT-001"],
            "performing_lane_change": ["HWY-002"],
            "overtaking": ["HWY-002"],
            
            # Traffic
            "high_traffic_without_safety_distance": ["URB-001", "HWY-005"],
            "crossing_intersection": ["URB-004"],
            
            # Road type
            "highway": ["HWY-001"],
            "city": ["URB-001"],
            "tunnel": ["HWY-001", "ENV-006"],
            
            # Vehicle states
            "vehicle_recharging": ["SPC-003", "SPC-004"],
            "driving_with_trailer": ["SPC-005"],
        }
    
    def get_scenarios_for_conditions(self, conditions: List[str]) -> List[str]:
        """Map driving conditions to operational situation IDs."""
        scenario_ids = []
        for condition in conditions:
            # Fuzzy matching - find closest key
            for key, scenarios in self.condition_to_scenario_map.items():
                if key.lower() in condition.lower() or condition.lower() in key.lower():
                    scenario_ids.extend(scenarios)
                    break
        # Remove duplicates while preserving order
        return list(dict.fromkeys(scenario_ids))
    
    def calculate_min_exposure(self, exposures: List[str]) -> str:
        """Calculate minimum exposure from list."""
        exposure_order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
        if not exposures:
            return "E4"
        return min(exposures, key=lambda x: exposure_order.get(x, 4))


@tool(
    return_direct=True,
    examples=[
        "build scenario for highway driving in heavy rain at night",
        "create scenario for urban parking in winter conditions",
        "construct scenario for fast charging in extreme heat"
    ]
)
def build_driving_scenario_for_hazard(tool_input, cat):
    """
    Build a complete driving scenario for HARA exposure assessment.
    
    This tool helps construct realistic driving scenarios by:
    1. Identifying key conditions (speed, visibility, road, traffic, etc.)
    2. Mapping to basic operational situations from database
    3. Calculating combined exposure using MIN rule
    4. Generating scenario description
    
    Args:
        tool_input: Hazard context or scenario description
        cat: Cheshire Cat instance
        
    Returns:
        Complete driving scenario with exposure rating
        
    Example:
        User: "build scenario for highway driving in heavy rain at night"
        Output: Selected scenarios (HWY-001, ENV-002, ENV-006), combined exposure E2
    """
    
    log.info("🔧 TOOL CALLED: build_driving_scenario_for_hazard")
    
    # Parse input
    scenario_context = ""
    if isinstance(tool_input, str):
        scenario_context = tool_input.strip()
    elif isinstance(tool_input, dict):
        scenario_context = tool_input.get("context", tool_input.get("scenario", ""))
    
    if not scenario_context:
        return """❌ **No Scenario Context Provided**

**Usage:**
```
build scenario for [scenario description]
```

**Examples:**
- `build scenario for highway driving in heavy rain at night`
- `build scenario for urban parking during winter`
- `build scenario for battery charging in hot weather`
"""
    
    log.info(f"🏗️ Building scenario for: {scenario_context}")
    
    # Use LLM to extract key conditions
    extract_prompt = f"""Extract key driving conditions from this scenario description:

"{scenario_context}"

List ONLY the most relevant conditions from these categories:
- Speed: <150 km/h, 150-210 km/h, >210 km/h
- Visibility: normal, reduced (rain/fog), dark/night
- Road: highway, urban/city, rural, parking
- Weather: normal, rain, snow/ice, extreme heat/cold
- Traffic: normal, heavy/congested, no traffic
- Vehicle state: driving, parked, charging, towing
- Maneuver: normal, lane change, emergency braking, parking

Provide as a simple comma-separated list. Example output:
highway, heavy rain, night, high traffic

Your output:"""
    
    try:
        conditions_str = cat.llm(extract_prompt).strip()
        log.info(f"Extracted conditions: {conditions_str}")
        
        # Map to scenario IDs
        builder = ScenarioBuilder(plugin_folder)
        scenario_ids = builder.get_scenarios_for_conditions(conditions_str.split(','))
        
        if not scenario_ids:
            # Fallback - use default urban scenario
            scenario_ids = ["URB-001", "STA-001"]
        
        # Limit to 4 scenarios max
        scenario_ids = scenario_ids[:4]
        
        # Now call the exposure assessment tool to get details
        # Import from exposure_assessment_refined
        sys.path.insert(0, os.path.dirname(__file__))
        from exposure_assessment_refined import ExposureAssessor
        
        assessor = ExposureAssessor(plugin_folder)
        combined_exposure, rationale = assessor.calculate_combined_exposure(scenario_ids)
        
        # Get scenario details
        scenario_details = []
        for sid in scenario_ids:
            scenario = assessor.find_scenario_by_id(sid)
            if scenario:
                scenario_details.append(scenario)
        
        # Build output
        result = f"""✅ **Driving Scenario Built**

**Context:** {scenario_context}

**Extracted Conditions:** {conditions_str}

---

### Selected Operational Situations

"""
        
        for scenario in scenario_details:
            result += f"""**{scenario.get('id')}**: {scenario.get('name')} - **{scenario.get('exposure')}**
- {scenario.get('description')}
- Frequency: {scenario.get('frequency')}

"""
        
        result += f"""---

### Combined Scenario

**Name:** {' in '.join([s.get('name', '') for s in scenario_details])}

**Combined Exposure:** **{combined_exposure}**

**Calculation:** MIN({', '.join([s.get('exposure', 'E4') for s in scenario_details])}) = {combined_exposure}

**Rationale:**
{rationale}

---

**Usage in HARA:**
- Use this combined scenario for exposure assessment
- Combined exposure: {combined_exposure}
- Selected scenario IDs: {', '.join(scenario_ids)}

**Next Steps:**
1. Assess Severity (S) for your hazard in this scenario
2. Assess Controllability (C) for your hazard in this scenario
3. Calculate ASIL using E={combined_exposure}, S=?, C=?
"""
        
        # Store in working memory
        if "hara_built_scenarios" not in cat.working_memory:
            cat.working_memory["hara_built_scenarios"] = []
        
        cat.working_memory["hara_built_scenarios"].append({
            "context": scenario_context,
            "conditions": conditions_str,
            "scenario_ids": scenario_ids,
            "combined_exposure": combined_exposure,
            "scenario_details": scenario_details
        })
        
        return result
        
    except Exception as e:
        log.error(f"❌ Error building scenario: {e}")
        return f"""❌ **Error Building Scenario**

Error: {str(e)}

**Fallback Suggestion:**
Use the exposure assessment tool directly:
```
assess exposure for [hazard description]
```
"""


@tool(
    return_direct=True,
    examples=[
        "suggest scenarios for brake system failure",
        "what scenarios for battery thermal runaway",
        "recommend scenarios for steering malfunction"
    ]
)
def suggest_scenarios_for_hazard(tool_input, cat):
    """
    Suggest relevant operational situations for a specific hazard.
    
    Analyzes the hazard and recommends 3-5 most relevant basic operational
    situations from the database that should be considered for exposure assessment.
    
    Args:
        tool_input: Hazard or malfunction description
        cat: Cheshire Cat instance
        
    Returns:
        Recommended scenarios with justification
    """
    
    log.info("🔧 TOOL CALLED: suggest_scenarios_for_hazard")
    
    hazard = ""
    if isinstance(tool_input, str):
        hazard = tool_input.strip()
    elif isinstance(tool_input, dict):
        hazard = tool_input.get("hazard", "")
    
    if not hazard:
        return "❌ Please provide a hazard description"
    
    # Build prompt for LLM
    prompt = f"""You are a Functional Safety Engineer. Given this hazard, suggest 3-5 most relevant operational situations for exposure assessment.

**Hazard:** {hazard}

**Consider:**
- When is this hazard most likely to occur?
- What vehicle states make it more probable?
- What environmental conditions increase risk?
- What driving maneuvers are involved?
- What speeds or road types are relevant?

**Available Scenario Categories:**
- Urban driving (city traffic, parking, intersections, pedestrians, residential)
- Highway driving (cruising, lane changes, merging, exits)
- Environmental (rain, snow, ice, fog, night, extreme temps)
- Special situations (charging, towing, off-road, long parking, diagnostics)
- Critical maneuvers (emergency braking, evasive steering, loss of traction, collision)
- Vehicle states (normal, degraded, low SOC, thermal stress, initialization)

**Output Format:**
For each suggested scenario category, provide:
1. Category name
2. Specific scenario type
3. Suggested exposure level (E0-E4)
4. Justification (1-2 sentences)

Limit to 3-5 most relevant scenarios.
"""
    
    try:
        suggestions = cat.llm(prompt).strip()
        
        result = f"""💡 **Scenario Suggestions for Hazard**

**Hazard:** {hazard}

---

{suggestions}

---

**Next Steps:**
1. Review these suggestions
2. Use: `assess exposure for {hazard[:40]}...` to get detailed assessment
3. Or use: `build scenario for [specific scenario]` to construct custom scenario

**Note:** These are suggestions. The final exposure assessment tool will automatically
select and combine the most appropriate scenarios from the database.
"""
        
        return result
        
    except Exception as e:
        log.error(f"Error suggesting scenarios: {e}")
        return f"❌ Error: {str(e)}"