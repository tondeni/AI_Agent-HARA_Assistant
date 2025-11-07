# ==============================================================================
# tools/04_esc_assessment.py
# Tool for assessing Exposure, Severity, and Controllability
# Refactored to use ISO26262Tool base class
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os

#Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
code_folder = os.path.dirname(tools_folder) # Renamed for clarity
plugin_folder = os.path.dirname(code_folder) # Get the actual plugin root

# Add modules to path
sys.path.insert(0, os.path.join(code_folder, 'core'))
sys.path.insert(0, os.path.join(code_folder, 'generators')) # Corrected path

from iso26262_base import ISO26262Tool, WorkflowManager


class ESCAssessmentTool(ISO26262Tool):
    """
    Tool for assessing Exposure, Severity, and Controllability.
    
    Implements ISO 26262-3:2018, Clause 6.4.4 - Classification of hazardous events
    """
    
    REQUIRED_DATA = ['hazop_results', 'operational_situations', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def _format_json_output(self, hazards: list, system_name: str, stats: dict) -> dict:
        """Format E/S/C assessment as complete JSON structure with all metadata."""
        from datetime import datetime
        
        output = {
            "status": "success",
            "analysis_type": "ESC_Assessment",
            "iso_standard": "ISO 26262-3:2018",
            "clause": "6.4.4 - Classification of hazardous events",
            "system_name": system_name,
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_hazards": len(hazards),
                "severity_distribution": {
                    "S3": stats['severity'].get('S3', 0),
                    "S2": stats['severity'].get('S2', 0),
                    "S1": stats['severity'].get('S1', 0),
                    "S0": stats['severity'].get('S0', 0)
                },
                "exposure_distribution": {
                    "E4": stats['exposure'].get('E4', 0),
                    "E3": stats['exposure'].get('E3', 0),
                    "E2": stats['exposure'].get('E2', 0),
                    "E1": stats['exposure'].get('E1', 0),
                    "E0": stats['exposure'].get('E0', 0)
                },
                "controllability_distribution": {
                    "C3": stats['controllability'].get('C3', 0),
                    "C2": stats['controllability'].get('C2', 0),
                    "C1": stats['controllability'].get('C1', 0),
                    "C0": stats['controllability'].get('C0', 0)
                }
            },
            "hazards": [],
            "next_steps": [
                "Review E/S/C ratings and rationales",
                "Proceed to ASIL determination: `run asil determination`",
                "Validate ratings with safety experts"
            ],
            "compliance_notes": [
                "✓ Clause 6.4.4: E/S/C classification complete",
                "✓ Severity based on injury potential",
                "✓ Exposure based on operational situation probability",
                "✓ Controllability based on driver capability"
            ]
        }
        
        for hazard in hazards:
            hazard_data = {
                "hazard_id": hazard.get('id', 'H-???'),
                "function_id": hazard.get('function_id', 'F-??'),
                "function_name": hazard.get('function_name', 'Unknown'),
                "guide_word": hazard.get('guide_word', 'N/A'),
                "malfunction": hazard.get('malfunctioning_behavior', 'N/A'),
                "hazardous_event": hazard.get('hazardous_event', 'N/A'),
                "driving_scenario": hazard.get('operational_situation', 'General operation'),
                "severity": {
                    "rating": hazard.get('severity', 'S?'),
                    "rationale": hazard.get('severity_rationale', 'Not provided')
                },
                "exposure": {
                    "rating": hazard.get('exposure', 'E?'),
                    "rationale": hazard.get('exposure_rationale', 'Not provided')
                },
                "controllability": {
                    "rating": hazard.get('controllability', 'C?'),
                    "rationale": hazard.get('controllability_rationale', 'Not provided')
                }
            }
            output["hazards"].append(hazard_data)
        
        return output
    
    def _format_json_error(self, message: str, error_type: str, suggestions: list = None) -> str:
        """Format error as JSON string."""
        import json
        from datetime import datetime
        
        error_data = {
            "status": "error",
            "analysis_type": "ESC_Assessment",
            "iso_standard": "ISO 26262-3:2018",
            "clause": "6.4.4 - Classification of hazardous events",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "suggestions": suggestions or []
        }
        
        return json.dumps(error_data, indent=2, ensure_ascii=False)
    
    def execute(self, tool_input: str = "all") -> str:
        """Assess E/S/C for all hazards"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            # Provide specific guidance based on what's missing
            if 'hazop_results' in missing:
                return self._format_json_error(
                    "No HAZOP results available",
                    "missing_prerequisites",
                    ["Complete HAZOP analysis first: `apply hazop analysis`"]
                )
            elif 'operational_situations' in missing:
                return self._format_json_error(
                    "No operational situations defined",
                    "missing_prerequisites",
                    ["Define operational situations first: `define operational situations`"]
                )
            else:
                return self._format_json_error(
                    f"Missing required data: {', '.join(missing)}",
                    "missing_prerequisites",
                    ["Complete previous workflow steps"]
                )
        
        # Get data
        hazop_results = self.get_workflow_data('hazop_results')
        scenarios = self.get_workflow_data('operational_situations')
        item_name = self.get_workflow_data('hara_item_name')
        
        log.info(f"📋 Assessing E/S/C for {len(hazop_results)} hazards")
        
        try:
            # Import ESC generator
            from ..generators.esc_generator import ESCGenerator
            
            # Create generator
            generator = ESCGenerator(self.llm, self.plugin_folder)
            
            # Perform E/S/C assessment
            hazards = generator.assess_esc(
                hazop_results=hazop_results,
                scenarios=scenarios,
                system_name=item_name
            )
            
            if not hazards:
                return self._format_json_error(
                    "E/S/C assessment produced no results",
                    "assessment_failed",
                    [
                        "Verify HAZOP results are valid",
                        "Check operational situations",
                        "Verify LLM availability",
                        "Retry assessment"
                    ]
                )
            
            # Store results
            self.set_workflow_data('complete_hara_table', hazards)
            self.set_workflow_data('hara_hazardous_events', hazards)
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('esc_assessed')
            
            log.info(f"✅ E/S/C assessment complete for {len(hazards)} hazards")
            
            # Calculate statistics
            stats = generator.calculate_esc_statistics(hazards)
            
            # Format output as JSON
            output_data = self._format_json_output(hazards, item_name, stats)
            
            # Save JSON to file
            import json
            output_file = f"/mnt/user-data/outputs/esc_assessment_{item_name.replace(' ', '_').lower()}.json"
            os.makedirs("/mnt/user-data/outputs", exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ JSON saved to: {output_file}")
            
            # Return JSON string for tool decorator to parse and store
            return json.dumps(output_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            log.error(f"E/S/C assessment failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self._format_json_error(
                f"E/S/C assessment failed: {str(e)}",
                "execution_error",
                [
                    "Verify data integrity",
                    "Check LLM availability",
                    "Retry assessment"
                ]
            )



# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

@tool(
    return_direct=True,
    examples=[
        "assess all hazards",
        "assess esc",
        "run esc assessment",
        "perform E/S/C classification"
    ]
)
def assess_esc_for_hazards(tool_input, cat):
    """
    Assesses Exposure (E), Severity (S), and Controllability (C) for all hazards.
    
    This is Step 4 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.4).
    It uses the HAZOP results and Operational Situations to classify each hazard.
    
    Returns a complete JSON report with E/S/C ratings, statistics, 
    and compliance notes for external formatting.
    
    Args:
        tool_input: This argument is ignored. The tool always runs for ALL hazards.
        cat: Cheshire Cat instance
    
    Returns:
        JSON string with complete E/S/C assessment data.
    """
    
    log.info("🔧 TOOL CALLED: assess_esc_for_hazards")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = ESCAssessmentTool(cat, plugin_folder)
    # We pass "all" to the execute method, ignoring user input
    json_output = tool.execute("all")
    
    # Parse and store COMPLETE JSON in working memory for formatter plugins
    import json
    try:
        result_data = json.loads(json_output)
        
        if result_data.get('status') == 'success':
            # Store COMPLETE JSON output - formatter can access ALL fields
            cat.working_memory['esc_assessment_complete_output'] = result_data
            
            # The 'execute' method already saved the correct 'complete_hara_table'
            # (which contains the raw S,E,C data) to working memory.
            # We just store the other metadata here for the formatter.
            cat.working_memory['esc_statistics'] = result_data['statistics']
            cat.working_memory['esc_system_name'] = result_data['system_name']
            cat.working_memory['esc_timestamp'] = result_data['timestamp']
            cat.working_memory['esc_iso_standard'] = result_data['iso_standard']
            cat.working_memory['esc_clause'] = result_data['clause']
            cat.working_memory['esc_next_steps'] = result_data['next_steps']
            cat.working_memory['esc_compliance_notes'] = result_data['compliance_notes']
            
            # Signal that data is ready for formatting
            cat.working_memory['last_operation'] = 'esc_assessment_complete'
            cat.working_memory['needs_formatting'] = True
            
            log.info("✅ Complete E/S/C assessment JSON stored in working_memory")
            log.info(f"✅ 'complete_hara_table' (from generator) is safe in working_memory")
        
        elif result_data.get('status') == 'error':
            # Store error for potential error handling by formatter
            cat.working_memory['esc_assessment_error'] = result_data
            log.warning(f"⚠️ E/S/C assessment error: {result_data.get('message', 'Unknown error')}")
    
    except json.JSONDecodeError as e:
        log.error(f"❌ Could not parse E/S/C assessment output as JSON: {e}")
        cat.working_memory['esc_assessment_error'] = {
            'status': 'error',
            'error_type': 'json_parse_error',
            'message': str(e)
        }
    
    return json_output


@tool(
    return_direct=True,
    examples=[
        "show hara table",
        "display esc assessment",
        "view hazard ratings"
    ]
)
def show_hara_table(tool_input, cat):
    """
    Display complete HARA table with E/S/C ratings.
    
    Shows:
    - Hazard ID
    - Hazardous event
    - Operational situation
    - Severity (S), Exposure (E), Controllability (C)
    - Rationales
    
    Useful for reviewing before ASIL determination.
    """
    
    log.info("🔧 TOOL CALLED: show_hara_table")
    
    hazards = cat.working_memory.get('complete_hara_table', []) or \
              cat.working_memory.get('hara_hazardous_events', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazards:
        return """❌ **No HARA Table Available**

