# ==============================================================================
# code/tools/esc_assessment_tool.py
# Tool for assessing Exposure, Severity, and Controllability
# ==============================================================================

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

from ..generators.esc_generator import ESCGenerator


@tool(
    return_direct=True,
    examples=[
        "assess esc for all hazards",
        "evaluate exposure severity controllability",
        "perform esc assessment"
    ]
)
def assess_esc_for_hazards(tool_input, cat):
    """
    Assess Exposure, Severity, and Controllability for all hazards.
    
    This is Step 4 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.4).
    
    For each hazard from HAZOP analysis:
    - **Exposure (E0-E4):** How often does the operational situation occur?
    - **Severity (S0-S3):** How severe are potential injuries?
    - **Controllability (C0-C3):** Can drivers avoid harm?
    
    Each rating requires detailed rationale.
    
    Args:
        tool_input: Optional - "all" or specific hazard ID
        cat: Cheshire Cat instance
    
    Returns:
        Complete HARA table with E/S/C ratings
    
    Example:
        User: "assess esc for all hazards"
        Output: HARA table with E/S/C columns filled
    """
    
    log.info("🔧 TOOL CALLED: assess_esc_for_hazards")
    
    # Get data from working memory
    hazop_results = cat.working_memory.get('hazop_results', [])
    scenarios = cat.working_memory.get('operational_situations', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Results Available**

**Action Required:** Complete HAZOP analysis first

**Workflow:**
1. ✅ Extract functions
2. ❌ Apply HAZOP ← Complete this first
3. ❓ Define operational situations
4. ❓ Assess E/S/C"""
    
    if not scenarios:
        return """❌ **No Operational Situations Defined**

**Action Required:** Define operational situations first

Use: `define operational situations`

**Workflow:**
1. ✅ Extract functions
2. ✅ Apply HAZOP
3. ❌ Define operational situations ← Complete this first
4. ❓ Assess E/S/C"""
    
    log.info(f"📋 Assessing E/S/C for {len(hazop_results)} hazards")
    
    try:
        # Create ESC generator
        generator = ESCGenerator(cat.llm, plugin_folder)
        
        # Perform E/S/C assessment
        hazards = generator.assess_esc(
            hazop_results=hazop_results,
            scenarios=scenarios,
            system_name=item_name
        )
        
        if not hazards:
            return """❌ **E/S/C Assessment Failed**

**Possible causes:**
- LLM unable to perform assessment
- Insufficient context
- Invalid HAZOP/scenario data

**Try:**
- Verify HAZOP results are valid
- Check operational situations
- Retry assessment"""
        
        # Store results in working memory
        cat.working_memory['complete_hara_table'] = hazards
        cat.working_memory['hara_stage'] = 'esc_assessed'
        
        # Set formatter flags
        cat.working_memory['needs_formatting'] = True
        cat.working_memory['last_operation'] = 'esc_assessment'
        
        log.info(f"✅ E/S/C assessment complete for {len(hazards)} hazards")
        
        # Calculate statistics
        stats = generator.calculate_esc_statistics(hazards)
        
        # Build simple response (formatter will beautify)
        response = f"""Successfully assessed E/S/C for {item_name}.

Total hazards assessed: {len(hazards)}

Severity Distribution:
- S3 (Life-threatening): {stats['severity']['S3']}
- S2 (Severe injuries): {stats['severity']['S2']}
- S1 (Moderate injuries): {stats['severity']['S1']}
- S0 (No injuries): {stats['severity']['S0']}

Exposure Distribution:
- E4 (High): {stats['exposure']['E4']}
- E3 (Medium): {stats['exposure']['E3']}
- E2 (Low): {stats['exposure']['E2']}
- E1 (Very low): {stats['exposure']['E1']}
- E0 (Incredibly unlikely): {stats['exposure']['E0']}

Controllability Distribution:
- C3 (Difficult/uncontrollable): {stats['controllability']['C3']}
- C2 (Normally controllable): {stats['controllability']['C2']}
- C1 (Simply controllable): {stats['controllability']['C1']}
- C0 (Controllable in general): {stats['controllability']['C0']}

Next step: Determine ASIL ratings based on E/S/C combinations."""
        
        return response
        
    except Exception as e:
        log.error(f"E/S/C assessment failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"""❌ **E/S/C Assessment Error**

**Error:** {str(e)}

**Debug Info:**
- HAZOP results: {len(hazop_results)} items
- Scenarios: {len(scenarios)} items

**Try:**
- Verify data integrity
- Check LLM availability
- Retry assessment"""


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
    
    hazards = cat.working_memory.get('complete_hara_table', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazards:
        return """❌ **No HARA Table Available**

**Action:** Complete E/S/C assessment first: `assess esc for all hazards`"""
    
    # Get statistics
    from generators.esc_generator import ESCGenerator
    generator = ESCGenerator(None, None)
    stats = generator.calculate_esc_statistics(hazards)
    
    output = f"""📋 **HARA Table: {item_name}**

**Total Hazards:** {len(hazards)}

**E/S/C Distribution:**

Severity: S3={stats['severity']['S3']}, S2={stats['severity']['S2']}, S1={stats['severity']['S1']}, S0={stats['severity']['S0']}
Exposure: E4={stats['exposure']['E4']}, E3={stats['exposure']['E3']}, E2={stats['exposure']['E2']}, E1={stats['exposure']['E1']}, E0={stats['exposure']['E0']}
Controllability: C3={stats['controllability']['C3']}, C2={stats['controllability']['C2']}, C1={stats['controllability']['C1']}, C0={stats['controllability']['C0']}

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
2. Proceed to ASIL determination: `determine asil for all hazards`"""
    
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

**Note:** Assessments should consider:
- Average drivers (not experts or novices)
- Realistic response times
- Available information to driver
- Vehicle dynamics and physics"""