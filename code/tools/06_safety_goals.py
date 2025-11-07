# ==============================================================================
# tools/06_safety_goals.py
# Tool for deriving safety goals from ASIL-rated hazards
# Refactored to output JSON and store complete results
# =Remember the current location is Italy.
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os
import json
from datetime import datetime

#Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder) # Renamed for clarity
plugin_folder = os.path.dirname(code_folder) # Get the actual plugin root

# Add modules to path
sys.path.insert(0, os.path.join(code_folder, 'core'))
sys.path.insert(0, os.path.join(code_folder, 'generators')) # Corrected path

from iso26262_base import ISO26262Tool, WorkflowManager


class SafetyGoalsTool(ISO26262Tool):
    """
    Tool for deriving safety goals from hazardous events.
    
    Implements ISO 26262-3:2018, Clause 6.4.6 - Safety goal determination
    
    Returns complete JSON output for external formatting.
    Stores all data in working_memory for formatter plugins.
    """
    
    REQUIRED_DATA = ['complete_hara_table', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def _format_json_error(self, message: str, error_type: str, suggestions: list = None) -> str:
        """Format error as JSON string."""
        error_data = {
            "status": "error",
            "analysis_type": "Safety_Goal_Derivation",
            "iso_standard": "ISO 26262-3:2018",
            "clause": "6.4.6",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "suggestions": suggestions or []
        }
        return json.dumps(error_data, indent=2, ensure_ascii=False)

    def _format_json_warning(self, message: str, details: dict, next_steps: list = None) -> str:
        """Format a warning (e.g., no ASIL hazards) as JSON string."""
        warning_data = {
            "status": "warning",
            "analysis_type": "Safety_Goal_Derivation",
            "iso_standard": "ISO 26262-3:2018",
            "clause": "6.4.6",
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "details": details,
            "next_steps": next_steps or [
                "If you expected ASIL-rated hazards, review the E/S/C assessment: `show asil ratings`"
            ],
            "compliance_notes": [
                "QM (Quality Management) rated hazards do not require safety goals per ISO 26262-3:2018, Clause 6.4.5.",
                "The risk is considered acceptable with normal quality management."
            ]
        }
        return json.dumps(warning_data, indent=2, ensure_ascii=False)

    # --- FIX 1 ---
    # Removed 'tool_input' from the function definition. It's no longer needed.
    def execute(self) -> str:
        """Derive safety goals and return complete JSON"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self._format_json_error(
                "Cannot derive safety goals - missing required data",
                "missing_prerequisites",
                [
                    "Complete HARA workflow steps first",
                    "Determine ASIL ratings: `determine asil`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        hazards = self.get_workflow_data('complete_hara_table')
        item_name = self.get_workflow_data('hara_item_name')
        
        # Check for ASIL ratings
        if not hazards or 'asil' not in hazards[0]:
            return self._format_json_error(
                "Hazards are missing ASIL ratings",
                "missing_asil_data",
                ["Run ASIL determination first: `determine asil`"]
            )
            
        # Filter ASIL-rated hazards (A, B, C, D)
        asil_hazards = [h for h in hazards if h.get('asil', 'QM') in ['A', 'B', 'C', 'D']]
        
        if not asil_hazards:
            qm_count = len([h for h in hazards if h.get('asil') == 'QM'])
            return self._format_json_warning(
                "No ASIL-rated hazards found",
                details={
                    "total_hazards_analyzed": len(hazards),
                    "qm_rated_hazards": qm_count,
                    "asil_rated_hazards": 0
                }
            )
        
        log.info(f"📋 Deriving safety goals for {len(asil_hazards)} ASIL-rated hazards")
        
        try:
            # Import safety goal generator
            from ..generators.safety_goal_generator import SafetyGoalGenerator
            
            # Create generator
            generator = SafetyGoalGenerator(self.llm)
            
            # Generate safety goals (list of SafetyGoal objects)
            safety_goals_objects = generator.generate_from_hazards(asil_hazards, item_name)
            
            # Convert to list of dictionaries for JSON serialization
            safety_goals_dicts = [goal.to_dict() for goal in safety_goals_objects]
            
            # Store in working memory
            self.set_workflow_data('hara_safety_goals', safety_goals_dicts)
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('safety_goals_derived')
            
            # Calculate statistics
            stats = generator.calculate_goal_statistics(safety_goals_objects)
            
            # Validate goals and collect issues
            validation_issues = []
            for goal in safety_goals_objects:
                is_valid, issues = generator.validate_safety_goal(goal)
                if not is_valid:
                    validation_issues.extend(issues)
            
            log.info(f"✅ Derived {len(safety_goals_dicts)} safety goals")
            
            # Build complete JSON output
            output = {
                "status": "success",
                "analysis_type": "Safety_Goal_Derivation",
                "iso_standard": "ISO 26262-3:2018",
                "clause": "6.4.6",
                "system_name": item_name,
                "timestamp": datetime.now().isoformat(),
                "statistics": stats,
                "safety_goals": safety_goals_dicts,
                "validation_issues": validation_issues,
                "next_steps": [
                    "Review safety goals: `show safety goals`",
                    "Refine safe states and FTTI values with safety team",
                    "Generate HARA documentation: `generate hara report`"
                ],
                "compliance_notes": [
                    "✓ Clause 6.4.6: Safety goal determination complete",
                    "✓ Goals inherit ASIL from hazardous events",
                    "✓ Formulated at vehicle level",
                    "✓ Include initial safe state and FTTI specifications for review"
                ]
            }
            
            return json.dumps(output, indent=2, ensure_ascii=False)
            
        except Exception as e:
            log.error(f"Safety goal derivation failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self._format_json_error(
                f"Safety goal derivation failed: {str(e)}",
                "execution_error",
                [
                    "Verify ASIL ratings exist",
                    "Check hazard data quality",
                    "Verify LLM availability",
                    "Retry derivation"
                ]
            )


# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

@tool(
    return_direct=True,
    examples=[
        "derive safety goals",
        "generate safety goals",
        "create safety goals from hazards",
        "run safety goal derivation"
    ]
)
def derive_safety_goals(tool_input, cat):
    """
    Derives safety goals from ASIL-rated hazards.
    
    This is Step 6 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.6).
    
    The tool automatically finds all ASIL-rated (A, B, C, D) hazards
    from the HARA and generates a corresponding vehicle-level safety goal,
    safe state, and FTTI for each.
    
    Returns a complete JSON report for external formatting.
    
    Args:
        tool_input: not used. Always derive all safety Goals
        cat: Cheshire Cat instance
    
    Returns:
        JSON string with complete safety goal data
    
    Example:
        User: "derive safety goals"
        Output: Complete JSON with safety goals
    """
    
    log.info("🔧 TOOL CALLED: derive_safety_goals")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = SafetyGoalsTool(cat, plugin_folder)
    
    # --- FIX 4 ---
    # Call execute() with no arguments.
    json_output = tool.execute()
    
    # Parse and store COMPLETE JSON in working memory for formatter plugins
    try:
        result_data = json.loads(json_output)
        
        if result_data.get('status') == 'success' or result_data.get('status') == 'warning':
            # Store COMPLETE JSON output - formatter can access ALL fields
            cat.working_memory['safety_goals_complete_output'] = result_data
            
            # Also store individual components for backward compatibility
            cat.working_memory['hara_safety_goals'] = result_data.get('safety_goals', [])
            cat.working_memory['safety_goals_statistics'] = result_data.get('statistics', {})
            cat.working_memory['safety_goals_system_name'] = result_data.get('system_name', '')
            
            # Signal that data is ready for formatting
            cat.working_memory['last_operation'] = 'safety_goals_derived'
            cat.working_memory['needs_formatting'] = True
            
            log.info("✅ Complete Safety Goals JSON stored in working_memory")
        
        elif result_data.get('status') == 'error':
            # Store error for potential error handling by formatter
            cat.working_memory['safety_goals_error'] = result_data
            log.warning(f"⚠️ Safety Goal derivation error: {result_data.get('message', 'Unknown error')}")
    
    except json.JSONDecodeError as e:
        log.error(f"❌ Could not parse Safety Goal output as JSON: {e}")
        cat.working_memory['safety_goals_error'] = {
            'status': 'error',
            'error_type': 'json_parse_error',
            'message': str(e)
        }
    
    return json_output


@tool(
    return_direct=True,
    examples=[
        "show safety goals",
        "list safety goals",
        "display derived safety goals",
        "get safety goals json"
    ]
)
def show_safety_goals(tool_input, cat):
    """
    Retrieve derived safety goals from working memory as complete JSON.
    
    Returns the COMPLETE safety goal dataset with all fields.
    
    Available data includes:
    - Complete safety goal objects with all fields:
      * sg_id
      * statement
      * asil
      * hazard_id
      * safe_state
      * ftti_ms
      * rationale
    - Statistics (total_goals, asil_distribution)
    - System information (system_name, timestamp, etc.)
    - Next steps and compliance notes
    
    Useful for:
    - Passing data to output formatter plugins
    - Exporting safety goals
    """
    
    log.info("🔧 TOOL CALLED: show_safety_goals")
    
    # Try to get complete output first (preferred)
    complete_output = cat.working_memory.get('safety_goals_complete_output', None)
    
    if complete_output:
        log.info("✅ Returning complete safety goals output from working_memory")
        return json.dumps(complete_output, indent=2, ensure_ascii=False)
    
    # Fallback: reconstruct from individual components
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    if not safety_goals:
        error_result = {
            "status": "error",
            "error_type": "no_data",
            "message": "No safety goals found in working memory",
            "suggestion": "Derive safety goals first: `derive safety goals`"
        }
        return json.dumps(error_result, indent=2)

    # Reconstruct complete output from components
    stats = cat.working_memory.get('safety_goals_statistics', {})
    system_name = cat.working_memory.get('safety_goals_system_name',
                                         cat.working_memory.get('hara_item_name', 'System'))
    
    output = {
        "status": "success",
        "analysis_type": "Safety_Goal_Derivation",
        "iso_standard": "ISO 26262-3:2018",
        "clause": "6.4.6",
        "system_name": system_name,
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "safety_goals": safety_goals,
        "total_goals": len(safety_goals),
        "next_steps": [
             "Review safety goals",
             "Generate HARA documentation: `generate hara excel`"
        ],
        "compliance_notes": ["Safety goals reconstructed from working memory"]
    }
    
    log.info("✅ Reconstructed complete safety goals output from working_memory components")
    
    return json.dumps(output, indent=2, ensure_ascii=False)