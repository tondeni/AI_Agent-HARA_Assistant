# ==============================================================================
# tools/05_asil_determination.py
# Tool for determining ASIL based on E/S/C ratings
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


class ASILDeterminationTool(ISO26262Tool):
    """
    Tool for determining ASIL based on E/S/C ratings.
    
    Implements ISO 26262-3:2018, Clause 6.4.5 and Table 4
    """
    
    REQUIRED_DATA = ['complete_hara_table', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "all") -> str:
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
        if hazards and not all(key in hazards[0] for key in ['exposure', 'severity', 'controllability']):
            return self.format_error(
                "Hazards missing E/S/C ratings",
                ["Run E/S/C assessment: `assess esc for all hazards`"]
            )
        
        log.info(f"📋 Determining ASIL for {len(hazards)} hazards")
        
        try:
            # Import ASIL calculator
            from generators.asil_calculator import ASILCalculator
            
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
            
            return self.format_success(
                f"ASIL Determination Complete: {item_name}",
                {
                    "Total Hazards": len(updated_hazards),
                    "ASIL D": f"{stats['asil_counts']['D']} ({stats['asil_percentages']['D']:.1f}%)",
                    "ASIL C": f"{stats['asil_counts']['C']} ({stats['asil_percentages']['C']:.1f}%)",
                    "ASIL B": f"{stats['asil_counts']['B']} ({stats['asil_percentages']['B']:.1f}%)",
                    "ASIL A": f"{stats['asil_counts']['A']} ({stats['asil_percentages']['A']:.1f}%)",
                    "QM": f"{stats['asil_counts']['QM']} ({stats['asil_percentages']['QM']:.1f}%)",
                    "High-Priority (C-D)": stats['asil_counts']['C'] + stats['asil_counts']['D']
                },
                [
                    "Review ASIL distribution: `show asil distribution`",
                    "Derive safety goals: `derive safety goals`"
                ]
            ) + "\n\n**ISO 26262-3:2018 Compliance:**\n" + \
                "✓ Clause 6.4.5: ASIL determination per Table 4\n" + \
                "✓ Systematic application of E/S/C combinations\n" + \
                "✓ All hazards classified"
            
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
        User: "determine asil"
        Output: ASIL distribution and updated HARA table
    """
    
    log.info("🔧 TOOL CALLED: determine_asil")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = ASILDeterminationTool(cat, plugin_folder)
    return tool.execute(tool_input if tool_input else "all")


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
    - Recommendations
    
    Useful for understanding safety criticality.
    """
    
    log.info("🔧 TOOL CALLED: show_asil_distribution")
    
    hazards = cat.working_memory.get('complete_hara_table', []) or \
              cat.working_memory.get('hara_hazardous_events', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazards:
        return """❌ **No HARA Table Available**

**Action:** Complete ASIL determination first: `determine asil`"""
    
    # Check if ASIL determined
    if not hazards[0].get('asil'):
        return """❌ **ASIL Not Determined**

**Action:** Determine ASIL first: `determine asil`"""
    
    # Import calculator for statistics
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    sys.path.insert(0, os.path.join(plugin_folder, 'code', 'generators'))
    
    from generators.asil_calculator import ASILCalculator
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
**Requires Safety Goals (A-D):** {stats['asil_rated_count']} hazards

**Recommendations:**
"""
    
    # Add recommendations
    if stats['asil_counts']['D'] > 0:
        output += f"⚠️ **Critical:** {stats['asil_counts']['D']} ASIL D hazards require highest safety measures\n"
    
    if stats['asil_counts']['C'] > 0:
        output += f"⚠️ **Important:** {stats['asil_counts']['C']} ASIL C hazards need robust safety mechanisms\n"
    
    if stats['asil_rated_count'] > len(hazards) * 0.5:
        output += "⚠️ **Notice:** >50% of hazards require ASIL - consider system redesign\n"
    
    output += "\n---\n\n**Next Steps:**\n"
    output += "1. Review high-ASIL hazards (C-D) carefully\n"
    output += "2. Derive safety goals: `derive safety goals`\n"
    output += "3. Consider ASIL decomposition for ASIL D hazards"
    
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
    Display ISO 26262-3 ASIL determination matrix (Table 4).
    
    Shows:
    - How E/S/C combinations map to ASIL
    - Examples of each ASIL level
    
    Useful reference when reviewing ASIL assignments.
    """
    
    log.info("🔧 TOOL CALLED: show_asil_matrix")
    
    return """📖 **ASIL Determination Matrix - ISO 26262-3:2018 Table 4**

The ASIL is determined by combining Exposure (E), Severity (S), and Controllability (C).

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
- ASIL D requires the most rigorous safety processes per ISO 26262"""