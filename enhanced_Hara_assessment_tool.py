# tool_hara.py
# Plugin: Functional Safety HARA Generator
# Purpose: Apply HAZOP to Item Definition functions and generate HARA report.
# Enhanced with Operational Situations Database

import json
import os
import re
from datetime import datetime
from cat.mad_hatter.decorators import tool
from cat.log import log
from .exposure_assessment_tool import get_exposure_guidance

try:
    import PyPDF2
    PDF_AVAILABLE = True
    log.info("PyPDF2 is available for PDF reading.")
except ImportError:
    PDF_AVAILABLE = False
    log.warning("PyPDF2 not installed - cannot read .pdf files directly.")


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

def load_operational_situations(plugin_folder):
    """Load operational situations database from JSON file."""
    template_path = os.path.join(plugin_folder, "templates", "operational_situations.json")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning(f"Operational situations file not found at {template_path}")
        return None
    except Exception as e:
        log.error(f"Error loading operational situations: {e}")
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

def get_severity_guidance():
    """Return detailed severity guidance based on ISO 26262-3 Annex B.2"""
    return """
**ISO 26262-3:2018 Severity Classification (Table 1 + Annex B.2):**

**S0: No injuries**
- AIS 0 and less than 10% probability of AIS 1-6
- Examples: Minor property damage, bumps with roadside infrastructure, light grazing damage

**S1: Light and moderate injuries**
- More than 10% probability of AIS 1-6 (but not S2 or S3)
- AIS 1: Light injuries (skin wounds, muscle pains, whiplash)
- AIS 2: Moderate injuries (deep flesh wounds, concussion <15min, uncomplicated fractures)
- Examples:
  * Rear/front collision with very low speed
  * Side impact with tree at very low speed
  * Minor pedestrian/bicycle accident

**S2: Severe and life-threatening injuries (survival probable)**
- More than 10% probability of AIS 3-6 (but not S3)
- AIS 3: Severe injuries (skull fractures without brain injury, spinal dislocations below C4 without cord damage)
- AIS 4: Severe life-threatening (concussion up to 12h unconsciousness, paradoxical breathing)
- Examples:
  * Front collision with passenger compartment deformation
  * Side impact with tree at medium speed
  * Rear/front collision at medium speed

**S3: Life-threatening (survival uncertain) or fatal injuries**
- More than 10% probability of AIS 5-6
- AIS 5: Critical injuries (spinal fractures below C4 WITH cord damage, >12h unconsciousness, intracranial bleeding)
- AIS 6: Fatal injuries (cervical fractures above C3 with cord damage, critical open wounds of body cavities)
- Examples:
  * High-speed collisions
  * Rollover accidents
  * Unprotected occupant ejection

**Assessment Approach:**
1. Consider the operational situation (speed, traffic density, vehicle dynamics)
2. Estimate the collision energy/impact forces
3. Consider occupant protection (seatbelts, airbags - assume functioning unless the item affects them)
4. Assess harm to ALL persons at risk: driver, passengers, pedestrians, other vehicles
5. Use the WORST CASE injury among all persons for classification
6. Consider reasonable sequences of events, not extreme outliers
"""