**Action:** Complete E/S/C assessment first: `assess esc for all hazards`"""
    
    # Check if E/S/C assessed
    first_hazard = hazards[0]
    if not all(key in first_hazard for key in ['exposure', 'severity', 'controllability']):
        return """❌ **E/S/C Assessment Incomplete**

**Action:** Assess E/S/C first: `assess esc for all hazards`"""
    
    # Calculate statistics
    stats = {
        'severity': {},
        'exposure': {},
        'controllability': {}
    }
    
    for hazard in hazards:
        s = hazard.get('severity', 'S0')
        e = hazard.get('exposure', 'E0')
        c = hazard.get('controllability', 'C0')
        
        stats['severity'][s] = stats['severity'].get(s, 0) + 1
        stats['exposure'][e] = stats['exposure'].get(e, 0) + 1
        stats['controllability'][c] = stats['controllability'].get(c, 0) + 1
    
    output = f"""📋 **HARA Table: {item_name}**

**Total Hazards:** {len(hazards)}

**E/S/C Distribution:**

Severity: S3={stats['severity'].get('S3', 0)}, S2={stats['severity'].get('S2', 0)}, S1={stats['severity'].get('S1', 0)}, S0={stats['severity'].get('S0', 0)}
Exposure: E4={stats['exposure'].get('E4', 0)}, E3={stats['exposure'].get('E3', 0)}, E2={stats['exposure'].get('E2', 0)}, E1={stats['exposure'].get('E1', 0)}, E0={stats['exposure'].get('E0', 0)}
Controllability: C3={stats['controllability'].get('C3', 0)}, C2={stats['controllability'].get('C2', 0)}, C1={stats['controllability'].get('C1', 0)}, C0={stats['controllability'].get('C0', 0)}

