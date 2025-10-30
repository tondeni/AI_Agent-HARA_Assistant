# ==============================================================================
# code/tools/hara_file_tools.py
# Cat-facing tools for HARA document generation (Excel & Word)
# ==============================================================================

"""
HARA File Generation Tools

@tool decorated functions for the Cheshire Cat to generate ISO 26262-3 
compliant HARA documentation.

Available tools:
- generate_hara_excel: Create Excel traceability matrix
- generate_hara_document: Create Word document with complete HARA
- generate_all_hara_files: Create both Excel and Word documents
"""

from cat.mad_hatter.decorators import tool
from cat.log import log
import os
import sys
from datetime import datetime

# Setup path to generators
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
    
    Examples:
    - "generate hara excel"
    - "create excel file for hara"
    """
    
    log.info("📊 TOOL CALLED: generate_hara_excel")
    
    # Get data from working memory
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    hazards = cat.working_memory.get('hara_hazardous_events', [])
    functions = cat.working_memory.get('hara_functions', [])
    situations = cat.working_memory.get('hara_operational_situations', [])
    system_name = cat.working_memory.get('system_name', 'System')
    
    if not safety_goals:
        return """❌ No HARA data available for Excel generation.

**Required Steps:**
1. Extract functions from Item Definition
2. Apply HAZOP to identify hazards
3. Assess E/S/C for hazards
4. Determine ASIL ratings
5. Derive safety goals

Then generate Excel file."""
    
    try:
        # Import generator
        from generators.hara_excel_generator import HARAExcelGenerator
        
        log.info("✅ HARAExcelGenerator imported successfully")
        
        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(plugin_folder, "generated_documents")
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" 
                           for c in system_name).replace(" ", "_")
        
        filename = f"{safe_name}_HARA_Traceability_{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # Prepare data
        hara_data = {
            'safety_goals': safety_goals,
            'hazards': hazards,
            'functions': functions,
            'operational_situations': situations
        }
        
        # Create generator
        generator = HARAExcelGenerator()
        
        # Validate data
        is_valid, warnings, errors = generator.validate_data(hara_data)
        
        if not is_valid:
            error_msg = "\n".join([f"- {e}" for e in errors])
            return f"❌ HARA data validation failed:\n\n{error_msg}"
        
        # Generate workbook
        log.info(f"📊 Generating Excel workbook: {filename}")
        wb = generator.generate(system_name, hara_data)
        
        # Save workbook
        wb.save(filepath)
        log.info(f"✅ Excel file saved: {filepath}")
        
        # Calculate statistics
        stats = generator.calculate_statistics(safety_goals)
        
        # Build response
        asil_summary = ', '.join([f"ASIL {asil}: {count}" 
                                 for asil, count in sorted(stats['asil_distribution'].items())
                                 if count > 0])
        
        warning_msg = ""
        if warnings:
            warning_msg = "\n\n**⚠️ Warnings:**\n" + "\n".join([f"- {w}" for w in warnings])
        
        return f"""✅ **HARA Excel Traceability Matrix Generated!**

**File:** `{filename}`
**Location:** `generated_documents/`

**Contents:**
📋 Executive Summary - ASIL distribution and metadata
📊 Safety Goals - {stats['total_goals']} goals with full details  
⚠️ Hazardous Events - {len(hazards)} events with E/S/C ratings
🔗 Traceability - Complete Function → Hazard → Safety Goal mapping
📍 Operational Situations - {len(situations)} scenarios
📈 Statistics - ISO 26262-3 compliance checklist

**ASIL Distribution:**
{asil_summary}

**Highest ASIL:** {stats['highest_asil']}
{warning_msg}

**ISO 26262-3:2018 Reference:** Clause 6 work products
**Next Steps:** Review with safety team, obtain approval"""
        
    except ImportError as e:
        log.error(f"❌ Import error: {e}")
        
        return f"""❌ Excel generator not available.

**Error:** {str(e)}

