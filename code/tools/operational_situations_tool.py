# ==============================================================================
# code/tools/operational_situations_tool.py
# Tool for defining operational situations for exposure assessment
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

from ..generators.scenarios_generator import ScenariosGenerator


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
    
    # Get system context
    item_name = cat.working_memory.get('hara_item_name', 'System')
    hazop_results = cat.working_memory.get('hazop_results', [])
    
    if not hazop_results:
        return """❌ **No HAZOP Results Available**

**Action Required:** Complete HAZOP analysis first

Use: `apply hazop analysis`

**Workflow:**
1. ✅ Extract functions
2. ✅ Apply HAZOP
3. ❌ Define operational situations ← You are here
4. ❓ Assess E/S/C
5. ❓ Determine ASIL"""
    
    log.info(f"📋 Defining operational situations for: {item_name}")
    
    try:
        # Create scenarios generator
        generator = ScenariosGenerator(cat.llm, plugin_folder)
        
        # Generate operational situations
        scenarios = generator.generate_scenarios(
            system_name=item_name,
            hazop_results=hazop_results
        )
        
        if not scenarios:
            return """❌ **Scenario Generation Failed**

**Possible causes:**
- LLM unable to generate scenarios
- System context insufficient

**Try:**
- Provide more context about system usage
- Manually define scenarios using template"""
        
        # Store in working memory
        cat.working_memory['operational_situations'] = scenarios
        cat.working_memory['hara_stage'] = 'scenarios_defined'
        
        # Set formatter flags
        cat.working_memory['needs_formatting'] = True
        cat.working_memory['last_operation'] = 'operational_situations'
        
        log.info(f"✅ Defined {len(scenarios)} operational situations")
        
        # Build simple response (formatter will beautify)
        response = f"""Successfully defined operational situations for {item_name}.

Total operational situations: {len(scenarios)}

Scenarios cover various driving conditions including:
- Urban driving scenarios
- Highway/motorway scenarios
- Parking and low-speed maneuvers
- Adverse weather conditions
- Emergency situations

Exposure ratings assigned based on typical driving patterns.

Next step: Assess Exposure, Severity, and Controllability for each hazard."""
        
        return response
        
    except Exception as e:
        log.error(f"Scenario definition failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"""❌ **Scenario Definition Error**

**Error:** {str(e)}

**Try:**
- Check system context
- Verify HAZOP results exist
- Retry generation"""


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
    
    scenarios = cat.working_memory.get('operational_situations', [])
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
2. Proceed to E/S/C assessment: `assess esc for all hazards`"""
    
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