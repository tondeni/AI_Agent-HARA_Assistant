# ==============================================================================
# tools/02_hazop_analysis.py
# Tool for applying HAZOP analysis to functions
# Refactored to use ISO26262Tool base class
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
plugin_folder = os.path.dirname(tools_folder)

# Add modules to path
sys.path.insert(0, os.path.join(plugin_folder, 'core'))
sys.path.insert(0, os.path.join(plugin_folder, 'code', 'generators'))

from iso26262_base import ISO26262Tool, WorkflowManager, calculate_statistics



class HAZOPAnalysisTool(ISO26262Tool):
    """
    Tool for applying HAZOP analysis to extracted functions.
    
    Implements ISO 26262-3:2018, Clause 6.4.3 - Hazard identification
    """
    
    REQUIRED_DATA = ['item_functions', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "all") -> str:
        """Apply HAZOP analysis to functions"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self.format_error(
                "Cannot perform HAZOP analysis - missing required data",
                [
                    "Extract functions first: `extract functions from [System Name]`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        functions = self.get_workflow_data('item_functions')
        item_name = self.get_workflow_data('hara_item_name')
        item_definition = self.get_workflow_data('item_definition_content', '')
        
        log.info(f"📋 Performing HAZOP for: {item_name}")
        
        try:
            # Import HAZOP generator
            from generators.hazop_generator import HAZOPGenerator
            
            # Create generator
            generator = HAZOPGenerator(self.llm, self.plugin_folder)
            
            # Generate HAZOP analysis
            hazop_results = generator.generate_hazop(
                functions=functions,
                system_name=item_name,
                item_definition=item_definition
            )
            
            if not hazop_results:
                return self.format_error(
                    "HAZOP analysis produced no results",
                    [
                        "Check LLM availability",
                        "Verify function format",
                        "Simplify function descriptions",
                        "Retry analysis"
                    ]
                )
            
            # Store results
            self.set_workflow_data('hazop_results', hazop_results)
            self.set_workflow_data('hara_hazardous_events', hazop_results)  # Alias
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('hazop_complete')
            
            # Calculate statistics
            stats = self._calculate_hazop_statistics(hazop_results)
            
            log.info(f"✅ HAZOP complete: {stats['total']} malfunctioning behaviors")
            
            # Format response
            return self.format_success(
                f"HAZOP Analysis Complete: {item_name}",
                {
                    "Total Malfunctioning Behaviors": stats['total'],
                    "Severity S3 (Life-threatening)": stats['severity_distribution'].get('S3', 0),
                    "Severity S2 (Severe injuries)": stats['severity_distribution'].get('S2', 0),
                    "Severity S1 (Moderate injuries)": stats['severity_distribution'].get('S1', 0),
                    "Severity S0 (No injuries)": stats['severity_distribution'].get('S0', 0)
                },
                [
                    "Review HAZOP results: `show hazop results`",
                    "Define operational situations: `define operational situations`"
                ]
            ) + "\n\n**ISO 26262-3:2018 Compliance:**\n" + \
                "✓ Clause 6.4.3: Systematic hazard identification using HAZOP\n" + \
                "✓ 10 guide words applied to each function\n" + \
                "✓ Preliminary severity estimates provided"
            
        except Exception as e:
            log.error(f"HAZOP analysis failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                f"HAZOP analysis failed: {str(e)}",
                [
                    "Verify LLM is available",
                    "Check function format",
                    "Review HAZOP templates",
                    "Contact support if issue persists"
                ]
            )
    
    def _calculate_hazop_statistics(self, hazop_results: list) -> dict:
        """Calculate HAZOP statistics"""
        stats = {
            'total': len(hazop_results),
            'severity_distribution': {}
        }
        
        # Count by severity
        for hazard in hazop_results:
            severity = hazard.get('severity', 'S0')
            stats['severity_distribution'][severity] = stats['severity_distribution'].get(severity, 0) + 1
        
        return stats


# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

@tool(
    return_direct=True,
    examples=[
        "apply hazop analysis",
        "perform hazop",
        "start hazop for all functions"
    ]
)
def apply_hazop_analysis(tool_input, cat):
    """
    Apply HAZOP analysis to extracted functions.
    
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
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = HAZOPAnalysisTool(cat, plugin_folder)

        # Store results
    cat.working_memory['hazop_results'] = hazop_results
    
    # ⭐ ADD THESE 2 LINES ⭐
    trigger_hara_formatting(cat, 'hazop_analysis')
    return f"HAZOP analysis complete. {len(hazop_results)} hazards identified."

    return tool.execute(tool_input if tool_input else "all")


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
    - Complete HAZOP table (preview)
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
    
    # Calculate statistics
    stats = {
        'total': len(hazop_results),
        'severity_distribution': {}
    }
    
    for hazard in hazop_results:
        severity = hazard.get('severity', 'S0')
        stats['severity_distribution'][severity] = stats['severity_distribution'].get(severity, 0) + 1
    
    # Format preview (first 5 hazards)
    preview = f"""📋 **HAZOP Analysis Results: {item_name}**

**Total Malfunctioning Behaviors:** {stats['total']}

**Severity Distribution:**
- S3 (Life-threatening): {stats['severity_distribution'].get('S3', 0)}
- S2 (Severe injuries): {stats['severity_distribution'].get('S2', 0)}
- S1 (Moderate injuries): {stats['severity_distribution'].get('S1', 0)}
- S0 (No injuries): {stats['severity_distribution'].get('S0', 0)}

**Sample Hazards (first 5):**

"""
    
    for idx, hazard in enumerate(hazop_results[:5], 1):
        preview += f"{idx}. **{hazard.get('id', 'H-???')}**: {hazard.get('hazardous_event', 'N/A')[:60]}...\n"
        preview += f"   Severity: {hazard.get('severity', '?')}\n\n"
    
    if len(hazop_results) > 5:
        preview += f"... and {len(hazop_results) - 5} more hazards\n\n"
    
    preview += """---

**Next Steps:**
1. Review all hazards carefully
2. Define operational situations: `define operational situations`
3. Proceed to E/S/C assessment"""
    
    return preview


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
    
    return """📖 **HAZOP Guide Words - ISO 26262-3:2018**

The HAZOP method uses 10 systematic guide words to identify failure modes:

1. **NO / NOT** - Complete absence of the function
   - Example: Brake system provides no braking force

2. **MORE** - Quantitative increase
   - Example: Excessive brake force applied

3. **LESS** - Quantitative decrease
   - Example: Insufficient brake force

4. **EARLY** - Timing too soon
   - Example: Brakes engage before driver command

5. **LATE** - Timing too late
   - Example: Delayed brake response

6. **REVERSE** - Opposite effect
   - Example: Acceleration instead of braking

7. **OTHER THAN** - Completely different result
   - Example: Steering input instead of braking

8. **PART OF** - Incomplete function
   - Example: Only front brakes engage

9. **AS WELL AS** - Additional unintended function
   - Example: Braking plus unintended steering

10. **WHERE ELSE** - Function occurs at wrong location
    - Example: Wrong wheel receives braking force

---

**Systematic Application:**
Each guide word is applied to each safety-relevant function to ensure
comprehensive hazard coverage per ISO 26262-3:2018, Clause 6.4.3."""