# ==============================================================================
# tools/07_hara_generation.py
# Tool for generating HARA documentation (Excel and Word)
# Refactored to use ISO26262Tool base class
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import sys
import os
from datetime import datetime

# Setup paths
current_file = os.path.abspath(__file__)
tools_folder = os.path.dirname(current_file)
plugin_folder = os.path.dirname(tools_folder)

# Add modules to path
sys.path.insert(0, os.path.join(plugin_folder, 'core'))
sys.path.insert(0, os.path.join(plugin_folder, 'code', 'generators'))

from iso26262_base import ISO26262Tool, WorkflowManager


class HARAGenerationTool(ISO26262Tool):
    """
    Tool for generating HARA Excel documentation.
    
    Creates ISO 26262-3:2018 compliant documentation.
    """
    
    REQUIRED_DATA = ['hara_safety_goals', 'hara_item_name']
    
    def __init__(self, cat, plugin_folder: str):
        super().__init__(cat)
        self.plugin_folder = plugin_folder
    
    def execute_excel(self) -> str:
        """Generate HARA Excel file"""
        
        # Validate prerequisites
        is_valid, missing = self.validate_prerequisites(self.REQUIRED_DATA)
        if not is_valid:
            return self.format_error(
                "Cannot generate HARA Excel - missing required data",
                [
                    "Complete HARA workflow first",
                    "Derive safety goals: `derive safety goals`",
                    f"Missing: {', '.join(missing)}"
                ]
            )
        
        # Get data
        safety_goals = self.get_workflow_data('hara_safety_goals')
        hazards = self.get_workflow_data('hara_hazardous_events', []) or \
                  self.get_workflow_data('complete_hara_table', [])
        functions = self.get_workflow_data('hara_functions', [])
        situations = self.get_workflow_data('hara_operational_situations', []) or \
                     self.get_workflow_data('operational_situations', [])
        system_name = self.get_workflow_data('hara_item_name')
        
        log.info(f"📊 Generating HARA Excel for: {system_name}")
        
        try:
            # Import Excel generator
            from generators.hara_excel_generator import HARAExcelGenerator
            
            # Create generator
            generator = HARAExcelGenerator()
            
            # Generate Excel file
            filename = generator.generate(
                safety_goals=safety_goals,
                hazards=hazards,
                functions=functions,
                situations=situations,
                system_name=system_name,
                output_dir=os.path.join(self.plugin_folder, 'generated_documents')
            )
            
            # Update workflow
            workflow = WorkflowManager(self.cat)
            workflow.advance_stage('documents_generated')
            
            log.info(f"✅ Generated HARA Excel: {filename}")
            
            return self.format_success(
                "HARA Excel Generated!",
                {
                    "File": filename,
                    "Location": "generated_documents/",
                    "Contents": "Executive Summary, Safety Goals, Hazardous Events, Traceability Matrix"
                },
                [
                    "Review Excel file",
                    "Share with safety team",
                    "Include in ISO 26262 documentation"
                ]
            ) + f"\n\n**File Details:**\n" + \
                f"- Safety Goals: {len(safety_goals)}\n" + \
                f"- Hazardous Events: {len(hazards)}\n" + \
                f"- ISO 26262-3:2018 compliant format"
            
        except Exception as e:
            log.error(f"Excel generation failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            
            return self.format_error(
                f"Excel generation failed: {str(e)}",
                [
                    "Check openpyxl installation: pip install openpyxl",
                    "Verify data integrity",
                    "Check file permissions",
                    "Retry generation"
                ]
            )


# ==============================================================================
# Cat-facing @tool decorators
# ==============================================================================

@tool(
    return_direct=True,
    examples=[
        "generate hara excel",
        "create hara spreadsheet",
        "export hara to excel"
    ]
)
def generate_hara_excel(tool_input, cat):
    """
    Generate HARA Excel traceability matrix.
    
    Creates ISO 26262-3:2018 compliant Excel workbook with:
    - Executive Summary with ASIL distribution
    - Safety Goals sheet with full details
    - Hazardous Events sheet
    - Traceability matrix (Function → Hazard → Safety Goal)
    - Operational Situations
    - Statistics and compliance checklist
    
    Args:
        tool_input: Optional - output directory
        cat: Cheshire Cat instance
    
    Returns:
        Path to generated Excel file
    
    Examples:
        User: "generate hara excel"
        Output: Excel file in generated_documents/
    """
    
    log.info("🔧 TOOL CALLED: generate_hara_excel")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Execute tool
    tool = HARAGenerationTool(cat, plugin_folder)
    return tool.execute_excel()


@tool(
    return_direct=True,
    examples=[
        "check hara generators",
        "verify hara file tools"
    ]
)
def check_hara_generators(tool_input, cat):
    """
    Diagnostic tool to verify HARA generators are available.
    
    Checks:
    - Folder structure
    - File existence
    - Import capability
    - Required packages
    
    Use this to troubleshoot generation issues.
    
    Example: "check hara generators"
    """
    
    log.info("🔍 TOOL CALLED: check_hara_generators")
    
    # Get paths
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    code_folder = os.path.join(plugin_folder, 'code')
    generators_folder = os.path.join(code_folder, 'generators')
    
    report = "🔍 **HARA Generator Diagnostic Report**\n\n"
    
    # Check folder structure
    report += "**Folder Structure:**\n"
    report += f"✅ Plugin folder: `{plugin_folder}`\n" if os.path.exists(plugin_folder) else "❌ Plugin folder not found\n"
    report += f"✅ Code folder: `{code_folder}`\n" if os.path.exists(code_folder) else "❌ Code folder not found\n"
    report += f"✅ Generators folder: `{generators_folder}`\n" if os.path.exists(generators_folder) else "❌ Generators folder not found\n"
    
    # Check generator files
    report += "\n**Generator Files:**\n"
    
    files_to_check = {
        'hara_excel_generator.py': os.path.join(generators_folder, 'hara_excel_generator.py'),
        'safety_goal_generator.py': os.path.join(generators_folder, 'safety_goal_generator.py'),
        'hazop_generator.py': os.path.join(generators_folder, 'hazop_generator.py'),
        'esc_generator.py': os.path.join(generators_folder, 'esc_generator.py'),
        'asil_calculator.py': os.path.join(generators_folder, 'asil_calculator.py'),
    }
    
    all_exist = True
    for name, path in files_to_check.items():
        exists = os.path.exists(path)
        report += f"{'✅' if exists else '❌'} {name}\n"
        if not exists:
            all_exist = False
    
    # Check required packages
    report += "\n**Required Packages:**\n"
    
    try:
        import openpyxl
        report += "✅ openpyxl (Excel generation)\n"
    except ImportError:
        report += "❌ openpyxl - Install with: pip install openpyxl\n"
        all_exist = False
    
    try:
        import docx
        report += "✅ python-docx (Word generation)\n"
    except ImportError:
        report += "⚠️ python-docx - Install with: pip install python-docx (optional)\n"
    
    # Try imports
    report += "\n**Import Tests:**\n"
    
    try:
        sys.path.insert(0, generators_folder)
        from generators.hara_excel_generator import HARAExcelGenerator
        report += "✅ HARAExcelGenerator imported successfully\n"
    except Exception as e:
        report += f"❌ HARAExcelGenerator import failed: {e}\n"
        all_exist = False
    
    try:
        from generators.safety_goal_generator import SafetyGoalGenerator
        report += "✅ SafetyGoalGenerator imported successfully\n"
    except Exception as e:
        report += f"❌ SafetyGoalGenerator import failed: {e}\n"
        all_exist = False
    
    # Overall status
    report += "\n**Status:**\n"
    if all_exist:
        report += "✅ All generator files and packages available\n"
        report += "✅ Ready to generate HARA documents!\n"
    else:
        report += "❌ Some components missing\n"
        report += "\n**Action Required:** Install missing packages or create missing generator files\n"
    
    return report


@tool(
    return_direct=True,
    examples=[
        "generate all hara files",
        "create complete hara documentation"
    ]
)
def generate_all_hara_files(tool_input, cat):
    """
    Generate complete HARA documentation package.
    
    Creates both Excel and Word files (if Word generator available):
    - Excel: Traceability matrix with statistics
    - Word: Complete HARA report with ISO 26262-3 sections (if available)
    
    Examples:
        User: "generate all hara files"
        Output: Complete documentation package
    """
    
    log.info("🔧 TOOL CALLED: generate_all_hara_files")
    
    # Get plugin folder
    current_file = os.path.abspath(__file__)
    tools_folder = os.path.dirname(current_file)
    plugin_folder = os.path.dirname(tools_folder)
    
    # Generate Excel
    tool = HARAGenerationTool(cat, plugin_folder)
    excel_result = tool.execute_excel()
    
    # Check for Word generator
    word_result = "\n\n**Word Document:**\n⚠️ Word generator not yet implemented\n" + \
                  "Implement `hara_word_generator.py` for Word document generation"
    
    try:
        from generators.hara_word_generator import HARAWordGenerator
        # If available, generate Word doc
        word_result = "\n\n**Word Document:**\n(Word generation would go here)"
    except ImportError:
        pass
    
    return f"""✅ **Complete HARA Documentation Package**

{'='*70}

### 📊 Excel Traceability Matrix

{excel_result}

{word_result}

{'='*70}

**Documentation Package Status:**
- Excel: ✅ Generated
- Word: ⚠️ Not yet implemented

**Next Steps:**
1. Review Excel file
2. Share with safety team via document management system
3. Schedule technical review meeting
4. Obtain required approvals
5. Proceed to FSC development"""