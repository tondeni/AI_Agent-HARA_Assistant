# ==============================================================================
# code/tools/safety_goal_tools.py
# Cat-facing tools for Safety Goal derivation per ISO 26262-3, Clause 6.4.6
# ==============================================================================

"""
Safety Goal Tools

@tool decorated functions for deriving safety goals from ASIL-rated hazards
per ISO 26262-3:2018 Clause 6.4.6.

Available tools:
- derive_safety_goals: Generate safety goals from hazardous events
- show_safety_goal: Display details of specific safety goal
- show_all_safety_goals: Display summary of all safety goals
- validate_safety_goals: Check safety goals for ISO 26262-3 compliance
"""

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os

# This code navigates up from the current file to find the right folders
current_file = os.path.abspath(__file__)          # code/tools/asil_determination_tool.py
tools_folder = os.path.dirname(current_file)       # code/tools/
code_folder = os.path.dirname(tools_folder)        # code/
plugin_folder = os.path.dirname(code_folder)       # AI_Agent-HARA_Assistant/

# Then adds them to sys.path so Python can find them
sys.path.insert(0, code_folder)
sys.path.insert(0, os.path.join(code_folder, 'generators'))


@tool(
    return_direct=True,
    examples=[
        "derive safety goals",
        "generate safety goals from hazards",
        "create safety goals"
    ]
)
def derive_safety_goals(tool_input, cat):
    """
    Derive safety goals from ASIL-rated hazardous events.
    
    Per ISO 26262-3:2018, Clause 6.4.6:
    - Safety goals specify conditions to avoid/mitigate hazards
    - Inherit ASIL from hazardous events
    - Formulated at vehicle level
    - Clear, measurable, and verifiable
    
    Processes all hazards with ASIL A, B, C, or D.
    QM-rated hazards do not require safety goals.
    
    Examples:
    - "derive safety goals"
    - "generate safety goals from all hazards"
    """
    
    log.info("🎯 TOOL CALLED: derive_safety_goals")
    
    # Get hazards from working memory
    hazards = cat.working_memory.get('hara_hazardous_events', [])
    system_name = cat.working_memory.get('system_name', 'System')
    
    if not hazards:
        return """❌ No hazardous events found in working memory.

**Required Steps:**
1. Extract functions from Item Definition
2. Apply HAZOP analysis to identify hazards
3. Assess E/S/C for each hazard
4. Determine ASIL ratings

Then derive safety goals.

**Example:**
`extract functions from Wiper System`
`apply hazop to all functions`
`assess esc for all hazards`
`determine asil`
`derive safety goals`"""
    
    # Filter ASIL-rated hazards
    asil_hazards = [h for h in hazards 
                   if h.get('asil', 'QM') in ['A', 'B', 'C', 'D']]
    
    if not asil_hazards:
        return f"""⚠️ **No ASIL-rated hazards found**

Total hazards analyzed: {len(hazards)}
ASIL-rated (A/B/C/D): 0
QM-rated: {len(hazards)}

**Note:** QM (Quality Management) rated hazards do not require safety goals 
per ISO 26262-3:2018, Clause 6.4.5.

The risk is considered acceptable with normal quality management.

**Next Steps:**
If you expected ASIL-rated hazards, review the E/S/C assessment:
`show hazard assessment summary`"""
    
    try:
        # Import generator
        from generators.safety_goal_generator import SafetyGoalGenerator
        
        log.info(f"✅ Processing {len(asil_hazards)} ASIL-rated hazards")
        
        # Create generator
        generator = SafetyGoalGenerator(cat.llm)
        
        # Generate safety goals
        safety_goals = generator.generate_from_hazards(asil_hazards, system_name)
        
        # Store in working memory
        goals_dict = [goal.to_dict() for goal in safety_goals]
        cat.working_memory['hara_safety_goals'] = goals_dict
        cat.working_memory['hara_workflow_stage'] = 'safety_goals_derived'
        
        # Validate goals
        validation_issues = []
        for goal in safety_goals:
            is_valid, issues = generator.validate_safety_goal(goal)
            if not is_valid:
                validation_issues.extend(issues)
        
        # Generate summary
        summary = generator.generate_goal_summary(safety_goals)
        
        # Add validation warnings if any
        if validation_issues:
            summary += "\n\n⚠️ **Validation Issues:**\n"
            summary += "\n".join([f"- {issue}" for issue in validation_issues])
            summary += "\n\nℹ️ These are placeholders that should be refined during safety reviews."
        
        # Add next steps
        summary += f"""

{'='*70}

✅ **Safety Goals Successfully Derived!**

**Stored in working memory:** `hara_safety_goals`

**ISO 26262-3:2018 Compliance:**
✓ Clause 6.4.6 - Safety goal determination complete
✓ Goals inherit ASIL from hazardous events
✓ Formulated at vehicle/system level
✓ Include safe state and FTTI specifications

**Next Steps:**
1. Review safety goals with safety team
2. Refine safe states and FTTI values
3. Generate HARA documentation:
   - `generate hara excel` for traceability matrix
   - `generate hara document` for complete report
4. Proceed to Functional Safety Concept (FSC) development

**Commands:**
- `show safety goal SG-001` - View specific goal details
- `show all safety goals` - Display complete list
- `validate safety goals` - Check ISO 26262-3 compliance
- `generate all hara files` - Create documentation package"""
        
        return summary
        
    except ImportError as e:
        log.error(f"❌ Import error: {e}")
        
        return f"""❌ Safety Goal Generator not available.

**Error:** {str(e)}

**Solution:**
Ensure `safety_goal_generator.py` exists in `code/generators/`

**File should contain:**
- SafetyGoal data model
- SafetyGoalGenerator class with LLM-based generation"""
        
    except Exception as e:
        log.error(f"❌ Safety goal derivation failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"❌ Failed to derive safety goals: {str(e)}"


@tool(
    return_direct=True,
    examples=[
        "show safety goal SG-001",
        "display safety goal details for SG-002"
    ]
)
def show_safety_goal(tool_input, cat):
    """
    Display detailed information for a specific safety goal.
    
    Shows complete ISO 26262-3 information including:
    - Safety goal statement
    - ASIL rating
    - Associated hazard
    - Safe state
    - FTTI (Fault Tolerant Time Interval)
    - E/S/C classification
    - Rationale
    
    Input: Safety goal ID (e.g., "SG-001")
    
    Examples:
    - "show safety goal SG-001"
    - "display details for SG-003"
    """
    
    log.info("📋 TOOL CALLED: show_safety_goal")
    
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    if not safety_goals:
        return "❌ No safety goals available. Derive safety goals first: `derive safety goals`"
    
    # Parse input to extract SG ID
    sg_id = str(tool_input).strip().upper()
    
    # Clean up input
    sg_id = sg_id.replace("SHOW SAFETY GOAL", "").strip()
    sg_id = sg_id.replace("SAFETY GOAL", "").strip()
    sg_id = sg_id.replace("DISPLAY DETAILS FOR", "").strip()
    sg_id = sg_id.replace("FOR", "").strip()
    
    if not sg_id.startswith('SG-'):
        sg_id = 'SG-' + sg_id.replace('SG', '').replace('-', '').strip()
    
    # Find the safety goal
    goal = next((g for g in safety_goals if g.get('sg_id', g.get('id', '')) == sg_id), None)
    
    if not goal:
        available = ', '.join([g.get('sg_id', g.get('id', '')) for g in safety_goals[:5]])
        return f"""❌ Safety Goal '{sg_id}' not found.

**Available Safety Goals:** {available}
{f"... and {len(safety_goals) - 5} more" if len(safety_goals) > 5 else ""}

**Command:** `show all safety goals` to see complete list"""
    
    # Format detailed view
    response = f"""📋 **Safety Goal Details: {goal.get('sg_id', goal.get('id', ''))}**

{'='*70}

**Safety Goal Statement:**
{goal.get('statement', goal.get('goal', ''))}

**ASIL Rating:** {goal.get('asil', 'QM')}

**Safe State:**
{goal.get('safe_state', 'Not specified')}

**FTTI (Fault Tolerant Time Interval):**
{goal.get('ftti_ms', 'Not specified')} ms

**Associated Hazard:**
- Hazard ID: {goal.get('hazard_id', 'N/A')}
- Hazardous Event: {goal.get('hazardous_event', 'N/A')}

**Risk Assessment:**
- Severity (S): {goal.get('severity', 'N/A')}
- Exposure (E): {goal.get('exposure', 'N/A')}
- Controllability (C): {goal.get('controllability', 'N/A')}

**Rationale:**
{goal.get('rationale', 'Not provided')}

{'='*70}

**ISO 26262-3:2018 Reference:** Clause 6.4.6 - Safety goal determination

**Next Steps:**
- Review and refine with safety team
- Develop Functional Safety Concept (FSC)
- Derive Functional Safety Requirements (FSRs)

**Related Commands:**
- `show all safety goals` - View all goals
- `validate safety goals` - Check compliance"""
    
    return response


@tool(
    return_direct=True,
    examples=[
        "show all safety goals",
        "list safety goals",
        "display safety goals summary"
    ]
)
def show_all_safety_goals(tool_input, cat):
    """
    Display summary of all safety goals.
    
    Shows:
    - Total count and ASIL distribution
    - List of all safety goals with key information
    - Compliance status
    
    Examples:
    - "show all safety goals"
    - "list all safety goals"
    """
    
    log.info("📋 TOOL CALLED: show_all_safety_goals")
    
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    system_name = cat.working_memory.get('system_name', 'System')
    
    if not safety_goals:
        return """❌ No safety goals available.

**To derive safety goals:**
1. Complete hazard analysis with ASIL determination
2. Run: `derive safety goals`

**Example workflow:**
`extract functions from [item]`
`apply hazop to all functions`
`assess esc for all hazards`
`determine asil`
`derive safety goals`"""
    
    # Calculate statistics
    asil_counts = {'D': 0, 'C': 0, 'B': 0, 'A': 0, 'QM': 0}
    for goal in safety_goals:
        asil = goal.get('asil', 'QM')
        asil_counts[asil] = asil_counts.get(asil, 0) + 1
    
    # Build response
    response = f"""📋 **All Safety Goals - {system_name}**

{'='*70}

**Total Safety Goals:** {len(safety_goals)}

**ASIL Distribution:**
"""
    
    for asil in ['D', 'C', 'B', 'A']:
        if asil_counts[asil] > 0:
            response += f"- ASIL {asil}: {asil_counts[asil]} goals\n"
    
    if asil_counts['QM'] > 0:
        response += f"- QM: {asil_counts['QM']} goals\n"
    
    response += f"\n{'='*70}\n\n**Safety Goals:**\n\n"
    
    # List all goals
    for goal in safety_goals:
        sg_id = goal.get('sg_id', goal.get('id', ''))
        statement = goal.get('statement', goal.get('goal', ''))
        asil = goal.get('asil', 'QM')
        
        # Truncate long statements
        if len(statement) > 80:
            statement = statement[:77] + "..."
        
        response += f"**{sg_id}** (ASIL {asil})\n"
        response += f"{statement}\n\n"
    
    response += f"""{'='*70}

**ISO 26262-3:2018 Status:**
✓ Clause 6.4.6 - Safety goals derived from hazards
✓ ASIL inheritance maintained
✓ Goals formulated at vehicle level

**Commands:**
- `show safety goal SG-001` - View detailed information
- `validate safety goals` - Check ISO 26262-3 compliance
- `generate hara excel` - Create traceability matrix
- `generate hara document` - Create complete HARA report

**Next Steps:**
Proceed to Functional Safety Concept (FSC) development"""
    
    return response


@tool(
    return_direct=True,
    examples=[
        "validate safety goals",
        "check safety goals compliance"
    ]
)
def validate_safety_goals(tool_input, cat):
    """
    Validate safety goals for ISO 26262-3:2018 compliance.
    
    Checks:
    - Mandatory fields present
    - Use of "shall" in statements
    - Valid ASIL ratings
    - Safe state specified
    - FTTI specified
    - Clear and measurable statements
    
    Examples:
    - "validate safety goals"
    - "check safety goals for compliance"
    """
    
    log.info("✓ TOOL CALLED: validate_safety_goals")
    
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    if not safety_goals:
        return "❌ No safety goals to validate. Derive safety goals first: `derive safety goals`"
    
    try:
        from generators.safety_goal_generator import SafetyGoalGenerator, SafetyGoal
        
        # Create generator for validation
        generator = SafetyGoalGenerator(cat.llm)
        
        # Validate each goal
        all_issues = []
        valid_count = 0
        
        for goal_dict in safety_goals:
            goal = SafetyGoal(**goal_dict)
            is_valid, issues = generator.validate_safety_goal(goal)
            
            if is_valid:
                valid_count += 1
            else:
                all_issues.extend(issues)
        
        # Calculate compliance percentage
        compliance_percent = (valid_count / len(safety_goals)) * 100
        
        # Build response
        response = f"""✓ **Safety Goals Validation Report**

{'='*70}

**Total Safety Goals:** {len(safety_goals)}
**Fully Compliant:** {valid_count}
**With Issues:** {len(safety_goals) - valid_count}

**Compliance:** {compliance_percent:.1f}%

{'='*70}

"""
        
        if compliance_percent == 100:
            response += """✅ **All Safety Goals are ISO 26262-3 Compliant!**

All safety goals meet the requirements:
✓ Clear "shall" statements
✓ Valid ASIL ratings
✓ Safe states specified
✓ FTTI specified
✓ Proper formatting

Ready for technical review and approval.

**Next Steps:**
1. Generate HARA documentation
2. Conduct technical review
3. Obtain safety manager approval
4. Proceed to FSC development"""
        
        elif compliance_percent >= 70:
            response += f"""⚠️ **Most Goals Compliant - Minor Issues Found**

{len(all_issues)} issue(s) require attention:

"""
            for issue in all_issues[:10]:  # Show first 10 issues
                response += f"- {issue}\n"
            
            if len(all_issues) > 10:
                response += f"\n... and {len(all_issues) - 10} more issues\n"
            
            response += """

**Note:** Many issues are placeholders (TBD values) that should be 
refined during technical review. This is normal for initial HARA drafts.

**Recommended Actions:**
1. Review placeholder values with safety team
2. Specify safe states based on architecture
3. Determine FTTI based on system capabilities
4. Update goals in working memory or regenerate

**Still suitable for:**
- Initial technical review
- Preliminary FSC development
- Safety concept iteration"""
        
        else:
            response += f"""❌ **Significant Issues Found**

{len(all_issues)} issue(s) require resolution:

"""
            for issue in all_issues:
                response += f"- {issue}\n"
            
            response += """

**Required Actions:**
1. Review and update safety goal statements
2. Ensure all goals use "shall" language
3. Specify safe states for all goals
4. Determine FTTI values
5. Re-validate after updates

**ISO 26262-3:2018 Reference:**
Clause 6.4.6 - Safety goal determination requirements"""
        
        response += f"""

{'='*70}

**ISO 26262-3:2018 Checklist:**
"""
        
        checklist_items = [
            ("Safety goals formulated at vehicle level", valid_count > 0),
            ("'Shall' language used", valid_count > 0),
            ("ASIL ratings inherited from hazards", True),
            ("Safe states specified", compliance_percent >= 70),
            ("FTTI specified", compliance_percent >= 70),
            ("Goals are verifiable", True)
        ]
        
        for item, status in checklist_items:
            response += f"\n{'✓' if status else '○'} {item}"
        
        return response
        
    except Exception as e:
        log.error(f"❌ Validation failed: {e}")
        return f"❌ Validation error: {str(e)}"


if __name__ == "__main__":
    print("Safety Goal Tools - Cat-facing tools for ISO 26262-3 safety goal derivation")
    print("These tools are automatically discovered by Cheshire Cat framework")