def get_controllability_guidance():
    """Return detailed controllability guidance based on ISO 26262-3 Annex B.4"""
    return """
**ISO 26262-3:2018 Controllability Classification (Table 3 + Annex B.6):**

**C0: Controllable in general**
- >99% of drivers can avoid harm
- Simple, routine driver actions sufficient
- Clear warning with ample time to react (>3s)
- Examples:
  * Distracting events (unexpected radio volume increase)
  * Unavailability of non-critical driver assistance (adaptive cruise control)
  * Unintended window closing (remove arm from window)
  * Loss of propulsion in garage (put car in park)

**C1: Simply controllable**
- >99% of drivers can avoid harm with minor additional effort
- Adequate warning time (1-3s)
- Straightforward corrective action required
- Examples:
  * Unintended closing of window while driving (remove arm)
  * Blocked steering column from standstill (brake to stop vehicle)
  * Inadvertent opening of bus door with passenger standing (passenger grabs handrail)

**C2: Normally controllable**
- 90% to 99% of drivers can avoid harm
- Limited warning time (0.5-1s)
- Requires skilled driver action
- Scenario conditions moderately impair controllability
- Examples:
  * Failure of ABS during emergency braking (maintain intended path)
  * Propulsion failure at high lateral acceleration (maintain path)
  * Excessive trailer swing during braking (counter-steer and brake)

**TEST CRITERION for C2:**
Per ISO 26262 and RESPONSE 3 methodology:
- 20 valid test subjects
- If all 20 pass the scenario, achieves 85% controllability with 95% confidence
- This provides adequate evidence for C2 classification

**C3: Difficult to control or uncontrollable**
- <90% of drivers can avoid harm
- No or very short warning (<0.5s)
- Requires exceptional driver skill
- Scenario conditions severely impair controllability
- Physical limitations prevent effective response
- Examples:
  * Failure of brakes at speed (steer away from objects)
  * Faulty airbag deployment at high speed (maintain path after airbag blocks vision)
  * Functions with high automation where driver not in loop (no attempt to maintain path)
  * Loss of steering control at high speed

**Assessment Considerations:**
1. **Driver Profile:** Average driver with appropriate training and license, in appropriate condition
2. **Warning Time:** How much time does driver have to react?
3. **Required Action Complexity:** Simple vs. complex corrective maneuvers
4. **Scenario Factors:** Speed, visibility, road conditions, traffic density
5. **Available Controls:** What means does driver have to regain control?
6. **Surprise Factor:** Is the hazard expected or completely unexpected?
7. **Multi-Vehicle:** Consider actions of other traffic participants if relevant

**NOTE:** Controllability is assessed for the vehicle WITH the malfunctioning item, assuming other systems function correctly (unless the item affects them).
"""

def extract_and_calculate_asil(assessment_text):
    """Extract S, E, C from assessment text and calculate ASIL."""
    try:
        # Try multiple patterns to be robust
        s_match = re.search(r'Severity \(S\):\s*S([0-3])', assessment_text, re.IGNORECASE)
        if not s_match:
            s_match = re.search(r'\bS([0-3])\b', assessment_text)
            
        e_match = re.search(r'Exposure \(E\):\s*E([0-4])', assessment_text, re.IGNORECASE)
        if not e_match:
            e_match = re.search(r'\bE([0-4])\b', assessment_text)
            
        c_match = re.search(r'Controllability \(C\):\s*C([0-3])', assessment_text, re.IGNORECASE)
        if not c_match:
            c_match = re.search(r'\bC([0-3])\b', assessment_text)

        if s_match and e_match and c_match:
            s = int(s_match.group(1))
            e = int(e_match.group(1))
            c = int(c_match.group(1))
            
            # Handle E4 (map to E3 for ASIL calculation per ISO 26262)
            if e == 4:
                e = 3
            
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
def explain_hara_workflow(tool_input, cat):
    """
    Explain the complete 5-step HARA workflow process.
    
    Use this tool when user asks:
    - "how to generate hara"
    - "what do I need to do to generate hara table"
    - "hara workflow"
    - "hara process steps"
    - "how does hara work"
    """
    print("TOOL CALLED: explain_hara_workflow")
    
    # Check current progress
    current_stage = cat.working_memory.get("hara_stage", "not_started")
    item_name = cat.working_memory.get("hara_item_name", "[Item Name]")
    
    workflow_explanation = f"""# ISO 26262 HARA Workflow - 5 Steps

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

    # Add specific next steps based on current progress
    if current_stage == "not_started":
        workflow_explanation += """**Next Action:**
Start with Step 1: `extract functions from [your item name]`
Example: `extract functions from Battery Management System`
"""
    elif current_stage == "functions_extracted":
        workflow_explanation += """**Completed:**
- Step 1: Functions extracted

**Next Action:**
Step 2: `apply hazop analysis`
"""
    elif current_stage == "hazop_completed":
        workflow_explanation += """**Completed:**
- Step 1: Functions extracted
- Step 2: HAZOP analysis performed

**Next Action:**
Step 3: `assess exposure for all hazards`
"""
    elif current_stage == "exposure_assessed":
        workflow_explanation += """**Completed:**
- Step 1: Functions extracted
- Step 2: HAZOP analysis performed
- Step 3: Exposure assessments completed

