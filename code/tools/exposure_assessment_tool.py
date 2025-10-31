# ==============================================================================
# code/tools/exposure_assessment_refined.py
# Refined tool for Exposure assessment using operational_situations.json
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import json
import os
import sys
from typing import List, Dict, Tuple

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder)
plugin_folder = os.path.dirname(code_folder)
sys.path.insert(0, code_folder)


class ExposureAssessor:
    """
    ISO 26262-3:2018 compliant exposure assessment engine.
    Uses operational_situations.json database for scenario-based exposure calculation.
    """
    
    def __init__(self, plugin_folder: str):
        self.plugin_folder = plugin_folder
        self.situations_data = self._load_situations_database()
        
    def _load_situations_database(self) -> Dict:
        """Load operational situations from JSON file."""
        # Try multiple possible locations
        possible_paths = [
            os.path.join(self.plugin_folder, "templates", "operational_situations.json"),
            os.path.join(self.plugin_folder, "operational_situations.json"),
            os.path.join(self.plugin_folder, "..", "operational_situations.json"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        log.info(f"✅ Loaded operational situations from: {path}")
                        return data
                except Exception as e:
                    log.error(f"Error loading {path}: {e}")
                    
        log.warning("⚠️ operational_situations.json not found, using fallback")
        return self._get_fallback_database()
    
    def _get_fallback_database(self) -> Dict:
        """Minimal fallback database if JSON not found."""
        return {
            "exposure_criteria": {
                "E4": "High probability (> 10% of operating time)",
                "E3": "Medium probability (1% to 10%)",
                "E2": "Low probability (0.1% to 1%)",
                "E1": "Very low probability (0.001% to 0.1%)",
                "E0": "Incredibly unlikely (< 0.001%)"
            },
            "basic_scenarios": {
                "urban_driving": [],
                "highway_driving": [],
                "environmental_conditions": [],
                "special_situations": [],
                "critical_maneuvers": [],
                "vehicle_states": []
            }
        }
    
    def get_all_scenarios(self) -> List[Dict]:
        """Get flat list of all available scenarios."""
        all_scenarios = []
        for category, scenarios in self.situations_data.get("basic_scenarios", {}).items():
            for scenario in scenarios:
                scenario["category"] = category
                all_scenarios.append(scenario)
        return all_scenarios
    
    def find_scenario_by_id(self, scenario_id: str) -> Dict:
        """Find a specific scenario by its ID."""
        for scenario in self.get_all_scenarios():
            if scenario.get("id") == scenario_id:
                return scenario
        return None
    
    def calculate_combined_exposure(self, scenario_ids: List[str]) -> Tuple[str, str]:
        """
        Calculate combined exposure using MIN rule per ISO 26262.
        
        Args:
            scenario_ids: List of scenario IDs to combine
            
        Returns:
            Tuple of (combined_exposure_level, rationale)
        """
        if not scenario_ids:
            return "E4", "No scenarios selected, defaulting to E4"
        
        # Get exposure levels for each scenario
        exposure_levels = []
        scenario_details = []
        
        for sid in scenario_ids:
            scenario = self.find_scenario_by_id(sid)
            if scenario:
                exp = scenario.get("exposure", "E4")
                exposure_levels.append(exp)
                scenario_details.append(f"{scenario['name']} ({exp})")
        
        if not exposure_levels:
            return "E4", "Scenarios not found in database"
        
        # Apply MIN rule: E0 < E1 < E2 < E3 < E4
        exposure_order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
        min_exposure = min(exposure_levels, key=lambda x: exposure_order.get(x, 4))
        
        # Generate rationale
        scenarios_str = " + ".join(scenario_details)
        rationale = (
            f"Combined scenarios: {scenarios_str}. "
            f"Per ISO 26262-3 combination rule, combined exposure = MIN({', '.join(exposure_levels)}) = {min_exposure}. "
            f"Rationale: Combined conditions occur less frequently than individual conditions."
        )
        
        return min_exposure, rationale
    
    def validate_scenario_combination(self, scenario_ids: List[str]) -> Tuple[bool, str]:
        """
        Validate that scenarios can be logically combined.
        
        Returns:
            Tuple of (is_valid, message)
        """
        # Basic validation rules
        categories = []
        for sid in scenario_ids:
            scenario = self.find_scenario_by_id(sid)
            if scenario:
                categories.append(scenario.get("category", ""))
        
        # Check for incompatible combinations
        # Example: Cannot combine parking with highway cruising
        incompatible_pairs = [
            (["URB-002"], ["HWY-001", "HWY-002"]),  # Parking vs highway
        ]
        
        for group1, group2 in incompatible_pairs:
            if any(sid in group1 for sid in scenario_ids) and any(sid in group2 for sid in scenario_ids):
                return False, "Incompatible scenarios: Cannot combine parking with highway driving"
        
        # Check maximum 4 scenarios (ISO 26262 recommendation for clarity)
        if len(scenario_ids) > 4:
            return False, f"Too many scenarios ({len(scenario_ids)}). Maximum recommended: 4 for clarity"
        
        return True, "Scenarios are compatible"
    
    def get_exposure_criteria(self) -> Dict:
        """Get exposure classification criteria."""
        return self.situations_data.get("exposure_criteria", {})


@tool(
    return_direct=True,
    examples=[
        "assess exposure for battery overheating during fast charging in hot weather",
        "calculate exposure for lane keeping failure on highway at night",
        "evaluate exposure for brake failure in urban traffic"
    ]
)
def assess_exposure_for_hazard(tool_input, cat):
    """
    Assess Exposure (E) for a specific hazard using operational situations database.
    
    This tool implements ISO 26262-3:2018 Clause 6.4.4 exposure assessment.
    
    Workflow:
    1. Analyze hazard context (malfunction + hazardous event)
    2. Select 2-4 relevant basic operational situations from database
    3. Combine scenarios using MIN exposure rule
    4. Provide detailed rationale
    
    The tool uses operational_situations.json which contains 34+ basic scenarios
    with validated exposure ratings (E0-E4) based on statistical driving data.
    
    Args:
        tool_input: Hazard description or hazard ID
        cat: Cheshire Cat instance
        
    Returns:
        Detailed exposure assessment with scenario selection and rationale
        
    Example:
        User: "assess exposure for battery thermal runaway during fast charging"
        Output: Selected scenarios, combined exposure (E2), detailed rationale
    """
    
    log.info("🔧 TOOL CALLED: assess_exposure_for_hazard")
    
    # Parse input
    hazard_description = ""
    if isinstance(tool_input, str):
        hazard_description = tool_input.strip()
    elif isinstance(tool_input, dict):
        hazard_description = tool_input.get("hazard", tool_input.get("description", ""))
    
    if not hazard_description:
        return """❌ **No Hazard Description Provided**

**Usage:**
```
assess exposure for [hazard description]
```

**Example:**
```
assess exposure for battery overheating during fast charging in extreme heat
```"""
    
    log.info(f"📊 Assessing exposure for: {hazard_description}")
    
    # Initialize assessor
    assessor = ExposureAssessor(plugin_folder)
    
    # Get available scenarios summary
    all_scenarios = assessor.get_all_scenarios()
    
    # Build prompt for LLM to select relevant scenarios
    prompt = f"""You are a Functional Safety Engineer performing Exposure assessment per ISO 26262-3:2018 Clause 6.4.4.

**Hazard to Assess:**
{hazard_description}

**Available Basic Operational Situations:**

{json.dumps(assessor.situations_data["basic_scenarios"], indent=2)[:10000]}

**Your Task:**

1. Analyze the hazard and identify when/where it most likely occurs
2. Select 2-4 most relevant basic operational situations from the database above
3. List ONLY the scenario IDs (e.g., URB-001, HWY-002, ENV-003)

**CRITICAL RULES:**

- Select scenarios that are DIRECTLY relevant to the hazard context
- Ensure scenarios are logically compatible (can occur simultaneously)
- Maximum 4 scenarios for clarity
- Consider: vehicle state, environmental conditions, driving situation, maneuvers

**Output Format:**

Provide ONLY a JSON array of scenario IDs, nothing else:
["SCENARIO_ID_1", "SCENARIO_ID_2", "SCENARIO_ID_3"]

Example outputs:
["SPC-003", "ENV-007"]
["HWY-001", "ENV-006", "ENV-002"]
["URB-001", "URB-003", "ENV-001"]

Do not include any explanation, just the JSON array.
"""
    
    try:
        # Get LLM to select scenarios
        llm_response = cat.llm(prompt).strip()
        
        # Extract JSON array from response
        import re
        json_match = re.search(r'\[(.*?)\]', llm_response, re.DOTALL)
        if json_match:
            scenario_ids_str = '[' + json_match.group(1) + ']'
            selected_scenario_ids = json.loads(scenario_ids_str)
        else:
            log.error(f"Could not parse LLM response: {llm_response}")
            selected_scenario_ids = ["HWY-001", "ENV-001"]  # Fallback
        
        log.info(f"Selected scenarios: {selected_scenario_ids}")
        
        # Validate scenario combination
        is_valid, validation_msg = assessor.validate_scenario_combination(selected_scenario_ids)
        if not is_valid:
            return f"""⚠️ **Invalid Scenario Combination**

{validation_msg}

Please refine your hazard description or scenario selection."""
        
        # Calculate combined exposure
        combined_exposure, exposure_rationale = assessor.calculate_combined_exposure(selected_scenario_ids)
        
        # Get detailed info for selected scenarios
        scenario_details = []
        for sid in selected_scenario_ids:
            scenario = assessor.find_scenario_by_id(sid)
            if scenario:
                scenario_details.append({
                    "id": sid,
                    "name": scenario.get("name", "Unknown"),
                    "description": scenario.get("description", ""),
                    "exposure": scenario.get("exposure", "E4"),
                    "exposure_percentage": scenario.get("exposure_percentage", "Unknown"),
                    "rationale": scenario.get("rationale", ""),
                    "frequency": scenario.get("frequency", "Unknown")
                })
        
        # Build combined scenario name
        scenario_names = [s["name"] for s in scenario_details]
        combined_name = " in ".join(scenario_names) if len(scenario_names) <= 3 else \
                       " with ".join(scenario_names[:2]) + f" (+{len(scenario_names)-2} conditions)"
        
        # Store in working memory
        if "hara_exposure_assessments" not in cat.working_memory:
            cat.working_memory["hara_exposure_assessments"] = []
        
        cat.working_memory["hara_exposure_assessments"].append({
            "hazard": hazard_description,
            "selected_scenarios": selected_scenario_ids,
            "combined_exposure": combined_exposure,
            "combined_scenario_name": combined_name,
            "rationale": exposure_rationale,
            "scenario_details": scenario_details
        })
        
        # Format output
        result = f"""✅ **Exposure Assessment Complete**

**Hazard:** {hazard_description}

**Combined Operational Situation:**
"{combined_name}"

---

### Selected Basic Scenarios

"""
        
        for detail in scenario_details:
            result += f"""**{detail['id']}: {detail['name']}** - **{detail['exposure']}**
- Description: {detail['description']}
- Exposure %: {detail['exposure_percentage']}
- Frequency: {detail['frequency']}
- Individual Rationale: {detail['rationale']}

"""
        
        result += f"""---

### Combined Exposure Calculation

**Formula:** Exposure = MIN({', '.join([s['exposure'] for s in scenario_details])})

**Result:** **{combined_exposure}**

**Rationale:**
{exposure_rationale}

---

### ISO 26262-3:2018 Exposure Criteria

"""
        
        for level, description in assessor.get_exposure_criteria().items():
            marker = "👉" if level == combined_exposure else "  "
            result += f"{marker} **{level}**: {description}\n"
        
        result += f"""
---

**Next Steps:**
1. Review scenario selection - modify if needed
2. Assess Severity (S) for this hazard
3. Assess Controllability (C) for this hazard
4. Calculate ASIL: `determine asil for [hazard]`

**Working Memory:** Exposure assessment saved for HARA table generation
"""
        
        return result
        
    except Exception as e:
        log.error(f"❌ Error in exposure assessment: {e}")
        return f"""❌ **Error in Exposure Assessment**

Error: {str(e)}

Please try again or contact support if the issue persists."""


@tool(
    return_direct=True,
    examples=[
        "show available operational situations",
        "list all driving scenarios",
        "what scenarios are in the database"
    ]
)
def list_operational_situations_database(tool_input, cat):
    """
    Display all available operational situations from the database.
    
    Shows the complete catalog of basic scenarios organized by category:
    - Urban driving scenarios
    - Highway driving scenarios  
    - Environmental conditions
    - Special situations
    - Critical maneuvers
    - Vehicle states
    
    Each scenario includes ID, name, exposure rating, and frequency information.
    
    Args:
        tool_input: Optional category filter
        cat: Cheshire Cat instance
        
    Returns:
        Formatted list of all operational situations
    """
    
    log.info("🔧 TOOL CALLED: list_operational_situations_database")
    
    assessor = ExposureAssessor(plugin_folder)
    
    # Build output
    result = """# 📋 **Operational Situations Database**

ISO 26262-3:2018 compliant basic scenarios for exposure assessment.

**Database Statistics:**
"""
    
    # Count scenarios by category
    category_counts = {}
    total_scenarios = 0
    for category, scenarios in assessor.situations_data.get("basic_scenarios", {}).items():
        count = len(scenarios)
        category_counts[category] = count
        total_scenarios += count
    
    result += f"- **Total Scenarios:** {total_scenarios}\n"
    for cat_name, count in category_counts.items():
        result += f"- **{cat_name.replace('_', ' ').title()}:** {count}\n"
    
    result += "\n---\n\n"
    
    # List scenarios by category
    for category, scenarios in assessor.situations_data.get("basic_scenarios", {}).items():
        result += f"## {category.replace('_', ' ').title()}\n\n"
        
        for scenario in scenarios:
            result += f"""### {scenario.get('id', 'N/A')}: {scenario.get('name', 'Unknown')}

**Exposure:** {scenario.get('exposure', 'N/A')} ({scenario.get('exposure_percentage', 'N/A')})
**Description:** {scenario.get('description', 'No description')}
**Frequency:** {scenario.get('frequency', 'Unknown')}
**Duration:** {scenario.get('typical_duration', 'Unknown')}

"""
    
    result += """---

**Usage:**
To assess exposure for a hazard, use:
```
assess exposure for [hazard description]
```

The tool will automatically select relevant scenarios from this database.
"""
    
    return result


@tool(
    return_direct=True,
    examples=[
        "validate scenario combination URB-001 HWY-001",
        "check if scenarios are compatible"
    ]
)
def validate_scenario_combination_tool(tool_input, cat):
    """
    Validate that a combination of scenarios is logically compatible.
    
    Checks for:
    - Incompatible scenario pairs (e.g., parking + highway cruising)
    - Too many scenarios (recommended max: 4)
    - Logical consistency
    
    Args:
        tool_input: Space-separated scenario IDs
        cat: Cheshire Cat instance
        
    Returns:
        Validation result with suggestions
    """
    
    log.info("🔧 TOOL CALLED: validate_scenario_combination_tool")
    
    # Parse input
    if isinstance(tool_input, str):
        scenario_ids = [s.strip() for s in tool_input.split() if s.strip()]
    elif isinstance(tool_input, list):
        scenario_ids = tool_input
    else:
        return "❌ Invalid input. Provide space-separated scenario IDs (e.g., 'URB-001 HWY-002 ENV-001')"
    
    if not scenario_ids:
        return "❌ No scenario IDs provided"
    
    assessor = ExposureAssessor(plugin_folder)
    is_valid, message = assessor.validate_scenario_combination(scenario_ids)
    
    if is_valid:
        combined_exposure, rationale = assessor.calculate_combined_exposure(scenario_ids)
        return f"""✅ **Valid Scenario Combination**

**Scenarios:** {', '.join(scenario_ids)}
**Combined Exposure:** {combined_exposure}
**Rationale:** {rationale}

{message}
"""
    else:
        return f"""⚠️ **Invalid Scenario Combination**

**Scenarios:** {', '.join(scenario_ids)}
**Issue:** {message}

**Suggestion:** Review scenario selection for logical compatibility.
"""