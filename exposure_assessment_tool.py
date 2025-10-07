# exposure_assessment_tool.py - Refined
# Tool for batch assessment of exposure for all HAZOP hazards

import json
import os
from cat.mad_hatter.decorators import tool
from cat.log import log
import re


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_operational_situations(plugin_folder):
    """Load operational situations database from JSON file."""
    template_path = os.path.join(plugin_folder, "templates", "operational_situations.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"Operational situations file not found: {template_path}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"Invalid operational situations JSON: {e}")
        return None
    except Exception as e:
        log.error(f"Error loading operational situations: {e}")
        return None


def get_exposure_guidance():
    """Return detailed ISO 26262-3 exposure guidance."""
    return """# ISO 26262-3:2018 Exposure Classification

## Table 2: Probability of Exposure Classes

**E4: High probability** - >10% operating time
- Examples: Highway cruising, city traffic, lane changes
- Almost every drive

**E3: Medium probability** - 1-10% operating time
- Examples: Wet road, heavy traffic, overtaking, parking
- Once per month or more

**E2: Low probability** - 0.1-1% operating time
- Examples: Snow/ice, highway exit, refueling, evasive maneuver
- Few times per year

**E1: Very low probability** - 0.001-0.1% operating time
- Examples: Mountain pass with engine off, driving in reverse
- Less than once per year

**E0: Incredible** - <0.001% operating time
- Examples: Force majeure (earthquake, plane landing on highway)
- Requires exclusion rationale

## Assessment Method

**Duration-based:** For hazards present throughout a driving condition
- Example: Driving on ice = E2

**Frequency-based:** For hazards triggered by events
- Example: Gear shifting, starting engine

## Combination Rule (Critical)

When combining scenarios: **Use MINIMUM exposure**
- Combined events occur LESS frequently than individual events
- Example: Highway (E4) + Rain (E2) = E2
- Rationale: Highway in rain less frequent than either alone
"""


def build_exposure_assessment_prompt(hazop_analysis, situations_data, item_name):
    """Build structured prompt for exposure assessment."""
    
    # Truncate HAZOP if too long
    hazop_truncated = hazop_analysis[:8000]
    if len(hazop_analysis) > 8000:
        hazop_truncated += "\n\n[... HAZOP table truncated ...]"
    
    # Truncate situations database
    situations_json = json.dumps(situations_data.get("basic_scenarios", {}), indent=2)
    situations_truncated = situations_json[:8000]
    if len(situations_json) > 8000:
        situations_truncated += "\n\n[... database truncated ...]"
    
    prompt = f"""You are a Functional Safety Engineer performing Exposure assessment per ISO 26262-3:2018 Clause 6.4.4.

**System:** {item_name}

# HAZOP Analysis Results

{hazop_truncated}

# Available Operational Situations Database

{situations_truncated}

# ISO 26262 Guidance

{get_exposure_guidance()}

# Your Task

For EACH hazard in the HAZOP table, perform exposure assessment:

1. **Analyze hazard context** (malfunction + hazardous event)
2. **Select 2-4 relevant scenarios** from database
3. **Combine into specific scenario** with descriptive name
4. **Calculate exposure** using MIN rule: E_combined = MIN(E1, E2, ...)
5. **Provide clear rationale** for selection and calculation

# Critical Rules

- **MIN Rule**: Combined exposure = MINIMUM of selected scenarios
- **Scenario Selection**: Must be directly relevant to when/where hazard occurs
- **Compatibility**: Selected scenarios must be logically compatible
- **Relevance**: Consider malfunction and hazardous event context

# Output Format

Generate ONLY a raw markdown table. NO code blocks, NO fences.

## Table Columns

| Hazard ID | Malfunction | Hazardous Event | Selected Scenarios | Combined Scenario | Exposure | Rationale |

## Column Specifications

- **Hazard ID**: Copy from HAZOP (HAZ-001, etc.)
- **Malfunction**: Brief description (max 10 words)
- **Hazardous Event**: From HAZOP (max 10 words)
- **Selected Scenarios**: List IDs with exposures
  Format: "URB-001 (E4), ENV-002 (E2), ENV-006 (E3)"
- **Combined Scenario**: Descriptive name
  Example: "Urban traffic in heavy rain at night"
- **Exposure**: E0-E4 (MINIMUM of selected scenarios)
- **Rationale**: Brief explanation (1-2 sentences)
  Must include MIN calculation and frequency justification

# Example Format

| HAZ-001 | No voltage monitoring | Battery overcharge thermal runaway | SPC-003 (E2), ENV-007 (E2) | Fast charging in extreme heat | E2 | MIN(E2, E2) = E2. Fast charging weekly, extreme heat seasonal, combination less frequent |

**Generate the exposure assessment table now:**
"""
    
    return prompt