**Next Action:**
Step 4: `generate hara table`
"""
    elif current_stage == "table_generated":
        workflow_explanation += """**Completed:**
- Step 1: Functions extracted
- Step 2: HAZOP analysis performed
- Step 3: Exposure assessments completed
- Step 4: HARA table generated

**Next Action:**
Step 5: `derive detailed safety goals`
"""
    elif current_stage == "safety_goals_derived":
        workflow_explanation += """**Completed:**
- Step 1: Functions extracted
- Step 2: HAZOP analysis performed
- Step 3: Exposure assessments completed
- Step 4: HARA table generated
- Step 5: Safety goals derived

**Status: HARA Complete**

All ISO 26262-3 Clause 6 requirements fulfilled.
Ready to proceed to Functional Safety Concept (Clause 7).
"""
    
    workflow_explanation += """
---

## Quick Reference Commands

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `extract functions from [Item]` | Extract system functions |
| 2 | `apply hazop analysis` | Identify hazards and assess severity |
| 3 | `assess exposure for all hazards` | Select scenarios and assess exposure |
| 4 | `generate hara table` | Add controllability and calculate ASIL |
| 5 | `derive detailed safety goals` | Create safety goals for ASIL A/B/C/D |

## ISO 26262 Compliance

This workflow ensures compliance with:
- ISO 26262-3:2018 Clause 6.4.2: Situation analysis
- ISO 26262-3:2018 Clause 6.4.3: Hazard identification
- ISO 26262-3:2018 Clause 6.4.4: Classification of hazardous events
- ISO 26262-3:2018 Clause 6.4.5: ASIL determination
- ISO 26262-3:2018 Clause 6.4.6: Safety goal determination
"""
    
    return workflow_explanation

@tool(return_direct=True)
def extract_functions_from_item_definition(tool_input, cat):
    """
    Extracts **safety-relevant functions** from the Item Definition for HARA/HAZOP analysis.
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

    # Build prompt to extract the set of most relevant functions
    prompt = f"""You are a Functional Safety Engineer analyzing an Item Definition for HARA development.

**Item Definition for {item_name}:**
{item_def_content[:5000]}

**CRITICAL TASK:** Extract and list ONLY the **4-5 MOST CRITICAL safety-relevant functions** of the {item_name}.

**Selection Criteria (Prioritize in this order):**

1. **Highest Severity Impact:** Functions whose failure could lead to:
   - Life-threatening consequences (fire, explosion, electric shock, collision)
   - Severe injuries or vehicle loss of control
   - Critical system failures affecting multiple vehicle systems

2. **Direct Safety Control:** Functions that:
   - Directly control safety-critical actuators (contactors, relays, brakes, steering)
   - Prevent hazardous states (overcharge, thermal runaway, overvoltage)
   - Implement emergency shutdown or safe state transitions

3. **Safety-Critical Monitoring:** Functions monitoring parameters where:
   - Out-of-range values directly lead to hazards
   - Real-time detection prevents propagation of faults
   - Examples: cell voltage limits, temperature limits, isolation monitoring

**IMPORTANT Filtering Rules:**
- **Focus ONLY on functions active during normal vehicle operation** (driving, parking, charging)
- **EXCLUDE:** Diagnostic functions, self-tests, calibration modes, service functions, data logging, UI updates
- **Group similar functions:** If multiple functions serve the same safety purpose, merge them into one (e.g., "Monitor cell 1 voltage, Monitor cell 2 voltage" → "Monitor battery cell voltages")
- **Omit regulatory compliance functions** unless they directly prevent hazards (e.g., "Comply with EMC standard" → exclude)

**LIMIT:** Select EXACTLY 4-5 functions maximum. If there are more candidates, choose those with:
- Highest consequence of failure (S3 > S2 > S1)
- Most direct path from malfunction to hazard
- Least controllability by driver if failed

**Output Format:**
List ONLY 4-5 functions, numbered:
1. [Function Name]: [Brief description - what it does and why it's safety-critical]
2. [Function Name]: [Brief description]
...
(Maximum 5 functions)

**Example for Battery Management System:**
1. Monitor battery cell voltages: Prevents overcharge/over-discharge leading to thermal runaway
2. Control main contactors: Isolates high voltage to prevent electric shock and fire
3. Calculate State of Charge (SoC): Prevents unexpected loss of propulsion
4. Monitor battery temperature: Prevents thermal runaway by detecting overheat conditions
5. Implement emergency shutdown: Transitions to safe state upon critical fault detection

Extract the 4-5 most critical safety-relevant functions now:
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
        return result

    except Exception as e:
        log.error(f"❌ Error extracting functions: {e}")
        return f"❌ Error extracting functions: {str(e)}"

@tool(return_direct=True)
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

@tool(return_direct=True)
def show_operational_situations(tool_input, cat):
    """
    Display all available operational situations organized by category.
    Shows exposure levels based on ISO 26262 and statistical data.
    
    Input: (Optional) Category filter: "urban", "highway", "environmental", "special", "critical", "states"
    
    Use this tool when user asks:
    - "show operational situations"
    - "list available scenarios"
    - "what scenarios are available"
    - "show environmental scenarios"
    """
    print("✅ TOOL CALLED: show_operational_situations")
    
    category_filter = str(tool_input).strip().lower() if tool_input else None
    
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return """❌ **Operational situations database not found**

