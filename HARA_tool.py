# tool_hara.py
# Plugin: Functional Safety HARA Generator
# Purpose: Apply HAZOP to Item Definition functions and generate HARA report.

import json
import os
import re
from datetime import datetime
from cat.mad_hatter.decorators import tool
from cat.log import log

# Import the ASIL Calculator from the same plugin folder
from .ASIL_Calculator import ASILCalculator

# --- HELPER FUNCTIONS ---

def load_hazop_guidewords(plugin_folder):
    """Load HAZOP guide words from the template file."""
    template_path = os.path.join(plugin_folder, "templates", "hazop_guidewords.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"HAZOP guide words template not found at {template_path}")
        return {"hazop_guide_words": {}}
    except Exception as e:
        log.error(f"Error loading HAZOP guide words: {e}")
        return {"hazop_guide_words": {}}


def find_item_definition(cat, item_name):
    """
    Find Item Definition content in working memory or plugin folders.
    Search priority:
    1. Working memory (most recent)
    2. HARA plugin folder (item_definitions/)
    3. ItemDefinition_Developer plugin folders
    4. OutputFormatter plugin folders
    """
    
    # 1. Check working memory first (highest priority)
    if "item_definition_content" in cat.working_memory:
        log.info("✅ Found Item Definition in working memory")
        return cat.working_memory["item_definition_content"]
    
    # 2. Search in plugin folders
    plugin_folder = os.path.dirname(__file__)
    
    # Define search paths in priority order
    search_paths = [
        # HARA plugin's own folder
        os.path.join(plugin_folder, "item_definitions"),
        
        # ItemDefinition_Developer plugin folders
        os.path.join(plugin_folder, "..", "AI_Agent-ItemDefinition_Developer", "item_definitions"),
        os.path.join(plugin_folder, "..", "AI_Agent-ItemDefinition_Developer", "generated_documents", "item_definition_work_product"),
        
        # OutputFormatter plugin folders
        os.path.join(plugin_folder, "..", "AI_Agent-OutputFormatter", "generated_documents", "item_definition_work_product"),
        
        # Legacy paths
        os.path.join(plugin_folder, "..", "AI_Agent-ItemDefinition_Developer", "generated_definitions"),
        os.path.join(plugin_folder, "..", "AI_Agent-OutputFormatter", "generated_documents", "01_Item_Definition"),
    ]
    
    log.info(f"🔍 Searching for Item Definition for '{item_name}'...")
    
    for folder_path in search_paths:
        if not os.path.exists(folder_path):
            continue
            
        log.info(f"   Checking folder: {folder_path}")
        
        try:
            for filename in os.listdir(folder_path):
                # Check various file extensions
                if filename.endswith(('.txt', '.md', '.docx')):
                    file_path = os.path.join(folder_path, filename)
                    
                    try:
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check if the item name is mentioned in the file
                        # Use flexible matching (case-insensitive, partial match)
                        if item_name.lower() in content.lower():
                            log.info(f"✅ Found Item Definition in file: {filename}")
                            return content
                            
                    except Exception as read_error:
                        log.warning(f"⚠️ Error reading {filename}: {read_error}")
                        continue
                        
        except Exception as folder_error:
            log.warning(f"⚠️ Error accessing folder {folder_path}: {folder_error}")
            continue
    
    # 3. Not found anywhere
    log.warning(f"❌ No Item Definition found for '{item_name}'")
    return None


def extract_and_calculate_asil(assessment_text):
    """Extract S, E, C from assessment text and calculate ASIL."""
    try:
        # Try multiple patterns to be robust
        s_match = re.search(r'Severity \(S\):\s*S([0-3])', assessment_text, re.IGNORECASE)
        if not s_match:
            s_match = re.search(r'\bS([0-3])\b', assessment_text)
            
        e_match = re.search(r'Exposure \(E\):\s*E([0-3])', assessment_text, re.IGNORECASE)
        if not e_match:
            e_match = re.search(r'\bE([0-3])\b', assessment_text)
            
        c_match = re.search(r'Controllability \(C\):\s*C([0-3])', assessment_text, re.IGNORECASE)
        if not c_match:
            c_match = re.search(r'\bC([0-3])\b', assessment_text)

        if s_match and e_match and c_match:
            s = int(s_match.group(1))
            e = int(e_match.group(1))
            c = int(c_match.group(1))
            
            asil = ASILCalculator.calculate_asil(s, e, c)
            log.info(f"✅ ASIL calculated: {asil} (S{s}, E{e}, C{c})")
            
            return f"ASIL {asil} (S{s}, E{e}, C{c})"
        else:
            log.warning("⚠️ Could not parse S, E, C values from assessment")
            return "ASIL Calculation Failed - S/E/C values not found"
            
    except Exception as e:
        log.error(f"❌ Error calculating ASIL: {e}")
        return f"ASIL Calculation Error: {str(e)}"


# --- TOOLS ---

@tool(return_direct=True)
def extract_functions_from_item_definition(tool_input, cat):
    """
    Extracts functions from the Item Definition.
    The Item Definition can be:
    - In working memory (after generation)
    - Saved in plugin folders (item_definitions/)
    
    Input: The name of the item (e.g., "Battery Management System", "Wiper System").
    
    Use this tool when user asks:
    - "extract functions from [item]"
    - "get functions for [item]"
    - "start HARA for [item]"
    """
    print("✅ TOOL CALLED: extract_functions_from_item_definition")
    
    # Parse input
    item_name = "Unknown System"
    if isinstance(tool_input, str):
        item_name = tool_input.strip()
    elif isinstance(tool_input, dict):
        item_name = tool_input.get("item_name", item_name)

    log.info(f"📋 Extracting functions for: {item_name}")

    # Find Item Definition content
    item_def_content = find_item_definition(cat, item_name)
    
    if not item_def_content:
        return f"""❌ **No Item Definition found for '{item_name}'**

**Please ensure:**
1. The Item Definition has been generated using the ItemDefinition_Developer plugin
2. The item name matches exactly (e.g., "Battery Management System")
3. The Item Definition is saved in one of these locations:
   - Working memory (if just generated)
   - `item_definitions/` folder in HARA plugin
   - Generated documents folder in ItemDefinition_Developer plugin

**Alternative:**
You can manually provide the Item Definition by storing it in working memory:
```
cat.working_memory["item_definition_content"] = "[your item definition text]"
```

Or save it to: `plugins/AI_Agent-HARA_Assistant/item_definitions/[item_name].txt`
"""

    log.info(f"📄 Item Definition found, length: {len(item_def_content)} characters")

    # Build prompt to extract functions
    prompt = f"""You are a Functional Safety Engineer analyzing an Item Definition for HARA development.

**Item Definition for {item_name}:**
{item_def_content[:5000]}

**Task:** Extract and list ALL primary functions of the {item_name} from the Item Definition.

**Instructions:**
- Focus on functional behaviors described in sections like "Functionality", "Operating Modes", "Functions", etc.
- Each function should be a distinct capability or behavior
- Format each function clearly and concisely
- Include what the function does, not how it does it
- Examples of functions:
  * "Monitor battery cell voltages"
  * "Calculate state of charge (SoC)"
  * "Control main contactor opening/closing"
  * "Communicate status via CAN bus"

**Output Format:**
List each function on a new line with a brief description:
1. [Function Name]: [Brief description]
2. [Function Name]: [Brief description]
...

Extract the functions now:
"""

    try:
        functions_list = cat.llm(prompt).strip()
        
        # Store results in working memory
        cat.working_memory["hara_item_name"] = item_name
        cat.working_memory["item_functions"] = functions_list
        cat.working_memory["item_definition_content"] = item_def_content  # Store for later use
        cat.working_memory["hara_stage"] = "functions_extracted"

        log.info(f"✅ Functions extracted and stored in working memory")

        result = f"""✅ **Functions Extracted for {item_name}**

{functions_list}

---

**Next Steps:**
1. **Apply HAZOP analysis:** `apply hazop analysis`
2. **Or generate complete HARA table:** `generate hara table` (includes HAZOP automatically)

*Tip: You can add more functions manually by saying:*
*"Add function: [description]"*
"""
        return result

    except Exception as e:
        log.error(f"❌ Error extracting functions: {e}")
        return f"❌ Error extracting functions: {str(e)}"


@tool(return_direct=True)
def apply_hazop_analysis(tool_input, cat):
    """
    Apply HAZOP guide words to identified functions to discover hazards.
    Now processes ONE FUNCTION AT A TIME to ensure full coverage of all guide words.
    Outputs a complete, unified markdown table with all (function × guide word) combinations.
    Input: (Optional) Specific function to focus on. If empty, applies to ALL functions.
    """
    print("✅ TOOL CALLED: apply_hazop_analysis (Per-Function Mode)")
    
    # Check for required data
    functions_text = cat.working_memory.get("item_functions", "")
    item_name = cat.working_memory.get("hara_item_name", "the system")
    if not functions_text:
        return """❌ **No functions found in working memory**
Please first extract functions using:
`extract functions from [item name]`
Example: `extract functions from Battery Management System`
"""

    log.info(f"🔍 Applying HAZOP analysis for {item_name} (per-function mode)")

    # Load HAZOP guide words (ALL of them)
    plugin_folder = os.path.dirname(__file__)
    guide_words_data = load_hazop_guidewords(plugin_folder)
    guide_words = guide_words_data.get("hazop_guide_words", {})
    if not guide_words:
        log.error("❌ No HAZOP guide words loaded!")
        return "❌ Error: HAZOP guide words template not found or empty"
    
    guide_word_list = list(guide_words.keys())
    log.info(f"📚 Loaded {len(guide_word_list)} HAZOP guide words: {', '.join(guide_word_list)}")

    # Parse functions (assume format: "1. Name: desc", "2. Name: desc", etc.)
    function_lines = [line.strip() for line in functions_text.split('\n') if line.strip() and line[0].isdigit()]
    functions = []
    for line in function_lines:
        # Extract function name (before colon or after number)
        if ':' in line:
            func = line.split(':', 1)[0].split('.', 1)[-1].strip()
        else:
            func = line.split('.', 1)[-1].strip()
        if func:
            functions.append(func)

    if not functions:
        # Fallback: treat each line as a function
        functions = [line.strip() for line in functions_text.split('\n') if line.strip()]

    if not functions:
        return "❌ Could not parse any functions from the input."

    log.info(f"⚙️ Found {len(functions)} functions to analyze")

    # Determine scope
    focus_function = None
    if isinstance(tool_input, str) and tool_input.strip():
        focus_function = tool_input.strip()
    elif isinstance(tool_input, dict):
        focus_function = tool_input.get("focus_function")

    functions_to_process = [focus_function] if focus_function else functions

    all_hazop_rows = []

    for func in functions_to_process:
        if focus_function and func != focus_function:
            continue

        log.info(f"  → Analyzing function: {func}")

        # Build prompt for this single function + all guide words
        guide_words_str = ", ".join(guide_word_list)
        prompt = f"""You are a Functional Safety Engineer performing HAZOP analysis per ISO 26262 for {item_name}.

**Function to Analyze:**
{func}

**HAZOP Guide Words to Apply (use ALL):**
{guide_words_str}

**Instructions:**
1. For **each guide word**, generate ONE row with:
   - **Malfunction**: [Function] + [guide word] → e.g., "No voltage monitoring"
   - **Hazard**: Plausible hazardous event at vehicle/item level (e.g., "Battery fire")
   - **Severity Class**: S3, S2, S1, or S0
   - **Rationale**: 1–2 sentences explaining severity
2. Only include hazards with **S1 or higher**.
3. Be **concise**: max 10 words per cell except rationale.
4. Output ONLY a markdown table with these columns:
   | Function | HAZOP Guideword | Malfunction | Hazard | Severity Class | Rationale for Chosen Severity |

**Begin table now (no header explanation, just the table):**
"""

        try:
            response = cat.llm(prompt).strip()
            # Extract table rows (skip header/separator)
            lines = response.split('\n')
            data_rows = []
            for line in lines:
                if line.startswith('|') and not any(x in line for x in ['---', 'Function', 'Guideword']):
                    data_rows.append(line)
            all_hazop_rows.extend(data_rows)
            log.info(f"    → Generated {len(data_rows)} hazard rows for '{func}'")
        except Exception as e:
            log.error(f"⚠️ Error analyzing function '{func}': {e}")
            continue

    if not all_hazop_rows:
        return "❌ No HAZOP results generated. Try refining function descriptions."

    # Build final table with sequential IDs
    header = "| ID | Function | HAZOP Guideword | Malfunction | Hazard | Severity Class | Rationale for Chosen Severity |"
    separator = "|----|----------|------------------|-------------|--------|----------------|-------------------------------|"
    final_rows = []
    for i, row in enumerate(all_hazop_rows, 1):
        # Insert ID at start of row
        content = row.strip('|').split('|')
        if len(content) >= 6:
            new_row = f"| HAZ-{i:03d} | {content[0]} | {content[1]} | {content[2]} | {content[3]} | {content[4]} | {content[5]} |"
            final_rows.append(new_row)

    full_table = '\n'.join([header, separator] + final_rows)

    # Store in working memory
    cat.working_memory["hazop_analysis"] = full_table
    cat.working_memory["hara_stage"] = "hazop_completed"
    cat.working_memory["document_type"] = "hazop_analysis"
    cat.working_memory["system_name"] = item_name

    log.info(f"✅ HAZOP analysis completed: {len(final_rows)} total hazards")

    result = f"""✅ **Complete HAZOP Analysis for {item_name}**
{full_table}

---
**Summary:** {len(final_rows)} hazards generated across {len(functions_to_process)} function(s).
**Next Steps:**
1. **Assess specific hazards:** `assess hazard [description]`
2. **Generate HARA table:** `generate hara table`
3. **Export full report** via OutputFormatter plugin
"""
    return result

@tool(return_direct=True)
def assess_hazard_severity_exposure_controllability(tool_input, cat):
    """
    Assess Severity (S), Exposure (E), and Controllability (C) for a specific hazard,
    then calculate ASIL.
    
    Input: A string describing the hazard to assess
    Example: "Battery thermal runaway due to overvoltage"
    
    Use this tool when user asks:
    - "assess hazard [description]"
    - "evaluate S E C for [hazard]"
    - "what is the ASIL for [hazard]"
    """
    print("✅ TOOL CALLED: assess_hazard_severity_exposure_controllability")
    
    hazard_description = str(tool_input).strip() if tool_input else ""
    if not hazard_description:
        return """❌ **Hazard description required**

Please specify which hazard to assess.

**Example:**
`assess hazard: Battery overcharge leading to thermal runaway`

Or from HAZOP results:
`assess hazard: [copy hazardous event from HAZOP analysis]`
"""

    item_name = cat.working_memory.get("hara_item_name", "the item")
    
    log.info(f"📊 Assessing S/E/C for hazard: {hazard_description[:100]}...")

    prompt = f"""You are a Functional Safety Engineer performing risk assessment per ISO 26262-3:2018 for {item_name}.

**Hazard to Assess:**
{hazard_description}

**Context:**
- **Item:** {item_name}
- **Standard:** ISO 26262-3:2018

**Assessment Criteria:**

**Severity (S):** Assess potential harm to persons
- **S0**: No injuries
- **S1**: Light and moderate injuries (minor cuts, bruises - no hospitalization)
- **S2**: Severe and life-threatening injuries (survival probable - hospitalization required)
- **S3**: Life-threatening injuries (survival uncertain) or fatal injuries

**Exposure (E):** Probability of operational situation where hazard can occur
- **E0**: Incredibly unlikely (< 0.001% of operating time)
- **E1**: Very low probability (0.001% to 0.1%)
- **E2**: Low probability (0.1% to 1%)
- **E3**: Medium to high probability (> 1% of operating time)

**Controllability (C):** Ability of driver/persons to avoid harm
- **C0**: Controllable in general (>99% of all drivers/persons, normal skills)
- **C1**: Simply controllable (>99%, minor additional effort)
- **C2**: Normally controllable (>90%, corrective action needed)
- **C3**: Difficult to control or uncontrollable (<90% of drivers/persons)

**Task:** 
Provide a thorough assessment with clear rationale for each rating.

**Required Output Format:**
---
**Severity (S): S[0/1/2/3]**
**Rationale:** [Detailed explanation considering vehicle speed, collision type, occupant protection, etc.]

**Exposure (E): E[0/1/2/3]**
**Rationale:** [Detailed explanation considering frequency of operational situation, duration, statistical data]

**Controllability (C): C[0/1/2/3]**
**Rationale:** [Detailed explanation considering warning time, required driver actions, average driver capability]
---

Provide your assessment:
"""

    try:
        assessment = cat.llm(prompt).strip()
        
        # Calculate ASIL based on the assessment
        asil_result = extract_and_calculate_asil(assessment)
        
        final_output = f"""✅ **Hazard Assessment Complete**

**Hazard:** {hazard_description}

{assessment}

---

**Calculated ASIL:** {asil_result}

---

**Next Steps:**
- Assess another hazard: `assess hazard [description]`
- Generate complete HARA table: `generate hara table`
- Derive safety goal for this hazard: `derive safety goal for this hazard`
"""
        
        # Store assessment in working memory
        if "hara_assessments" not in cat.working_memory:
            cat.working_memory["hara_assessments"] = []
        
        cat.working_memory["hara_assessments"].append({
            "hazard": hazard_description,
            "assessment": assessment,
            "asil": asil_result,
            "timestamp": datetime.now().isoformat()
        })
        
        log.info(f"✅ Assessment completed: {asil_result}")

        return final_output

    except Exception as e:
        log.error(f"❌ Error assessing hazard S/E/C: {e}")
        return f"❌ Error assessing hazard: {str(e)}"


@tool(return_direct=True)
def generate_hara_table(tool_input, cat):
    """
    Generate the complete HARA report as a structured markdown table.
    
    This tool compiles:
    - Hazards from HAZOP analysis
    - S/E/C assessments
    - ASIL calculations
    - Safety goals
    
    Into an ISO 26262-3:2018 compliant HARA table.
    
    Use this tool when user asks:
    - "generate hara table"
    - "create hara report"
    - "compile hara"
    """
    print("✅ TOOL CALLED: generate_hara_table")
    
    hazop_analysis = cat.working_memory.get("hazop_analysis", "")
    item_name = cat.working_memory.get("hara_item_name", "Unknown Item")
    functions = cat.working_memory.get("item_functions", "")

    if not hazop_analysis:
        return """❌ **Insufficient data to generate HARA table**

**Required steps:**
1. `extract functions from [item name]`
2. `apply hazop analysis`

After completing these steps, run `generate hara table` again.

**Quick Start:**
You can also run these steps in sequence:
1. `extract functions from Battery Management System`
2. `apply hazop analysis`
3. `generate hara table`
"""

    log.info(f"📊 Generating HARA table for {item_name}")

    prompt = f"""You are a Functional Safety Engineer creating the final HARA table per ISO 26262-3:2018 Clause 6 for {item_name}.

**Available Data:**

**Item:** {item_name}

**Functions:**
{functions}

**HAZOP Analysis Results:**
{hazop_analysis}

**Task:** Create a complete, professional HARA table in markdown format.

**Required Columns:**
| Hazard ID | Function | Malfunctioning Behavior | Hazardous Event | Operational Situation | Severity (S) | Exposure (E) | Controllability (C) | ASIL | Safety Goal | Safe State |

**Instructions:**
1. Parse the HAZOP analysis to identify distinct hazard scenarios
2. For each hazard:
   - Assign unique ID (HAZ-001, HAZ-002, etc.)
   - Identify the function affected
   - Describe the malfunction clearly
   - State the hazardous event (actual harm scenario)
   - Define operational situation (e.g., "Highway driving", "Fast charging")
   - Assess S, E, C based on ISO 26262-3:2018 criteria
   - Calculate ASIL using the standard matrix
   - Formulate the Safe state (a condition where the system operates without posing an unacceptable risk, even if a malfunction occurs.)

3. **CRITICAL - Safety Goal Formulation (ISO 26262-3 Clause 6.4.6):**
   Safety Goals must follow these strict guidelines:
   
   ✅ **DO:**
   - Derive directly from the hazardous event
   - State the INTENDED SAFETY OUTCOME (what must be achieved)
   - Focus on RESULTS, not technical solutions
   - Use risk reduction language: "prevent", "avoid", "mitigate", "ensure", "maintain"
   - Include ASIL designation in parentheses
   - Include Safe State when applicable (e.g., "Safe State: HV disconnected")
   - Include FTTI when time-critical (e.g., "FTTI: 100ms")
   - Be clear and unambiguous
   
   ❌ **DO NOT:**
   - Prescribe HOW to achieve the goal (no technical solutions)
   - Specify implementation details (sensors, algorithms, timing values for detection)
   - Use technical jargon unnecessarily
   - Combine multiple goals into one
   
   **Safety Goal Format:**
   "The [hazardous event] shall be [prevented/avoided/mitigated] [under conditions]. (ASIL X, Safe State: [state], FTTI: [time])"
   
   **Good Examples:**
   - "Avoid thermal runaway due to cell overvoltage. (ASIL D, Safe State: Battery isolated, FTTI: 100ms)"
   - "Avoid unintended vehicle acceleration. (ASIL D, Safe State: Engine torque limited)"
   - "Ensure driver visibility during wiper operation. (ASIL B)"
   - "Ensure safe battery operation within specified temperature limits. (ASIL C, Safe State: Charging stopped)"
   
   **Bad Examples (DO NOT USE):**
   - ❌ "The BMS shall monitor cell voltage with 10ms sampling and disconnect within 50ms if overvoltage" (too technical, prescriptive)
   - ❌ "The system shall use redundant sensors to validate voltage measurements" (specifies implementation)
   - ❌ "The wiper controller shall activate wipers within 500ms upon rain sensor signal" (specifies how, not what)
   
4. Be consistent and professional
5. 4. Output ONLY a markdown table with these columns:
   | Hazard ID | Function | Malfunctioning Behavior | Hazardous Event | Operational Situation | Severity (S) | Exposure (E) | Controllability (C) | ASIL | Safety Goal |

**Generate the HARA Table:**
"""

    try:
        hara_table = cat.llm(prompt).strip()
        
        # Store in working memory
        cat.working_memory["document_type"] = "hara"
        cat.working_memory["hara_table"] = hara_table
        cat.working_memory["hara_stage"] = "table_generated"

        log.info("✅ HARA table generated and stored in working memory")
        
        result = f"""✅ **HARA Table Generated for {item_name}**

{hara_table}

---

**Table Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Next Steps:**
- Export to document: Use the Output Formatter plugin to generate Word/Excel
- Review and refine: Ask to modify specific hazards or add more
- Derive detailed safety requirements from safety goals

**ISO 26262 Compliance:**
✅ Clause 6.4.3 - Hazard identification (HAZOP method)
✅ Clause 6.4.4 - Classification of hazardous events (S, E, C)
✅ Clause 6.4.5 - ASIL determination
✅ Clause 6.4.6 - Safety goal determination
"""
        
        return result

    except Exception as e:
        log.error(f"❌ Error generating HARA table: {e}")
        return f"❌ Error generating HARA table: {str(e)}"


@tool(return_direct=True)
def derive_safety_goal(tool_input, cat):
    """
    Derive a detailed Safety Goal from a specific hazardous event.
    
    This tool creates ISO 26262-3:2018 Clause 6.4.6 compliant Safety Goals that:
    - Are result-oriented (what to achieve, not how)
    - Include ASIL designation
    - Specify safe state when applicable
    - Include FTTI when time-critical
    
    Input: Hazardous event description or Hazard ID from HARA table
    
    Use this tool when user asks:
    - "derive safety goal for [hazard]"
    - "create safety goal for [hazardous event]"
    - "what is the safety goal for [hazard]"
    """
    print("✅ TOOL CALLED: derive_safety_goal")
    
    hazard_info = str(tool_input).strip() if tool_input else ""
    if not hazard_info:
        return """❌ **Hazard description required**

Please specify the hazardous event for which to derive a safety goal.

**Example:**
`derive safety goal for: Cell overvoltage leading to thermal runaway`

Or use a Hazard ID from the HARA table:
`derive safety goal for HAZ-001`
"""

    item_name = cat.working_memory.get("hara_item_name", "the system")
    hara_table = cat.working_memory.get("hara_table", "")
    
    prompt = f"""You are a Functional Safety Engineer deriving a Safety Goal per ISO 26262-3:2018 Clause 6.4.6 for {item_name}.

**Hazardous Event:**
{hazard_info}

**Context:**
Item: {item_name}
{f"HARA Table Context: {hara_table[:1000]}" if hara_table else ""}

**Task:** Derive a complete Safety Goal following ISO 26262 guidelines.

**ISO 26262-3:2018 Safety Goal Requirements:**

1. **Result-Oriented:** Focus on WHAT must be achieved (safety outcome), not HOW (technical solution)
2. **Directly Linked:** Must clearly address the identified hazardous event
3. **ASIL Designation:** Include the assigned ASIL level
4. **Safe State:** Specify the safe state to be achieved (when applicable)
5. **FTTI:** Include Fault-Tolerant Time Interval for time-critical scenarios (when applicable)
6. **Clear Language:** Use unambiguous risk reduction terminology

**Safety Goal Template:**
"The [system/item] shall [prevent/avoid/mitigate/ensure/maintain] [hazardous event description] [operational context]. (ASIL X, Safe State: [description], FTTI: [time])"

**Language Guidelines:**
✅ USE: prevent, avoid, mitigate, ensure, maintain, detect, limit, control
❌ AVOID: monitor, measure, use, implement, activate, send, receive

**Example Analysis:**

**Hazardous Event:** "Cell overcharge leading to thermal runaway and fire"

**Poor Safety Goal (too technical):**
❌ "The BMS shall monitor cell voltage every 10ms and open the main contactor within 50ms if voltage exceeds 4.25V per cell"
*Why poor: Specifies HOW (monitoring rate, voltage threshold, timing) instead of WHAT*

**Good Safety Goal (result-oriented):**
✅ "The system shall prevent cell overvoltage to avoid thermal runaway and fire during all charging operations. (ASIL D, Safe State: Battery electrically isolated from charger, FTTI: 100ms)"
*Why good: Focuses on preventing the hazard, includes ASIL, safe state, and FTTI*

**Your Task:**
Analyze the provided hazardous event and derive a complete safety goal.

**Provide:**
1. **Safety Goal Statement:** [The complete safety goal following the template]
2. **ASIL Justification:** [Why this ASIL was assigned - reference S/E/C values]
3. **Safe State Description:** [Detailed description of the safe state]
4. **FTTI Rationale:** [Why this time interval was chosen, if applicable]
5. **Assumptions:** [Any assumptions made about system behavior or operational context]

**Output Format:**

---
## Safety Goal for: [Hazardous Event Summary]

**Safety Goal:**
[Complete safety goal statement]

**ASIL:** [X] 
**Justification:** [S/E/C values and rationale]

**Safe State:** 
[Detailed description of safe state]

**Fault-Tolerant Time Interval (FTTI):** [X ms/seconds] *(if applicable)*
**Rationale:** [Why this FTTI]

**Assumptions:**
- [Assumption 1]
- [Assumption 2]
...

**Verification Criteria:**
[How this safety goal can be verified/validated]

---

Derive the safety goal now:
"""

    try:
        safety_goal_analysis = cat.llm(prompt).strip()
        
        # Store in working memory
        if "derived_safety_goals" not in cat.working_memory:
            cat.working_memory["derived_safety_goals"] = []
        
        cat.working_memory["derived_safety_goals"].append({
            "hazard": hazard_info,
            "analysis": safety_goal_analysis,
            "timestamp": datetime.now().isoformat()
        })
        
        log.info(f"✅ Safety goal derived for: {hazard_info[:50]}...")
        
        result = f"""✅ **Safety Goal Derived**

{safety_goal_analysis}

---

**Next Steps:**
- Derive more safety goals: `derive safety goal for [another hazard]`
- Refine existing goal: `refine safety goal: [provide feedback]`
- Generate complete HARA table: `generate hara table`
- Proceed to Functional Safety Concept development
"""
        
        return result

    except Exception as e:
        log.error(f"❌ Error deriving safety goal: {e}")
        return f"❌ Error deriving safety goal: {str(e)}"


@tool(return_direct=False)
def add_function_manually(tool_input, cat):
    """
    Add a function manually to the functions list.
    
    Use this when user wants to add a function that wasn't extracted automatically.
    
    Input: Function description
    Example: "Monitor battery temperature in all operating modes"
    """
    print("✅ TOOL CALLED: add_function_manually")
    
    function_description = str(tool_input).strip() if tool_input else ""
    if not function_description:
        return {"error": "Function description required"}
    
    # Get existing functions
    existing_functions = cat.working_memory.get("item_functions", "")
    
    # Add new function
    updated_functions = f"{existing_functions}\n{function_description}"
    cat.working_memory["item_functions"] = updated_functions
    
    log.info(f"✅ Function added: {function_description}")
    
    return {
        "success": True,
        "message": f"Function added: {function_description}",
        "total_functions": updated_functions.count('\n') + 1
    }