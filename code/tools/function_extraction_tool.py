# ==============================================================================
# code/tools/function_extraction_tool.py
# Tool for extracting safety-relevant functions from Item Definition
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder)
plugin_folder = os.path.dirname(code_folder)

# Add to path for imports
if code_folder not in sys.path:
    sys.path.insert(0, code_folder)

from loaders.item_definition_loader import ItemDefinitionLoader


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
    Extract safety-relevant functions from Item Definition for HARA analysis.
    
    This is Step 1 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.3).
    
    Sources for Item Definition:
    1. Working memory (after generation by ItemDefinition_Developer)
    2. item_definitions/ folder
    3. Output Formatter generated documents
    
    Args:
        tool_input: Item name (e.g., "Battery Management System")
        cat: Cheshire Cat instance
    
    Returns:
        Formatted list of 4-5 safety-relevant functions
    
    Example:
        User: "extract functions from Windscreen Wiper System"
        Output: Numbered list of critical functions
    """
    
    log.info("🔧 TOOL CALLED: extract_functions")
    
    # Parse input
    item_name = "Unknown System"
    if isinstance(tool_input, str):
        item_name = tool_input.strip()
    elif isinstance(tool_input, dict):
        item_name = tool_input.get("item_name", item_name)
    
    log.info(f"📋 Extracting functions for: {item_name}")
    
    # Load Item Definition
    loader = ItemDefinitionLoader(plugin_folder)
    item_def_content = loader.load_item_definition(item_name, cat)
    
    if not item_def_content:
        return f"""❌ **No Item Definition Found: '{item_name}'**

**Please ensure:**
1. Item Definition generated via ItemDefinition_Developer plugin
2. Item name matches exactly
3. File exists in one of these locations:
   - Working memory (if just generated)
   - `item_definitions/` folder in HARA plugin
   - Output Formatter generated documents

**Manual Setup:**
- Save to: `plugins/AI_Agent-HARA_Assistant/item_definitions/{item_name}.txt`
- Or store in working memory:
  ```python
  cat.working_memory["item_definition_content"] = "[content]"
  ```

**Try again after setup.**"""
    
    log.info(f"📄 Found Item Definition: {len(item_def_content)} characters")
    
    # Build extraction prompt
    prompt = f"""You are a Functional Safety Engineer performing a HARA (Hazard Analysis and Risk Assessment) per ISO 26262-3:2018.

**Task:** Extract 4-5 **safety-relevant functions** from the Item Definition below.

**Item Definition:**
{item_def_content}

**Instructions:**
- Identify functions that, if malfunctioning, could lead to hazardous situations
- Focus on critical control, monitoring, and actuation functions
- Ignore non-safety-relevant functions (e.g., user interface, diagnostics logging)
- Each function should have clear inputs, processing, and outputs

**Output Format:**
Provide a numbered list:

1. **[Function Name]:** [Brief description including normal parameters]
2. **[Function Name]:** [Brief description including normal parameters]
...

**Example:**
1. **Battery Voltage Monitoring:** Continuously monitor cell voltage (normal range: 3.0-4.2V per cell)
2. **Over-Current Protection:** Detect and interrupt current flow when exceeding 150A threshold
...

Extract functions now:"""
    
    try:
        log.info("🤖 Extracting functions with LLM...")
        functions_list = cat.llm(prompt).strip()
        
        # Store in working memory
        cat.working_memory["hara_item_name"] = item_name
        cat.working_memory["item_functions"] = functions_list
        cat.working_memory["item_definition_content"] = item_def_content
        cat.working_memory["hara_stage"] = "functions_extracted"
        
        # Set formatter flags (for Output Formatter integration)
        cat.working_memory["needs_formatting"] = False  # Already formatted by tool
        cat.working_memory["last_operation"] = "function_extraction"
        
        log.info(f"✅ Functions extracted and stored")
        
        return f"""✅ **Functions Extracted: {item_name}**

{functions_list}

---

## Workflow Progress: 1/6 Steps Complete

**Completed:**
- ✅ Step 1: Functions extracted

**Next Steps:**
➡️ Step 2: `apply hazop analysis`
- Applies HAZOP guide words to identify hazards
- Assesses Severity (S) for each hazard
- Output: HAZOP table with malfunctions and hazardous events

**Remaining Steps:**
3. ❓ Define operational situations
4. ❓ Assess Exposure (E) and Controllability (C)
5. ❓ Determine ASIL
6. ❓ Derive safety goals
7. ❓ Generate HARA document

**ISO 26262-3:2018 Reference:**
- Clause 6.4.3: Hazard identification
- Clause 6.4.2.3: Item definition analysis"""
        
    except Exception as e:
        log.error(f"Function extraction failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return f"""❌ **Function Extraction Failed**

**Error:** {str(e)}

**Possible causes:**
- LLM service unavailable
- Item Definition format issue
- Insufficient context

**Try:**
- Verify Item Definition is readable text
- Simplify Item Definition structure
- Check LLM configuration"""


@tool(
    return_direct=True,
    examples=[
        "show extracted functions",
        "list functions",
        "what functions did we extract"
    ]
)
def show_extracted_functions(tool_input, cat):
    """
    Display previously extracted functions from working memory.
    
    Shows:
    - System name
    - List of extracted functions
    - Current HARA stage
    
    Useful for reviewing before proceeding to HAZOP analysis.
    """
    
    log.info("🔧 TOOL CALLED: show_extracted_functions")
    
    item_name = cat.working_memory.get('hara_item_name', 'Unknown')
    functions = cat.working_memory.get('item_functions', '')
    stage = cat.working_memory.get('hara_stage', 'not_started')
    
    if not functions:
        return """❌ **No Functions Found**

**Action:** Extract functions first: `extract functions from [System Name]`"""
    
    return f"""📋 **Extracted Functions: {item_name}**

{functions}

---

**HARA Stage:** {stage}
**Next Step:** `apply hazop analysis` (if not yet done)"""