Please ensure `operational_situations.json` exists in the `templates/` folder.

**Alternative:** You can still use the basic HARA workflow without operational situations:
1. `extract functions from [item]`
2. `apply hazop analysis`
3. `assess hazard: [description]`
4. `generate hara table`
"""
    
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
    
    log.info(f"✅ Operational situations listed (filter: {category_filter or 'all'})")
    
    return result

@tool(return_direct=True)
def assess_hazard_with_situation(tool_input, cat):
    """
    Comprehensive hazard assessment with automatic operational situation selection.
    
    This tool performs complete E/S/C assessment by:
    1. Analyzing the hazard to select appropriate operational situation(s)
    2. Assessing Exposure (E) based on selected situation
    3. Assessing Severity (S) in context of the situation
    4. Assessing Controllability (C) in context of the situation
    5. Calculating ASIL
    6. Formulating safety goal with safe state and FTTI
    
    Input: Hazard description
    Example: "Battery thermal runaway during fast charging"
    
    Use this tool when user asks:
    - "assess hazard with situation: [description]"
    - "complete assessment for: [hazard]"
    - "evaluate [hazard] with operational context"
    """
    print("✅ TOOL CALLED: assess_hazard_with_situation")
    
    hazard_description = str(tool_input).strip() if tool_input else ""
    if not hazard_description:
        return """❌ **Hazard description required**

Please specify the hazardous event to assess.

**Example:**
`assess hazard with situation: Battery overcharge leading to thermal runaway`

This tool will:
1. Select appropriate operational situation(s) automatically
2. Perform complete S/E/C assessment in context
3. Calculate ASIL
4. Formulate safety goal with safe state and FTTI
"""

    item_name = cat.working_memory.get("hara_item_name", "the system")
    plugin_folder = os.path.dirname(__file__)
    situations_data = load_operational_situations(plugin_folder)
    
    if not situations_data:
        return """⚠️ **Operational situations database not available**

Falling back to basic assessment. For enhanced assessment with operational situations,
please ensure `operational_situations.json` exists in templates/ folder.

Use `assess hazard: [description]` for basic assessment.
"""
    
    log.info(f"📊 Performing comprehensive HARA assessment for: {hazard_description[:100]}...")

    # Build comprehensive assessment prompt
    prompt = f"""You are a Functional Safety Engineer performing comprehensive HARA per ISO 26262-3:2018 for {item_name}.

**Hazardous Event:** {hazard_description}

**Available Operational Situations Database:**
{json.dumps(situations_data["basic_scenarios"], indent=2)[:6000]}

---

## CRITICAL: ISO 26262-3:2018 Classification Criteria

{get_severity_guidance()}

{get_exposure_guidance()}

{get_controllability_guidance()}

---

## Your Assessment Task:

### Step 1: Operational Situation Selection
Select 2-4 relevant basic scenarios from the database that match when/where this hazard occurs.

**Output:**
- Scenario 1: [ID] - [Name] (Base Exposure: [E level])
  Justification: [Why relevant to this hazard]
