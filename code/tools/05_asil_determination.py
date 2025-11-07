# ==============================================================================
# tools/05_asil_determination.py
# Tool for determining ASIL based on E/S/C ratings
# Refactored to use ISO26262Tool base class
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


class ASILDeterminationTool(ISO26262Tool):
    """
    Tool for determining ASIL based on E/S/C ratings.
    
    Implements ISO 26262-3:2018, Clause 6.4.5 and Table 4
    """
    
    REQUIRED_DATA = ['complete_hara_table', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def _format_json_output(self, hazards: list, system_name: str, stats: dict) -> dict:
        """Format ASIL determination as a complete JSON dictionary."""
        
        output = {
            "status": "success",
            "analysis_type": "ASIL_Determination",
            "iso_standard": "ISO 26262-3:2018",
            "clause": "6.4.5 - ASIL determination",
            "system_name": system_name,
            "timestamp": datetime.now().isoformat(),
            "statistics": stats, # The stats from the calculator are already well-formatted
            "hazards": hazards, # The full list with ASIL ratings
            "next_steps": [
                "Review ASIL ratings: `show asil ratings`",
                "Derive safety goals: `create safety goals from hazards`"
            ],
            "compliance_notes": [
                "✓ Clause 6.4.5: ASIL determination per Table 4",
                "✓ Systematic application of E/S/C combinations",
                "✓ All hazards classified"
            ]
        }
        return output
    
    # --- FIX 1 ---
    # Removed 'tool_input' from the function definition.
    def execute(self) -> str:
        """Determine ASIL for all hazards"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self.format_error(
                "Cannot determine ASIL - missing required data",
                [
                    "Complete E/S/C assessment first: `assess esc for all hazards`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        hazards = self.get_workflow_data('complete_hara_table')
        item_name = self.get_workflow_data('hara_item_name')
        
        # Verify E/S/C ratings exist
        if not hazards or not all(key in hazards[0] for key in ['exposure', 'severity', 'controllability']):
            return self.format_error(
                "Hazards missing E/S/C ratings",
                ["Run E/S/C assessment: `assess esc for all hazards`"]
            )
        
        log.info(f"📋 Determining ASIL for {len(hazards)} hazards")
        
        try:
            # Import ASIL calculator
            from ..generators.asil_calculator import ASILCalculator
            
            # Create calculator
            calculator = ASILCalculator()
            
            # Determine ASIL for all hazards
            updated_hazards = calculator.determine_asil_for_hazards(hazards)
            
            # Store updated hazards
            self.set_workflow_data('complete_hara_table', updated_hazards)
            self.set_workflow_data('hara_hazardous_events', updated_hazards)
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('asil_determined')
            
            log.info(f"✅ ASIL determination complete")
            
            # Calculate statistics
            stats = calculator.calculate_asil_statistics(updated_hazards)
            
            # Format output as JSON dictionary
            output_data = self._format_json_output(updated_hazards, item_name, stats)
            
            # Return JSON string
            return json.dumps(output_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            log.error(f"ASIL determination failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                f"ASIL determination failed: {str(e)}",
                [
                    "Verify E/S/C ratings are valid",
                    "Check rating format (S0-S3, E0-E4, C0-C3)",
                    "Retry determination"
                ]
            )


# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

@tool(
    return_direct=True,
    examples=[
        "determine asil",
        "calculate asil ratings",
        "run asil determination"
    ]
)
# --- FIX 2 ---
# Removed 'tool_input' from the function definition.
def determine_asil(tool_input, cat):
    """
    Determines ASIL ratings for all hazards based on E/S/C combinations.
    
    This is Step 5 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.5).
    It applies the ISO 26262-3 Table 4 matrix to determine the
    ASIL (QM, A, B, C, or D) for each hazard.
    
    Returns a complete JSON report with ASIL ratings, statistics, 
    and compliance notes for external formatting.
    
    --- FIX 3 ---
    # Simplified the Args docstring.
    Args:
        tool_input: not used. Always determine asil for all safety goals
        cat: Cheshire Cat instance
    
    Returns:
        JSON string with the complete ASIL determination report.
    
    Example:
        User: "determine asil"
        Output: Complete JSON with ASIL determination results...
    """
    
    log.info("🔧 TOOL CALLED: determine_asil")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
   # Execute tool
    tool = ASILDeterminationTool(cat, plugin_folder)
    # --- FIX 4 ---
    # Call execute() with no arguments.
    json_output = tool.execute()

    # Parse and store COMPLETE JSON in working memory for formatter plugins
    try:
        result_data = json.loads(json_output)
        
        if result_data.get('status') == 'success':
            # Store COMPLETE JSON output (as a dict)
            # Renamed key for consistency with other HARA steps
            cat.working_memory['asil_determination_complete_output'] = result_data
            
            # Also store main data (overwriting the old table)
            cat.working_memory['complete_hara_table'] = result_data['hazards']
            cat.working_memory['hara_hazardous_events'] = result_data['hazards']
            
            # Signal that data is ready for formatting
            cat.working_memory['last_operation'] = 'asil_determination_complete' # This key must match the formatter
            cat.working_memory['needs_formatting'] = True
            
            log.info("✅ Complete ASIL determination JSON stored in working_memory")
        
        elif result_data.get('status') == 'error':
            cat.working_memory['asil_determination_error'] = result_data # Use a distinct error key
            log.warning(f"⚠️ ASIL determination error: {result_data.get('message', 'Unknown error')}")
    
    except json.JSONDecodeError as e:
        log.error(f"❌ Could not parse ASIL determination output as JSON: {e}")
        cat.working_memory['asil_determination_error'] = {
            'status': 'error',
            'error_type': 'json_parse_error',
            'message': str(e)
        }

    # Return the raw JSON string
    return json_output


# --- FIX 5 ---
# Replaced the buggy 'show_asil_distribution' with 'show_asil_ratings',
# which follows the standard JSON "show" pattern for your formatter.
@tool(
    return_direct=True,
    examples=[
        "show asil ratings",
        "display asil table",
        "get asil json",
        "show complete hara table",
        "show asil distribution" # Added this example
    ]
)
def show_asil_ratings(tool_input, cat):
    """
    Retrieve ASIL determination results from working memory as complete JSON.
    
    Returns the COMPLETE HARA dataset including ASIL ratings and statistics.
    
    Available data includes:
    - Complete hazard objects with all fields:
      * hazard_id
      * hazardous_event
      * severity (S), exposure (E), controllability (C)
      * asil (QM, A, B, C, D)
      * asil_rationale
    - Statistics (total_hazards, asil_distribution)
    - System information (system_name, timestamp, etc.)
    
    Useful for:
    - Passing data to output formatter plugins
    - Exporting HARA results
    """
    
    log.info("🔧 TOOL CALLED: show_asil_ratings")
    
    # Try to get complete output first (preferred)
    complete_output = cat.working_memory.get('asil_determination_complete_output', None)
    
    if complete_output:
        log.info("✅ Returning complete ASIL determination output from working_memory")
        return json.dumps(complete_output, indent=2, ensure_ascii=False)
    
    # Fallback: reconstruct from individual components
    hazards = cat.working_memory.get('complete_hara_table', [])
    
    if not hazards:
        error_result = {
            "status": "error",
            "error_type": "no_data",
            "message": "No HARA results found in working memory",
            "suggestion": "Run HARA workflow: `apply hazop analysis`, `assess esc`, `determine asil`"
        }
        return json.dumps(error_result, indent=2)

    # Check if ASIL determination was run
    if 'asil' not in hazards[0]:
        error_result = {
            "status": "error",
            "error_type": "missing_asil_data",
            "message": "ASIL ratings not found in HARA table",
            "suggestion": "Run ASIL determination first: `determine asil`"
        }
        return json.dumps(error_result, indent=2)

    # Reconstruct complete output from components
    # We need the calculator to rebuild stats if we only have the table
    try:
        from generators.asil_calculator import ASILCalculator
        calculator = ASILCalculator()
        stats = calculator.calculate_asil_statistics(hazards)
    except Exception:
        stats = {"message": "Could not recalculate stats"}
        
    system_name = cat.working_memory.get('hara_item_name', 'System')
    
    output = {
        "status": "success",
        "analysis_type": "ASIL_Determination (Reconstructed)",
        "iso_standard": "ISO 26262-3:2018",
        "clause": "6.4.5",
        "system_name": system_name,
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "hazards": hazards,
        "total_hazards": len(hazards),
        "next_steps": [
             "Review ASIL ratings: `show asil ratings`",
             "Derive safety goals: `create safety goals from hazards`"
        ],
        "compliance_notes": ["ASIL ratings reconstructed from working memory"]
    }
    
    log.info("✅ Reconstructed complete ASIL determination output from working_memory components")
    
    return json.dumps(output, indent=2, ensure_ascii=False)


@tool(
    return_direct=True,
    examples=[
        "show asil matrix",
        "display asil determination table",
        "how is asil calculated"
    ]
)
def show_asil_matrix(tool_input, cat):
    """
    Display ISO 26262-3 ASIL determination matrix (Table 4).
    
    Shows:
    - How E/S/C combinations map to ASIL
    - Examples of each ASIL level
    
    Useful reference when reviewing ASIL assignments.
    """
    
    log.info("🔧 TOOL CALLED: show_asil_matrix")
    
    # This is static content, so it's fine as-is.
    
    return """📖 **ASIL Determination Matrix - ISO 26262-3:2018 Table 4**