# ============================================================================
# TOOL
# ============================================================================

@tool(
    return_direct=True,
    examples=[
        "assess exposure for all hazards",
        "evaluate exposure",
        "perform step 3"
    ]
)
def assess_exposure_for_all_hazards(tool_input, cat):
    """
    Assess Exposure for all hazards.
    
    This tool processes each hazard from the HAZOP table and:
    1. Selects 2-4 relevant basic operational situations
    2. Combines them into a realistic driving scenario
    3. Calculates combined Exposure using MIN rule
    4. Outputs a table with Hazard ID, Driving Scenario, and Exposure Class
    
    Input: None (uses HAZOP analysis from working memory)
    
    Use this tool when user asks:
    - "assess exposure for all hazards"
    - "select driving scenarios for hazards"
    - "determine exposure for all hazards"
    - "step 3" or "perform step 3"
    """
    print("TOOL CALLED: assess_exposure_for_all_hazards")
    
    # Check for HAZOP analysis
    hazop_analysis = cat.working_memory.get("hazop_analysis", "")
    if not hazop_analysis:
        return """No HAZOP analysis found in working memory.

**Please complete Step 2 first:**
`apply hazop analysis`

**Then run this tool:**
`assess exposure for all hazards`
"""
    
    item_name = cat.working_memory.get("hara_item_name", "the system")
    
    # Load operational situations database
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return "Error: Could not load operational situations database. Check that operational_situations.json exists in templates/ folder."
    
    log.info(f"Assessing exposure for all HAZOP hazards for {item_name}")
    
    # Parse HAZOP table to extract hazards
    hazop_lines = [line.strip() for line in hazop_analysis.split('\n') if line.strip().startswith('| HAZ-')]
    
    if not hazop_lines:
        return "No hazards found in HAZOP analysis. Please verify the HAZOP table format."
    
    log.info(f"Found {len(hazop_lines)} hazards to assess")
    
    # Build comprehensive prompt
    prompt = f"""You are a Functional Safety Engineer performing Exposure assessment for HARA per ISO 26262-3:2018 Clause 6.4.4.

**System:** {item_name}

**HAZOP Analysis Results (with Severity already assessed):**
{hazop_analysis}

**Available Basic Operational Situations Database:**
{json.dumps(situations_data["basic_scenarios"], indent=2)[:8000]}

**CRITICAL RULES:**

1. **Exposure Combination Rule (ISO 26262):**
   - Combined Exposure = MINIMUM exposure level among selected basic scenarios
   - Example: Highway (E4) + Heavy Rain (E2) + Night (E3) → Combined = E2
   - Rationale: Combined scenarios represent intersection of conditions (less frequent than individual conditions)

2. **Scenario Selection Criteria:**
   - Select 2-4 basic operational situations that are DIRECTLY relevant to when/where the hazard occurs
   - Scenarios must be logically compatible (can happen simultaneously)
   - Consider the malfunction and hazardous event context

**Your Task:**

For EACH hazard in the HAZOP table, perform exposure assessment by:

1. Analyzing the hazard context (malfunction + hazardous event)
2. Selecting 2-4 relevant basic operational situations from the database
3. Combining them into a specific driving scenario
4 * IMPORTANT*: E1 is the minimum value, E4 is the maximum ones 
4. *CRITICAL ** Calculating combined Exposure using MIN rule. (eg. if driving scenario has (E4, E3), the exposure is E3 (the minimum one))
5. Providing rationale for the selection and exposure level

**CRITICAL OUTPUT FORMAT:**

Generate ONLY a markdown table. DO NOT wrap it in code blocks or markdown fences.
DO NOT include ```markdown or ``` markers.
Output the raw table directly.

**Table Columns:**
| Hazard ID | Malfunction | Hazardous Event | Selected Basic Scenarios | Combined Driving Scenario | Exposure (E) | Rationale |

**Column Specifications:**

- **Hazard ID**: Copy from HAZOP (HAZ-001, HAZ-002, etc.)
- **Malfunction**: Brief malfunction description from HAZOP (max 10 words)
- **Hazardous Event**: Hazardous event from HAZOP (max 10 words)
- **Selected Basic Scenarios**: List scenario IDs with individual exposures
  Format: "URB-001 (E4), ENV-002 (E2), ENV-006 (E3)"
- **Combined Driving Scenario**: Descriptive name of combined scenario
  Example: "Urban traffic in heavy rain at night"
- **Exposure (E)**: Combined exposure level (E0-E4)
  Must be MINIMUM of selected scenarios
- **Rationale**: Brief explanation of scenario selection and exposure calculation
  Example: "MIN(E4, E2, E3) = E2. Combination of urban driving with adverse weather reduces frequency."

**Example Format (DO NOT include this in your output, just follow the format):**

| HAZ-001 | No cell voltage monitoring | Battery overcharge and thermal runaway | SPC-003 (E2), ENV-007 (E2) | Fast charging in extreme heat | E2 | MIN(E2, E2) = E2. Fast charging in hot conditions occurs occasionally |

**Important:**
- Be SPECIFIC with driving scenarios (not generic)
- Ensure exposure calculation is correct: Combined E = MIN(individual E values)
- Keep each cell concise (max 10-15 words except rationale)
- Output ONLY the table, no explanations before or after
- NO code blocks, NO markdown fences, just the raw table

**Begin table output now:**
"""
    
    try:
        exposure_table = cat.llm(prompt).strip()
            # Clean up any markdown code block wrappers if LLM adds them
        if exposure_table.startswith('```'):
            # Remove code block markers
            lines = exposure_table.split('\n')
            # Find first line that starts with |
            start_idx = next((i for i, line in enumerate(lines) if line.strip().startswith('|')), 0)
            # Find last line that starts with |
            end_idx = next((i for i in range(len(lines)-1, -1, -1) if lines[i].strip().startswith('|')), len(lines))
            exposure_table = '\n'.join(lines[start_idx:end_idx+1])


        # Store in working memory for Step 4
        cat.working_memory["exposure_assessments"] = exposure_table
        cat.working_memory["hara_stage"] = "exposure_assessed"

        
        # Count assessed hazards
        exposure_lines = [line for line in exposure_table.split('\n') if line.strip().startswith('| HAZ-')]
        
        log.info(f"Exposure assessment completed for {len(exposure_lines)} hazards")
        
        result = f"""**Step 3 Complete: Exposure Assessment for All Hazards**

**System:** {item_name}
**Hazards Assessed:** {len(exposure_lines)}

{exposure_table}

---

**Summary:**
- Total hazards from HAZOP: {len(hazop_lines)}
- Hazards with exposure assessed: {len(exposure_lines)}
- Exposure levels assigned: {', '.join(set([re.search(r'E[0-4]', line).group() for line in exposure_lines if re.search(r'E[0-4]', line)]))}

**Exposure Combination Method:**
- Combined Exposure = MIN(individual exposures) per ISO 26262 guidance
- Reflects intersection of operational conditions

**ISO 26262-3:2018 Compliance:**
- Clause 6.4.2: Situation analysis completed
- Clause 6.4.4: Exposure classification performed

## Workflow Progress: 3/5 Steps Complete

**Completed:**
- ✅ Step 1: Functions extracted
- ✅ Step 2: HAZOP analysis performed (Severity assessed)
- ✅ Step 3: Exposure for all hazard assessed

**Next Steps:**

➡️ Step 4: `Generate HARA table`
- Combines hazard data (Function, Malfunction, Hazardous Event, S) from HAZOP.
- Integrates Operational Situations and Exposure (E) assessments.
- Assesses Controllability (C) for each hazard within its scenario context.
- Calculates final ASIL using S, E, and C.
- Outputs complete HARA table including Safety Goals.

**Remaining Steps:**
5. ❓Derive detailed safety goals

**Verification Checklist:**
- [ ] All hazards have specific driving scenarios (not generic)
- [ ] Exposure calculations follow MIN rule
- [ ] Selected scenarios are logically compatible
- [ ] Scenarios are relevant to each specific hazard
"""
        
        return result
        
    except Exception as e:
        log.error(f"Error in exposure assessment: {e}")
        import traceback
        log.error(traceback.format_exc())
        return f"Error in exposure assessment: {str(e)}"