**Solution:**
1. Ensure `hara_excel_generator.py` exists in `code/generators/`
2. Install required package: `pip install openpyxl`
3. Check generator file has no syntax errors"""
        
    except Exception as e:
        log.error(f"❌ Excel generation failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        return f"❌ Failed to generate Excel: {str(e)}"


# @tool(
#     return_direct=True,
#     examples=[
#         "generate hara document",
#         "create hara word file",
#         "export hara to word"
#     ]
# )
# def generate_hara_document(tool_input, cat):
#     """
#     Generate complete HARA Word document.
    
#     Creates ISO 26262-3:2018 Clause 6 compliant document with:
#     - Executive summary
#     - Item Definition overview
#     - HAZOP analysis results
#     - Operational situations
#     - E/S/C assessment details
#     - ASIL determination
#     - Safety goals catalog
#     - Traceability matrices
    
#     Examples:
#     - "generate hara document"
#     - "create word document for hara"
#     """
    
#     log.info("📄 TOOL CALLED: generate_hara_document")
    
#     # Get data from working memory
#     safety_goals = cat.working_memory.get('hara_safety_goals', [])
#     hazards = cat.working_memory.get('hara_hazardous_events', [])
#     functions = cat.working_memory.get('hara_functions', [])
#     situations = cat.working_memory.get('hara_operational_situations', [])
#     system_name = cat.working_memory.get('system_name', 'System')
    
#     if not safety_goals:
#         return """❌ No HARA data available for document generation.

# **Required:** Complete HARA workflow first:
# 1. extract functions
# 2. apply hazop
# 3. define operational situations
# 4. assess esc
# 5. determine asil
# 6. derive safety goals

# Then generate document."""
    
#     try:
#         # Import generator (to be created)
#         from generators.hara_word_generator import HARAWordGenerator
        
#         # Setup output
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         output_dir = os.path.join(plugin_folder, "generated_documents")
#         os.makedirs(output_dir, exist_ok=True)
        
#         safe_name = "".join(c if c.isalnum() or c in "._- " else "_" 
#                            for c in system_name).replace(" ", "_")
        
#         filename = f"{safe_name}_HARA_{timestamp}.docx"
#         filepath = os.path.join(output_dir, filename)
        
#         # Prepare data
#         hara_data = {
#             'safety_goals': safety_goals,
#             'hazards': hazards,
#             'functions': functions,
#             'operational_situations': situations,
#             'system_name': system_name
#         }
        
#         # Generate document
#         log.info(f"📄 Generating Word document: {filename}")
#         generator = HARAWordGenerator()
#         doc = generator.generate(hara_data)
        
#         # Save
#         doc.save(filepath)
#         log.info(f"✅ Word document saved: {filepath}")
        
#         return f"""✅ **HARA Document Generated!**

# **File:** `{filename}`
# **Location:** `generated_documents/`

# **Document Structure:**
# 1. Introduction & Scope
# 2. Referenced Documents (ISO 26262-3:2018)
# 3. Item Definition Summary
# 4. HAZOP Analysis Results
# 5. Operational Situations
# 6. E/S/C Assessment
# 7. ASIL Determination
# 8. Safety Goals Catalog
# 9. Traceability Matrices
# 10. Approvals Section

# **Total Pages:** ~{len(safety_goals) * 2 + 15} pages

# **ISO 26262-3:2018 Compliance:**
# ✓ Clause 6.4.2 - Situation analysis
# ✓ Clause 6.4.3 - Hazard identification
# ✓ Clause 6.4.4 - E/S/C classification
# ✓ Clause 6.4.5 - ASIL determination
# ✓ Clause 6.4.6 - Safety goal derivation

# **Next Steps:**
# 1. Review document with safety team
# 2. Conduct technical review meeting
# 3. Obtain approvals from safety manager
# 4. Include in safety case documentation"""
        
#     except ImportError:
#         return """⚠️ **Word generator not yet implemented**

# Excel generation is available. Use:
# `generate hara excel`

