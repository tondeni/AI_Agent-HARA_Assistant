"""
Function Extraction Tool
========================
ISO 26262 function extraction from item definition documents.
"""

from cat.mad_hatter.decorators import tool
from cat.log import log
from pathlib import Path
from typing import List, Dict
import re

from ..utils import get_item_definitions_path


# ============================================================================
# FUZZY MATCHING - Enhanced for "Item Definition_system.pdf" format
# ============================================================================

def fuzzy_match_system_name(input_name: str, filename: str, threshold: int = 60) -> bool:
    """
    Match system name with fuzzy logic.
    
    Enhanced to handle formats like:
    - "Item Definition_wiper.pdf"
    - "Item Definition_BMS.docx"
    - "BMS_Item_Definition.pdf"
    - "Wiper and Washer System.docx"
    
    Examples:
    - "Wiper" matches "Item Definition_wiper.pdf" ✅
    - "BMS" matches "Item Definition_BMS.pdf" ✅
    - "wiper" matches "Item Definition_Wiper.pdf" ✅ (case insensitive)
    """
    from difflib import SequenceMatcher
    
    # Normalize inputs (lowercase, strip spaces)
    input_normalized = input_name.lower().strip()
    filename_normalized = filename.lower().strip()
    
    # Remove file extension
    filename_no_ext = Path(filename_normalized).stem
    
    # Handle "Item Definition_system" format specifically
    # Split on common separators
    if "item definition" in filename_no_ext or "item_definition" in filename_no_ext:
        # Extract the part after "item definition" or "item_definition"
        parts = re.split(r'item[_\s-]+definition[_\s-]+', filename_no_ext, flags=re.IGNORECASE)
        if len(parts) > 1:
            system_part = parts[1].strip('_- ')
            # Check direct match with system part
            if input_normalized in system_part or system_part in input_normalized:
                return True
            # Check fuzzy match with system part
            similarity = SequenceMatcher(None, input_normalized, system_part).ratio() * 100
            if similarity >= threshold:
                return True
    
    # Replace common separators with spaces
    filename_words = filename_no_ext.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # Check 1: Exact substring match
    if input_normalized in filename_words:
        return True
    
    # Check 2: Check if input is acronym of filename
    # e.g., "BMS" matches "Battery Management System"
    words = [w for w in filename_words.split() if w and w not in ['item', 'definition', 'the', 'and']]
    if words:
        acronym = ''.join([w[0] for w in words])
        if input_normalized == acronym:
            return True
    
    # Check 3: Fuzzy match with each significant word
    for word in words:
        if len(word) < 2:  # Skip very short words
            continue
        similarity = SequenceMatcher(None, input_normalized, word).ratio() * 100
        if similarity >= threshold:
            return True
    
    # Check 4: Fuzzy match with full filename
    similarity = SequenceMatcher(None, input_normalized, filename_words).ratio() * 100
    if similarity >= threshold:
        return True
    
    return False


def find_matching_files(system_name: str, item_definitions_path: Path, cat) -> List[Path]:
    """
    Find all files that match the system name in item_definitions folder.
    
    Args:
        system_name: The system name to search for (e.g., "Wiper", "BMS")
        item_definitions_path: Path to item_definitions folder
        cat: StrayCat instance
        
    Returns:
        List of matching file paths
    """
    
    if not item_definitions_path or not item_definitions_path.exists():
        log.error(f"❌ item_definitions folder does not exist: {item_definitions_path}")
        return []
    
    matching_files = []
    supported_extensions = ['.docx', '.pdf', '.txt', '.doc']
    
    # Get all files with supported extensions
    all_files = []
    for ext in supported_extensions:
        all_files.extend(item_definitions_path.glob(f"*{ext}"))
    
    log.info(f"🔍 Searching {len(all_files)} files for system: '{system_name}'")
    
    # Log all files being checked (helpful for debugging)
    for file_path in all_files:
        log.debug(f"  📄 Found file: {file_path.name}")
    
    # Match files
    for file_path in all_files:
        is_match = fuzzy_match_system_name(system_name, file_path.name)
        
        if is_match:
            log.info(f"  ✅ MATCH: '{system_name}' matched '{file_path.name}'")
            matching_files.append(file_path)
        else:
            log.debug(f"  ❌ NO MATCH: '{system_name}' vs '{file_path.name}'")
    
    if not matching_files:
        log.warning(f"⚠️ No matches found for '{system_name}'")
        log.info(f"📋 Available files: {[f.name for f in all_files]}")
    
    return matching_files