The ASIL is determined by combining Exposure (E), Severity (S), and Controllability (C).

---

## Severity S1 (Light to Moderate Injuries)

| E \ C | C0 | C1 | C2 | C3 |
|---|---|---|---|---|
| **E1** | QM | QM | QM | A |
| **E2** | QM | QM | A | B |
| **E3** | QM | A | B | C |
| **E4** | QM | B | C | D |

---

## Severity S2 (Severe Injuries)

| E \ C | C0 | C1 | C2 | C3 |
|---|---|---|---|---|
| **E1** | QM | QM | A | B |
| **E2** | QM | A | B | C |
| **E3** | QM | B | C | D |
| **E4** | QM | C | D | D |

---

## Severity S3 (Life-threatening to Fatal)

| E \ C | C0 | C1 | C2 | C3 |
|---|---|---|---|---|
| **E1** | QM | A | B | C |
| **E2** | QM | B | C | D |
| **E3** | QM | C | D | D |
| **E4** | QM | D | D | D |

---

**Key Principles:**
- S0 (no injuries) always leads to QM
- E0 (no exposure) always leads to QM
- C0 (controllable) always leads to QM
- Higher values (S3, E4, C3) lead to higher ASIL
- ASIL D requires the most rigorous safety processes per ISO 26262"""