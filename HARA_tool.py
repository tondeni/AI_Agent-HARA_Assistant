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
    """Find Item Definition content in working memory or related plugin folders."""
    
    # 1. Check working memory first (most likely place after Item Def generation)
    if "item_definition_content" in cat.working_memory:
        log.info("Found Item Definition in working memory.")
        return cat.working_memory["item_definition_content"]

    # 2. Fallback: Search in known plugin output folders (if not in memory)
    plugin_folder = os.path.dirname(__file__)
    # Common locations where Item Definition plugins might save content
    possible_paths = [
        os.path.join(plugin_folder, "..", "AI_Agent-OutputFormatter", "generated_documents", "01_Item_Definition"),
        os.path.join(plugin_folder, "..", "AI_Agent-ItemDefinition_Developer", "generated_definitions"),
        os.path.join(plugin_folder, "item_definitions"), # Local storage option
    ]

    for folder_path in possible_paths:
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(('.txt', '.md', '.docx')):
                    file_path = os.path.join(folder_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Check if the item name is mentioned in the file content
                        if item_name.lower() in content.lower():
                            log.info(f"Found Item Definition for '{item_name}' in {filename}")
                            return content
                    except Exception as e:
                        log.warning(f"Error reading {file_path}: {e}")

    log.warning(f"No Item Definition found for '{item_name}' in memory or common folders.")
    return None

def extract_and_calculate_asil(assessment_text):
    """Extract S, E, C from assessment text and calculate ASIL."""
    try:
        s_match = re.search(r'Severity \(S\): S([0-3])', assessment_text)
        e_match = re.search(r'Exposure \(E\): E([0-3])', assessment_text)
        c_match = re.search(r'Controllability \(C\): C([0-3])', assessment_text)

        if s_match and e_match and c_match:
            s = int(s_match.group(1))
            e = int(e_match.group(1))
            c = int(c_match.group(1))
            asil = ASILCalculator.calculate_asil(s, e, c)
            return f"ASIL {asil} (S{s}, E{e}, C{c})"
        else:
            log.warning("Could not parse S, E, C values from assessment for ASIL calculation.")
            return "ASIL Calculation Failed"
    except Exception as e:
        log.error(f"Error calculating ASIL: {e}")
        return f"ASIL Calculation Error: {str(e)}"

# --- TOOLS ---

@tool(return_direct=True)
def extract_functions_from_item_definition(tool_input, cat):
    """
    Extracts functions from the Item Definition stored in working memory.
    Input: The name of the item (e.g., "BMS", "Wiper System").
    The Item Definition must already be available.
    """
    print("✅ TOOL CALLED: extract_functions_from_item_definition")
    
    # Parse input
    item_name = "Unknown System"
    if isinstance(tool_input, str):
        item_name = tool_input.strip()
    elif isinstance(tool_input, dict):
        item_name = tool_input.get("item_name", item_name)

    # Find Item Definition content
    item_def_content = find_item_definition(cat, item_name)
    if not item_def_content:
        return f"""⚠️ No Item Definition found for '{item_name}'.
Please ensure the Item Definition has been generated and is available in working memory or the standard plugin output folders."""

    # Build prompt to extract functions
    prompt = f"""
You are a Functional Safety Engineer analyzing an Item Definition for HARA development.

**Item Definition for {item_name}:**


**Task:** Extract and list ALL primary functions of the {item_name} from the Item Definition.
**Instructions:**
- Focus on core functionalities (e.g., monitor, control, communicate, store).
- List each function on a new line.
- Do not include constraints, interfaces, or general descriptions as functions.
- Output only the list of functions, nothing else.

Functions:
"""

    try:
        functions_list = cat.llm(prompt).strip()
        
        # Store results in working memory
        cat.working_memory["hara_item_name"] = item_name
        cat.working_memory["item_functions"] = functions_list
        cat.working_memory["hara_stage"] = "functions_extracted"

        result = f"""✅ **Functions Extracted for {item_name}**
{functions_list}

**Next Steps:**
1. Apply HAZOP guide words: `apply hazop analysis`
2. Or generate HARA table directly: `generate hara table` (uses HAZOP internally)
"""
        return result

    except Exception as e:
        log.error(f"Error extracting functions: {e}")
        return f"❌ Error extracting functions: {str(e)}"


@tool(return_direct=True)
def apply_hazop_analysis(tool_input, cat):
    """
    .
    Input: (Optional) Specific function to focus on, otherwise applies to all functions.
    Requires functions to be in cat.working_memory["item_functions"].
    """
    print("✅ TOOL CALLED: apply_hazop_analysis")
    
    # Check for required data
    functions_text = cat.working_memory.get("item_functions", "")
    item_name = cat.working_memory.get("hara_item_name", "the system")

    if not functions_text:
        return "⚠️ No functions found in memory. Please run 'extract functions from item definition' first."

    # Load HAZOP guide words
    plugin_folder = os.path.dirname(__file__)
    guide_words_data = load_hazop_guidewords(plugin_folder)
    guide_words = guide_words_data.get("hazop_guide_words", {})

    # Build guide word summary for prompt
    guide_words_summary = "\n".join([
        f"**{word}**: {details['meaning']} — {details['description']}"
        for word, details in guide_words.items()
    ])

    prompt = f"""
You are a Functional Safety Engineer performing a HAZOP analysis for {item_name}.

Apply the following HAZOP guide words to each function to identify potential malfunctions.

**HAZOP Guide Words:**
{guide_words_summary}

**Functions to analyze:**
{functions_text}

**Task:** For each function, apply each guide word systematically and generate a potential malfunction scenario.
Example: Function: 'Monitor cell voltage' -> Guide Word: 'NO' -> Malfunction: 'No voltage monitoring occurs'.
Describe the potential hazardous event resulting from each malfunction.

**Output Format:**
List each identified hazard in this structured format:
- Function: [Original Function]
- Guide Word: [Applied Guide Word]
- Malfunction: [Brief explanation of the malfunction]
- Hazardous Event: [The potential hazardous event]

Do not add explanations or notes outside the list.
"""

    try:
        hazop_analysis = cat.llm(prompt).strip()
        
        # Store HAZOP results in working memory
        cat.working_memory["hazop_analysis"] = hazop_analysis
        cat.working_memory["hara_stage"] = "hazop_performed"

        log.info("HAZOP analysis completed and stored in working memory.")
        result = f"""✅ **HAZOP Analysis Completed for {item_name}**
{hazop_analysis}

**Next Steps:**
1. Assess specific hazards: `assess hazard severity exposure controllability for [description]`
2. Generate full HARA table: `generate hara table`
"""
        return result

    except Exception as e:
        log.error(f"Error during HAZOP analysis: {e}")
        return f"❌ Error during HAZOP analysis: {str(e)}"


@tool(return_direct=True)
def assess_hazard_severity_exposure_controllability(tool_input, cat):
    """
    Assesses S, E, C for a given hazard description and calculates ASIL.
    Input: A string describing the hazard (e.g., "Battery thermal runaway due to overvoltage").
    """
    print("✅ TOOL CALLED: assess_hazard_severity_exposure_controllability")
    
    hazard_description = str(tool_input).strip() if tool_input else ""
    if not hazard_description:
        return "❌ Error: Hazard description is required for S/E/C assessment."

    item_name = cat.working_memory.get("hara_item_name", "the item")

    prompt = f"""
You are a Functional Safety Engineer assessing risk per ISO 26262-3:2018 for {item_name}.

**Hazard to Assess:**
{hazard_description}

**Context (Item):**
{item_name}

**Task:** Assess Severity (S), Exposure (E), and Controllability (C) for this hazard.
Use ISO 26262-3:2018 definitions:
- **Severity (S):** S0 (no injury), S1 (light/moderate), S2 (severe), S3 (fatal)
- **Exposure (E):** E0 (inconceivable), E1 (low), E2 (medium), E3 (high)
- **Controllability (C):** C0 (controllable), C1 (simply controllable), C2 (normally controllable), C3 (difficult/uncontrollable)

**Provide your assessment with a clear rationale for each rating:**
- **Severity (S):** [Rating] - Rationale: [Why this rating was chosen based on potential harm]
- **Exposure (E):** [Rating] - Rationale: [Why this rating was chosen based on operational scenario frequency]
- **Controllability (C):** [Rating] - Rationale: [Why this rating was chosen based on driver/system ability to mitigate]

Response Format:
Severity (S): [S0/S1/S2/S3] - Rationale: ...
Exposure (E): [E0/E1/E2/E3] - Rationale: ...
Controllability (C): [C0/C1/C2/C3] - Rationale: ...
"""

    try:
        assessment = cat.llm(prompt).strip()
        
        # Calculate ASIL based on the assessment
        asil_result = extract_and_calculate_asil(assessment)
        final_output = f"{assessment}\n\n**Calculated ASIL: {asil_result}**"
        
        # Optionally store individual assessments if needed later
        # cat.working_memory["current_hazard_assessment"] = final_output 

        return final_output

    except Exception as e:
        log.error(f"Error assessing hazard S/E/C: {e}")
        return f"❌ Error assessing hazard: {str(e)}"


@tool(return_direct=True)
def generate_hara_table(tool_input, cat):
    """
    Generates the final HARA report as a markdown table.
    It uses the HAZOP analysis and item name stored in working memory.
    """
    print("✅ TOOL CALLED: generate_hara_table")
    
    hazop_analysis = cat.working_memory.get("hazop_analysis", "")
    item_name = cat.working_memory.get("hara_item_name", "Unknown Item")

    if not hazop_analysis:
        return "⚠️ No HAZOP analysis found in memory. Please run 'apply hazop analysis' first (or 'extract functions' if HAZOP hasn't been run)."

    prompt = f"""
You are a Functional Safety Engineer compiling the final HARA report for {item_name}.

**HAZOP Analysis Results:**
{hazop_analysis}

**Task:** Create a complete HARA table in markdown format with the following columns:
| Hazard ID | Hazardous Event | Operational Situation | Severity (S) | Exposure (E) | Controllability (C) | ASIL | Safety Goal |

**Instructions for LLM:**
1.  Parse the HAZOP analysis to identify distinct malfunction scenarios and their potential hazardous events.
2.  Derive a plausible operational situation where the hazard could occur (e.g., "Highway driving", "Charging").
3.  Assign S, E, C ratings based on ISO 26262-3:2018 principles (you are an expert). Provide a rationale for each rating.
4.  Calculate ASIL using the standard matrix (QM, A, B, C, D). You have the calculator logic.
5.  Derive a SMART safety goal in the format: "The {item_name} shall [action] to prevent/mitigate [hazardous event]."
6.  Assign a simple ID (e.g., HAZ-001, HAZ-002).
7.  Output ONLY the markdown table. Do not add any other text or explanations.

**Example Row:**
| HAZ-001 | Cell overvoltage leads to thermal runaway | Fast charging at high ambient temperature | S3 | E2 | C3 | D | The {item_name} shall detect cell overvoltage within 10ms and isolate the battery to prevent thermal runaway. |

**HARA Table:**
"""

    try:
        hara_table = cat.llm(prompt).strip()
        
        # Store in working memory for formatter hook (if you have one listening for "hara")
        cat.working_memory["document_type"] = "hara"
        cat.working_memory["hara_table"] = hara_table
        cat.working_memory["hara_stage"] = "table_generated"

        log.info("HARA table generated and stored in working memory.")
        return hara_table

    except Exception as e:
        log.error(f"Error generating HARA table: {e}")
        return f"❌ Error generating HARA table: {str(e)}"
