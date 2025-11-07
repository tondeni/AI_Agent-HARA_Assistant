# ==============================================================================
# tools/02_hazop_analysis.py
# Tool for applying HAZOP analysis to functions
# Modified to output JSON and store complete results for external formatting
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os
import json

#Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder) # Renamed for clarity
plugin_folder = os.path.dirname(code_folder) # Get the actual plugin root

# Add modules to path
sys.path.insert(0, os.path.join(code_folder, 'core'))
sys.path.insert(0, os.path.join(code_folder, 'generators')) # Corrected path

from iso26262_base import ISO26262Tool, WorkflowManager

class HAZOPAnalysisTool(ISO26262Tool):
    """
    Tool for applying HAZOP analysis to extracted functions.
    
    Implements ISO 26262-3:2018, Clause 6.4.3 - Hazard identification
    
    Returns complete JSON output for external formatting.
    Stores all data in working_memory for formatter plugins.
    """
    
    REQUIRED_DATA = ['item_functions', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "all") -> str:
        """Apply HAZOP analysis to functions and return complete JSON"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            error_result = {
                "status": "error",
                "error_type": "missing_prerequisites",
                "message": "Cannot perform HAZOP analysis - missing required data",
                "missing_data": missing,
                "suggestions": [
                    "Extract functions first: `extract functions from [System Name]`",
                    f"Missing: {', '.join(missing)}"
                ]
            }
            return json.dumps(error_result, indent=2)
        
        # Get data
        functions = self.get_workflow_data('item_functions')
        item_name = self.get_workflow_data('hara_item_name')
        item_definition = self.get_workflow_data('item_definition_content', '')
        
        log.info(f"📋 Performing HAZOP for: {item_name}")
        
        try:    
            # Import HAZOP generator
            from ..generators.hazop_generator import HAZOPGenerator
            
            # Create generator
            generator = HAZOPGenerator(self.llm, self.plugin_folder)
            
            # Generate HAZOP analysis
            hazop_results = generator.generate_hazop(
                functions=functions,
                system_name=item_name,
                item_definition=item_definition
            )
            
            if not hazop_results:
                error_result = {
                    "status": "error",
                    "error_type": "no_results",
                    "message": "HAZOP analysis produced no results",
                    "suggestions": [
                        "Check LLM availability",
                        "Verify function format",
                        "Simplify function descriptions",
                        "Retry analysis"
                    ]
                }
                return json.dumps(error_result, indent=2)
            
            # Store results in working memory (for internal workflow)
            self.set_workflow_data('hazop_results', hazop_results)
            self.set_workflow_data('hara_hazardous_events', hazop_results)  # Alias
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('hazop_complete')
            
            # Calculate statistics
            stats = self._calculate_hazop_statistics(hazop_results)
            
            log.info(f"✅ HAZOP complete: {stats['total']} malfunctioning behaviors")
            
            # Build complete JSON output with ALL fields
            output = {
                "status": "success",
                "analysis_type": "HAZOP",
                "iso_standard": "ISO 26262-3:2018",
                "clause": "6.4.3",
                "system_name": item_name,
                "timestamp": self._get_timestamp(),
                "statistics": {
                    "total_hazards": stats['total'],
                    "severity_distribution": stats['severity_distribution'],
                    "functions_analyzed": stats.get('functions_analyzed', len(functions) if isinstance(functions, list) else 0)
                },
                "hazards": hazop_results,  # Complete hazard list with all fields
                "next_steps": [
                    "Review HAZOP results: `show hazop results`",
                    "Define operational situations: `identify relevant driving situations`"
                ],
                "compliance_notes": [
                    "Clause 6.4.3: Systematic hazard identification using HAZOP",
                    "10 guide words applied to each function",
                    "Preliminary severity estimates provided"
                ]
            }
            
            return json.dumps(output, indent=2, ensure_ascii=False)
            
        except Exception as e:
            log.error(f"HAZOP analysis failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            error_result = {
                "status": "error",
                "error_type": "analysis_failed",
                "message": f"HAZOP analysis failed: {str(e)}",
                "traceback": traceback.format_exc(),
                "suggestions": [
                    "Verify LLM is available",
                    "Check function format",
                    "Review HAZOP templates",
                    "Contact support if issue persists"
                ]
            }
            return json.dumps(error_result, indent=2)
    
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
        
        # Count unique functions
        unique_functions = set(h.get('function_id', '') for h in hazop_results)
        stats['functions_analyzed'] = len(unique_functions)
        
        return stats
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()


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
    
    Returns complete JSON with ALL fields for external formatting.
    
    Args:
        tool_input: Optional - specific function to analyze (otherwise analyzes all)
        cat: Cheshire Cat instance
    
    Returns:
        JSON string with complete HAZOP data including:
        - status
        - analysis_type
        - iso_standard
        - clause
        - system_name
        - timestamp
        - statistics (total_hazards, severity_distribution, functions_analyzed)
        - hazards (array with complete hazard objects)
        - next_steps
        - compliance_notes
    
    Example:
        User: "apply hazop analysis"
        Output: Complete JSON with all HAZOP data
    """
    
    log.info("🔧 TOOL CALLED: apply_hazop_analysis")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    hazop_tool = HAZOPAnalysisTool(cat, plugin_folder)
    json_output = hazop_tool.execute(tool_input if tool_input else "all")
    
    # Parse and store COMPLETE JSON in working memory for formatter plugins
    try:
        result_data = json.loads(json_output)
        
        if result_data.get('status') == 'success':
            # Store COMPLETE JSON output - formatter can access ALL fields
            cat.working_memory['hazop_complete_output'] = result_data
            
            # Also store individual components for backward compatibility
            cat.working_memory['hazop_results'] = result_data['hazards']
            cat.working_memory['hazop_statistics'] = result_data['statistics']
            cat.working_memory['hazop_system_name'] = result_data['system_name']
            cat.working_memory['hazop_timestamp'] = result_data['timestamp']
            cat.working_memory['hazop_iso_standard'] = result_data['iso_standard']
            cat.working_memory['hazop_clause'] = result_data['clause']
            cat.working_memory['hazop_next_steps'] = result_data['next_steps']
            cat.working_memory['hazop_compliance_notes'] = result_data['compliance_notes']
            
            # Signal that data is ready for formatting
            cat.working_memory['last_operation'] = 'hazop_analysis'
            cat.working_memory['needs_formatting'] = True  # Signal to OutputFormatter
            
            log.info("✅ Complete HAZOP JSON stored in working_memory['hazop_complete_output']")
            log.info(f"✅ {len(result_data['hazards'])} hazards available for formatting")
        
        elif result_data.get('status') == 'error':
            # Store error for potential error handling by formatter
            cat.working_memory['hazop_error'] = result_data
            log.warning(f"⚠️ HAZOP analysis error: {result_data.get('message', 'Unknown error')}")
    
    except json.JSONDecodeError as e:
        log.error(f"❌ Could not parse HAZOP output as JSON: {e}")
        cat.working_memory['hazop_error'] = {
            'status': 'error',
            'error_type': 'json_parse_error',
            'message': str(e)
        }
    
    return json_output