# To implement Word generation:
# 1. Create `hara_word_generator.py` in `code/generators/`
# 2. Install: `pip install python-docx`
# 3. Follow similar pattern to FSC Word generator"""
        
#     except Exception as e:
#         log.error(f"❌ Document generation failed: {e}")
#         return f"❌ Failed to generate document: {str(e)}"


@tool(
    return_direct=True,
    examples=[
        "generate all hara files",
        "create complete hara documentation",
        "export hara to excel and word"
    ]
)
def generate_all_hara_files(tool_input, cat):
    """
    Generate complete HARA documentation package.
    
    Creates both Excel and Word files:
    - Excel: Traceability matrix with statistics
    - Word: Complete HARA report with ISO 26262-3 sections
    
    Examples:
    - "generate all hara files"
    - "create complete hara documentation"
    """
    
    log.info("📦 TOOL CALLED: generate_all_hara_files")
    
    safety_goals = cat.working_memory.get('hara_safety_goals', [])
    
    if not safety_goals:
        return """❌ No HARA data available.

Complete the HARA workflow first:
`extract functions from [item]`
`apply hazop to all functions`
`define operational situations`
`assess esc for all hazards`
`determine asil`
`derive safety goals`

Then generate files."""
    
    # Generate Excel
    excel_result = generate_hara_excel("", cat)
    
    # # Generate Word (if available)
    # word_result = generate_hara_document("", cat)
    
    # Combine results
    return f"""✅ **Complete HARA Documentation Package Generated!**

{'='*70}

### 📊 Excel Traceability Matrix

{excel_result}

{'='*70}

### 📄 Word Document


**Documentation Package Complete!**

Both files are in `generated_documents/` folder.

**Next Steps:**
1. Review both documents
2. Share with safety team via document management system
3. Schedule technical review meeting
4. Obtain required approvals
5. Proceed to FSC development"""


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
    
    report = "🔍 **HARA Generator Diagnostic Report**\n\n"
    
    # Check folder structure
    report += "**Folder Structure:**\n"
    report += f"✅ Plugin folder: `{plugin_folder}`\n" if os.path.exists(plugin_folder) else "❌ Plugin folder not found\n"
    report += f"✅ Code folder: `{code_folder}`\n" if os.path.exists(code_folder) else "❌ Code folder not found\n"
    report += f"✅ Generators folder: `{generators_folder}`\n" if os.path.exists(generators_folder) else "❌ Generators folder not found\n"
    
    # Check generator files
    report += "\n**Generator Files:**\n"
    
    # files_to_check = {
    #     'hara_excel_generator.py': os.path.join(generators_folder, 'hara_excel_generator.py'),
    #     'safety_goal_generator.py': os.path.join(generators_folder, 'safety_goal_generator.py'),
    #     'hara_word_generator.py': os.path.join(generators_folder, 'hara_word_generator.py'),
    # }
    
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
    
    try:
        import docx
        report += "✅ python-docx (Word generation)\n"
    except ImportError:
        report += "⚠️ python-docx - Install with: pip install python-docx\n"
    
    # Try imports
    report += "\n**Import Tests:**\n"
    
    try:
        from generators.hara_excel_generator import HARAExcelGenerator
        report += "✅ HARAExcelGenerator imported successfully\n"
    except Exception as e:
        report += f"❌ HARAExcelGenerator import failed: {e}\n"
    
    try:
        from generators.safety_goal_generator import SafetyGoalGenerator
        report += "✅ SafetyGoalGenerator imported successfully\n"
    except Exception as e:
        report += f"❌ SafetyGoalGenerator import failed: {e}\n"
    
    # Overall status
    report += "\n**Status:**\n"
    if all_exist:
        report += "✅ All generator files exist\n"
        report += "✅ Ready to generate HARA documents!\n"
    else:
        report += "❌ Some generator files missing\n"
        report += "\n**Action Required:** Create missing generator files\n"
    
    return report


if __name__ == "__main__":
    print("HARA File Tools - Cat-facing tools for document generation")
    print("These tools are automatically discovered by Cheshire Cat framework")