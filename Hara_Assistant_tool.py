# enhanced_Hara_assessment_tool.py - Refined HARA Assistant Tools
import json
import os
import re
from datetime import datetime
from cat.mad_hatter.decorators import tool
from cat.log import log
from .exposure_assessment_tool import get_exposure_guidance
from .ASIL_Calculator import ASILCalculator

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    log.warning("PyPDF2 not available - PDF reading disabled")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_hazop_guidewords(plugin_folder):
    """Load HAZOP guide words from template file."""
    template_path = os.path.join(plugin_folder, "templates", "hazop_guidewords.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"HAZOP guide words template not found: {template_path}")
        return {"hazop_guide_words": {}}
    except json.JSONDecodeError as e:
        log.error(f"Invalid HAZOP template JSON: {e}")
        return {"hazop_guide_words": {}}


def load_operational_situations(plugin_folder):
    """Load operational situations database from JSON file."""
    template_path = os.path.join(plugin_folder, "templates", "operational_situations.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning(f"Operational situations file not found: {template_path}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"Invalid operational situations JSON: {e}")
        return None


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
    
    # If not in memory, try to find in plugin folders (fallback)
    plugin_folder = os.path.dirname(__file__)
    search_paths = [
        os.path.join(plugin_folder, "item_definitions"),
        os.path.join(plugin_folder, "..", "AI_Agent-OutputFormatter", "generated_documents", "01_Item_Definition")
    ]

    log.info(f"🔍 Searching for Item Definition for '{item_name}'...")
    
    for folder_path in search_paths:
        if not os.path.exists(folder_path):
            continue
            
        log.info(f"   Checking folder: {folder_path}")
        
        try:
            for filename in os.listdir(folder_path):
                # Check various file extensions
                for folder_path in search_paths:
                    if os.path.exists(folder_path):
                        for filename in os.listdir(folder_path):
                            # Check for text files
                            if filename.lower().endswith(('.txt', '.md')):
                                file_path = os.path.join(folder_path, filename)
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                        if item_name.lower() in content.lower():
                                            log.info(f"Found item definition in {filename}")
                                        return content
                                except Exception as e:
                                    log.warning(f"Error reading {filename}: {e}")

                            # Check for PDF files
                            elif PDF_AVAILABLE and filename.lower().endswith('.pdf'):
                                file_path = os.path.join(folder_path, filename)
                                try:
                                    with open(file_path, 'rb') as f: # Open in binary mode for PDF
                                        pdf_reader = PyPDF2.PdfReader(f)
                                        content = ""
                                        for page in pdf_reader.pages:
                                            content += page.extract_text() + "\n" # Extract text from each page
                                    # Check if item name is in the extracted PDF text
                                    if item_name.lower() in content.lower():
                                        log.info(f"Found item definition in PDF: {filename}")
                                        return content
                                except Exception as e:
                                    log.warning(f"Error reading PDF {filename}: {e}")
        except Exception as e:
            log.warning(f"File not found {filename}: {e}")
    
    # 3. Not found anywhere
    log.warning(f"❌ No Item Definition found for '{item_name}'")
    return None


def parse_functions_from_text(functions_text):
    """
    Parse function list from LLM-generated text.
    
    Args:
        functions_text: Text containing numbered function list
        
    Returns:
        list: Parsed function names
    """
    function_lines = [
        line.strip() 
        for line in functions_text.split('\n') 
        if line.strip() and any(c.isdigit() for c in line[:3])
    ]
    
    functions = []
    for line in function_lines:
        if ':' in line:
            func = line.split(':', 1)[0].split('.', 1)[-1].strip()
        else:
            func = line.split('.', 1)[-1].strip() if '.' in line else line.strip()
        
        if func:
            functions.append(func)
    
    # Fallback: treat each line as a function
    if not functions:
        functions = [line.strip() for line in functions_text.split('\n') if line.strip()]
    
    return functions


def extract_asil_distribution(hara_table):
    """
    Extract ASIL distribution from HARA table.
    
    Args:
        hara_table: HARA table text
        
    Returns:
        dict: ASIL counts
    """
    table_rows = [line for line in hara_table.split('\n') if line.strip().startswith('| HAZ-')]
    asil_counts = {}
    
    for row in table_rows:
        asil_match = re.search(r'\|\s*(ASIL\s*[A-D]|QM)\s*\|', row)
        if asil_match:
            asil = asil_match.group(1).strip()
            asil_counts[asil] = asil_counts.get(asil, 0) + 1
    
    return asil_counts


def build_function_extraction_prompt(item_def_content, item_name):
    """Build structured prompt for function extraction."""
    
    # Truncate if too long
    max_length = 10000
    item_def_truncated = item_def_content[:max_length]
    if len(item_def_content) > max_length:
        item_def_truncated += "\n\n[... content truncated ...]"
    
    prompt = f"""You are a Functional Safety Engineer analyzing an Item Definition for HARA development.

# Item Definition for {item_name}

{item_def_truncated}

# Your Task

Extract the 4-5 **most safety-relevant functions** from this Item Definition.

# Function Selection Criteria

Focus on functions that:
- Have potential for hazardous behavior if malfunctioning
- Interact with vehicle-level safety
- Affect occupant protection, vehicle control, or critical systems
- Could lead to injuries, collisions, or fires

# Output Format

Provide a numbered list with brief descriptions:

1. [Function Name]: [Why it's safety-critical - one sentence]
2. [Function Name]: [Why it's safety-critical - one sentence]
...

**Maximum 5 functions**

# Example for Battery Management System

1. Monitor battery cell voltages: Prevents overcharge/over-discharge leading to thermal runaway
2. Control main contactors: Isolates high voltage to prevent electric shock and fire
3. Calculate State of Charge (SoC): Prevents unexpected loss of propulsion
4. Monitor battery temperature: Prevents thermal runaway by detecting overheat conditions
5. Implement emergency shutdown: Transitions to safe state upon critical fault detection

Extract the 4-5 most critical safety-relevant functions now:
"""
    
    return prompt


# ============================================================================
# TOOLS
# ============================================================================

@tool(
    return_direct=True,
    examples=[
        "explain hara workflow",
        "how to generate hara",
        "hara process steps"
    ]
)
def explain_hara_workflow(tool_input, cat):
    """Show ISO 26262 HARA workflow steps and current progress.
    Input: not required.
    Returns 5-step workflow guide with next actions."""
    
    log.info("🔧 TOOL CALLED: explain_hara_workflow")
    
    current_stage = cat.working_memory.get("hara_stage", "not_started")
    item_name = cat.working_memory.get("hara_item_name", "[Item Name]")
    
    workflow = f"""# ISO 26262 HARA Workflow - 5 Steps

**Item:** {item_name}  
**Current Stage:** {current_stage}

**Complete Process for Hazard Analysis and Risk Assessment**

---

## Step 1: Extract Functions from Item Definition
**Command:** `extract functions from {item_name}`

**What it does:**
- Reads the Item Definition document for your system
- Identifies all primary functions of the item
- Lists functions with descriptions and normal parameters
- Stores functions for HAZOP analysis

**Prerequisites:**
- Item Definition document must exist (generated or uploaded)

**Output:**
- List of all system functions

---

## Step 2: Apply HAZOP Analysis
**Command:** `apply hazop analysis`

**What it does:**
- Takes each function from Step 1
- Systematically applies 11 HAZOP guide words (NO, MORE, LESS, EARLY, LATE, etc.)
- Identifies malfunctioning behaviors
- Describes potential hazardous events
- Assesses preliminary Severity (S0-S3)

**Prerequisites:**
- Step 1 must be completed

**Output:**
- HAZOP table with: Hazard ID, Function, Malfunction, Hazardous Event, Severity Class

---

## Step 3: Assess Exposure for All Hazards
**Command:** `assess exposure for all hazards`

**What it does:**
- For each hazard from Step 2:
  - Selects 2-4 relevant basic operational situations from database
  - Combines them into a specific driving scenario
  - Calculates combined Exposure using MIN rule: E_combined = MIN(E1, E2, E3, ...)
  - Links each hazard to realistic operational context

**Prerequisites:**
- Step 2 must be completed

**Output:**
- Exposure assessment table with: Hazard ID, Selected Scenarios, Combined Driving Scenario, Exposure (E0-E4)

---

## Step 4: Generate Complete HARA Table
**Command:** `generate hara table`

**What it does:**
- Combines data from Steps 2 and 3
- Assesses Controllability (C0-C3) for each hazard considering driving scenario
- Calculates ASIL using ISO 26262 Table 4: ASIL = f(S, E, C)
- Formulates preliminary safety goals
- Defines safe states and FTTI

**Prerequisites:**
- Steps 2 and 3 must be completed

**Output:**
- Complete HARA table with 12 columns: Hazard ID, Function, Malfunction, Hazardous Event, Operational Situation, S, E, C, ASIL, Safety Goal, Safe State, FTTI

---

## Step 5: Derive Detailed Safety Goals
**Command:** `derive detailed safety goals`

**What it does:**
- For each hazard with ASIL A, B, C, or D:
  - Formulates complete ISO 26262-compliant safety goal
  - Defines detailed safe state specification
  - Specifies FTTI with justification
  - Provides verification criteria
  - Documents assumptions

**Prerequisites:**
- Step 4 must be completed

**Output:**
- Detailed safety goals document for all ASIL A/B/C/D hazards

---

## Your Current Progress

**Item:** {item_name}
**Current Stage:** {current_stage}

"""
    
    # Add progress-specific guidance
    if current_stage == "not_started":
        workflow += f"\n**Next:** `extract functions from [your item name]`"
    elif current_stage == "functions_extracted":
        workflow += "\n**✅ Completed:** Step 1\n**Next:** `apply hazop analysis`"
    elif current_stage == "hazop_completed":
        workflow += "\n**✅ Completed:** Steps 1-2\n**Next:** `assess exposure for all hazards`"
    elif current_stage == "exposure_assessed":
        workflow += "\n**✅ Completed:** Steps 1-3\n**Next:** `generate hara table`"
    elif current_stage == "table_generated":
        workflow += "\n**✅ Completed:** Steps 1-4\n**Next:** `derive detailed safety goals`"
    elif current_stage == "safety_goals_derived":
        workflow += "\n**Status:** HARA Complete! ✅"
    
    return workflow


@tool(
    return_direct=True,
    examples=[
        "extract functions from Battery Management System",
        "get functions for Brake System",
        "start HARA for Steering Control"
    ]
)
def extract_functions(tool_input, cat):
    """
    Extracts **safety-relevant functions** from the Item Definition for HARA/HAZOP analysis.
    The Item Definition can be:
    - In working memory (after generation)
    - Saved in plugin folders (item_definitions/)
    
    Input: The name of the item (e.g., "Battery Management System", "Wiper System").
    
    Returns numbered list of 4-5 critical functions."""
    
    log.info("🔧 TOOL CALLED: extract_functions")
    
    # Parse input
    item_name = "Unknown System"
    if isinstance(tool_input, str):
        item_name = tool_input.strip()
    elif isinstance(tool_input, dict):
        item_name = tool_input.get("item_name", item_name)
    
    log.info(f"📋 Extracting functions for: {item_name}")
    
    # Find Item Definition
    item_def_content = find_item_definition(cat, item_name)
    
    if not item_def_content:
        return f"""❌ **No Item Definition Found: '{item_name}'**

**Please ensure:**
1. Item Definition generated via ItemDefinition_Developer plugin
2. Item name matches exactly
3. File exists in one of these locations:
   - Working memory (if just generated)
   - `item_definitions/` folder in HARA plugin
   - ItemDefinition_Developer plugin folders

**Manual Setup:**
- Save to: `plugins/AI_Agent-HARA_Assistant/item_definitions/{item_name}.txt`
- Or store in working memory:
  ```
  cat.working_memory["item_definition_content"] = "[content]"
  ```

**Try again after setup.**"""
    
    log.info(f"📄 Found Item Definition: {len(item_def_content)} characters")
    
    # Build extraction prompt
    try:
        prompt = build_function_extraction_prompt(item_def_content, item_name)
        log.info("🤖 Extracting functions with LLM...")
        
        functions_list = cat.llm(prompt).strip()
        
        # Store in working memory
        cat.working_memory["hara_item_name"] = item_name
        cat.working_memory["item_functions"] = functions_list
        cat.working_memory["item_definition_content"] = item_def_content
        cat.working_memory["hara_stage"] = "functions_extracted"
        
        log.info(f"✅ Functions extracted and stored")
        
        return f"""✅ **Functions Extracted: {item_name}**

{functions_list}

---

## Workflow Progress: 1/5 Steps Complete

**Completed:**
- ✅ Step 1: Functions extracted

**Next Steps:**
➡️ Step 2: `apply hazop analysis`
- Applies HAZOP guide words to identify hazards
- Assesses Severity (S) for each hazard
- Output: HAZOP table with malfunctions and hazardous events

**Remaining Steps:**
3. ❓Assess exposure for all hazards
4. ❓Generate HARA table
5. ❓Derive detailed safety goals

**Tips:** 
- You can view the complete workflow anytime by asking: "explain hara workflow"
- You can add more functions manually by saying:* *"Add function: [description]"*
"""
    
    except Exception as e:
        log.error(f"Function extraction failed: {e}")
        return f"""❌ **Function Extraction Failed**

Error: {e}

**Possible causes:**
- Item Definition too large or malformed
- LLM service unavailable
- Invalid content format

**Recommendations:**
1. Check Item Definition file is readable
2. Verify LLM connection in Cheshire Cat
3. Try with a smaller/simpler Item Definition"""

@tool(
    return_direct=True,
    examples=[
        "apply hazop analysis",
        "apply HAZOP to functions"
        "identify hazards using hazop",
        "use guide words"
    ]
)
def apply_hazop_analysis(tool_input, cat):
    """
    Applies relevant HAZOP guide words to functions/malfunctions to generate hazards.
    The agent intelligently selects guide words based on the function/malfunction context.
    Use this tool when the user asks to:
    - "Apply HAZOP"
    - "Apply HAZOP to functions"
    - "Identify hazards using HAZOP"
    - "Use guide words"
    Input can be:
    - Empty (uses functions from memory)
    - Specific function name to analyze
    - {"focus_function": "Function Name"}
    """
    print("✅ TOOL CALLED: apply_hazop_analysis")
    
    # Get functions from working memory
    functions_text = cat.working_memory.get("item_functions", "")
    item_name = cat.working_memory.get("hara_item_name", "the system")

    if not functions_text:
        return """⚠️ No functions found in memory.
Please first extract functions using: `extract functions from item definition`"""

    # Parse input for specific function focus
    focus_function = None
    if isinstance(tool_input, dict):
        focus_function = tool_input.get("focus_function")
    elif isinstance(tool_input, str) and tool_input.strip():
        focus_function = tool_input.strip()

    # Load HAZOP guide words
    plugin_folder = os.path.dirname(__file__)
    guide_words_data = load_hazop_guidewords(plugin_folder)
    guide_words = guide_words_data.get("hazop_guide_words", {})
    
    if not guide_words:
        log.error("❌ No HAZOP guide words loaded!")
        return "❌ Error: HAZOP guide words template not found or empty"

    # Build a concise summary of guide words for the prompt
    guide_words_summary = "\n".join([
        f"- **{word}**: {details['meaning']} - {details['description']}"
        for word, details in guide_words.items()
    ])

    # Parse functions list
    function_lines = [line.strip() for line in functions_text.split('\n') 
                     if line.strip() and any(c.isdigit() for c in line[:3])]
    functions = []
    for line in function_lines:
        if ':' in line:
            func = line.split(':', 1)[0].split('.', 1)[-1].strip()
        else:
            func = line.split('.', 1)[-1].strip() if '.' in line else line.strip()
        if func:
            functions.append(func)

    # Fallback: treat each line as a function
    if not functions:
        functions = [line.strip() for line in functions_text.split('\n') if line.strip()]

    if not functions:
        return "❌ Could not parse any functions from the input."

    log.info(f"⚙️ Found {len(functions)} functions to analyze")

    # Determine functions to process
    functions_to_process = [focus_function] if focus_function else functions

    all_hazop_rows = []

    # Process each function
    for func in functions_to_process:
        log.info(f"  → Analyzing function: {func}")

        prompt = f"""You are a Functional Safety Engineer performing a HAZOP analysis for {item_name}.

**HAZOP Guide Words:**
{guide_words_summary}

**Function to Analyze:**
{func}

**Instructions for Selective Application:**
- Consider which guide words are **logically applicable** to this specific function.
- Apply **only the relevant guide words** that make sense for this function.
- Describe the potential malfunctioning behavior resulting from each relevant deviation.
- Identify the potential hazardous event resulting from each plausible malfunction.

**Output Instructions:**
1. For **each logically applicable guide word**, generate ONE row with:
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
    cat.working_memory["system_name"] = item_name

    log.info(f"✅ HAZOP analysis completed: {len(final_rows)} total hazards")

    result = f"""✅ **Complete HAZOP Analysis for {item_name}**

{full_table}

---
## Workflow Progress: 2/5 Steps Complete

**Summary:** {len(final_rows)} hazards identified across {len(functions_to_process)} function(s)

**Completed:**
- ✅ Step 1: Functions extracted
- ✅ Step 2: HAZOP analysis performed (Severity assessed)

**Next Steps:**

➡️ Step 3: `assess exposure for all hazards`
- Selects relevant driving scenarios for each hazard
- Combines basic operational situations
- Calculates Exposure (E) using MIN rule
- Output: Exposure assessment table

**Remaining Steps:**
4.❓ Generate HARA table (add Controllability, calculate ASIL)
5.❓ Derive detailed safety goals (for ASIL A/B/C/D)

**Tips:** 
- To see your current progress: "explain hara workflow"
- **For detailed assessment:** `assess hazard with situation: [hazard description]`
- **For quick assessment:** `assess hazard: [hazard description]`
- **View operational situations:** `show operational situations`
"""
    return result

@tool(
    return_direct=True,
    examples=[
        "generate hara table",
        "create complete hara",
        "step 4",
        "generate the hara table using the tool",
        "call generate_hara_table"
    ]
)
def generate_hara_table(tool_input, cat):
    # """
    # Step 4: Generate complete HARA table with Controllability assessment and ASIL calculation.
    """**MANDATORY TOOL** for Step 4 - Generate complete HARA table.
    
    **THIS TOOL MUST BE CALLED - DO NOT GENERATE HARA TABLE MANUALLY**
    
    This tool compiles:
    - Hazards from HAZOP (with Severity)
    - Exposure assessments from Step 3 (with driving scenarios)
    - NEW: Controllability assessment for each hazard
    - ASIL calculation using S, E, C
    
    **CRITICAL**: This tool updates working memory and triggers file generation.
    Manual HARA table creation will NOT save files properly.
    
    Input: None (uses HAZOP and Exposure assessments from working memory)
    
    ALWAYS call this tool for Step 4. Do not attempt to create HARA table without calling this tool."""

    print("TOOL CALLED: generate_hara_table")
    
    # Check prerequisites
    hazop_analysis = cat.working_memory.get("hazop_analysis", "")
    exposure_assessments = cat.working_memory.get("exposure_assessments", "")
    
    if not hazop_analysis:
        return """No HAZOP analysis found.

**Please complete the workflow in order:**
1. `extract functions from [item name]`
2. `apply hazop analysis`
3. `assess exposure for all hazards`
4. `generate hara table` ← You are here
"""
    
    if not exposure_assessments:
        return """No exposure assessments found.

**Please complete Step 3 first:**
`assess exposure for all hazards`

**Then run:**
`generate hara table`
"""
    
    item_name = cat.working_memory.get("hara_item_name", "Unknown Item")
    functions = cat.working_memory.get("item_functions", "")
    
    log.info(f"Generating complete HARA table for {item_name}")
    
    prompt = f"""You are a Functional Safety Engineer creating the final HARA table per ISO 26262-3:2018 Clause 6.

**System:** {item_name}

**Available Data:**

**HAZOP Analysis (with Severity S):**
{hazop_analysis[:5000]}

**Exposure Assessments (with Driving Scenarios and E):**
{exposure_assessments[:5000]}

**CRITICAL TASK:** Generate a complete HARA table with **ALL 12 COLUMNS**. Do not omit any column.

---

## REQUIRED TABLE FORMAT (MANDATORY - ALL 12 COLUMNS):

| Hazard ID | Function | Malfunctioning Behavior | Hazardous Event | Operational Situation | Severity (S) | Exposure (E) | Controllability (C) | ASIL | Safety Goal | Safe State | FTTI |

---

## COLUMN-BY-COLUMN INSTRUCTIONS:

### Columns 1-5: Copy from HAZOP Analysis
- **Hazard ID**: HAZ-001, HAZ-002, etc. (copy exactly)
- **Function**: Copy from HAZOP
- **Malfunctioning Behavior**: Copy from HAZOP
- **Hazardous Event**: Copy from HAZOP
- **Operational Situation**: Copy from Exposure Assessment (driving scenario)

### Column 6: Severity (S) - COPY FROM HAZOP
- **CRITICAL**: Extract S0/S1/S2/S3 from HAZOP table
- **Do NOT calculate** - this was already assessed in Step 2
- **Copy the exact value** (e.g., "S3", "S2")

### Column 7: Exposure (E) - COPY FROM EXPOSURE ASSESSMENT
- Extract E0/E1/E2/E3/E4 from Exposure Assessment table
- Match by Hazard ID
- Note: E4 will map to E3 for ASIL calculation

### Column 8: Controllability (C) - NEW ASSESSMENT
Consider the operational situation (driving scenario) to assess:

- **C0**: >99% controllable (clear warning, simple action, >3s reaction time)
- **C1**: >99% controllable with minor effort (adequate warning, 1-3s reaction time)
- **C2**: >90% controllable (skilled action needed, 0.5-1s reaction time)
- **C3**: <90% controllable (no warning, <0.5s reaction, or physically impossible)

**Context matters:**
- High-speed + adverse weather → C3 (difficult to control)
- Low-speed + normal conditions → C0 or C1 (easy to control)
- City : low speed
- Country road : medium speed
- Highway : high speed 

### Column 9: ASIL - CALCULATE
Use ISO 26262-3:2018 Table 4:
- Input: S (from HAZOP), E (from Exposure), C (just assessed)
- Output: QM, A, B, C, or D
- Verify calculation is correct

### Column 10: Safety Goal - FORMULATE
**CRITICAL FORMAT RULES:**
- ✅ Start with: Avoid, Prevent, Ensure, Maintain, Mitigate, Limit
- ❌ DO NOT write: "The [system] shall..." or "System shall..."
- Result-oriented at vehicle level
- Keep concise (one sentence)
- Do NOT include ASIL, Safe State, or FTTI here

**Examples:**
- ✅ "Avoid battery overcharge to prevent thermal runaway during charging"
- ✅ "Prevent unintended airbag deployment during normal driving"
- ✅ "Ensure driver visibility through windscreen in all weather"
- ❌ "The BMS shall prevent overcharge..." (WRONG)

### Column 11: Safe State - DEFINE
Specific system condition ensuring safety:
- Measurable and verifiable
- Examples: "Battery isolated from HV bus", "Airbag armed but not deployed", "Vehicle immobilized with parking brake"

### Column 12: FTTI - SPECIFY
Fault-Tolerant Time Interval:
- Format: "50ms", "100ms", "500ms", "1s", "N/A"
- Guidelines:
  * ASIL D + high-speed: 50-200ms
  * ASIL D + low-speed: 100-500ms
  * ASIL C: 100-500ms
  * ASIL B: 500ms-2s or N/A
  * ASIL A/QM: Usually N/A

---

## COMPLETE EXAMPLE (ALL 12 COLUMNS):

| HAZ-001 | Monitor battery cell voltage | No voltage monitoring | Battery overcharge leading to thermal runaway and fire | Fast charging in extreme heat | S3 | E2 | C3 | ASIL D | Avoid battery overcharge to prevent thermal runaway during charging operations | Battery isolated from charger, thermal management active | 100ms |

---

## GENERATION INSTRUCTIONS:

1. **Start with header row** (copy the 12-column format above)
2. **For each hazard** in HAZOP table:
   - Extract columns 1-5 from HAZOP and Exposure tables
   - **COPY Severity (S)** from HAZOP (do not recalculate)
   - **COPY Exposure (E)** from Exposure Assessment
   - **ASSESS Controllability (C)** based on operational situation
   - **CALCULATE ASIL** using S, E, C
   - **FORMULATE Safety Goal** (start with action verb)
   - **DEFINE Safe State** (specific condition)
   - **SPECIFY FTTI** (based on ASIL and dynamics)

3. **Verify each row has exactly 12 columns**

4. **Do NOT omit Severity (S)** - this is critical for ASIL calculation

**Generate the complete 12-column HARA table now:**
"""
    
    try:
        log.warning("🔥 ENTERING TRY BLOCK")
        hara_table = cat.llm(prompt).strip()
        log.warning(f"✅ LLM RETURNED! Table length: {len(hara_table)}")
        # Store in working memory
        cat.working_memory["document_type"] = "hara"
        cat.working_memory["hara_table"] = hara_table
        cat.working_memory["hara_stage"] = "table_generated"
        cat.working_memory["system_name"] = item_name

        log.warning(f"📌 Working memory updated - hara_stage: {cat.working_memory.get('hara_stage')}")
        
        # Count rows
        table_rows = [line for line in hara_table.split('\n') if line.strip().startswith('| HAZ-')]
        
        # Extract ASIL distribution
        asil_counts = {}
        for row in table_rows:
            asil_match = re.search(r'\|\s*(ASIL\s*[A-D]|QM)\s*\|', row)
            if asil_match:
                asil = asil_match.group(1).strip()
                asil_counts[asil] = asil_counts.get(asil, 0) + 1
        
        log.info(f"HARA table generated: {len(table_rows)} hazards")
        log.info(f"ASIL distribution: {asil_counts}")
        
        result = f"""**Step 4 Complete: HARA Table Generated**

**System:** {item_name}
**Total Hazards:** {len(table_rows)}

{hara_table}

---

## Workflow Progress: 4/5 Steps Complete

**ASIL Distribution:**
{chr(10).join([f'- {asil}: {count} hazard(s)' for asil, count in sorted(asil_counts.items())])}

**Completed:**
- ✅ Step 1: Functions extracted
- ✅ Step 2: HAZOP analysis performed
- ✅ Step 3: Exposure assessed with driving scenarios
- ✅ Step 4: HARA table generated (S, E, C, ASIL determined)

**ISO 26262-3:2018 Compliance:**
- ✅ Clause 6.4.2: Situation analysis (driving scenarios selected)
- ✅ Clause 6.4.3: Hazard identification (HAZOP method)
- ✅ Clause 6.4.4: Classification of hazardous events (S, E, C assessed)
- ✅ Clause 6.4.5: ASIL determination (calculated per Table 4)
- ✅ Clause 6.4.6: Safety goals (preliminary formulation)

➡️ Step 5: `derive detailed safety goals`
- Creates detailed safety goals for ASIL A/B/C/D hazards
- Defines safe states
- Specifies FTTI with justification
- Provides verification criteria
- Output: Complete safety goals document

**Note:** If all hazards are QM (no ASIL A/B/C/D), Step 5 will confirm HARA is complete.

**ISO 26262 Deliverables Ready:**
- HAZOP analysis table
- Exposure assessment table
- Complete HARA table

**One optional Step Remaining:** Derive detailed safety goals to complete ISO 26262-3 Clause 6.
"""
        
        return result
        
    except Exception as e:
        log.error(f"Error generating HARA table: {e}")
        import traceback
        log.error(traceback.format_exc())
        return f"Error generating HARA table: {str(e)}"
    
@tool(
    return_direct=True,
    examples=[
        "derive detailed safety goals",
        "formulate safety goals",
        "step 5"
    ]
)
def derive_safety_goals(tool_input, cat):
    """ Derive a detailed Safety Goal from a specific hazardous event.
    
    This tool creates ISO 26262-3:2018 Clause 6.4.6 compliant Safety Goals that:
    - Are result-oriented at vehicle level (what to achieve, not how)
    - Include ASIL designation
    - Specify safe state when applicable
    - Include FTTI when time-critical
    
    Input: Hazardous event description or Hazard ID from HARA table"""
    
    log.info("🔧 TOOL CALLED: derive_safety_goals")
    
    # Check prerequisites
    hara_table = cat.working_memory.get("hara_table", "")
    
    if not hara_table:
        return """❌ **No HARA Table Found**

**Please complete Step 4 first:**
`generate hara table`

**Then run:**
`derive detailed safety goals`"""
    
    item_name = cat.working_memory.get("hara_item_name", "Unknown Item")
    
    # Extract ASIL A/B/C/D hazards
    hara_lines = [line for line in hara_table.split('\n') if line.strip().startswith('| HAZ-')]
    asil_hazards = [line for line in hara_lines if re.search(r'ASIL\s*[A-D]', line)]
    
    if not asil_hazards:
        log.info("No ASIL A/B/C/D hazards found")
        return """✅ **HARA Complete - No Safety Goals Needed**

All hazards classified as QM (Quality Management).

**No safety goals required** per ISO 26262-3:2018.

**HARA Status:** Complete! All ISO 26262-3 Clause 6 requirements fulfilled.

**Next Phase:** Functional Safety Concept (ISO 26262-4)"""
    
    log.info(f"Found {len(asil_hazards)} ASIL hazards requiring safety goals")
    
    # Truncate table if too long
    hara_truncated = hara_table[:8000]
    if len(hara_table) > 8000:
        hara_truncated += "\n\n[... table truncated ...]"
    
    prompt = f"""You are a Functional Safety Engineer deriving Safety Goals per ISO 26262-3:2018 Clause 6.4.6.

**System:** {item_name}

# HARA Table

{hara_truncated}

# Your Task

For each hazard with ASIL A, B, C, or D, derive a complete detailed safety goal following ISO 26262 guidelines.

# Safety Goal Requirements (ISO 26262-3:2018)

1. **Result-Oriented**: Focus on WHAT to achieve, not HOW
2. **Directly Linked**: Address the specific hazardous event
3. **ASIL Designation**: Include ASIL level
4. **Safe State**: Specify safe condition to reach
5. **FTTI**: Include when time-critical
6. **Clear Language**: Unambiguous terminology

# Safety Goal Format

**Template:**
[Action Verb] [hazardous event description] [during operational context]. (ASIL X)

**Action Verbs:** Avoid, Ensure, Maintain, Limit

**Format Rules:**
- Start DIRECTLY with action verb (capitalized)
- NO "The [system] shall"
- End with ASIL in parentheses

**Example Analysis:**

**Hazardous Event:** "Cell overcharge leading to thermal runaway and fire"

**Poor Safety Goal (too technical):**
❌ "The BMS shall monitor cell voltage every 10ms and open the main contactor within 50ms if voltage exceeds 4.25V per cell"
*Why poor: Specifies HOW (monitoring rate, voltage threshold, timing) instead of WHAT*

**Good Safety Goal (result-oriented at vehicle level):**
✅ "Avoid unintended wiper stop, avoid cell thermal runaway, avoid unintende acceleration (ASIL D, Safe State: Battery electrically isolated from charger, FTTI: 100ms)"
*Why good: Focuses on preventing the hazard at vehicle level, includes ASIL, safe state, and FTTI*

**More Safety Goal Examples (Correct Format):**

1. "Avoid loss of braking force during highway driving. (ASIL D)"
2. "Prevent steering system lockup during lane changes. (ASIL D)"
3. "Ensure battery isolation in case of internal short circuit. (ASIL D)"
4. "Maintain safe cell voltage range during all charging operations. (ASIL C)"
5. "Limit battery power output to prevent motor overspeed. (ASIL C)"
6. "Avoid unintended airbag deployment during normal driving. (ASIL C)"
7. "Prevent loss of communication between safety-critical ECUs. (ASIL B)"
8. "Ensure wiper activation when requested by driver. (ASIL B)"
9. "Maintain visibility through windscreen during rain. (ASIL B)"
10. "Avoid false fault warnings to driver. (ASIL A)"

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
        log.info("🤖 Generating detailed safety goals...")
        safety_goals = cat.llm(prompt).strip()
        
        # Store results
        cat.working_memory["safety_goals"] = safety_goals
        cat.working_memory["hara_stage"] = "safety_goals_derived"
        
        log.info(f"✅ Safety goals derived for {len(asil_hazards)} hazards")
        
        return f"""✅ **Safety Goals Derived: {item_name}**

**ASIL Hazards:** {len(asil_hazards)}

{safety_goals}

---

**Progress:** 5/5 Steps Complete ✅

**HARA Status:** COMPLETE!

**ISO 26262-3:2018 Compliance:**
- ✅ Clause 6.4.2: Situation analysis
- ✅ Clause 6.4.3: Hazard identification
- ✅ Clause 6.4.4: Risk classification
- ✅ Clause 6.4.5: ASIL determination
- ✅ Clause 6.4.6: Safety goal determination

**Deliverables Ready:**
1. HAZOP analysis table
2. Exposure assessment table
3. Complete HARA table (12 columns)
4. Detailed safety goals document

**Next Phase:** Functional Safety Concept (ISO 26262-4 Clause 6)

**Export:** Use Output Formatter plugin to generate Word/Excel documents"""
    
    except Exception as e:
        log.error(f"Safety goals derivation failed: {e}")
        return f"""❌ **Safety Goals Derivation Failed**

Error: {e}

**Try:**
- Check HARA table is valid
- Reduce number of ASIL hazards
- Verify LLM service availability"""


@tool(
    return_direct=True,
    examples=[
        "show operational situations",
        "list available scenarios",
        "what scenarios are available"
    ]
)
def show_scenarios(tool_input, cat):
    """Display available operational situations by category.
    Input: optional category filter (urban/highway/environmental/special/critical/states).
    Returns organized list of scenarios with exposure levels."""
    
    log.info("🔧 TOOL CALLED: show_scenarios")
    
    category_filter = str(tool_input).strip().lower() if tool_input else None
    
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return """❌ **Operational Situations Database Missing**

Database file not found.

**Check:**
- File exists: `templates/operational_situations.json`
- Plugin correctly installed
- File permissions correct"""
    
    # Build scenario listing
    output_lines = ["# Operational Situations Database\n"]
    
    for category_key, category_data in situations_data.items():
        if category_key == "metadata":
            continue
        
        category_name = category_data.get("name", category_key)
        
        # Apply filter if specified
        if category_filter and category_filter not in category_key.lower():
            continue
        
        output_lines.append(f"\n## {category_name}\n")
        
        for situation in category_data.get("situations", []):
            situation_id = situation.get("id", "")
            name = situation.get("name", "")
            exposure = situation.get("exposure", "")
            description = situation.get("description", "")
            
            output_lines.append(f"**{situation_id}**: {name} ({exposure})")
            output_lines.append(f"  {description}\n")
    
    result = "\n".join(output_lines)
    
    log.info(f"✅ Scenarios displayed: {category_filter or 'all categories'}")
    
    return result


# ============================================================================
# LEGACY COMPATIBILITY (optional)
# ============================================================================

# Maintain backward compatibility with old names
extract_functions_from_item_definition = extract_functions
# apply_hazop_analysis = apply_hazop
# assess_exposure_for_all_hazards = assess_exposure
show_operational_situations = show_scenarios