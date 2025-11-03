# ==============================================================================
# tools/06_safety_goals.py
# Tool for deriving safety goals from ASIL-rated hazards
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

from iso26262_base import ISO26262Tool, WorkflowManager


class SafetyGoalsTool(ISO26262Tool):
    """
    Tool for deriving safety goals from hazardous events.
    
    Implements ISO 26262-3:2018, Clause 6.4.6 - Safety goal determination
    """
    
    REQUIRED_DATA = ['complete_hara_table', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "all") -> str:
        """Derive safety goals from ASIL-rated hazards"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self.format_error(
                "Cannot derive safety goals - missing required data",
                [
                    "Complete HARA workflow steps first",
                    "Determine ASIL ratings: `determine asil`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        hazards = self.get_workflow_data('complete_hara_table')
        item_name = self.get_workflow_data('hara_item_name')
        
        # Filter ASIL-rated hazards (A, B, C, D)
        asil_hazards = [h for h in hazards if h.get('asil', 'QM') in ['A', 'B', 'C', 'D']]
        
        if not asil_hazards:
            qm_count = len([h for h in hazards if h.get('asil') == 'QM'])
            return self.format_warning(
                "No ASIL-rated hazards found",
                [
                    f"Total hazards analyzed: {len(hazards)}",
                    f"QM-rated: {qm_count}",
                    "",
                    "QM (Quality Management) rated hazards do not require safety goals per ISO 26262-3:2018, Clause 6.4.5.",
                    "The risk is considered acceptable with normal quality management."
                ]
            ) + "\n\n**Next Steps:**\nIf you expected ASIL-rated hazards, review the E/S/C assessment: `show hara table`"
        
        log.info(f"📋 Deriving safety goals for {len(asil_hazards)} ASIL-rated hazards")
        
        try:
            # Import safety goal generator
            from generators.safety_goal_generator import SafetyGoalGenerator
            
            # Create generator
            generator = SafetyGoalGenerator(self.llm)
            
            # Generate safety goals
            safety_goals = generator.generate_from_hazards(asil_hazards, item_name)
            
            # Store in working memory
            goals_dict = [goal.to_dict() for goal in safety_goals]
            self.set_workflow_data('hara_safety_goals', goals_dict)
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('safety_goals_derived')
            
            # Validate goals
            validation_issues = []
            for goal in safety_goals:
                is_valid, issues = generator.validate_safety_goal(goal)
                if not is_valid:
                    validation_issues.extend(issues)
            
            # Generate summary
            summary = generator.generate_goal_summary(safety_goals)
            
            log.info(f"✅ Derived {len(safety_goals)} safety goals")
            
            # Add validation warnings if any
            response = summary
            if validation_issues:
                response += "\n\n⚠️ **Validation Issues:**\n"
                response += "\n".join([f"- {issue}" for issue in validation_issues[:5]])
                if len(validation_issues) > 5:
                    response += f"\n... and {len(validation_issues) - 5} more issues"
                response += "\n\nℹ️ These are placeholders that should be refined during safety reviews."
            
            # Add next steps
            response += f"\n\n{'='*70}\n\n"
            response += self.format_success(
                "Safety Goals Successfully Derived!",
                {
                    "Total Safety Goals": len(safety_goals),
                    "ASIL D Goals": len([g for g in safety_goals if g.asil == 'D']),
                    "ASIL C Goals": len([g for g in safety_goals if g.asil == 'C']),
                    "ASIL B Goals": len([g for g in safety_goals if g.asil == 'B']),
                    "ASIL A Goals": len([g for g in safety_goals if g.asil == 'A'])
                },
                [
                    "Review safety goals with safety team",
                    "Refine safe states and FTTI values",
                    "Generate HARA documentation: `generate hara excel`"
                ]
            )
            
            response += "\n\n**ISO 26262-3:2018 Compliance:**\n"
            response += "✓ Clause 6.4.6: Safety goal determination complete\n"
            response += "✓ Goals inherit ASIL from hazardous events\n"
            response += "✓ Formulated at vehicle/system level\n"
            response += "✓ Include safe state and FTTI specifications"
            
            return response
            
        except Exception as e:
            log.error(f"Safety goal derivation failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                f"Safety goal derivation failed: {str(e)}",
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
        "create safety goals from hazards"
    ]
)
def derive_safety_goals(tool_input, cat):
    """
    Derive safety goals from ASIL-rated hazards.
    
    This is Step 6 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.6).
    
    For each hazard with ASIL rating (A, B, C, or D):
    - Formulate safety goal at vehicle/system level
    - Inherit ASIL rating from hazardous event
    - Define safe state
    - Specify Fault Tolerant Time Interval (FTTI)
    
    QM-rated hazards do not require safety goals.
    
    Args:
        tool_input: Optional - "all" or specific hazard ID
        cat: Cheshire Cat instance
    
    Returns:
        List of safety goals with ASIL ratings
    
    Example:
        User: "derive safety goals"
        Output: Safety goals for all ASIL-rated hazards
    """
    
    log.info("🔧 TOOL CALLED: derive_safety_goals")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = SafetyGoalsTool(cat, plugin_folder)
    return tool.execute(tool_input if tool_input else "all")


@tool(
    return_direct=True,
    examples=[
        "show safety goals",
        "list safety goals",
        "display derived safety goals"
    ]
)
def show_safety_goals(tool_input, cat):
    """
    Display derived safety goals from working memory.
    
    Shows:
    - Safety goal ID and description
    - ASIL rating
    - Safe state
    - FTTI
    - Associated hazard
    
    Useful for reviewing before document generation.
    """
    
    log.info("🔧 TOOL CALLED: show_safety_goals")
    
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not safety_goals:
        return """❌ **No Safety Goals Found**

**Action:** Derive safety goals first: `derive safety goals`"""
    
    output = f"""📋 **Safety Goals: {item_name}**

**Total Safety Goals:** {len(safety_goals)}

**ASIL Distribution:**
"""
    
    # Count by ASIL
    asil_counts = {}
    for goal in safety_goals:
        asil = goal.get('asil', 'QM')
        asil_counts[asil] = asil_counts.get(asil, 0) + 1
    
    for asil in ['D', 'C', 'B', 'A']:
        if asil in asil_counts:
            output += f"- ASIL {asil}: {asil_counts[asil]} goals\n"
    
    output += "\n**Safety Goals:**\n\n"
    
    for idx, goal in enumerate(safety_goals, 1):
        output += f"{idx}. **{goal.get('id', 'SG-???')}** (ASIL {goal.get('asil', '?')})\n"
        output += f"   {goal.get('description', 'N/A')[:100]}...\n"
        output += f"   Safe State: {goal.get('safe_state', 'TBD')}\n"
        output += f"   FTTI: {goal.get('ftti', 'TBD')}\n\n"
    
    output += """---

**Next Steps:**
1. Review and refine safety goals
2. Generate HARA documentation: `generate hara excel`
3. Proceed to FSC development"""
    
    return output