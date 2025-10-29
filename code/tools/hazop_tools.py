# ==============================================================================
# code/tools/hazop_tool.py
# Tool for applying HAZOP analysis to functions
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

from generators.HARA.hazop_generator import HAZOPGenerator, format_hazop_table, get_hazop_statistics


@tool(
    return_direct=True,
    examples=[
        "apply hazop analysis",
        "perform hazop on functions",
        "identify hazards with hazop"
    ]
)
def apply_hazop_analysis(tool_input, cat):
    """
    Apply HAZOP (Hazard and Operability) analysis to extracted functions.
    
    This is Step 2 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.3).
    
    Applies 10 HAZOP guide words to each function:
    - NO, MORE, LESS, EARLY, LATE
    - REVERSE, OTHER THAN, PART OF, AS WELL AS, WHERE ELSE
    
    For each combination, identifies:
    - Malfunctioning behavior
    - Hazardous event
    - Preliminary severity (S0-S3)
    
    Args:
        tool_input: Optional - specific function to analyze (otherwise analyzes all)
        cat: Cheshire Cat instance
    
    Returns:
        HAZOP analysis table with malfunctioning behaviors
    
    Example:
        User: "apply hazop analysis"
        Output: Complete HAZOP table for all functions
    """
    
    log.info("🔧 TOOL CALLED: apply_hazop_analysis")
    
    # Get functions from working memory
    functions = cat.working_memory.get('item_functions', '')
    item_name = cat.working_memory.get('hara_item_name', 'System')
    item_definition = cat.working_memory.get('item_definition_content', '')
    
    if not functions:
        return """❌ **No Functions Available**

**Action Required:** Extract functions first

Use: `extract functions from [System Name]`

**Example:**
```
extract functions from Battery Management System
```"""
    
    log.info(f"📋 Performing HAZOP for: {item_name}")
    
    try:
        # Create HAZOP generator
        generator = HAZOPGenerator(cat.llm, plugin_folder)
        
        # Generate HAZOP analysis
        hazop_results = generator.generate_hazop(
            functions=functions,
            system_name=item_name,
            item_definition=item_definition
        )
        
        if not hazop_results:
            return """❌ **HAZOP Analysis Failed**

**Possible causes:**
- LLM unable to analyze functions
- Functions not in expected format
- LLM service unavailable

**Try:**
- Simplify function descriptions
- Check LLM configuration
- Retry analysis"""
        
        # Store results in working memory
        cat.working_memory['hazop_results'] = hazop_results
        cat.working_memory['hara_stage'] = 'hazop_complete'
        
        # Set formatter flags
        cat.working_memory['needs_formatting'] = True
        cat.working_memory['last_operation'] = 'hazop_analysis'
        
        # Get statistics
        stats = get_hazop_statistics(hazop_results)
        
        log.info(f"✅ HAZOP complete: {stats['total']} malfunctioning behaviors")
        
        # Build simple response (formatter will make it pretty)
        response = f"""Successfully completed HAZOP analysis for {item_name}.

Total malfunctioning behaviors identified: {stats['total']}

Severity distribution:
- S3 (Life-threatening): {stats['severity_distribution']['S3']}
- S2 (Severe injuries): {stats['severity_distribution']['S2']}
- S1 (Moderate injuries): {stats['severity_distribution']['S1']}
- S0 (No injuries): {stats['severity_distribution']['S0']}

HAZOP results stored in working memory.

Next step: Define operational situations for exposure assessment."""
        
        return response
        
    except Exception as e:
        log.error(f"HAZOP analysis failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"""❌ **HAZOP Analysis Error**

**Error:** {str(e)}

**Debug Info:**
- Functions found: {'Yes' if functions else 'No'}
- Item name: {item_name}

**Try:**
- Check function format
- Verify LLM availability
- Retry with simpler functions"""


@tool(
    return_direct=True,
    examples=[
        "show hazop results",
        "display hazop table",
        "what hazards were identified"
    ]
)
def show_hazop_results(tool_input, cat):
    """
    Display HAZOP analysis results from working memory.
    
    Shows:
    - Complete HAZOP table
    - Statistics (severity distribution)
    - Next steps
    
    Useful for reviewing HAZOP before proceeding to exposure assessment.
    """
    
    log.info("🔧 TOOL CALLED: show_hazop_results")
    
    hazop_results = cat.working_memory.get('hazop_results', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Results Found**

**Action:** Perform HAZOP analysis first: `apply hazop analysis`"""
    
    # Get statistics
    stats = get_hazop_statistics(hazop_results)
    
    # Format table
    table = format_hazop_table(hazop_results)
    
    return f"""📋 **HAZOP Analysis Results: {item_name}**

**Total Malfunctioning Behaviors:** {stats['total']}

**Severity Distribution:**
- S3 (Life-threatening): {stats['severity_distribution']['S3']}
- S2 (Severe injuries): {stats['severity_distribution']['S2']}
- S1 (Moderate injuries): {stats['severity_distribution']['S1']}
- S0 (No injuries): {stats['severity_distribution']['S0']}

**HAZOP Table (Preview):**

{table[:1000]}...

---

**Next Steps:**
1. Define operational situations: `define operational situations`
2. Assess exposure and controllability
3. Determine ASIL
4. Derive safety goals"""


@tool(
    return_direct=True,
    examples=[
        "show hazop guide words",
        "list hazop guide words",
        "what are the hazop guide words"
    ]
)
def show_hazop_guide_words(tool_input, cat):
    """
    Display the 10 HAZOP guide words used in analysis.
    
    Shows:
    - Guide word name
    - Description
    - Example application
    
    Useful for understanding HAZOP methodology.
    """
    
    log.info("🔧 TOOL CALLED: show_hazop_guide_words")
    
    guide_words = {
        'NO': 'Function not performed / Complete absence',
        'MORE': 'Excessive performance / Quantitative increase',
        'LESS': 'Insufficient performance / Quantitative decrease',
        'EARLY': 'Too soon / Premature occurrence',
        'LATE': 'Delayed / Too late occurrence',
        'REVERSE': 'Opposite function / Logical opposite',
        'OTHER THAN': 'Different function / Substitution',
        'PART OF': 'Incomplete function / Partial execution',
        'AS WELL AS': 'Additional unintended function / Extra action',
        'WHERE ELSE': 'Wrong location or target / Misdirection'
    }
    
    output = "📖 **HAZOP Guide Words Reference**\n\n"
    output += "ISO 26262-3:2018 uses these 10 standard guide words:\n\n"
    
    for idx, (word, description) in enumerate(guide_words.items(), 1):
        output += f"**{idx}. {word}**\n"
        output += f"   {description}\n\n"
    
    output += "**Usage:** Each guide word is systematically applied to every safety function\n"
    output += "to identify potential malfunctioning behaviors and hazardous events.\n\n"
    output += "**Example:**\n"
    output += "Function: 'Monitor battery voltage (normal: 3.0-4.2V)'\n"
    output += "- NO → Voltage not monitored → Overcharge undetected (S3)\n"
    output += "- MORE → Excessive monitoring frequency → CPU overload (S1)\n"
    output += "- LATE → Delayed detection → Battery damage before protection (S2)\n"
    
    return output