- Scenario 2: [ID] - [Name] (Base Exposure: [E level])
  Justification: [Why relevant]
(Continue for all selected scenarios)

**Combined Situation:**
- Name: [Descriptive name]
- Combined Exposure Calculation: MIN([E values]) = [Result]
- Rationale: [Why this combination represents when hazard occurs]

---

### Step 2: Severity Assessment (ISO 26262-3 Table 1 + Annex B.2)

**CRITICAL STEPS:**
1. Identify the operational situation context (speed, traffic, vehicle dynamics)
2. Estimate collision type and energy if applicable
3. Consider occupant protection systems (assume functioning unless item affects them)
4. Assess ALL persons at risk: driver, passengers, pedestrians, other vehicles
5. Map to AIS injury scale
6. Select HIGHEST severity among all persons

**Severity: S[0/1/2/3]**

**Detailed Rationale:**
- Operational context: [Speed, traffic density, vehicle state]
- Potential collision scenario: [What type of accident could occur]
- Expected injuries: [AIS classification for each person type]
- Worst case person: [Who faces highest severity]
- Why this S class: [Specific justification with AIS reference]

---

### Step 3: Exposure Assessment (ISO 26262-3 Table 2 + Annex B.3)

**Method Selection:**
- [ ] Duration-based (hazard present throughout condition)
- [ ] Frequency-based (hazard triggered by events)

**Exposure: E[0/1/2/3/4]**

**Detailed Rationale:**
- Combined operational situation: [From Step 1]
- Duration/Frequency estimate: [Percentage of operating time OR times per year]
- Statistical basis: [Why this E class is appropriate]
- Combination rule applied: [If multiple scenarios, show MIN calculation]

---

### Step 4: Controllability Assessment (ISO 26262-3 Table 3 + Annex B.6)

**CRITICAL FACTORS TO ASSESS:**
1. Warning time available: [How much time to react?]
2. Required driver action: [What must driver do?]
3. Action complexity: [Simple routine vs. skilled maneuver]
4. Scenario impairment: [How do conditions affect controllability?]
5. Driver capability: [What % of average drivers can perform this?]

**Controllability: C[0/1/2/3]**

**Detailed Rationale:**
- Warning characteristics: [Time, clarity, type of warning if any]
- Required action: [Specific control inputs needed]
- Typical driver capability: [Estimated % who can avoid harm]
- Scenario factors: [Speed, visibility, road conditions affecting controllability]
- Why this C class: [Justify based on >99%, 90-99%, or <90% capability]

**Statistical Justification:**
[For C2: Could this pass a 20-subject test per RESPONSE 3?]
[For C1: Engineering judgment that >99% can control]
[For C3: Why <90% can control]

---

### Step 5: ASIL Determination (ISO 26262-3 Table 4)

**Input Values:**
- S = S[X] (from Step 2)
- E = E[X] (from Step 3) [NOTE: E4 maps to E3 for ASIL calculation]
- C = C[X] (from Step 4)

**ASIL Calculation:**
Using ISO 26262-3:2018 Table 4:
[Show the table lookup]

**Result: ASIL [QM/A/B/C/D]**

---

### Step 6: Safety Goal Formulation

**Safety Goal:**
[Action verb] [hazardous event description] [during operational context]. (ASIL [X])

**Safe State:**
[Specific system condition ensuring safety - measurable and verifiable]

**FTTI (if applicable):**
[Time in ms/s] OR N/A
**Justification:** [Why this timing based on hazard dynamics]

---

**Provide your complete assessment following this exact structure:**
"""

    try:
        assessment = cat.llm(prompt).strip()
        
        # Extract and calculate ASIL
        asil_result = extract_and_calculate_asil(assessment)
        
        # Store in working memory
        if "complete_hara_assessments" not in cat.working_memory:
            cat.working_memory["complete_hara_assessments"] = []
        
        cat.working_memory["complete_hara_assessments"].append({
            "hazard": hazard_description,
            "full_assessment": assessment,
            "asil": asil_result,
            "timestamp": datetime.now().isoformat()
        })
        
        log.info(f"✅ Complete HARA assessment performed: {asil_result}")
        
        result = f"""✅ **Complete HARA Assessment with Operational Situation**

