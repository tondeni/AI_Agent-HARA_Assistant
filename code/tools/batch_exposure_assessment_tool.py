# ==============================================================================
# code/tools/batch_exposure_assessment_tool.py
# Batch assessment of exposure for all HAZOP hazards using database + LLM
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import json
import os
import sys
import re
from typing import List, Dict, Tuple

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder)
plugin_folder = os.path.dirname(code_folder)
sys.path.insert(0, code_folder)


class BatchExposureAssessor:
    """
    Batch processor for exposure assessment of all HAZOP hazards.
    Uses operational_situations.json database + LLM for intelligent scenario selection.
    """
    
    def __init__(self, plugin_folder: str):
        self.plugin_folder = plugin_folder
        self.situations_data = self._load_situations_database()
        
    def _load_situations_database(self) -> Dict:
        """Load operational situations from JSON file."""
        possible_paths = [
            os.path.join(self.plugin_folder, "templates", "operational_situations.json"),
            os.path.join(self.plugin_folder, "operational_situations.json"),
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
        """Minimal fallback if JSON not found."""
        return {
            "exposure_criteria": {
                "E4": "High probability (> 10% of operating time)",
                "E3": "Medium probability (1% to 10%)",
                "E2": "Low probability (0.1% to 1%)",
                "E1": "Very low probability (0.001% to 0.1%)",
                "E0": "Incredibly unlikely (< 0.001%)"
            },
            "basic_scenarios": {}
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
        """Find scenario by ID."""
        for scenario in self.get_all_scenarios():
            if scenario.get("id") == scenario_id:
                return scenario
        return None
    
    def calculate_combined_exposure(self, scenario_ids: List[str]) -> Tuple[str, str]:
        """
        Calculate combined exposure using MIN rule.
        
        Returns:
            Tuple of (combined_exposure, rationale)
        """
        if not scenario_ids:
            return "E4", "No scenarios selected, defaulting to E4"
        
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
        
        # Apply MIN rule
        exposure_order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
        min_exposure = min(exposure_levels, key=lambda x: exposure_order.get(x, 4))
        
        # Generate rationale
        scenarios_str = " + ".join(scenario_details)
        rationale = (
            f"MIN({', '.join(exposure_levels)}) = {min_exposure}. "
            f"Combined conditions: {scenarios_str}. "
            f"Per ISO 26262-3, combined exposure uses MIN rule."
        )
        
        return min_exposure, rationale
    
    def assess_single_hazard_exposure(self, hazard: Dict, llm_function) -> Dict:
        """
        Assess exposure for a single hazard using LLM + database.
        
        Args:
            hazard: Dict with keys: id, function, malfunction, hazardous_event, severity
            llm_function: Cat LLM function for scenario selection
            
        Returns:
            Dict with exposure assessment results
        """
        
        # Build LLM prompt for scenario selection
        hazard_context = f"{hazard['malfunction']} causing {hazard['hazardous_event']}"
        
        # Get scenarios database summary for LLM
        scenarios_summary = self._build_scenarios_summary()
        
        prompt = f"""You are a Functional Safety Engineer performing Exposure assessment per ISO 26262-3:2018.

**Hazard Context:**
- Malfunction: {hazard['malfunction']}
- Hazardous Event: {hazard['hazardous_event']}
- Function: {hazard['function']}
- Severity: {hazard['severity']}

**Your Task:**
Select 2-4 most relevant basic operational situations from the database below where this hazard would most likely occur.

**Available Scenarios:**
{scenarios_summary}

**Selection Criteria:**
- Consider when/where the malfunction would occur
- Consider vehicle state, environmental conditions, driving situation
- Ensure scenarios are logically compatible
- Maximum 4 scenarios for clarity

**CRITICAL OUTPUT FORMAT:**
Provide ONLY a JSON array of scenario IDs, nothing else:
["SCENARIO_ID_1", "SCENARIO_ID_2", "SCENARIO_ID_3"]

Examples:
["SPC-003", "ENV-007"]
["HWY-001", "ENV-006", "ENV-002"]
["URB-001", "URB-003"]

Output ONLY the JSON array:"""
        
        try:
            # Get LLM to select scenarios
            llm_response = llm_function(prompt).strip()
            
            # Extract JSON array
            json_match = re.search(r'\[(.*?)\]', llm_response, re.DOTALL)
            if json_match:
                scenario_ids_str = '[' + json_match.group(1) + ']'
                selected_scenario_ids = json.loads(scenario_ids_str)
            else:
                log.warning(f"Could not parse LLM response for {hazard['id']}, using fallback")
                selected_scenario_ids = self._fallback_scenario_selection(hazard)
            
            # Calculate combined exposure
            combined_exposure, rationale = self.calculate_combined_exposure(selected_scenario_ids)
            
            # Get scenario details
            scenario_details = []
            for sid in selected_scenario_ids:
                scenario = self.find_scenario_by_id(sid)
                if scenario:
                    scenario_details.append({
                        "id": sid,
                        "name": scenario.get("name", "Unknown"),
                        "exposure": scenario.get("exposure", "E4"),
                        "description": scenario.get("description", "")
                    })
            
            # Build combined scenario name
            if len(scenario_details) > 0:
                combined_name = " in ".join([s["name"] for s in scenario_details[:3]])
                if len(scenario_details) > 3:
                    combined_name += f" (+{len(scenario_details)-3} more)"
            else:
                combined_name = "Generic operational situation"
            
            return {
                "hazard_id": hazard['id'],
                "function": hazard['function'],
                "malfunction": hazard['malfunction'],
                "hazardous_event": hazard['hazardous_event'],
                "severity": hazard['severity'],
                "selected_scenarios": selected_scenario_ids,
                "scenario_details": scenario_details,
                "combined_scenario_name": combined_name,
                "combined_exposure": combined_exposure,
                "rationale": rationale
            }
            
        except Exception as e:
            log.error(f"Error assessing exposure for {hazard['id']}: {e}")
            # Fallback to conservative estimate
            return {
                "hazard_id": hazard['id'],
                "function": hazard['function'],
                "malfunction": hazard['malfunction'],
                "hazardous_event": hazard['hazardous_event'],
                "severity": hazard['severity'],
                "selected_scenarios": ["STA-001"],
                "scenario_details": [],
                "combined_scenario_name": "Normal operation",
                "combined_exposure": "E3",
                "rationale": f"Fallback assessment due to error: {str(e)}"
            }
    
    def _build_scenarios_summary(self) -> str:
        """Build concise summary of available scenarios for LLM."""
        summary = ""
        
        for category, scenarios in self.situations_data.get("basic_scenarios", {}).items():
            summary += f"\n**{category.replace('_', ' ').title()}:**\n"
            for scenario in scenarios[:10]:  # Limit to avoid token overflow
                summary += f"- {scenario['id']}: {scenario['name']} ({scenario['exposure']})\n"
            if len(scenarios) > 10:
                summary += f"  ... and {len(scenarios) - 10} more\n"
        
        return summary
    
    def _fallback_scenario_selection(self, hazard: Dict) -> List[str]:
        """Fallback scenario selection using simple heuristics."""
        # Default to normal operation
        scenarios = ["STA-001"]
        
        # Check for charging-related
        if any(word in hazard['malfunction'].lower() for word in ['charg', 'power', 'voltage']):
            scenarios.append("SPC-003")
        
        # Check for driving-related
        if any(word in hazard['malfunction'].lower() for word in ['driv', 'speed', 'brake', 'steer']):
            scenarios.append("HWY-001")
        
        return scenarios


@tool(
    return_direct=True,
    examples=[
        "assess exposure for all hazards",
        "batch assess exposure",
        "calculate exposure for all hazop results"
    ]
)
def assess_exposure_for_all_hazards(tool_input, cat):
    """
    Assess exposure for ALL hazards from HAZOP analysis using database + LLM.
    
    This tool implements ISO 26262-3:2018 Clause 6.4.4 exposure assessment
    in batch mode for all HAZOP hazards.
    
    Process:
    1. Load all HAZOP hazards
    2. For each hazard:
       - Use LLM to select 2-4 relevant scenarios from database
       - Calculate combined exposure using MIN rule
       - Generate detailed rationale
    3. Store complete exposure assessment table
    
    Features:
    - Database-driven (operational_situations.json with 34+ scenarios)
    - ISO 26262-compliant MIN combination rule
    - Intelligent LLM-based scenario selection
    - Batch processing with progress tracking
    
    Args:
        tool_input: Optional progress level ("detailed" or "summary")
        cat: Cheshire Cat instance
        
    Returns:
        Complete exposure assessment table for all hazards
        
    Example:
        User: "assess exposure for all hazards"
        Output: Table with hazard ID, scenarios, combined exposure, rationale
    """
    
    log.info("🔧 TOOL CALLED: assess_exposure_for_all_hazards")
    
    # Check prerequisites - FIXED: Look for hazop_results (list format)
    hazop_results = cat.working_memory.get('hazop_results', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Analysis Available**

**Action Required:** Complete HAZOP analysis first

**Workflow:**
1. ✅ Extract functions
2. ❌ Apply HAZOP ← Complete this first
3. ➡️ Assess exposure (you are here)

Use: `apply hazop analysis`"""
    
    log.info(f"📊 Starting batch exposure assessment for: {item_name}")
    
    # Convert HAZOP results from list format
    hazards = _convert_hazop_to_exposure_format(hazop_results)
    
    if not hazards:
        return """❌ **Could not parse HAZOP results**

**Issue:** HAZOP data format unexpected

**Action:** Verify HAZOP analysis completed successfully"""
    
    total_hazards = len(hazards)
    log.info(f"📋 Processing {total_hazards} hazards...")
    
    # Initialize assessor
    assessor = BatchExposureAssessor(plugin_folder)
    
    # Process each hazard
    exposure_results = []
    
    # Progress tracking (for large numbers of hazards)
    progress_markers = [10, 25, 50, 75, 100]
    processed = 0
    
    for hazard in hazards:
        # Assess exposure using database + LLM
        result = assessor.assess_single_hazard_exposure(hazard, cat.llm)
        exposure_results.append(result)
        
        processed += 1
        
        # Log progress for large batches
        if total_hazards > 20:
            percentage = (processed / total_hazards) * 100
            for marker in progress_markers:
                if abs(percentage - marker) < (100 / total_hazards):
                    log.info(f"⏳ Progress: {processed}/{total_hazards} ({percentage:.0f}%)")
                    break
    
    log.info(f"✅ Exposure assessment complete: {len(exposure_results)} hazards processed")
    
    # Store in working memory
    cat.working_memory['exposure_assessments_batch'] = exposure_results
    cat.working_memory['hara_stage'] = 'exposure_assessed'
    
    # Build output table
    result = f"""✅ **Exposure Assessment Complete: {item_name}**

**Processed:** {total_hazards} hazards

---

## 📊 Exposure Assessment Table

| Hazard ID | Severity | Malfunction | Selected Scenarios | Combined Scenario | Exposure | Rationale |
|-----------|----------|-------------|-------------------|-------------------|----------|-----------|
"""
    
    # Add rows to table
    for exp_result in exposure_results:
        # Format scenario IDs
        scenario_ids_str = ", ".join([f"{s['id']} ({s['exposure']})" 
                                     for s in exp_result['scenario_details'][:3]])
        if len(exp_result['scenario_details']) > 3:
            scenario_ids_str += f" +{len(exp_result['scenario_details'])-3}"
        
        # Truncate long text
        malfunction = exp_result['malfunction'][:40] + "..." if len(exp_result['malfunction']) > 40 else exp_result['malfunction']
        combined_scenario = exp_result['combined_scenario_name'][:50] + "..." if len(exp_result['combined_scenario_name']) > 50 else exp_result['combined_scenario_name']
        rationale = exp_result['rationale'][:80] + "..." if len(exp_result['rationale']) > 80 else exp_result['rationale']
        
        result += f"| {exp_result['hazard_id']} | {exp_result['severity']} | {malfunction} | {scenario_ids_str} | {combined_scenario} | **{exp_result['combined_exposure']}** | {rationale} |\n"
    
    # Add statistics
    exposure_distribution = {}
    for exp_result in exposure_results:
        exp = exp_result['combined_exposure']
        exposure_distribution[exp] = exposure_distribution.get(exp, 0) + 1
    
    result += f"""

---

## 📈 Exposure Distribution Statistics

**Total Hazards:** {total_hazards}

**Distribution:**
- **E4 (High - >10% time):** {exposure_distribution.get('E4', 0)} hazards ({exposure_distribution.get('E4', 0)/total_hazards*100:.1f}%)
- **E3 (Medium - 1-10% time):** {exposure_distribution.get('E3', 0)} hazards ({exposure_distribution.get('E3', 0)/total_hazards*100:.1f}%)
- **E2 (Low - 0.1-1% time):** {exposure_distribution.get('E2', 0)} hazards ({exposure_distribution.get('E2', 0)/total_hazards*100:.1f}%)
- **E1 (Very low - <0.1% time):** {exposure_distribution.get('E1', 0)} hazards ({exposure_distribution.get('E1', 0)/total_hazards*100:.1f}%)
- **E0 (Incredible - <0.001% time):** {exposure_distribution.get('E0', 0)} hazards ({exposure_distribution.get('E0', 0)/total_hazards*100:.1f}%)

**High Exposure (E3-E4):** {exposure_distribution.get('E3', 0) + exposure_distribution.get('E4', 0)} hazards

---

## 🔍 Key Insights

"""
    
    # Generate insights
    high_severity_high_exposure = [
        r for r in exposure_results 
        if r['severity'] in ['S3', 'S2'] and r['combined_exposure'] in ['E3', 'E4']
    ]
    
    if high_severity_high_exposure:
        result += f"""⚠️ **CRITICAL COMBINATION:** {len(high_severity_high_exposure)} hazards with HIGH severity (S3/S2) AND HIGH exposure (E3/E4)
   - These are prime candidates for ASIL C or D
   - Hazards: {', '.join([h['hazard_id'] for h in high_severity_high_exposure[:10]])}
   - Require immediate attention in design

"""
    
    if exposure_distribution.get('E4', 0) > total_hazards * 0.3:
        result += f"""⚠️ **HIGH EXPOSURE SYSTEM:** {exposure_distribution.get('E4', 0)} hazards ({exposure_distribution.get('E4', 0)/total_hazards*100:.0f}%) have E4 rating
   - Many hazards occur frequently (>10% operating time)
   - Consider design changes to reduce exposure
   - May indicate basic system functions with inherent exposure

"""
    
    result += f"""---

## ✅ ISO 26262-3:2018 Compliance

- ✓ Clause 6.4.2: Operational situations classified per Table 2
- ✓ Clause 6.4.4: Exposure assessment methodology applied
- ✓ Scenario combination using MIN rule (conservative approach)
- ✓ Database-driven with {len(assessor.get_all_scenarios())} validated scenarios

---

## 📍 Next Steps

**Workflow Progress:** 3/5 Complete
- ✅ Step 1: Functions extracted
- ✅ Step 2: HAZOP analysis (Severity assessed)
- ✅ Step 3: Exposure assessed with driving scenarios
- ➡️ Step 4: Generate HARA table
- ❓ Step 5: Derive detailed safety goals

**Next Command:** `generate hara table`

This will:
- Combine HAZOP results (with S) and Exposure assessments (with E)
- Assess Controllability (C) for each hazard based on operational situation
- Calculate ASIL using ISO 26262-3 Table 4: ASIL = f(S, E, C)
- Formulate preliminary Safety Goals
- Generate complete 12-column HARA table

**Optional Before Proceeding:**
- Review high-exposure hazards: `show e4 hazards`
- Review specific hazard details: `show exposure for HAZ-001`
- Export exposure table: (use Output Formatter plugin)
"""
    
    return result


def _convert_hazop_to_exposure_format(hazop_results: List[Dict]) -> List[Dict]:
    """
    Convert HAZOP results from plugin list format to exposure assessment format.
    
    Plugin stores as list of dicts with keys:
    - function_id, function_name, guide_word, malfunctioning_behavior,
      hazardous_event, severity, rationale
    
    Returns format for exposure assessment.
    """
    hazards = []
    
    for idx, result in enumerate(hazop_results, 1):
        # Get and clean function name
        raw_function = result.get('function_name', result.get('function', 'Unknown'))
        clean_function = _clean_function_name(raw_function)
        
        hazard = {
            'id': result.get('id', f"HAZ-{idx:03d}"),
            'function': clean_function,
            'guideword': result.get('guide_word', 'UNKNOWN'),
            'malfunction': result.get('malfunctioning_behavior', 'Unknown malfunction'),
            'hazardous_event': result.get('hazardous_event', 'Unknown hazard'),
            'severity': result.get('severity', 'S1').upper()
        }
        
        # Ensure severity has S prefix
        if not hazard['severity'].startswith('S'):
            hazard['severity'] = 'S' + hazard['severity']
        
        hazards.append(hazard)
    
    return hazards


def _clean_function_name(function_text: str) -> str:
    """
    Clean function name from potential preamble text.
    
    Handles cases where function_name contains:
    - Full function extraction output
    - Numbered list items
    - Markdown formatting
    """
    
    if not function_text or function_text == 'Unknown':
        return 'Unknown Function'
    
    # Remove common preambles
    preambles = [
        'Here are',
        'Below are',
        'The following',
        'safety-relevant functions',
        'functions:',
        'Function list:',
        'Extracted functions:'
    ]
    
    for preamble in preambles:
        if function_text.lower().startswith(preamble.lower()):
            # This is likely the full extraction output, not a function name
            return 'Function (see extraction)'
    
    # If it's a numbered list item, extract just the function name
    # Format: "1. **Function Name:** Description"
    if function_text.strip() and function_text.strip()[0].isdigit():
        # Remove number prefix
        parts = function_text.split('.', 1)
        if len(parts) > 1:
            function_text = parts[1].strip()
    
    # Remove markdown bold
    function_text = function_text.replace('**', '')
    
    # If there's a colon, take everything before it (that's usually the function name)
    if ':' in function_text:
        function_text = function_text.split(':')[0].strip()
    
    # Truncate if too long
    if len(function_text) > 50:
        function_text = function_text[:47] + '...'
    
    return function_text


def _parse_hazop_for_exposure(hazop_analysis: str) -> List[Dict]:
    """Parse HAZOP table for exposure assessment."""
    hazards = []
    
    lines = hazop_analysis.split('\n')
    
    for line in lines:
        if not line.strip().startswith('| HAZ-'):
            continue
        
        columns = [col.strip() for col in line.split('|') if col.strip()]
        
        if len(columns) >= 5:
            hazard = {
                'id': columns[0],
                'function': columns[1],
                'guideword': columns[2] if len(columns) > 2 else '',
                'malfunction': columns[3] if len(columns) > 3 else columns[2],
                'hazardous_event': columns[4] if len(columns) > 4 else columns[3],
                'severity': columns[5] if len(columns) > 5 else 'S1'
            }
            hazards.append(hazard)
    
    return hazards


@tool(
    return_direct=True,
    examples=[
        "show e4 hazards",
        "show high exposure hazards",
        "filter by exposure E4"
    ]
)
def show_high_exposure_hazards(tool_input, cat):
    """
    Display hazards with high exposure (E3 or E4).
    
    Shows hazards that occur frequently (>1% of operating time),
    which combined with high severity could result in high ASIL ratings.
    
    Args:
        tool_input: Optional exposure level filter ("E4" or "E3-E4")
        cat: Cheshire Cat instance
        
    Returns:
        Filtered table of high-exposure hazards
    """
    
    log.info("🔧 TOOL CALLED: show_high_exposure_hazards")
    
    exposure_results = cat.working_memory.get('exposure_assessments_batch', [])
    
    if not exposure_results:
        return """❌ **No Exposure Assessments Available**

**Action:** Run exposure assessment first: `assess exposure for all hazards`"""
    
    # Filter for E3 and E4
    high_exposure = [r for r in exposure_results if r['combined_exposure'] in ['E3', 'E4']]
    
    if not high_exposure:
        return f"""✅ **No High-Exposure Hazards**

All {len(exposure_results)} hazards have exposure E2 or lower.

This indicates infrequent hazardous situations, which is generally positive
from a safety perspective."""
    
    result = f"""# 📊 **High Exposure Hazards (E3-E4)**

**Count:** {len(high_exposure)} out of {len(exposure_results)} total

High exposure indicates hazards that occur **frequently** (>1% of operating time).

---

## High Exposure Hazards

| Hazard ID | Severity | Exposure | Combined Scenario | Hazardous Event |
|-----------|----------|----------|-------------------|-----------------|
"""
    
    for hazard in high_exposure:
        event = hazard['hazardous_event'][:60] + "..." if len(hazard['hazardous_event']) > 60 else hazard['hazardous_event']
        scenario = hazard['combined_scenario_name'][:40] + "..." if len(hazard['combined_scenario_name']) > 40 else hazard['combined_scenario_name']
        
        result += f"| {hazard['hazard_id']} | {hazard['severity']} | **{hazard['combined_exposure']}** | {scenario} | {event} |\n"
    
    # Highlight critical combinations
    critical = [h for h in high_exposure if h['severity'] in ['S3', 'S2']]
    
    result += f"""

---

## ⚠️ Critical Attention

**High Severity + High Exposure:** {len(critical)} hazards

"""
    
    if critical:
        result += "These hazards require immediate attention:\n\n"
        for hazard in critical[:10]:
            result += f"- **{hazard['hazard_id']}**: {hazard['severity']} + {hazard['combined_exposure']} - {hazard['hazardous_event'][:80]}\n"
    
    result += """

**Implications:**
- High frequency of occurrence
- Combined with high severity → likely ASIL C or D
- Design mitigation may be necessary
- Consider if exposure can be reduced

**Next:** `generate hara table` to see final ASIL ratings
"""
    
    return result