# ============================================================================
# FILE PARSERS
# ============================================================================

def parse_docx_file(file_path: Path, cat) -> str:
    """Extract text from DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        
        # Extract text from paragraphs
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        
        # Also extract text from tables
        table_text = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        table_text.append(cell.text)
        
        text = '\n'.join(paragraphs + table_text)
        log.info(f"✅ Extracted {len(text)} chars from DOCX: {file_path.name}")
        return text
        
    except ImportError:
        error_msg = "ERROR: python-docx library not installed. Add 'python-docx' to requirements.txt"
        log.error(f"❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"ERROR reading DOCX file: {str(e)}"
        log.error(f"❌ {error_msg}")
        return error_msg


def parse_pdf_file(file_path: Path, cat) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2
        
        text_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            log.info(f"📄 PDF has {len(pdf_reader.pages)} pages")
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)
        
        text = '\n'.join(text_parts)
        log.info(f"✅ Extracted {len(text)} chars from PDF: {file_path.name}")
        return text
        
    except ImportError:
        error_msg = "ERROR: PyPDF2 library not installed. Add 'PyPDF2' to requirements.txt"
        log.error(f"❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"ERROR reading PDF file: {str(e)}"
        log.error(f"❌ {error_msg}")
        return error_msg


def parse_txt_file(file_path: Path, cat) -> str:
    """Extract text from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        log.info(f"✅ Extracted {len(text)} chars from TXT: {file_path.name}")
        return text
        
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                text = file.read()
            log.warning(f"⚠️ Used latin-1 encoding for: {file_path.name}")
            return text
        except Exception as e:
            error_msg = f"ERROR reading TXT file: {str(e)}"
            log.error(f"❌ {error_msg}")
            return error_msg
    except Exception as e:
        error_msg = f"ERROR reading TXT file: {str(e)}"
        log.error(f"❌ {error_msg}")
        return error_msg


def parse_file(file_path: Path, cat) -> str:
    """
    Parse file based on extension and extract text.
    
    Args:
        file_path: Path to the file
        cat: StrayCat instance
        
    Returns:
        Extracted text or error message
    """
    extension = file_path.suffix.lower()
    
    if extension in ['.docx', '.doc']:
        return parse_docx_file(file_path, cat)
    elif extension == '.pdf':
        return parse_pdf_file(file_path, cat)
    elif extension == '.txt':
        return parse_txt_file(file_path, cat)
    else:
        return f"ERROR: Unsupported file type: {extension}"


# ============================================================================
# FUNCTION EXTRACTION
# ============================================================================