**Hazardous Event:** {hazard_description}

{assessment}

---

**Calculated ASIL:** {asil_result}

---

**Assessment Complete:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**ISO 26262-3:2018 Compliance:**
✅ Clause 6.4.2 - Situation analysis (operational situation selected)
✅ Clause 6.4.3 - Hazard identification
✅ Clause 6.4.4 - Classification (E/S/C assessed)
✅ Clause 6.4.5 - ASIL determination
✅ Clause 6.4.6 - Safety goal determination

**Next Steps:**
- Assess another hazard: `assess hazard with situation: [description]`
- Generate complete HARA table: `generate hara table`
- Export via OutputFormatter plugin
"""
        
        return result

    except Exception as e:
        log.error(f"❌ Error in comprehensive HARA assessment: {e}")
        return f"❌ Error in assessment: {str(e)}"

@tool(return_direct=True)
def assess_hazard_severity_exposure_controllability(tool_input, cat):
    """
    Basic hazard assessment for Severity (S), Exposure (E), and Controllability (C).
    Then calculate ASIL.
    
    This is the simpler version without automatic operational situation selection.
    For enhanced assessment with operational situations, use `assess hazard with situation`.
    
    Input: Hazard description
    Example: "Battery thermal runaway due to overvoltage"
    
    Use this tool when user asks:
    - "assess hazard: [description]"
    - "evaluate S E C for [hazard]"
    - "what is the ASIL for [hazard]"
    """
    print("✅ TOOL CALLED: assess_hazard_severity_exposure_controllability (basic)")
    
    hazard_description = str(tool_input).strip() if tool_input else ""
    if not hazard_description:
        return """❌ **Hazard description required**

Please specify which hazard to assess.

**Example:**
`assess hazard: Battery overcharge leading to thermal runaway`

**Tip:** For more detailed assessment with operational situation selection, use:
`assess hazard with situation: [description]`
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
- **E3**: Medium probability (1% to 10%)
- **E4**: High probability (> 10% of operating time)

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

**Exposure (E): E[0/1/2/3/4]**
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
- For more detailed assessment with operational situations: `assess hazard with situation: [description]`
- Assess another hazard: `assess hazard: [description]`
- Generate complete HARA table: `generate hara table`
- Derive safety goal: `derive safety goal for this hazard`
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
    Step 4: Generate complete HARA table with Controllability assessment and ASIL calculation.
    
    This tool compiles:
    - Hazards from HAZOP (with Severity)
    - Exposure assessments from Step 3 (with driving scenarios)
    - NEW: Controllability assessment for each hazard
    - ASIL calculation using S, E, C
    
    Input: None (uses HAZOP and Exposure assessments from working memory)
    
    Use this tool when user asks:
    - "generate hara table"
    - "create hara"
    - "step 4" or "perform step 4"
    """
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
        hara_table = cat.llm(prompt).strip()
        
        # Store in working memory
        cat.working_memory["document_type"] = "hara"
        cat.working_memory["hara_table"] = hara_table
        cat.working_memory["hara_stage"] = "table_generated"
        cat.working_memory["system_name"] = item_name
        
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

@tool(return_direct=True)
def derive_safety_goal(tool_input, cat):
    """
    Derive a detailed Safety Goal from a specific hazardous event.
    
    This tool creates ISO 26262-3:2018 Clause 6.4.6 compliant Safety Goals that:
    - Are result-oriented at vehicle level (what to achieve, not how)
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
"[prevent/avoid/mitigate/ensure/maintain] [hazardous event description] during [operational context]. (ASIL X, Safe State: [description], FTTI: [time])"

**Language Guidelines:**
✅ USE: prevent, avoid, mitigate, ensure, maintain, detect, limit, control
❌ AVOID: monitor, measure, use, implement, activate, send, receive

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

