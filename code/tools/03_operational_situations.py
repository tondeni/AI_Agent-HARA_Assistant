# ==============================================================================
# tools/03_operational_situations.py
# Tool for defining operational situations for exposure assessment
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


class OperationalSituationsTool(ISO26262Tool):
    """
    Tool for defining operational situations for exposure assessment.
    
    Implements ISO 26262-3:2018, Clause 6.4.4 - Classification of hazardous events
    """
    
    REQUIRED_DATA = ['hazop_results', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute(self, tool_input: str = "") -> str:
        """Define operational situations"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self.format_error(
                "Cannot define operational situations - missing required data",
                [
                    "Complete HAZOP analysis first: `apply hazop analysis`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        hazop_results = self.get_workflow_data('hazop_results')
        item_name = self.get_workflow_data('hara_item_name')
        
        log.info(f"📋 Defining operational situations for: {item_name}")
        
        try:
            # Import scenarios generator
            from generators.scenarios_generator import ScenariosGenerator
            
            # Create generator
            generator = ScenariosGenerator(self.llm, self.plugin_folder)
            
            # Generate scenarios
            scenarios = generator.generate_scenarios(
                system_name=item_name,
                hazop_results=hazop_results
            )
            
            if not scenarios:
                return self.format_error(
                    "Scenario generation produced no results",
                    [
                        "Provide more system context",
                        "Check LLM availability",
                        "Manually define scenarios using template",
                        "Retry generation"
                    ]
                )
            
            # Store results
            self.set_workflow_data('operational_situations', scenarios)
            self.set_workflow_data('hara_operational_situations', scenarios)  # Alias
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('situations_defined')
            
            log.info(f"✅ Defined {len(scenarios)} operational situations")
            
            # Build scenario summary
            scenario_list = "\n".join([
                f"{idx}. **{s.get('name', f'Scenario {idx}')}** "
                f"(Exposure: {s.get('exposure_class', 'TBD')})"
                for idx, s in enumerate(scenarios, 1)
            ])
            
            return self.format_success(
                f"Operational Situations Defined: {item_name}",
                {
                    "Total Scenarios": len(scenarios),
                    "Scenario Types": "Urban, Highway, Parking, Environmental, Emergency"
                },
                [
                    "Review scenarios: `show operational situations`",
                    "Proceed to E/S/C assessment: `assess esc for all hazards`"
                ]
            ) + f"\n\n**Defined Scenarios:**\n\n{scenario_list}\n\n" + \
                "---\n\n**ISO 26262-3:2018 Compliance:**\n" + \
                "✓ Clause 6.4.4: Operational situations identified\n" + \
                "✓ Exposure ratings assigned based on driving statistics\n" + \
                "✓ Covers various driving conditions and environments"
            
        except Exception as e:
            log.error(f"Scenario definition failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                f"Scenario definition failed: {str(e)}",
                [
                    "Check system context",
                    "Verify HAZOP results exist",
                    "Retry generation"
                ]
            )


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
    
    Args:
        tool_input: Optional - system context or custom scenarios
        cat: Cheshire Cat instance
    
    Returns:
        List of operational situations with exposure ratings
    
    Example:
        User: "define operational situations"
        Output: 5-7 scenarios (urban, highway, parking, etc.)
    """
    
    log.info("🔧 TOOL CALLED: define_operational_situations")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = OperationalSituationsTool(cat, plugin_folder)
    return tool.execute(tool_input)


@tool(
    return_direct=True,
    examples=[
        "show operational situations",
        "list scenarios",
        "display driving situations"
    ]
)
def show_operational_situations(tool_input, cat):
    """
    Display defined operational situations from working memory.
    
    Shows:
    - Scenario ID and name
    - Description
    - Exposure rating (E0-E4)
    - Duration/frequency
    
    Useful for reviewing before E/S/C assessment.
    """
    
    log.info("🔧 TOOL CALLED: show_operational_situations")
    
    scenarios = cat.working_memory.get('operational_situations', []) or \
                cat.working_memory.get('hara_operational_situations', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not scenarios:
        return """❌ **No Operational Situations Found**

**Action:** Define scenarios first: `define operational situations`"""
    
    output = f"""📋 **Operational Situations: {item_name}**

**Total Scenarios:** {len(scenarios)}

**Scenarios:**

"""
    
    for idx, scenario in enumerate(scenarios, 1):
        output += f"{idx}. **{scenario.get('name', f'Scenario {idx}')}**\n"
        output += f"   - Exposure: {scenario.get('exposure_class', 'TBD')}\n"
        output += f"   - Duration: {scenario.get('duration_percentage', 0)}% of operating time\n"
        output += f"   - Description: {scenario.get('description', 'N/A')[:100]}...\n\n"
    
    output += """---

**Next Steps:**
1. Review scenarios for completeness
2. Add custom scenarios if needed: `add custom scenario`
3. Proceed to E/S/C assessment: `assess esc for all hazards`"""
    
    return output


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
    "Add scenario: [name] | [description] | [exposure: E0-E4]"
    
    Example:
        "Add scenario: Extreme Cold Weather | Driving in -30°C conditions | E1"
    """
    
    log.info("🔧 TOOL CALLED: add_custom_scenario")
    
    # Parse input
    if isinstance(tool_input, str) and '|' in tool_input:
        parts = [p.strip() for p in tool_input.split('|')]
        
        if len(parts) >= 3:
            name = parts[0].replace('Add scenario:', '').strip()
            description = parts[1]
            exposure = parts[2].replace('exposure:', '').strip()
            
            # Create scenario dict
            custom_scenario = {
                'id': f"OS-CUSTOM-{len(cat.working_memory.get('operational_situations', [])) + 1:02d}",
                'name': name,
                'description': description,
                'exposure_class': exposure.upper(),
                'duration_percentage': 0,  # User should specify if needed
                'vehicle_state': 'Custom',
                'environmental_conditions': 'As described',
                'custom': True
            }
            
            # Add to working memory
            scenarios = cat.working_memory.get('operational_situations', [])
            scenarios.append(custom_scenario)
            cat.working_memory['operational_situations'] = scenarios
            cat.working_memory['hara_operational_situations'] = scenarios
            
            return f"""✅ **Custom Scenario Added**

**ID:** {custom_scenario['id']}
**Name:** {name}
**Exposure:** {exposure}

**Total Scenarios:** {len(scenarios)}

Use `show operational situations` to view all scenarios."""
        
    return """❌ **Invalid Format**

**Expected format:**
```
Add scenario: [name] | [description] | [exposure: E0-E4]
```

**Example:**
```
Add scenario: Extreme Cold Weather | Driving in -30°C conditions | E1
```"""