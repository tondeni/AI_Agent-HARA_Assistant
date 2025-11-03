# ==============================================================================
# tools/utils_status.py
# Utility tools for checking HARA workflow status
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
code_folder = os.path.dirname(tools_folder)

# Add modules to path
sys.path.insert(0, os.path.join(code_folder, 'core'))

from iso26262_base import WorkflowManager


@tool(
    return_direct=True,
    examples=[
        "show hara status",
        "check hara completion",
        "is hara complete",
        "hara workflow status"
    ]
)
def show_hara_status(tool_input, cat):
    """
    Show HARA workflow completion status.
    
    Displays:
    - Completed steps
    - Remaining steps
    - Data quality indicators
    - Next actions
    - Document generation readiness
    
    Use this to verify HARA is complete before generating documents.
    
    Example:
        User: "show hara status"
        Output: Complete workflow status with next steps
    """
    
    log.info("🔧 TOOL CALLED: show_hara_status")
    
    # Create workflow manager
    workflow = WorkflowManager(cat)
    
    # Get status
    current_stage = workflow.get_current_stage()
    completion_status = workflow.get_completion_status()
    progress = workflow.get_progress_percentage()
    next_step = workflow.get_next_step()
    ready_for_docs, missing_steps = workflow.is_ready_for_document_generation()
    
    # Get item name if available
    item_name = cat.working_memory.get('hara_item_name', 'No item loaded')
    
    output = f"""📊 **HARA Workflow Status**

**System:** {item_name}
**Progress:** {progress}% Complete
**Current Stage:** {workflow.STAGE_NAMES.get(current_stage, current_stage)}

---

## Step Completion

"""
    
    # Format each step with icon
    steps = [
        ('functions_extracted', '1. Extract Functions'),
        ('hazop_complete', '2. Apply HAZOP Analysis'),
        ('situations_defined', '3. Define Operational Situations'),
        ('esc_assessed', '4. Assess E/S/C'),
        ('asil_determined', '5. Determine ASIL'),
        ('safety_goals_derived', '6. Derive Safety Goals')
    ]
    
    for key, name in steps:
        icon = "✅" if completion_status.get(key) else "❌"
        output += f"{icon} {name}\n"
    
    output += "\n---\n\n"
    
    # Add data summary
    output += "## Data Summary\n\n"
    
    functions_count = len(cat.working_memory.get('item_functions', '').split('\n'))
    hazop_count = len(cat.working_memory.get('hazop_results', []))
    situations_count = len(cat.working_memory.get('operational_situations', []))
    hara_table_count = len(cat.working_memory.get('complete_hara_table', []))
    safety_goals_count = len(cat.working_memory.get('hara_safety_goals', []))
    
    output += f"- **Functions:** {functions_count}\n"
    output += f"- **HAZOP Results:** {hazop_count} hazards\n"
    output += f"- **Operational Situations:** {situations_count} scenarios\n"
    output += f"- **HARA Table:** {hara_table_count} assessed hazards\n"
    output += f"- **Safety Goals:** {safety_goals_count} goals\n"
    
    output += "\n---\n\n"
    
    # Next steps
    if ready_for_docs:
        output += "## Status: Ready for Document Generation ✅\n\n"
        output += "**Action:** Generate HARA documentation\n"
        output += "```\ngenerate hara excel\n```"
    elif next_step:
        output += f"## Next Step\n\n**Action:** {next_step}\n"
    else:
        output += "## Status: Workflow Complete ✅\n\n"
    
    # Add warnings if needed
    if not ready_for_docs and missing_steps:
        output += "\n**⚠️ Missing for Document Generation:**\n"
        for step in missing_steps:
            output += f"- {step.replace('_', ' ').title()}\n"
    
    output += "\n---\n\n**ISO 26262-3:2018 Compliance:**\n"
    output += f"Completed {sum(1 for v in completion_status.values() if v)} of 6 required steps"
    
    return output