# @tool(
#     return_direct=True,
#     examples=[
#         "assess exposure for all hazards",
#         "evaluate exposure",
#         "perform step 3"
#     ]
# )
# def assess_all_exposure(tool_input, cat):
#     """Assess Exposure for all HAZOP hazards.
    
#     This tool processes each hazard from the HAZOP table and:
#     1. Selects 2-4 relevant basic operational situations
#     2. Combines them into a realistic driving scenario
#     3. Calculates combined Exposure using MIN rule
#     4. Outputs a table with Hazard ID, Driving Scenario, and Exposure Class
    
#     Input: None (uses HAZOP analysis from working memory)
#     Returns exposure table with scenarios and combined E levels."""
    
#     log.info("🔧 TOOL CALLED: assess_all_exposure")
    
#     # Check prerequisites
#     hazop_analysis = cat.working_memory.get("hazop_analysis", "")
    
#     if not hazop_analysis:
#         return """❌ **No HAZOP Analysis Found**

# **Complete steps in order:**

# **Please complete Step 2 first:**
# `apply hazop analysis`

# **Then run this tool:**
# `assess exposure for all hazards` ← You are here
# """
    
#     item_name = cat.working_memory.get("hara_item_name", "Unknown Item")
    
#     # Load operational situations
#     plugin_folder = os.path.dirname(__file__)
#     situations_data = load_operational_situations(plugin_folder)
    
