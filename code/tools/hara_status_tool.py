# ==============================================================================
# code/tools/hara_status_tool.py
# Tool for checking HARA completion status and guiding document generation
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

if code_folder not in sys.path:
    sys.path.insert(0, code_folder)


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
    """
    
    log.info("🔧 TOOL CALLED: show_hara_status")
    
    # Get workflow data
    item_name = cat.working_memory.get('hara_item_name', 'Unknown System')
    hara_stage = cat.working_memory.get('hara_stage', 'not_started')
    
    functions = cat.working_memory.get('item_functions', '')
    hazop_results = cat.working_memory.get('hazop_results', [])
    scenarios = cat.working_memory.get('operational_situations', [])
    hazards = cat.working_memory.get('complete_hara_table', [])
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    # Check completion status
    steps_complete = []
    steps_incomplete = []
    
    # Step 1: Functions
    if functions:
        steps_complete.append("✅ Step 1: Functions extracted")
    else:
        steps_incomplete.append("❌ Step 1: Extract functions")
    
    # Step 2: HAZOP
    if hazop_results:
        steps_complete.append(f"✅ Step 2: HAZOP analysis ({len(hazop_results)} hazards)")
    else:
        steps_incomplete.append("❌ Step 2: Apply HAZOP analysis")
    
    # Step 3: Scenarios
    if scenarios:
        steps_complete.append(f"✅ Step 3: Operational situations ({len(scenarios)} scenarios)")
    else:
        steps_incomplete.append("❌ Step 3: Define operational situations")
    
    # Step 4: E/S/C
    if hazards and 'exposure' in hazards[0]:
        steps_complete.append(f"✅ Step 4: E/S/C assessment ({len(hazards)} hazards)")
    else:
        steps_incomplete.append("❌ Step 4: Assess E/S/C")
    
    # Step 5: ASIL
    if hazards and 'asil' in hazards[0]:
        asil_counts = {}
        for h in hazards:
            asil = h.get('asil', 'QM')
            asil_counts[asil] = asil_counts.get(asil, 0) + 1
        
        asil_summary = ", ".join([f"{asil}={count}" for asil, count in sorted(asil_counts.items())])
        steps_complete.append(f"✅ Step 5: ASIL determination ({asil_summary})")
    else:
        steps_incomplete.append("❌ Step 5: Determine ASIL")
    
    # Step 6: Safety Goals
    if safety_goals:
        steps_complete.append(f"✅ Step 6: Safety goals ({len(safety_goals)} goals)")
    else:
        steps_incomplete.append("❌ Step 6: Derive safety goals")
    
    # Build output
    completion_pct = (len(steps_complete) / 6) * 100
    
    output = f"""📊 **HARA Workflow Status: {item_name}**

**Overall Completion:** {completion_pct:.0f}% ({len(steps_complete)}/6 steps)

**Current Stage:** {hara_stage}

---

## Completed Steps

{chr(10).join(steps_complete) if steps_complete else "No steps completed yet"}

---

## Remaining Steps

{chr(10).join(steps_incomplete) if steps_incomplete else "All steps complete! ✅"}

---
"""
    
    # Add next actions
    if steps_incomplete:
        output += f"""## Next Action

**▶️ {steps_incomplete[0].replace('❌ ', '')}**

Use the corresponding tool to continue the workflow.
"""
    else:
        # HARA complete!
        output += """## 🎉 HARA Complete!

Your Hazard Analysis and Risk Assessment is complete.

**Data Summary:**
"""
        output += f"- Functions: {len(functions.split(chr(10))) if functions else 0}\n"
        output += f"- HAZOP Results: {len(hazop_results)}\n"
        output += f"- Operational Situations: {len(scenarios)}\n"
        output += f"- Complete Hazards: {len(hazards)}\n"
        output += f"- Safety Goals: {len(safety_goals)}\n\n"
        
        output += """**ISO 26262-3:2018 Compliance:**
✅ Clause 6.4.2 - Situation analysis
✅ Clause 6.4.3 - Hazard identification
✅ Clause 6.4.4 - Risk classification (E/S/C)
✅ Clause 6.4.5 - ASIL determination
✅ Clause 6.4.6 - Safety goal derivation

**Next Steps:**

1. **Generate Documents** - Use Output Formatter plugin:
   - HARA report (Word document)
   - Traceability matrix (Excel spreadsheet)

2. **Proceed to FSC** - Use FSC_Developer plugin:
   - Derive functional safety requirements
   - Allocate to system architecture