@tool(
    return_direct=True,
    examples=[
        "show workflow progress",
        "what is the progress",
        "hara progress bar"
    ]
)
def show_workflow_progress(tool_input, cat):
    """
    Show visual workflow progress.
    
    Displays a simple progress bar and percentage completion.
    
    Example:
        User: "show workflow progress"
        Output: Progress bar visualization
    """
    
    log.info("🔧 TOOL CALLED: show_workflow_progress")
    
    workflow = WorkflowManager(cat)
    progress = workflow.get_progress_percentage()
    completion_status = workflow.get_completion_status()
    
    # Create progress bar
    filled = int(progress / 5)  # 20 blocks for 100%
    empty = 20 - filled
    bar = "█" * filled + "░" * empty
    
    output = f"""📊 **Workflow Progress**

{bar} {progress}%

**Completed Steps:** {sum(1 for v in completion_status.values() if v)}/6

"""
    
    # List completed steps
    completed = [k for k, v in completion_status.items() if v]
    if completed:
        output += "**✅ Completed:**\n"
        for step in completed:
            output += f"- {step.replace('_', ' ').title()}\n"
    
    # List remaining steps
    remaining = [k for k, v in completion_status.items() if not v]
    if remaining:
        output += "\n**❌ Remaining:**\n"
        for step in remaining:
            output += f"- {step.replace('_', ' ').title()}\n"
    
    return output


@tool(
    return_direct=True,
    examples=[
        "what data do I have",
        "show working memory",
        "list hara data"
    ]
)
def show_hara_data_summary(tool_input, cat):
    """
    Show summary of data stored in working memory.
    
    Displays:
    - What data is available
    - Data counts
    - Data quality indicators
    
    Useful for debugging or understanding current state.
    
    Example:
        User: "what data do I have"
        Output: Summary of all HARA data
    """
    
    log.info("🔧 TOOL CALLED: show_hara_data_summary")
    
    wm = cat.working_memory
    
    output = """📋 **HARA Data Summary**

**Working Memory Contents:**

"""
    
    # Check each key data item
    data_items = [
        ('hara_item_name', 'Item Name'),
        ('item_definition_content', 'Item Definition'),
        ('item_functions', 'Functions'),
        ('hazop_results', 'HAZOP Results'),
        ('operational_situations', 'Operational Situations'),
        ('hara_operational_situations', 'Operational Situations (alt)'),
        ('complete_hara_table', 'Complete HARA Table'),
        ('hara_hazardous_events', 'Hazardous Events'),
        ('hara_safety_goals', 'Safety Goals'),
        ('hara_workflow_stage', 'Workflow Stage'),
        ('hara_stage', 'Stage (legacy)')
    ]
    
    for key, name in data_items:
        if key in wm:
            value = wm[key]
            
            if isinstance(value, str):
                length = len(value)
                output += f"✅ **{name}:** {length} characters\n"
            elif isinstance(value, list):
                length = len(value)
                output += f"✅ **{name}:** {length} items\n"
            else:
                output += f"✅ **{name}:** Present\n"
        else:
            output += f"❌ **{name}:** Not found\n"
    
    output += "\n---\n\n**Data Quality:**\n"
    
    # Check data quality
    issues = []
    
    if wm.get('item_functions') and not wm.get('hazop_results'):
        issues.append("Functions extracted but HAZOP not performed")
    
    if wm.get('hazop_results') and not wm.get('operational_situations'):
        issues.append("HAZOP complete but operational situations not defined")
    
    if wm.get('complete_hara_table'):
        table = wm['complete_hara_table']
        if isinstance(table, list) and table:
            has_esc = all('exposure' in h and 'severity' in h and 'controllability' in h for h in table)
            has_asil = all('asil' in h for h in table)
            
            if not has_esc:
                issues.append("HARA table missing E/S/C ratings")
            elif not has_asil:
                issues.append("HARA table missing ASIL ratings")
    
    if issues:
        for issue in issues:
            output += f"⚠️ {issue}\n"
    else:
        output += "✅ All data appears complete\n"
    
    return output


