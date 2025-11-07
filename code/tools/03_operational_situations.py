# ==============================================================================
# tools/03_operational_situations.py
# Tool for defining operational situations for exposure assessment
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


class OperationalSituationsTool(ISO26262Tool):
    """
    Tool for defining operational situations for exposure assessment.
    
    Implements ISO 26262-3:2018, Clause 6.4.4 - Classification of hazardous events
    
    Returns complete JSON output for external formatting.
    Stores all data in working_memory for formatter plugins.
    """
    
    REQUIRED_DATA = ['hazop_results', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "") -> str:
        """Define operational situations and return complete JSON"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            error_result = {
                "status": "error",
                "error_type": "missing_prerequisites",
                "message": "Cannot define operational situations - missing required data",
                "missing_data": missing,
                "suggestions": [
                    "Complete HAZOP analysis first: `apply hazop analysis`",
                    f"Missing: {', '.join(missing)}"
                ]
            }
            return json.dumps(error_result, indent=2)
        
        # Get data
        hazop_results = self.get_workflow_data('hazop_results')
        item_name = self.get_workflow_data('hara_item_name')
        
        log.info(f"📋 Defining operational situations for: {item_name}")
        
        try:
            # Import scenarios generator
            from ..generators.scenarios_generator import ScenariosGenerator
            
            # Create generator
            generator = ScenariosGenerator(self.llm, self.plugin_folder)
            
            # Generate scenarios
            scenarios = generator.generate_scenarios(
                system_name=item_name,
                hazop_results=hazop_results
            )
            
            if not scenarios:
                error_result = {
                    "status": "error",
                    "error_type": "no_results",
                    "message": "Scenario generation produced no results",
                    "suggestions": [
                        "Provide more system context",
                        "Check LLM availability",
                        "Manually define scenarios using template",
                        "Retry generation"
                    ]
                }
                return json.dumps(error_result, indent=2)
            
            # Store results in working memory (for internal workflow)
            self.set_workflow_data('operational_situations', scenarios)
            self.set_workflow_data('hara_operational_situations', scenarios)  # Alias
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('situations_defined')
            
            # Calculate statistics
            stats = self._calculate_scenario_statistics(scenarios)
            
            log.info(f"✅ Defined {len(scenarios)} operational situations")
            
            # Build complete JSON output with ALL fields
            output = {
                "status": "success",
                "analysis_type": "Operational Situations",
                "iso_standard": "ISO 26262-3:2018",
                "clause": "6.4.4",
                "system_name": item_name,
                "timestamp": self._get_timestamp(),
                "statistics": {
                    "total_scenarios": stats['total'],
                    "exposure_distribution": stats['exposure_distribution'],
                    "total_duration_covered": stats['total_duration']
                },
                "scenarios": scenarios,  # Complete scenario list with all fields
                "next_steps": [
                    "Review scenarios: `show operational situations`",
                    "Add custom scenarios if needed: `add custom scenario`",
                    "Proceed to E/S/C assessment: `assess all hazards`"
                ],
                "compliance_notes": [
                    "Clause 6.4.4: Operational situations identified",
                    "Exposure ratings assigned per ISO 26262-3:2018 Table 4",
                    "Covers various driving conditions and environments"
                ]
            }
            
            return json.dumps(output, indent=2, ensure_ascii=False)
            
        except Exception as e:
            log.error(f"Scenario definition failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            error_result = {
                "status": "error",
                "error_type": "generation_failed",
                "message": f"Scenario definition failed: {str(e)}",
                "traceback": traceback.format_exc(),
                "suggestions": [
                    "Check system context",
                    "Verify HAZOP results exist",
                    "Retry generation",
                    "Contact support if issue persists"
                ]
            }
            return json.dumps(error_result, indent=2)
    
    def _calculate_scenario_statistics(self, scenarios: list) -> dict:
        """Calculate scenario statistics"""
        stats = {
            'total': len(scenarios),
            'exposure_distribution': {},
            'total_duration': 0
        }
        
        # Count by exposure class
        for scenario in scenarios:
            exposure = scenario.get('exposure_class', 'E0')
            stats['exposure_distribution'][exposure] = stats['exposure_distribution'].get(exposure, 0) + 1
            stats['total_duration'] += scenario.get('duration_percentage', 0)
        
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
        "define operational situations",
        "create operational scenarios",
        "identify driving situations"
    ]
)
def define_operational_situations(tool_input, cat):
    """
    Define operational situations for exposure assessment.
    
    This is Step 3 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.4).
    
    Operational situations are driving scenarios where hazards can occur.
    Each situation has:
    - Description of driving conditions
    - Vehicle state
    - Environmental conditions
    - Exposure rating (E0-E4) based on duration/frequency
    
    Returns complete JSON with ALL fields for external formatting.
    
    Args:
        tool_input: Optional - system context or custom scenarios
        cat: Cheshire Cat instance
    
    Returns:
        JSON string with complete operational situations data including:
        - status
        - analysis_type
        - iso_standard
        - clause
        - system_name
        - timestamp
        - statistics (total_scenarios, exposure_distribution, total_duration_covered)
        - scenarios (array with complete scenario objects)
        - next_steps
        - compliance_notes
    
    Example:
        User: "define operational situations"
        Output: Complete JSON with 5-7 operational scenarios
    """
    
    log.info("🔧 TOOL CALLED: define_operational_situations")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    situations_tool = OperationalSituationsTool(cat, plugin_folder)
    json_output = situations_tool.execute(tool_input)
    
    # Parse and store COMPLETE JSON in working memory for formatter plugins
    try:
        result_data = json.loads(json_output)
        
        if result_data.get('status') == 'success':
            # Store COMPLETE JSON output - formatter can access ALL fields
            cat.working_memory['operational_situations_complete_output'] = result_data
            
            # Also store individual components for backward compatibility
            cat.working_memory['operational_situations'] = result_data['scenarios']
            cat.working_memory['hara_operational_situations'] = result_data['scenarios']
            cat.working_memory['situations_statistics'] = result_data['statistics']
            cat.working_memory['situations_system_name'] = result_data['system_name']
            cat.working_memory['situations_timestamp'] = result_data['timestamp']
            cat.working_memory['situations_iso_standard'] = result_data['iso_standard']
            cat.working_memory['situations_clause'] = result_data['clause']
            cat.working_memory['situations_next_steps'] = result_data['next_steps']
            cat.working_memory['situations_compliance_notes'] = result_data['compliance_notes']
            
            # Signal that data is ready for formatting
            cat.working_memory['last_operation'] = 'operational_situations_defined'
            cat.working_memory['needs_formatting'] = True
            
            log.info("✅ Complete operational situations JSON stored in working_memory")
            log.info(f"✅ {len(result_data['scenarios'])} scenarios available for formatting")
        
        elif result_data.get('status') == 'error':
            # Store error for potential error handling by formatter
            cat.working_memory['situations_error'] = result_data
            log.warning(f"⚠️ Operational situations error: {result_data.get('message', 'Unknown error')}")
    
    except json.JSONDecodeError as e:
        log.error(f"❌ Could not parse operational situations output as JSON: {e}")
        cat.working_memory['situations_error'] = {
            'status': 'error',
            'error_type': 'json_parse_error',
            'message': str(e)
        }
    
    return json_output


@tool(
    return_direct=True,
    examples=[
        "show operational situations",
        "list scenarios",
        "display driving situations",
        "get scenarios json"
    ]
)
def show_operational_situations(tool_input, cat):
    """
    Retrieve operational situations from working memory as complete JSON.
    
    Returns the COMPLETE operational situations dataset with all fields.
    
    Available data includes:
    - Complete scenario objects with all fields:
      * scenario_id
      * name
      * description
      * exposure_class
      * duration_percentage
      * vehicle_state
      * environmental_conditions
      * rationale
      * metadata (system_name, created_date, iso_standard, clause)
    - Statistics (total_scenarios, exposure_distribution, total_duration_covered)
    - System information (system_name, timestamp, iso_standard, clause)
    - Next steps and compliance notes
    
    Useful for:
    - Passing data to output formatter plugins
    - Exporting operational situations
    - Further analysis or processing
    """
    
    log.info("🔧 TOOL CALLED: show_operational_situations")
    
    # Try to get complete output first (preferred)
    complete_output = cat.working_memory.get('operational_situations_complete_output', None)
    
    if complete_output:
        log.info("✅ Returning complete operational situations output from working_memory")
        return json.dumps(complete_output, indent=2, ensure_ascii=False)
    
    # Fallback: reconstruct from individual components
    scenarios = cat.working_memory.get('operational_situations', [])
    
    if not scenarios:
        error_result = {
            "status": "error",
            "error_type": "no_data",
            "message": "No operational situations found in working memory",
            "suggestion": "Define scenarios first: `define operational situations`"
        }
        return json.dumps(error_result, indent=2)
    
    # Reconstruct complete output from components
    stats = cat.working_memory.get('situations_statistics', {})
    system_name = cat.working_memory.get('situations_system_name',
                                         cat.working_memory.get('hara_item_name', 'System'))
    timestamp = cat.working_memory.get('situations_timestamp', '')
    iso_standard = cat.working_memory.get('situations_iso_standard', 'ISO 26262-3:2018')
    clause = cat.working_memory.get('situations_clause', '6.4.4')
    next_steps = cat.working_memory.get('situations_next_steps', [])
    compliance_notes = cat.working_memory.get('situations_compliance_notes', [])
    
    output = {
        "status": "success",
        "analysis_type": "Operational Situations",
        "iso_standard": iso_standard,
        "clause": clause,
        "system_name": system_name,
        "timestamp": timestamp,
        "statistics": stats,
        "scenarios": scenarios,
        "total_scenarios": len(scenarios),
        "next_steps": next_steps,
        "compliance_notes": compliance_notes
    }
    
    log.info("✅ Reconstructed complete operational situations output from working_memory components")
    
    return json.dumps(output, indent=2, ensure_ascii=False)


@tool(
    return_direct=True,
    examples=[
        "add custom scenario",
        "define specific situation"
    ]
)
def add_custom_scenario(tool_input, cat):
    """
    Add a custom operational situation.
    
    Allows defining project-specific scenarios not covered
    by standard templates.
    
    Input format:
    "Add scenario: [name] | [description] | [exposure: E0-E4] | [duration: %]"
    
    Example:
        "Add scenario: Extreme Cold Weather | Driving in -30°C conditions | E1 | 2"
    
    Returns:
        JSON with updated scenarios list
    """
    
    log.info("🔧 TOOL CALLED: add_custom_scenario")
    
    # Parse input
    if isinstance(tool_input, str) and '|' in tool_input:
        parts = [p.strip() for p in tool_input.split('|')]
        
        if len(parts) >= 3:
            name = parts[0].replace('Add scenario:', '').strip()
            description = parts[1]
            exposure = parts[2].replace('exposure:', '').strip().upper()
            duration = float(parts[3]) if len(parts) > 3 else 5.0
            
            # Get existing scenarios
            complete_output = cat.working_memory.get('operational_situations_complete_output', None)
            
            if complete_output:
                scenarios = complete_output['scenarios']
            else:
                scenarios = cat.working_memory.get('operational_situations', [])
            
            # Create custom scenario
            from datetime import datetime
            custom_scenario = {
                'scenario_id': f"OS-CUSTOM-{len(scenarios) + 1:03d}",
                'name': name,
                'description': description,
                'exposure_class': exposure if exposure.startswith('E') else f'E{exposure}',
                'duration_percentage': duration,
                'vehicle_state': 'Custom scenario - state as described',
                'environmental_conditions': 'As described',
                'rationale': 'Custom scenario added by user',
                'metadata': {
                    'system_name': cat.working_memory.get('hara_item_name', 'System'),
                    'created_date': datetime.now().isoformat(),
                    'iso_standard': 'ISO 26262-3:2018',
                    'clause': '6.4.4',
                    'custom': True
                }
            }
            
            # Add to scenarios
            scenarios.append(custom_scenario)
            
            # Update working memory
            if complete_output:
                complete_output['scenarios'] = scenarios
                complete_output['statistics']['total_scenarios'] = len(scenarios)
                cat.working_memory['operational_situations_complete_output'] = complete_output
            
            cat.working_memory['operational_situations'] = scenarios
            cat.working_memory['hara_operational_situations'] = scenarios
            cat.working_memory['needs_formatting'] = True  # Signal to OutputFormatter
            
            # Return JSON result
            result = {
                "status": "success",
                "message": "Custom scenario added",
                "scenario_added": custom_scenario,
                "total_scenarios": len(scenarios)
            }
            
            log.info(f"✅ Added custom scenario: {name}")
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        
    error_result = {
        "status": "error",
        "error_type": "invalid_format",
        "message": "Invalid input format",
        "expected_format": "Add scenario: [name] | [description] | [exposure: E0-E4] | [duration: %]",
        "example": "Add scenario: Extreme Cold Weather | Driving in -30°C conditions | E1 | 2"
    }
    
    return json.dumps(error_result, indent=2)


# ==============================================================================
# Utility function for external plugins
# ==============================================================================

def get_operational_situations_for_formatting(cat) -> dict:
    """
    Utility function for formatter plugins to get complete operational situations data.
    
    This function can be imported by your formatter plugin:
    
    from tools.03_operational_situations import get_operational_situations_for_formatting
    
    situations_data = get_operational_situations_for_formatting(cat)
    
    Returns:
        Complete operational situations data dictionary, or None if no data available
    """
    return cat.working_memory.get('operational_situations_complete_output', None)