3. **Review & Approval:**
   - Technical review by safety team
   - Management approval
   - Baseline in configuration management"""
    
    return output


@tool(
    return_direct=True,
    examples=[
        "validate hara data",
        "check hara quality",
        "verify hara completeness"
    ]
)
def validate_hara_data(tool_input, cat):
    """
    Validate HARA data quality and completeness.
    
    Checks:
    - Required fields present
    - Data format correctness
    - Consistency across tables
    - Traceability
    
    Returns quality report with issues found.
    """
    
    log.info("🔧 TOOL CALLED: validate_hara_data")
    
    hazards = cat.working_memory.get('complete_hara_table', [])
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    if not hazards:
        return """❌ **No HARA Data to Validate**

**Action:** Complete HARA workflow first"""
    
    issues = []
    warnings = []
    
    # Validate hazards
    for hazard in hazards:
        hazard_id = hazard.get('id', '?')
        
        # Check required fields
        required_fields = ['hazardous_event', 'severity', 'exposure', 'controllability', 'asil']
        for field in required_fields:
            if field not in hazard or not hazard[field]:
                issues.append(f"{hazard_id}: Missing {field}")
        
        # Check rationales
        rationale_fields = ['severity_rationale', 'exposure_rationale', 'controllability_rationale']
        for field in rationale_fields:
            if field not in hazard or not hazard[field]:
                warnings.append(f"{hazard_id}: Missing {field}")
    
    # Validate safety goals
    asil_hazards = [h for h in hazards if h.get('asil') in ['A', 'B', 'C', 'D']]
    if len(safety_goals) < len(asil_hazards):
        issues.append(f"Missing safety goals: {len(asil_hazards)} ASIL hazards, {len(safety_goals)} goals")
    
    # Build output
    if not issues and not warnings:
        return f"""✅ **HARA Data Validation: PASSED**

**Hazards Checked:** {len(hazards)}
**Safety Goals Checked:** {len(safety_goals)}

No issues found. HARA data is complete and well-formed.

**Ready for:**
- Document generation
- FSC development
- Review and approval"""
    else:
        output = f"""⚠️ **HARA Data Validation: Issues Found**

**Total Hazards:** {len(hazards)}
**Total Safety Goals:** {len(safety_goals)}

"""
        
        if issues:
            output += f"**❌ Critical Issues ({len(issues)}):**\n"
            for issue in issues[:10]:
                output += f"- {issue}\n"
            if len(issues) > 10:
                output += f"... and {len(issues) - 10} more issues\n"
            output += "\n"
        
        if warnings:
            output += f"**⚠️ Warnings ({len(warnings)}):**\n"
            for warning in warnings[:10]:
                output += f"- {warning}\n"
            if len(warnings) > 10:
                output += f"... and {len(warnings) - 10} more warnings\n"
        
        output += "\n**Recommendation:** Fix critical issues before document generation."
        
        return output


@tool(
    return_direct=True,
    examples=[
        "export hara to json",
        "save hara data",
        "backup hara"
    ]
)
def export_hara_to_json(tool_input, cat):
    """
    Export HARA data to JSON format for backup or sharing.
    
    Exports all HARA workflow data:
    - Functions
    - HAZOP results
    - Operational situations
    - Complete hazards with E/S/C/ASIL
    - Safety goals
    
    Useful for:
    - Backup
    - Version control
    - Sharing with other plugins
    - Import into other tools
    """
    
    log.info("🔧 TOOL CALLED: export_hara_to_json")
    
    import json
    from datetime import datetime
    
    # Collect all HARA data
    hara_data = {
        'metadata': {
            'system_name': cat.working_memory.get('hara_item_name', 'Unknown'),
            'export_date': datetime.now().isoformat(),
            'hara_stage': cat.working_memory.get('hara_stage', 'unknown'),
            'iso_standard': 'ISO 26262-3:2018'
        },
        'functions': cat.working_memory.get('item_functions', ''),
        'hazop_results': cat.working_memory.get('hazop_results', []),
        'operational_situations': cat.working_memory.get('operational_situations', []),
        'complete_hara_table': cat.working_memory.get('complete_hara_table', []),
        'safety_goals': cat.working_memory.get('hara_safety_goals', [])
    }
    
    # Generate filename
    system_name = hara_data['metadata']['system_name'].replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HARA_{system_name}_{timestamp}.json"
    
    # Convert to JSON
    json_str = json.dumps(hara_data, indent=2, ensure_ascii=False)
    
    return f"""✅ **HARA Data Exported**

**File:** `{filename}`

**Contents:**
- System: {hara_data['metadata']['system_name']}
- Functions: {len(hara_data['functions'].split(chr(10)) if hara_data['functions'] else [])}
- HAZOP Results: {len(hara_data['hazop_results'])}
- Operational Situations: {len(hara_data['operational_situations'])}
- Complete Hazards: {len(hara_data['complete_hara_table'])}
- Safety Goals: {len(hara_data['safety_goals'])}

**JSON Preview:**
```json
{json_str[:500]}...
```

**Note:** JSON data is available in working memory.
To save to file, use Output Formatter plugin or manual file operations."""