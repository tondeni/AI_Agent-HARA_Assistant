# operational_situation_tool.py
# Tool for selecting and combining operational situations for HARA

import json
import os
from cat.mad_hatter.decorators import tool
from cat.log import log

def load_operational_situations(plugin_folder):
    """Load operational situations database from JSON file."""
    template_path = os.path.join(plugin_folder, "templates", "operational_situations.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"Operational situations file not found at {template_path}")
        return None
    except Exception as e:
        log.error(f"Error loading operational situations: {e}")
        return None


def get_exposure_value(exposure_level):
    """Convert exposure level to numeric value for comparison."""
    exposure_map = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
    return exposure_map.get(exposure_level, 0)


def get_exposure_level(exposure_value):
    """Convert numeric value back to exposure level."""
    level_map = {0: "E0", 1: "E1", 2: "E2", 3: "E3", 4: "E4"}
    return level_map.get(exposure_value, "E0")


def calculate_combined_exposure(scenario_ids, situations_data):
    """
    Calculate combined exposure for multiple scenarios.
    Uses minimum exposure as per ISO 26262 guidance (intersection of conditions).
    """
    exposures = []
    
    # Extract exposure from each scenario
    for category_name, scenarios in situations_data["basic_scenarios"].items():
        for scenario in scenarios:
            if scenario["id"] in scenario_ids:
                exposure_value = get_exposure_value(scenario["exposure"])
                exposures.append(exposure_value)
    
    if not exposures:
        return "E0", "No valid scenarios found"
    
    # Take minimum (most restrictive) exposure
    min_exposure_value = min(exposures)
    combined_exposure = get_exposure_level(min_exposure_value)
    
    rationale = f"Combined exposure calculated as minimum of constituent scenarios: {' + '.join([get_exposure_level(e) for e in exposures])} = {combined_exposure}"
    
    return combined_exposure, rationale


@tool(return_direct=True)
def select_operational_situation(tool_input, cat):
    """
    Intelligently select appropriate operational situation(s) for a specific hazard in HARA.
    
    This tool analyzes the hazardous event and selects relevant basic scenarios,
    then combines them according to ISO 26262 guidelines.
    
    Input: Hazard description or hazardous event
    Example: "Battery overcharge during fast charging in extreme heat"
    
    Use this tool when:
    - "select operational situation for [hazard]"
    - "what operational situation for [hazard]"
    - "find driving scenario for [hazard]"
    """
    print("✅ TOOL CALLED: select_operational_situation")
    
    hazard_description = str(tool_input).strip() if tool_input else ""
    if not hazard_description:
        return """❌ **Hazard description required**

Please specify the hazardous event for which to select operational situation(s).

**Example:**
`select operational situation for: Battery thermal runaway during fast charging`

**Available scenario categories:**
- Urban driving (city traffic, parking, pedestrians)
- Highway driving (cruising, lane changes, merging)
- Environmental conditions (rain, snow, ice, fog, night, temperature extremes)
- Special operations (charging, towing, cold start, service mode)
- Critical maneuvers (emergency braking, evasive steering, collisions)
- Vehicle states (normal, degraded, low SoC, thermal stress)
"""

    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return "❌ Error: Could not load operational situations database"

    item_name = cat.working_memory.get("hara_item_name", "the system")
    
    log.info(f"🎯 Selecting operational situation for hazard: {hazard_description[:100]}...")

    # Build prompt for LLM to analyze and select scenarios
    prompt = f"""You are a Functional Safety Engineer selecting appropriate operational situations for HARA per ISO 26262-3:2018 Clause 6.4.2.

**System:** {item_name}

**Hazardous Event:** {hazard_description}

**Available Basic Scenarios Database:**
{json.dumps(situations_data["basic_scenarios"], indent=2)[:8000]}

**Task:** Analyze the hazardous event and select 1-3 basic scenarios that are most relevant.

**Selection Criteria:**
1. **Relevance:** Scenarios must be directly related to when/where the hazard could occur
2. **Probability:** Consider exposure frequency of each scenario
3. **Severity Impact:** Consider if the scenario would affect the severity of consequences
4. **Logical Compatibility:** Selected scenarios must be able to occur simultaneously

**Combination Rules:**
- If selecting multiple scenarios, they will be combined
- Combined exposure = MINIMUM exposure of constituent scenarios (intersection logic)
- Maximum 3 scenarios for clarity
- Scenarios must be compatible (e.g., cannot combine parking with highway cruising)

**Examples:**

Example 1:
Hazard: "Loss of braking during high-speed driving"
Selected Scenarios:
- HWY-001 (Highway Cruising, E4)
- ENV-006 (Night Driving, E3)
Combined: "Highway cruising at night" - Exposure E3

Example 2:
Hazard: "Battery overcharge during charging"
Selected Scenarios:
- SPC-003 (EV Fast Charging, E2)
- ENV-007 (Extreme Heat, E2)
Combined: "Fast charging in extreme heat" - Exposure E2

Example 3:
Hazard: "Loss of traction during lane change"
Selected Scenarios:
- HWY-002 (Highway Lane Changes, E4)
- ENV-003 (Light Snow/Slush, E2)
Combined: "Lane change on snowy highway" - Exposure E2

**Your Analysis:**

1. **Hazard Analysis:** What conditions make this hazard most likely or most severe?

2. **Selected Scenarios:** List 1-3 scenario IDs with justification
   - Scenario ID: [ID]
   - Name: [Name]
   - Exposure: [E level]
   - Justification: [Why relevant]

3. **Combined Operational Situation:**
   - Name: [Descriptive name combining selected scenarios]
   - Combined Exposure: [Minimum E level from selected scenarios]
   - Description: [Full description of the combined situation]
   - Duration: [Typical duration when this combination occurs]
   - Frequency: [How often this combination occurs]

4. **Exposure Justification:** Explain why this combined exposure level is appropriate

Provide your analysis now:
"""

    try:
        analysis = cat.llm(prompt).strip()
        
        # Store in working memory for use in HARA
        if "operational_situations" not in cat.working_memory:
            cat.working_memory["operational_situations"] = []
        
        cat.working_memory["operational_situations"].append({
            "hazard": hazard_description,
            "analysis": analysis,
            "timestamp": cat.working_memory.get("timestamp", "")
        })
        
        log.info(f"✅ Operational situation selected for hazard")
        
        result = f"""✅ **Operational Situation Selected**

{analysis}

---

**ISO 26262-3:2018 Compliance Notes:**
- Clause 6.4.2.3: Operational situations have been classified based on vehicle operation
- Clause 6.4.3.2: Exposure probability reflects realistic usage patterns
- Statistical data and real-world usage patterns considered

**Next Steps:**
- Use this operational situation in HARA table for Exposure (E) assessment
- Assess Severity (S) considering this operational context
- Assess Controllability (C) considering this operational context
- Calculate ASIL: `assess hazard: {hazard_description[:50]}...`

**View Database:** To see all available scenarios, ask: "show all operational situations"
"""
        
        return result

    except Exception as e:
        log.error(f"❌ Error selecting operational situation: {e}")
        return f"❌ Error selecting operational situation: {str(e)}"


@tool(return_direct=True)
def list_operational_situations_by_category(tool_input, cat):
    """
    List all available operational situations organized by category.
    
    Input: (Optional) Category name to filter results
    Options: "urban", "highway", "environmental", "special", "critical", "states"
    
    Use this tool when:
    - "show all operational situations"
    - "list available scenarios"
    - "what scenarios are available"
    - "show environmental scenarios"
    """
    print("✅ TOOL CALLED: list_operational_situations_by_category")
    
    category_filter = str(tool_input).strip().lower() if tool_input else None
    
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return "❌ Error: Could not load operational situations database"
    
    # Category name mapping
    category_map = {
        "urban": "urban_driving",
        "highway": "highway_driving",
        "environmental": "environmental_conditions",
        "special": "special_operations",
        "critical": "critical_maneuvers",
        "states": "vehicle_states"
    }
    
    output = ["# Available Operational Situations\n"]
    output.append("*Based on ISO 26262-3:2018 Clause 6.4.2 - Situation Analysis*\n")
    output.append("## Exposure Classification Criteria:\n")
    for level, description in situations_data["exposure_criteria"].items():
        output.append(f"- **{level}:** {description}")
    output.append("\n---\n")
    
    # Filter or show all categories
    categories_to_show = situations_data["basic_scenarios"].keys()
    if category_filter and category_filter in category_map:
        filter_key = category_map[category_filter]
        categories_to_show = [filter_key] if filter_key in situations_data["basic_scenarios"] else []
    
    for category_name in categories_to_show:
        scenarios = situations_data["basic_scenarios"][category_name]
        
        # Format category name
        display_name = category_name.replace("_", " ").title()
        output.append(f"## {display_name}\n")
        
        for scenario in scenarios:
            output.append(f"### {scenario['id']}: {scenario['name']}")
            output.append(f"**Exposure:** {scenario['exposure']} ({scenario['exposure_percentage']})")
            output.append(f"**Description:** {scenario['description']}")
            output.append(f"**Frequency:** {scenario['frequency']}")
            output.append(f"**Typical Duration:** {scenario['typical_duration']}")
            output.append(f"**Rationale:** {scenario['rationale']}\n")
    
    # Add combination rules
    output.append("\n---\n")
    output.append("## Scenario Combination Rules\n")
    output.append(situations_data["scenario_combination_rules"]["description"])
    output.append(f"\n**Exposure Calculation:** {situations_data['scenario_combination_rules']['exposure_calculation']}")
    output.append(f"\n**Rationale:** {situations_data['scenario_combination_rules']['rationale']}\n")
    
    output.append("\n### Example Combinations:\n")
    for example in situations_data["scenario_combination_rules"]["examples"]:
        output.append(f"- **{example['name']}** ({example['combination']})")
        output.append(f"  - Combined Exposure: {example['combined_exposure']}")
        output.append(f"  - {example['explanation']}\n")
    
    result = "\n".join(output)
    
    log.info(f"✅ Operational situations listed (filter: {category_filter or 'none'})")
    
    return result


@tool(return_direct=False)
def create_custom_operational_situation(tool_input, cat):
    """
    Create a custom operational situation by manually combining specific scenarios.
    
    Input: JSON string or dict with scenario IDs to combine
    Example: {"scenario_ids": ["HWY-001", "ENV-002", "ENV-006"], "name": "Night highway driving in heavy rain"}
    
    Use this tool when user wants to manually specify a combination.
    """
    print("✅ TOOL CALLED: create_custom_operational_situation")
    
    # Parse input
    try:
        if isinstance(tool_input, str):
            input_data = json.loads(tool_input)
        else:
            input_data = tool_input
            
        scenario_ids = input_data.get("scenario_ids", [])
        custom_name = input_data.get("name", "Custom Combined Situation")
        
        if not scenario_ids:
            return {"error": "No scenario IDs provided"}
        
    except Exception as e:
        return {"error": f"Invalid input format: {str(e)}"}
    
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return {"error": "Could not load operational situations database"}
    
    # Find the scenarios
    selected_scenarios = []
    for category_name, scenarios in situations_data["basic_scenarios"].items():
        for scenario in scenarios:
            if scenario["id"] in scenario_ids:
                selected_scenarios.append(scenario)
    
    if not selected_scenarios:
        return {"error": "No valid scenarios found with provided IDs"}
    
    # Calculate combined exposure
    combined_exposure, rationale = calculate_combined_exposure(scenario_ids, situations_data)
    
    # Build result
    result = {
        "success": True,
        "custom_situation": {
            "name": custom_name,
            "component_scenarios": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "exposure": s["exposure"]
                } for s in selected_scenarios
            ],
            "combined_exposure": combined_exposure,
            "rationale": rationale
        }
    }
    
    # Store in working memory
    if "custom_operational_situations" not in cat.working_memory:
        cat.working_memory["custom_operational_situations"] = []
    
    cat.working_memory["custom_operational_situations"].append(result["custom_situation"])
    
    log.info(f"✅ Custom operational situation created: {custom_name}")
    
    return result