def extract_functions_from_text(text: str, system_name: str, cat) -> List[Dict]:
    """
    Extract functions from text using multiple pattern matching strategies.
    
    Patterns recognized:
    1. "Function: <description>"
    2. "F-XXX: <description>"
    3. "F.XXX <description>"
    4. Numbered lists in "Functions" section
    5. Table rows with function identifiers
    
    Args:
        text: Extracted text from document
        system_name: Name of the system (for context)
        cat: StrayCat instance
        
    Returns:
        List of dictionaries with 'id' and 'description'
    """
    
    functions = []
    
    # Pattern 1: Explicit "Function:" labels
    pattern1 = r'(?:^|\n)\s*Function\s*:\s*(.+?)(?=\n|$)'
    matches1 = re.findall(pattern1, text, re.IGNORECASE | re.MULTILINE)
    for i, match in enumerate(matches1):
        functions.append({
            'id': f'F-{len(functions)+1:03d}',
            'description': match.strip(),
            'source': 'Explicit Function label'
        })
    
    # Pattern 2: Function IDs with dash (F-001:, F-002:, etc.)
    pattern2 = r'(F-\d+)\s*:?\s*(.+?)(?=\n(?:F-\d+|$)|\n\n|$)'
    matches2 = re.findall(pattern2, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for func_id, description in matches2:
        # Clean up description
        desc_clean = ' '.join(description.split())[:200]  # Limit length
        if desc_clean and len(desc_clean) > 10:  # Minimum meaningful length
            functions.append({
                'id': func_id.upper(),
                'description': desc_clean,
                'source': 'Function ID with dash'
            })
    
    # Pattern 3: Function IDs with dot (F.001, F.002, etc.)
    pattern3 = r'(F\.\d+)\s*:?\s*(.+?)(?=\n(?:F\.\d+|$)|\n\n|$)'
    matches3 = re.findall(pattern3, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    for func_id, description in matches3:
        desc_clean = ' '.join(description.split())[:200]
        if desc_clean and len(desc_clean) > 10:
            functions.append({
                'id': func_id.upper(),
                'description': desc_clean,
                'source': 'Function ID with dot'
            })
    
    # Pattern 4: Look for "Functions" section with numbered/bulleted lists
    # This is more heuristic - find section headers with "function"
    functions_section_pattern = r'(?:^|\n)#+?\s*(?:System\s+)?Functions?\s*:?\s*\n(.+?)(?=\n#+|\Z)'
    functions_sections = re.findall(functions_section_pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    for section in functions_sections:
        # Look for numbered or bulleted items
        list_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\-|\*|\•)\s*(.+?)(?=\n\s*(?:\d+\.|\-|\*|\•)|\n\n|$)', 
                                section, re.MULTILINE | re.DOTALL)
        for i, item in enumerate(list_items):
            item_clean = ' '.join(item.split())[:200]
            if item_clean and len(item_clean) > 10:
                functions.append({
                    'id': f'F-{len(functions)+1:03d}',
                    'description': item_clean,
                    'source': 'Functions section list'
                })
    
    # Remove duplicates (based on description similarity)
    unique_functions = []
    for func in functions:
        # Check if similar function already exists
        is_duplicate = False
        for existing in unique_functions:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, func['description'], existing['description']).ratio()
            if similarity > 0.85:  # 85% similar = duplicate
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_functions.append(func)
    
    log.info(f"✅ Extracted {len(unique_functions)} unique functions (from {len(functions)} total matches)")
    
    return unique_functions


# ============================================================================
# MAIN EXTRACTION TOOL
# ============================================================================

@tool(return_direct=False)
def extract_functions(tool_input: str, cat):
    """
    Extract functions from ISO 26262 item definition documents.
    
    This tool searches for item definition documents matching the given system name
    and extracts all functions defined in those documents.
    
    Usage examples:
    - "extract functions from Wiper"
    - "get functions for BMS"
    - "show me the functions in the Battery Management System"
    - "extract functions from Item Definition_wiper"
    
    The tool uses fuzzy matching, so "Wiper", "wiper", "WIPER" all work the same.
    
    Input should be the system name (e.g., "Wiper", "BMS", "ADAS").
    """
    
    log.info(f"=" * 60)
    log.info(f"🚀 FUNCTION EXTRACTION STARTED")
    log.info(f"📝 System name input: '{tool_input}'")
    log.info(f"=" * 60)
    
    # Clean and normalize input
    system_name = tool_input.strip().strip('"').strip("'").strip()
    log.info(f"✨ Cleaned system name: '{system_name}'")
    
    # Get item_definitions folder path
    item_definitions_path = get_item_definitions_path(cat)
    
    if not item_definitions_path:
        log.error("❌ Could not locate item_definitions folder")
        return """❌ **ERROR: Cannot find item_definitions folder**

**Expected plugin structure:**
```
YourPlugin/
├── Code/
│   ├── tools/
│   │   └── function_extraction_tool.py
│   └── loader/
│       └── item_definition_loader.py
├── item_definitions/          ← Should be HERE
│   └── Item Definition_wiper.pdf
├── plugin.json
└── requirements.txt
```

**Troubleshooting:**
1. Run: "debug plugin structure" to see current paths
2. Ensure item_definitions/ is at plugin root level
3. Check that plugin.json exists at plugin root
"""
    
    # Find matching files
    matching_files = find_matching_files(system_name, item_definitions_path, cat)
    
    if not matching_files:
        # Get list of available files for helpful error message
        all_files = list(item_definitions_path.glob("*"))
        available_files = [f.name for f in all_files if f.suffix in ['.docx', '.pdf', '.txt', '.doc']]
        
        return f"""❌ **No item definition found for '{system_name}'**

📁 **Available files in item_definitions/:**
{chr(10).join(['  • ' + f for f in available_files]) if available_files else '  (folder is empty)'}

💡 **Tips:**
• The fuzzy matcher can handle variations:
  - "Wiper" → "Item Definition_wiper.pdf" ✅
  - "BMS" → "Item Definition_BMS.docx" ✅
  - Case insensitive: "wiper" = "Wiper" = "WIPER" ✅

• Try using the exact system name from one of the files above
• Or run "debug plugin structure" for detailed diagnostics
"""
    
    # Process all matching files
    results = []
    total_functions = 0
    
    for file_path in matching_files:
        log.info(f"\n📄 Processing file: {file_path.name}")
        
        # Extract text from file
        text = parse_file(file_path, cat)
        
        if text.startswith("ERROR"):
            results.append(f"\n❌ **{file_path.name}**\n  {text}\n")
            continue
        
        # Extract functions from text
        functions = extract_functions_from_text(text, system_name, cat)
        
        if functions:
            result_text = f"\n✅ **{file_path.name}**\n"
            result_text += f"   Found **{len(functions)} functions**:\n\n"
            
            for func in functions:
                result_text += f"   **{func['id']}**: {func['description']}\n"
            
            results.append(result_text)
            total_functions += len(functions)
        else:
            results.append(f"\n⚠️ **{file_path.name}**\n   No functions found. Document may need manual review or different format.\n")
    
    # Build final response
    if results:
        header = f"# 📋 Functions Extracted from '{system_name}'\n\n"
        header += f"📁 **Source:** `item_definitions/`\n"
        header += f"📄 **Files processed:** {len(matching_files)}\n"
        header += f"🎯 **Total functions found:** {total_functions}\n"
        header += f"{'=' * 50}\n"
        
        return header + "".join(results)
    else:
        return f"⚠️ Files were found but no functions could be extracted. Please check the document format."


