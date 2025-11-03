# ==============================================================================
# tools/01_function_extraction.py
# Tool for extracting safety-relevant functions from Item Definition
# Refactored to use ISO26262Tool base class
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
itemdef_folder = os.path.join(plugin_folder, 'item_definitions')

# Add core module to path
sys.path.insert(0, os.path.join(code_folder, 'core'))

from iso26262_base import ISO26262Tool, WorkflowManager, parse_item_name
from loaders.item_definition_loader import ItemDefinitionLoader



class FunctionExtractionTool(ISO26262Tool):
    """
    Tool for extracting safety-relevant functions from Item Definition.
    
    Implements ISO 26262-3:2018, Clause 6.4.3 - Hazard identification
    """
    
    REQUIRED_DATA = []  # No prerequisites for first step
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, item_name: str) -> str:
        """Extract functions from Item Definition"""
        
        log.info(f"📋 Extracting functions for: {item_name}")
        
        # Load Item Definition
        item_def_content = self._load_item_definition(item_name)
        
        if not item_def_content:
            return self.format_error(
                f"No Item Definition found for '{item_name}'",
                [
                    "Ensure Item Definition is generated via ItemDefinition_Developer plugin",
                    "Check item name matches exactly",
                    f"Place file in: item_definitions/{item_name}.txt",
                    "Or store in working memory: cat.working_memory['item_definition_content']"
                ]
            )
        
        log.info(f"📄 Found Item Definition: {len(item_def_content)} characters")
        
        # Extract functions using LLM
        try:
            functions_list = self._extract_with_llm(item_name, item_def_content)
            
            # Store results
            self.set_workflow_data('hara_item_name', item_name)
            self.set_workflow_data('item_functions', functions_list)
            self.set_workflow_data('item_definition_content', item_def_content)
            
            # Update workflow stage
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('functions_extracted')
            
            # Count functions
            function_count = len([line for line in functions_list.split('\n') if line.strip() and line.strip()[0].isdigit()])
            
            return self.format_success(
                f"Functions Extracted: {item_name}",
                {
                    "Total Functions": function_count,
                    "Item Definition": f"{len(item_def_content)} characters"
                },
                [
                    "Review extracted functions",
                    "Apply HAZOP analysis: `apply hazop analysis`"
                ]
            ) + f"\n**Extracted Functions:**\n\n{functions_list}\n\n" + \
                "---\n\n**ISO 26262-3:2018 Reference:**\n" + \
                "- Clause 6.4.3: Hazard identification\n" + \
                "- Clause 6.4.2.3: Item definition analysis"
            
        except Exception as e:
            log.error(f"Function extraction failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                str(e),
                [
                    "Verify LLM is available",
                    "Check Item Definition format",
                    "Simplify Item Definition if too complex",
                    "Review LLM configuration"
                ]
            )
    
    def _load_item_definition(self, item_name: str) -> str:
        """Load Item Definition from various sources"""
        
        # Priority 1: Working memory (just generated)
        item_def = self.get_workflow_data('item_definition_content')
        if item_def:
            log.info("✅ Loaded Item Definition from working memory")
            return item_def
        
        # Priority 2: Use ItemDefinitionLoader
        # try:
            # from loaders.item_definition_loader import ItemDefinitionLoader
        loader = ItemDefinitionLoader(self.plugin_folder)
        log.warning(f"Item Definition folder {self.plugin_folder}")
        item_def = loader.load_item_definition(item_name, self.cat)
        if item_def:
            return item_def
        # except ImportError:
            # log.warning("ItemDefinitionLoader not available")
        
        # Priority 3: Direct file search
        import os
        search_locations = [
            os.path.join(self.plugin_folder, 'item_definitions', f'{item_name}.txt'),
            os.path.join(self.plugin_folder, 'item_definitions', f'{item_name}.md'),
            os.path.join(self.plugin_folder, 'data', 'item_definitions', f'{item_name}.txt')
        ]
        
        for file_path in search_locations:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    log.info(f"✅ Loaded Item Definition from: {file_path}")
                    return content
                except Exception as e:
                    log.warning(f"Error reading {file_path}: {e}")
        
        return None
    
    def _extract_with_llm(self, item_name: str, item_def_content: str) -> str:
        """Extract functions using LLM"""
        
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
        
        log.info("🤖 Extracting functions with LLM...")
        functions_list = self.llm(prompt).strip()
        log.info(f"✅ Functions extracted")
        
        return functions_list


# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

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
        Formatted list of 4-5 safety-relevant functions extracted from ItemDefinition
    
    Example:
        User: "extract functions from Windscreen Wiper System"
        Output: Numbered list of critical functions
    """
    
    log.info("🔧 TOOL CALLED: extract_functions")
    
    # Parse input
    item_name = parse_item_name(tool_input)
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = FunctionExtractionTool(cat, itemdef_folder)
    return tool.execute(item_name)


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
    
    # Get plugin folder for WorkflowManager
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    sys.path.insert(0, os.path.join(plugin_folder, 'core'))
    
    from iso26262_base import WorkflowManager
    workflow = WorkflowManager(cat)
    stage = workflow.get_current_stage()
    next_step = workflow.get_next_step()
    
    if not functions:
        return """❌ **No Functions Found**

**Action:** Extract functions first: `extract functions from [System Name]`

**Example:**
```
extract functions from Battery Management System
```"""
    
    return f"""📋 **Extracted Functions: {item_name}**

{functions}

---

**HARA Stage:** {stage}
**Next Step:** {next_step}"""