@tool(
    return_direct=True,
    examples=[
        "clear hara data",
        "reset workflow",
        "start over"
    ]
)
def clear_hara_workflow(tool_input, cat):
    """
    Clear HARA workflow data from working memory.
    
    ⚠️ WARNING: This will delete all HARA work in progress!
    
    Use this to start a new HARA analysis.
    
    Example:
        User: "clear hara data"
        Output: Confirmation and reset working memory
    """
    
    log.info("🔧 TOOL CALLED: clear_hara_workflow")
    
    # Keys to clear
    keys_to_clear = [
        'hara_item_name',
        'item_definition_content',
        'item_functions',
        'hazop_results',
        'operational_situations',
        'hara_operational_situations',
        'complete_hara_table',
        'hara_hazardous_events',
        'hara_safety_goals',
        'hara_workflow_stage',
        'hara_stage'
    ]
    
    cleared_count = 0
    for key in keys_to_clear:
        if key in cat.working_memory:
            del cat.working_memory[key]
            cleared_count += 1
    
    log.info(f"🗑️ Cleared {cleared_count} HARA data items")
    
    return f"""🗑️ **HARA Workflow Cleared**

**Cleared {cleared_count} data items from working memory**

You can now start a new HARA analysis:
```
extract functions from [New System Name]
```

**Note:** Previously generated documents are NOT deleted.
They remain in the `generated_documents/` folder."""


@tool(
    return_direct=True,
    examples=[
        "show next step",
        "what should I do next",
        "next action"
    ]
)
def show_next_hara_step(tool_input, cat):
    """
    Show the next recommended workflow step.
    
    Analyzes current state and recommends next action.
    
    Example:
        User: "what should I do next"
        Output: Recommended next step with example command
    """
    
    log.info("🔧 TOOL CALLED: show_next_hara_step")
    
    workflow = WorkflowManager(cat)
    next_step = workflow.get_next_step()
    current_stage = workflow.get_current_stage()
    
    if not next_step:
        return """✅ **HARA Workflow Complete!**

All steps are complete. You can now:
1. Generate documentation: `generate hara excel`
2. Review safety goals: `show safety goals`
3. Start FSC development"""
    
    output = f"""➡️ **Next Step in HARA Workflow**

**Current Stage:** {workflow.STAGE_NAMES.get(current_stage, current_stage)}

**Recommended Action:**
```
{next_step}
```

"""
    
    # Add context-specific help
    if 'extract functions' in next_step:
        output += """**Example:**
```
extract functions from Battery Management System
```

This will analyze the Item Definition and identify 4-5 safety-relevant functions."""
    
    elif 'hazop' in next_step:
        output += """**What happens next:**
- Applies 10 HAZOP guide words to each function
- Identifies ~40-50 potential malfunctioning behaviors
- Estimates preliminary severity (S0-S3)"""
    
    elif 'operational situations' in next_step:
        output += """**What happens next:**
- Defines 5-7 driving scenarios
- Assigns exposure ratings (E0-E4)
- Covers urban, highway, parking, adverse weather"""
    
    elif 'esc' in next_step:
        output += """**What happens next:**
- Assesses Exposure (E0-E4) for each hazard
- Assesses Severity (S0-S3) for injuries
- Assesses Controllability (C0-C3) for driver capability"""
    
    elif 'asil' in next_step:
        output += """**What happens next:**
- Applies ISO 26262-3 Table 4 matrix
- Determines ASIL (QM, A, B, C, D) for each hazard
- Identifies high-priority safety concerns"""
    
    elif 'safety goals' in next_step:
        output += """**What happens next:**
- Derives safety goals from ASIL-rated hazards
- Specifies safe states
- Defines FTTI (Fault Tolerant Time Interval)"""
    
    return output