# ============================================================================
# DEBUG TOOL
# ============================================================================

@tool(return_direct=True)
def debug_plugin_structure(tool_input: str, cat):
    """
    Debug tool to diagnose plugin folder structure issues.
    
    Shows:
    - Plugin root location
    - Folder structure
    - item_definitions location and contents
    - File accessibility
    
    Use this when extract_functions is not finding your files.
    Input is always None or can be empty.
    """
    
    log.info("🔍 Starting plugin structure diagnostic...")
    
    # Get validation results
    validation = validate_plugin_structure(cat)
    
    # Build diagnostic report
    report = ["# 🔍 Plugin Structure Diagnostic Report\n"]
    
    # Plugin root info
    report.append(f"## 📍 Plugin Root")
    if validation["plugin_root"]:
        report.append(f"**Path:** `{validation['plugin_root']}`")
        report.append(f"**Exists:** {'✅ Yes' if validation['plugin_root_exists'] else '❌ No'}")
    else:
        report.append("❌ **Could not determine plugin root!**")
    
    report.append("")
    
    # item_definitions info
    report.append(f"## 📁 item_definitions Folder")
    if validation["item_definitions_path"]:
        report.append(f"**Path:** `{validation['item_definitions_path']}`")
        report.append(f"**Exists:** {'✅ Yes' if validation['item_definitions_exists'] else '❌ No'}")
    
    report.append("")
    
    # Files found
    report.append(f"## 📄 Files in item_definitions")
    if validation["files_found"]:
        report.append(f"**Count:** {len(validation['files_found'])}")
        report.append("\n**Files:**")
        for filename in validation["files_found"]:
            report.append(f"  • {filename}")
    else:
        report.append("❌ **No files found** (folder may be empty)")
    
    report.append("")
    
    # Errors
    if validation["errors"]:
        report.append(f"## ⚠️ Issues Detected")
        for error in validation["errors"]:
            report.append(f"  • {error}")
        report.append("")
    
    # Status
    report.append(f"## ✅ Status")
    if validation["structure_valid"]:
        report.append("**Plugin structure is VALID** ✅")
        report.append("\nYou can now use: `extract functions from [system_name]`")
    else:
        report.append("**Plugin structure has ISSUES** ❌")
        report.append("\n**Next steps:**")
        report.append("1. Ensure `item_definitions/` folder exists at plugin root")
        report.append("2. Add your ISO 26262 documents to `item_definitions/`")
        report.append("3. Run this diagnostic again to verify")
    
    return "\n".join(report)