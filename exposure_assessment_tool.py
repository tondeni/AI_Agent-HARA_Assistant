# exposure_assessment_tool.py
# Tool for batch assessment of exposure for all HAZOP hazards

import json
import os
import re
from datetime import datetime
from cat.mad_hatter.decorators import tool
from cat.log import log


def load_operational_situations(plugin_folder):
    """Load operational situations database from JSON file."""
    template_path = os.path.join(plugin_folder, "templates", "operational_situations.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Error loading operational situations: {e}")
        return None


@tool(return_direct=True)
def assess_exposure_for_all_hazards(tool_input, cat):
    """
    Step 3: Select relevant driving scenarios and assess Exposure for ALL hazards from HAZOP analysis.
    
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
4. Calculating combined Exposure using MIN rule
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

**Next Step:**
`generate hara table` - This will add Controllability assessment and calculate ASIL for each hazard

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