@tool(
    return_direct=True,
    examples=[
        "show hazop results",
        "display hazop table",
        "what hazards were identified",
        "get hazop json"
    ]
)
def show_hazop_results(tool_input, cat):
    """
    Retrieve HAZOP analysis results from working memory as complete JSON.
    
    Returns the COMPLETE HAZOP dataset with all fields for external formatting.
    
    Available data includes:
    - Complete hazard objects with all fields:
      * hazard_id
      * function_id
      * function_name
      * guide_word
      * malfunctioning_behavior
      * hazardous_event
      * severity
      * severity_rationale
      * metadata (system_name, analysis_date, iso_standard, clause)
    - Statistics (total_hazards, severity_distribution, functions_analyzed)
    - System information (system_name, timestamp, iso_standard, clause)
    - Next steps and compliance notes
    
    Useful for:
    - Passing data to output formatter plugins
    - Exporting HAZOP results
    - Further analysis or processing
    """
    
    log.info("🔧 TOOL CALLED: show_hazop_results")
    
    # Try to get complete output first (preferred)
    complete_output = cat.working_memory.get('hazop_complete_output', None)
    
    if complete_output:
        log.info("✅ Returning complete HAZOP output from working_memory")
        return json.dumps(complete_output, indent=2, ensure_ascii=False)
    
    # Fallback: reconstruct from individual components
    hazop_results = cat.working_memory.get('hazop_results', [])
    
    if not hazop_results:
        error_result = {
            "status": "error",
            "error_type": "no_data",
            "message": "No HAZOP results found in working memory",
            "suggestion": "Perform HAZOP analysis first: `apply hazop analysis`"
        }
        return json.dumps(error_result, indent=2)
    
    # Reconstruct complete output from components
    hazop_stats = cat.working_memory.get('hazop_statistics', {})
    item_name = cat.working_memory.get('hazop_system_name', 
                                       cat.working_memory.get('hara_item_name', 'System'))
    timestamp = cat.working_memory.get('hazop_timestamp', '')
    iso_standard = cat.working_memory.get('hazop_iso_standard', 'ISO 26262-3:2018')
    clause = cat.working_memory.get('hazop_clause', '6.4.3')
    next_steps = cat.working_memory.get('hazop_next_steps', [])
    compliance_notes = cat.working_memory.get('hazop_compliance_notes', [])
    
    output = {
        "status": "success",
        "analysis_type": "HAZOP",
        "iso_standard": iso_standard,
        "clause": clause,
        "system_name": item_name,
        "timestamp": timestamp,
        "statistics": hazop_stats,
        "hazards": hazop_results,
        "total_hazards": len(hazop_results),
        "next_steps": next_steps,
        "compliance_notes": compliance_notes
    }
    
    log.info("✅ Reconstructed complete HAZOP output from working_memory components")
    
    return json.dumps(output, indent=2, ensure_ascii=False)


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
    Display the 10 HAZOP guide words used in analysis as JSON.
    
    Returns structured information about HAZOP methodology.
    """
    
    log.info("🔧 TOOL CALLED: show_hazop_guide_words")
    
    guide_words = {
        "status": "success",
        "data_type": "hazop_guide_words",
        "iso_standard": "ISO 26262-3:2018",
        "clause": "6.4.3",
        "guide_words": [
            {
                "keyword": "NO / NOT",
                "description": "Complete absence of the function",
                "example": "Brake system provides no braking force"
            },
            {
                "keyword": "MORE",
                "description": "Quantitative increase",
                "example": "Excessive brake force applied"
            },
            {
                "keyword": "LESS",
                "description": "Quantitative decrease",
                "example": "Insufficient brake force"
            },
            {
                "keyword": "EARLY",
                "description": "Timing too soon",
                "example": "Brakes engage before driver command"
            },
            {
                "keyword": "LATE",
                "description": "Timing too late",
                "example": "Delayed brake response"
            },
            {
                "keyword": "REVERSE",
                "description": "Opposite effect",
                "example": "Acceleration instead of braking"
            },
            {
                "keyword": "OTHER THAN",
                "description": "Completely different result",
                "example": "Steering input instead of braking"
            },
            {
                "keyword": "PART OF",
                "description": "Incomplete function",
                "example": "Only front brakes engage"
            },
            {
                "keyword": "AS WELL AS",
                "description": "Additional unintended function",
                "example": "Braking plus unintended steering"
            },
            {
                "keyword": "WHERE ELSE",
                "description": "Function occurs at wrong location",
                "example": "Wrong wheel receives braking force"
            }
        ],
        "note": "Each guide word is applied to each safety-relevant function to ensure comprehensive hazard coverage"
    }
    
    return json.dumps(guide_words, indent=2, ensure_ascii=False)


# ==============================================================================
# Utility function for external plugins
# ==============================================================================

def get_hazop_data_for_formatting(cat) -> dict:
    """
    Utility function for formatter plugins to get complete HAZOP data.
    
    This function can be imported by your formatter plugin:
    
    from tools.02_hazop_analysis import get_hazop_data_for_formatting
    
    hazop_data = get_hazop_data_for_formatting(cat)
    
    Returns:
        Complete HAZOP data dictionary, or None if no data available
    """
    return cat.working_memory.get('hazop_complete_output', None)