**Sample Hazards (first 5):**

"""
    
    for idx, hazard in enumerate(hazards[:5], 1):
        output += f"{idx}. **{hazard.get('id', 'H-???')}**: {hazard.get('hazardous_event', 'N/A')[:60]}...\n"
        output += f"   E: {hazard.get('exposure', '?')} | S: {hazard.get('severity', '?')} | C: {hazard.get('controllability', '?')}\n\n"
    
    if len(hazards) > 5:
        output += f"... and {len(hazards) - 5} more hazards\n\n"
    
    output += """---

**Next Steps:**
1. Review E/S/C ratings and rationales
2. Proceed to ASIL determination: `determine asil`"""
    
    return output


@tool(
    return_direct=True,
    examples=[
        "show esc rating scales",
        "explain esc ratings",
        "what are esc criteria"
    ]
)
def show_esc_rating_scales(tool_input, cat):
    """
    Display E/S/C rating scales and criteria.
    
    Shows ISO 26262-3:2018 rating definitions for:
    - Severity (S0-S3)
    - Exposure (E0-E4)
    - Controllability (C0-C3)
    
    Useful reference when performing assessments.
    """
    
    log.info("🔧 TOOL CALLED: show_esc_rating_scales")
    
    return """📖 **E/S/C Rating Scales - ISO 26262-3:2018**

## Severity (S)
**S0 - No injuries**
- No injuries possible

**S1 - Light to moderate injuries**
- Recoverable injuries
- Examples: Bruises, minor cuts, whiplash

**S2 - Severe injuries (survival probable)**
- Serious injuries but survival probable
- Examples: Broken bones, severe lacerations, internal injuries

**S3 - Life-threatening to fatal injuries**
- Critical injuries or fatalities
- Examples: Spinal injuries, severe head trauma, death

---

## Exposure (E)
**E0 - Incredibly unlikely** (<0.001% of operating time)
- Extremely rare situations
- Example: Specific combination of multiple rare events

**E1 - Very low probability** (0.001% to 0.1% of operating time)
- Rare situations
- Example: Extreme weather + specific road conditions

**E2 - Low probability** (0.1% to 1% of operating time)
- Uncommon situations
- Example: Heavy rain driving

**E3 - Medium probability** (1% to 10% of operating time)
- Occasional situations
- Example: Urban driving with pedestrians

**E4 - High probability** (≥10% of operating time)
- Common situations
- Example: Normal highway driving

---

## Controllability (C)
**C0 - Controllable in general**
- Hazard generally avoidable
- More than 99% of drivers can handle it

**C1 - Simply controllable**
- Most drivers can handle it
- ≥99% of drivers can avoid harm

**C2 - Normally controllable**
- Average drivers can handle it
- ≥90% of drivers can avoid harm

**C3 - Difficult to control or uncontrollable**
- Only expert drivers might avoid harm
- <90% of drivers can avoid harm

---

**Assessment Guidelines:**
- Consider average drivers (not experts or novices)
- Account for realistic response times
- Evaluate available information to driver
- Consider vehicle dynamics and physics"""