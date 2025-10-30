# ==============================================================================
# code/tools/asil_determination_tool.py
# Tool for determining ASIL based on E/S/C ratings
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

from ..generators.asil_calculator import ASILCalculator


@tool(
    return_direct=True,
    examples=[
        "determine asil for all hazards",
        "calculate asil ratings",
        "apply asil determination"
    ]
)
def determine_asil(tool_input, cat):
    """
    Determine ASIL ratings based on E/S/C combinations.
    
    This is Step 5 of the HARA workflow (ISO 26262-3:2018, Clause 6.4.5).
    
    Applies the ISO 26262-3 Table 4 ASIL determination matrix:
    - Combines Exposure (E), Severity (S), Controllability (C)
    - Determines ASIL: QM, A, B, C, or D
    - Validates all ratings
    
    Args:
        tool_input: Optional - "all" or specific hazard ID
        cat: Cheshire Cat instance
    
    Returns:
        HARA table with ASIL ratings assigned
    
    Example:
        User: "determine asil for all hazards"
        Output: ASIL distribution and updated HARA table
    """
    
    log.info("🔧 TOOL CALLED: determine_asil")
    
    # Get data from working memory
    hazards = cat.working_memory.get('complete_hara_table', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazards:
        return """❌ **No HARA Table Available**

**Action Required:** Complete E/S/C assessment first

Use: `assess esc for all hazards`

**Workflow:**
1. ✅ Extract functions
2. ✅ Apply HAZOP
3. ✅ Define operational situations
4. ❌ Assess E/S/C ← Complete this first
5. ❓ Determine ASIL"""
    
    # Verify E/S/C ratings exist
    first_hazard = hazards[0]
    if not all(key in first_hazard for key in ['exposure', 'severity', 'controllability']):
        return """❌ **Incomplete E/S/C Ratings**

**Issue:** Hazards missing E/S/C ratings

**Action:** Run E/S/C assessment: `assess esc for all hazards`"""
    
    log.info(f"📋 Determining ASIL for {len(hazards)} hazards")
    
    try:
        # Create ASIL calculator
        calculator = ASILCalculator()
        
        # Determine ASIL for all hazards
        updated_hazards = calculator.determine_asil_for_hazards(hazards)
        
        # Store updated hazards
        cat.working_memory['complete_hara_table'] = updated_hazards
        cat.working_memory['hara_stage'] = 'asil_determined'
        
        # Set formatter flags
        cat.working_memory['needs_formatting'] = True
        cat.working_memory['last_operation'] = 'asil_determination'
        
        log.info(f"✅ ASIL determination complete")
        
        # Calculate statistics
        stats = calculator.calculate_asil_statistics(updated_hazards)
        
        # Build simple response (formatter will beautify)
        response = f"""Successfully determined ASIL for {item_name}.

Total hazards assessed: {len(updated_hazards)}

ASIL Distribution:
- ASIL D: {stats['asil_counts']['D']} hazards ({stats['asil_percentages']['D']:.1f}%)
- ASIL C: {stats['asil_counts']['C']} hazards ({stats['asil_percentages']['C']:.1f}%)
- ASIL B: {stats['asil_counts']['B']} hazards ({stats['asil_percentages']['B']:.1f}%)
- ASIL A: {stats['asil_counts']['A']} hazards ({stats['asil_percentages']['A']:.1f}%)
- QM: {stats['asil_counts']['QM']} hazards ({stats['asil_percentages']['QM']:.1f}%)

High-priority hazards (ASIL C-D): {stats['asil_counts']['C'] + stats['asil_counts']['D']}

Next step: Derive safety goals for ASIL hazards (A-D)."""
        
        return response
        
    except Exception as e:
        log.error(f"ASIL determination failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"""❌ **ASIL Determination Error**

**Error:** {str(e)}

**Try:**
- Verify E/S/C ratings are valid
- Check rating format (S0-S3, E0-E4, C0-C3)
- Retry determination"""


@tool(
    return_direct=True,
    examples=[
        "show asil distribution",
        "display asil statistics",
        "asil summary"
    ]
)
def show_asil_distribution(tool_input, cat):
    """
    Display ASIL distribution and statistics.
    
    Shows:
    - ASIL counts and percentages
    - High-priority hazards (ASIL C-D)
    - E/S/C combinations leading to each ASIL
    - Recommendations
    
    Useful for understanding safety criticality.
    """
    
    log.info("🔧 TOOL CALLED: show_asil_distribution")
    
    hazards = cat.working_memory.get('complete_hara_table', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazards:
        return """❌ **No HARA Table Available**

**Action:** Complete ASIL determination first: `determine asil for all hazards`"""
    
    # Check if ASIL determined
    if 'asil' not in hazards[0]:
        return """❌ **ASIL Not Determined**

**Action:** Determine ASIL first: `determine asil for all hazards`"""
    
    # Calculate statistics
    calculator = ASILCalculator()
    stats = calculator.calculate_asil_statistics(hazards)
    
    output = f"""📊 **ASIL Distribution: {item_name}**

**Total Hazards:** {len(hazards)}

**ASIL Breakdown:**
- **ASIL D:** {stats['asil_counts']['D']} hazards ({stats['asil_percentages']['D']:.1f}%)
- **ASIL C:** {stats['asil_counts']['C']} hazards ({stats['asil_percentages']['C']:.1f}%)
- **ASIL B:** {stats['asil_counts']['B']} hazards ({stats['asil_percentages']['B']:.1f}%)
- **ASIL A:** {stats['asil_counts']['A']} hazards ({stats['asil_percentages']['A']:.1f}%)
- **QM:** {stats['asil_counts']['QM']} hazards ({stats['asil_percentages']['QM']:.1f}%)

**High Priority (ASIL C-D):** {stats['asil_counts']['C'] + stats['asil_counts']['D']} hazards
**Requires Safety Goals (A-D):** {stats['asil_counts']['A'] + stats['asil_counts']['B'] + stats['asil_counts']['C'] + stats['asil_counts']['D']} hazards

**Recommendations:**
"""
    
    # Add recommendations based on distribution
    total_asil = stats['asil_counts']['A'] + stats['asil_counts']['B'] + stats['asil_counts']['C'] + stats['asil_counts']['D']
    
    if stats['asil_counts']['D'] > 0:
        output += f"⚠️ **Critical:** {stats['asil_counts']['D']} ASIL D hazards require highest safety measures\n"
    
    if stats['asil_counts']['C'] > 0:
        output += f"⚠️ **Important:** {stats['asil_counts']['C']} ASIL C hazards need robust safety mechanisms\n"
    
    if total_asil > len(hazards) * 0.5:
        output += "⚠️ **Notice:** >50% of hazards require ASIL - consider system redesign\n"
    
    output += "\n---\n\n**Next Steps:**\n"
    output += "1. Review high-ASIL hazards (C-D) carefully\n"
    output += "2. Derive safety goals: `derive safety goals for all hazards`\n"
    output += "3. Consider ASIL decomposition for ASIL D hazards (if applicable)"
    
    return output


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
    Display ISO 26262-3 ASIL determination matrix.
    
    Shows:
    - Table 4 from ISO 26262-3:2018
    - How E/S/C combinations map to ASIL
    - Examples of each ASIL level
    
    Useful reference when reviewing ASIL assignments.
    """
    
    log.info("🔧 TOOL CALLED: show_asil_matrix")
    
    return """📖 **ASIL Determination Matrix - ISO 26262-3:2018 Table 4**

The ASIL is determined by combining Exposure (E), Severity (S), and Controllability (C).

## Matrix Legend

For each cell: **[S + E + C → ASIL]**

---

## Severity S1 (Light to Moderate Injuries)

| E \\ C | C0 | C1 | C2 | C3 |
|--------|----|----|----|----|
| **E1** | QM | **A** | **A** | **A** |
| **E2** | QM | **A** | **B** | **B** |
| **E3** | QM | **A** | **B** | **C** |
| **E4** | QM | **A** | **B** | **C** |

---

## Severity S2 (Severe Injuries)

| E \\ C | C0 | C1 | C2 | C3 |
|--------|----|----|----|----|
| **E1** | QM | **A** | **B** | **C** |
| **E2** | QM | **B** | **C** | **C** |
| **E3** | QM | **B** | **C** | **D** |
| **E4** | QM | **B** | **C** | **D** |

---

## Severity S3 (Life-threatening to Fatal)

| E \\ C | C0 | C1 | C2 | C3 |
|--------|----|----|----|----|
| **E1** | QM | **B** | **C** | **D** |
| **E2** | QM | **C** | **D** | **D** |
| **E3** | QM | **C** | **D** | **D** |
| **E4** | QM | **C** | **D** | **D** |

---

## Examples

**ASIL D:** S3 + E4 + C3 (Fatal injuries, frequent, uncontrollable)
- Example: Unintended acceleration on highway

**ASIL C:** S2 + E4 + C2 (Severe injuries, frequent, normally controllable)
- Example: Brake failure with warning

**ASIL B:** S2 + E2 + C1 (Severe injuries, uncommon, simply controllable)
- Example: Reduced brake performance in rain

**ASIL A:** S1 + E2 + C1 (Moderate injuries, uncommon, simply controllable)
- Example: Delayed wiper activation

**QM:** S0 or C0 (No injuries or always controllable)
- Example: Interior light malfunction

---

**Key Principles:**
- S0 (no injuries) always leads to QM
- C0 (controllable) always leads to QM
- Higher values (S3, E4, C3) lead to higher ASIL
- ASIL D requires the most rigorous safety processes"""