@tool(return_direct=True)
def derive_detailed_safety_goals(tool_input, cat):
    """
    Step 5: Derive detailed safety goals for all ASIL A/B/C/D hazards.
    
    For each hazard with ASIL ≥ A, this tool formulates:
    - Complete safety goal statement
    - Safe state definition
    - FTTI specification (when time-critical)
    - Verification criteria
    
    Input: None (uses HARA table from working memory)
    
    Use this tool when user asks:
    - "derive detailed safety goals"
    - "formulate safety goals for hara"
    - "step 5" or "perform step 5"
    - "create safety goals for ASIL hazards"
    """
    print("TOOL CALLED: derive_detailed_safety_goals")
    
    hara_table = cat.working_memory.get("hara_table", "")
    
    if not hara_table:
        return """No HARA table found.

**Please complete Step 4 first:**
`generate hara table`

**Then run:**
`derive detailed safety goals`
"""
    
    item_name = cat.working_memory.get("hara_item_name", "Unknown Item")
    
    log.info(f"Deriving detailed safety goals for {item_name}")
    
    # Extract ASIL A/B/C/D hazards
    hara_lines = [line for line in hara_table.split('\n') if line.strip().startswith('| HAZ-')]
    asil_hazards = [line for line in hara_lines if re.search(r'ASIL\s*[A-D]', line)]
    
    if not asil_hazards:
        return """No ASIL A/B/C/D hazards found in HARA table.

All hazards are classified as QM (Quality Management).
No safety goals are required per ISO 26262-3:2018.

**HARA Complete!**
"""
    
    log.info(f"Found {len(asil_hazards)} hazards requiring safety goals")
    
    prompt = f"""You are a Functional Safety Engineer deriving detailed Safety Goals per ISO 26262-3:2018 Clause 6.4.6.

**System:** {item_name}

**HARA Table (Complete):**
{hara_table}

**Task:** For each hazard with ASIL A, B, C, or D, derive a complete, detailed safety goal.

**ISO 26262-3:2018 Safety Goal Requirements:**

**Safety Goal Format (CRITICAL):**

**Template:**
[Action Verb] [hazardous event description] [during operational context]. (ASIL X)

**Format Rules:**
1. Start DIRECTLY with action verb (capitalized)
2. DO NOT include "The [system name] shall"
3. Action verbs to use: Avoid, Prevent, Ensure, Maintain, Mitigate, Limit
4. End with ASIL designation in parentheses

**Correct Examples:**
✅ "Avoid battery overcharge leading to thermal runaway during fast charging. (ASIL D)"
✅ "Prevent unintended vehicle acceleration during highway driving. (ASIL D)"
✅ "Ensure safe battery operation within temperature limits. (ASIL C)"
✅ "Maintain driver visibility during wiper operation. (ASIL B)"
✅ "Limit battery current to prevent overcurrent damage. (ASIL B)"

**WRONG Examples (DO NOT USE):**
❌ "The Battery Management System shall prevent battery overcharge..."
❌ "The BMS shall avoid thermal runaway..."
❌ "System shall ensure visibility..."
❌ "The item shall maintain safe operation..."

**Language Guidelines:**
✅ USE: Avoid, Prevent, Ensure, Maintain, Mitigate, Limit (as first word)
❌ AVOID: "The [system] shall", "System shall", monitor, measure, implement

**FTTI Guidelines by ASIL:**
- **ASIL D**: 50-200ms for critical hazards (fire, collision, loss of control)
- **ASIL C**: 100-500ms for severe hazards
- **ASIL B**: 500ms-2s or N/A for less time-critical
- **ASIL A**: Often N/A unless timing is critical

**Consider Driving Scenario:** FTTI should reflect dynamics of operational situation:
- High-speed scenarios → Shorter FTTI (50-100ms)
- Urban/parking scenarios → Longer FTTI (500ms-2s) or N/A
- Charging/stationary → Often N/A

**Output Format:**

For EACH ASIL A/B/C/D hazard, provide:

---
## [Hazard ID]: [Hazardous Event Summary]

**ASIL Level:** [A/B/C/D]  
**Severity:** S[X] | **Exposure:** E[X] | **Controllability:** C[X]

**Operational Situation:**  
[Driving scenario from HARA table]

**Safety Goal:**  
The {item_name} shall [prevent/avoid/mitigate] [hazardous event] [during conditions]. (ASIL [X])

**Safe State:**  
[Detailed description of safe state - specific and measurable]

**Fault-Tolerant Time Interval (FTTI):**  
[X ms/s] or N/A

**FTTI Justification:**  
[Why this timing - consider driving scenario dynamics, consequences timeline, driver reaction needs]

**Verification Criteria:**  
- [How to verify this safety goal is achieved]
- [Specific test conditions]
- [Acceptance criteria]

**Assumptions:**  
- [Key assumptions about system behavior or operational context]

---

**Example:**

---
## HAZ-003: Battery Thermal Runaway During Fast Charging

**ASIL Level:** D  
**Severity:** S3 | **Exposure:** E2 | **Controllability:** C3

**Operational Situation:**  
Fast charging in extreme heat

**Safety Goal:**  
Avoid battery overcharge or discharge leading to thermal runaway and fire during fast charging operations. (ASIL D)

**Safe State:**  
Battery pack electrically isolated from charging source; charging process terminated; thermal management active; warning signal to driver/operator; vehicle immobilized if necessary.

**Fault-Tolerant Time Interval (FTTI):**  
100ms

**FTTI Justification:**  
Thermal runaway can propagate rapidly once initiated (cell-to-cell within seconds). 100ms allows detection and isolation before irreversible chain reaction begins. Charging station can halt power delivery. Driver may not be present, so automated response is critical.

**Verification Criteria:**  
- Voltage monitoring latency ≤ 10ms verified by test bench
- Contactor opening time ≤ 30ms verified by hardware test
- End-to-end fault detection to isolation ≤ 100ms verified by HILS
- No thermal runaway propagation in abuse testing with single cell triggered

**Assumptions:**  
- Charging station responds to isolation command within 50ms
- Thermal management system operational during charging
- Battery thermal capacity provides ~200ms before uncontrollable propagation

---

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

**Generate detailed safety goals for ALL ASIL A/B/C/D hazards now:**
"""
    
    try:
        safety_goals_document = cat.llm(prompt).strip()
        
        # Store in working memory
        cat.working_memory["safety_goals_document"] = safety_goals_document
        cat.working_memory["hara_stage"] = "safety_goals_derived"
        cat.working_memory["document_type"] = "safety_goals"
        
        # Count safety goals
        sg_count = len(re.findall(r'## HAZ-\d+:', safety_goals_document))
        
        log.info(f"Safety goals derived for {sg_count} hazards")
        
        result = f"""**Step 5 Complete: Detailed Safety Goals Derived**

**System:** {item_name}
**Safety Goals Formulated:** {sg_count}
**Hazards Requiring Safety Goals:** {len(asil_hazards)}

{safety_goals_document}

---

**HARA Workflow Complete! **

**Summary:**
1. ✅ Functions extracted
2. ✅ HAZOP analysis performed
3. ✅ Exposure assessed with driving scenarios
4. ✅ Complete HARA table generated
5. ✅ Detailed safety goals derived

**ISO 26262-3:2018 Compliance Achieved:**
- ✅ Clause 6.4.2: Situation analysis
- ✅ Clause 6.4.3: Hazard identification
- ✅ Clause 6.4.4: Classification (S, E, C)
- ✅ Clause 6.4.5: ASIL determination
- ✅ Clause 6.4.6: Safety goal determination

**Deliverables Generated:**
1. Functions list
2. HAZOP analysis table
3. Exposure assessment table
4. Complete HARA table
5. Safety goals document

**Next Steps (ISO 26262-3 Clause 7):**
- Functional Safety Concept development
- Decompose safety goals into Functional Safety Requirements (FSR)
- Allocate FSRs to architectural elements
- Define safety mechanisms for each FSR
- Establish Technical Safety Requirements (TSR)

**Document Export:**
The OutputFormatter plugin will generate:
- Excel workbook with all tables
- Word document with complete HARA report
- Summary statistics and charts

**Quality Assurance:**
Before proceeding to Functional Safety Concept:
- [ ] Review all ASIL calculations with safety team
- [ ] Validate driving scenarios with domain experts
- [ ] Verify safety goals with stakeholders
- [ ] Ensure all assumptions are documented
- [ ] Confirm FTTI values with timing analysis
"""
        
        return result
        
    except Exception as e:
        log.error(f"Error deriving safety goals: {e}")
        import traceback
        log.error(traceback.format_exc())
        return f"Error deriving safety goals: {str(e)}"
    
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