#     if not situations_data:
#         log.error("Operational situations database unavailable")
#         return """❌ **Operational Situations Database Missing**

# Cannot perform automated exposure assessment.

# **Check:**
# - File exists: `templates/operational_situations.json`
# - Plugin correctly installed
# - File permissions correct

# **Alternative:**
# Manual assessment: `assess hazard: [description]`"""
    
#     log.info(f"📊 Assessing exposure for all hazards: {item_name}")
    
#     # Parse HAZOP to count hazards
#     hazop_lines = [line.strip() for line in hazop_analysis.split('\n') 
#                    if line.strip().startswith('| HAZ-')]
    
#     if not hazop_lines:
#         return """❌ **No Hazards Found in HAZOP**

# Please verify HAZOP table format and regenerate if needed."""
    
#     log.info(f"Found {len(hazop_lines)} hazards to assess")
    
#     # Build assessment prompt
#     try:
#         prompt = build_exposure_assessment_prompt(
#             hazop_analysis, 
#             situations_data, 
#             item_name
#         )
        
#         log.info("🤖 Generating exposure assessments...")
#         exposure_result = cat.llm(prompt).strip()
        
#         # Store results
#         cat.working_memory["exposure_assessments"] = exposure_result
#         cat.working_memory["hara_stage"] = "exposure_assessed"
        
#         log.info(f"✅ Exposure assessment complete")
        
#         return f"""✅ **Exposure Assessment Complete: {item_name}**

# {exposure_result}

# ---
# ## Workflow Progress: 3/5 Steps Complete

# **Completed:**
# - ✅ Step 1: Functions extracted
# - ✅ Step 2: HAZOP analysis performed (Severity assessed)
# - ✅ Step 3: Exposure for all hazard assessed

# **ISO 26262-3:2018 Compliance:**
# - ✅ Clause 6.4.2: Situation analysis completed
# - ✅ Clause 6.4.4: Exposure classification performed

# **Next Steps:**

# ➡️ Step 4: `Generate HARA table`
# - Combines hazard data (Function, Malfunction, Hazardous Event, S) from HAZOP.
# - Integrates Operational Situations and Exposure (E) assessments.
# - Assesses Controllability (C) for each hazard within its scenario context.
# - Calculates final ASIL using S, E, and C.
# - Outputs complete HARA table including Safety Goals.

# **Remaining Steps:**
# 5. ❓Derive detailed safety goals

# **Verification Checklist:**
# - [ ] All hazards have specific driving scenarios (not generic)
# - [ ] Exposure calculations follow MIN rule
# - [ ] Selected scenarios are logically compatible
# - [ ] Scenarios are relevant to each specific hazard
# """
    
#     except Exception as e:
#         log.error(f"Exposure assessment failed: {e}")
#         return f"""❌ **Exposure Assessment Failed**

# Error: {e}

# **Possible causes:**
# - HAZOP table too large for LLM context
# - Invalid database format
# - LLM service unavailable

# **Recommendations:**
# 1. Reduce number of hazards in HAZOP
# 2. Check operational situations database validity
# 3. Try again in a few moments"""


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Maintain old name as alias
# assess_exposure_for_all_hazards = assess_all_exposure