"""
Path Utilities for Nested Plugin Structure
===========================================
Handles path resolution when plugin has subdirectories like:
Plugin/
├── Code/
│   ├── tools/
│   └── loader/
└── item_definitions/

Usage:
    from .path_utils import get_plugin_root, get_item_definitions_path
"""

from pathlib import Path
from typing import Optional
from cat.log import log


def get_plugin_root(cat) -> Optional[Path]:
    """
    Get the plugin root directory, regardless of where this code is called from.
    
    Works with nested structure:
    - If called from Plugin/Code/tools/tool.py → returns Plugin/
    - If called from Plugin/Code/loader/loader.py → returns Plugin/
    - If called from Plugin/main.py → returns Plugin/
    
    Args:
        cat: StrayCat instance
        
    Returns:
        Path to plugin root directory
    """
    
    # Method 1: Use mad_hatter (MOST RELIABLE)
    try:
        plugin = cat.mad_hatter.get_plugin()
        if plugin and hasattr(plugin, 'path'):
            plugin_root = Path(plugin.path)
            log.info(f"✅ Plugin root (via mad_hatter): {plugin_root}")
            return plugin_root
    except Exception as e:
        log.warning(f"⚠️ Could not get plugin path from mad_hatter: {e}")
    
    # Method 2: Navigate up from current file location
    # This works when __file__ is available
    try:
        current_file = Path(__file__).resolve()
        
        # Search upwards for plugin.json (indicates plugin root)
        current = current_file.parent
        max_levels = 5  # Safety limit
        
        for _ in range(max_levels):
            plugin_json = current / "plugin.json"
            if plugin_json.exists():
                log.info(f"✅ Plugin root (via plugin.json search): {current}")
                return current
            
            # Check if we've reached the plugins directory
            if current.name == "plugins":
                log.error("❌ Reached 'plugins' directory without finding plugin.json")
                break
                
            current = current.parent
        
        log.error("❌ Could not find plugin.json within 5 parent directories")
        
    except Exception as e:
        log.error(f"❌ Error navigating file system: {e}")
    
    return None


def get_item_definitions_path(cat) -> Optional[Path]:
    """
    Get the path to item_definitions folder.
    
    Expected structure:
    Plugin/
    └── item_definitions/
        ├── Item Definition_wiper.pdf
        ├── BMS_Item_Definition.docx
        └── ...
    
    Args:
        cat: StrayCat instance
        
    Returns:
        Path to item_definitions folder, or None if not found
    """
    
    plugin_root = get_plugin_root(cat)
    
    if not plugin_root:
        log.error("❌ Cannot determine plugin root directory")
        return None
    
    item_definitions = plugin_root / "item_definitions"
    
    # Validation and debugging
    log.info(f"🔍 Plugin root: {plugin_root}")
    log.info(f"🔍 Looking for item_definitions at: {item_definitions}")
    log.info(f"🔍 Plugin root exists: {plugin_root.exists()}")
    log.info(f"🔍 item_definitions exists: {item_definitions.exists()}")
    
    if not item_definitions.exists():
        log.error(f"❌ item_definitions folder not found at: {item_definitions}")
        
        # List what IS in plugin root for debugging
        if plugin_root.exists():
            contents = list(plugin_root.glob("*"))
            log.info(f"📁 Plugin root contents: {[item.name for item in contents]}")
        
        return None
    
    # List files in item_definitions for debugging
    files = list(item_definitions.glob("*"))
    log.info(f"📁 Files in item_definitions ({len(files)}): {[f.name for f in files[:10]]}")
    
    return item_definitions


def validate_plugin_structure(cat) -> dict:
    """
    Validate the entire plugin structure and return diagnostic info.
    
    Returns:
        Dictionary with validation results
    """
    
    results = {
        "plugin_root": None,
        "plugin_root_exists": False,
        "item_definitions_path": None,
        "item_definitions_exists": False,
        "structure_valid": False,
        "files_found": [],
        "errors": []
    }
    
    # Check plugin root
    plugin_root = get_plugin_root(cat)
    if plugin_root:
        results["plugin_root"] = str(plugin_root)
        results["plugin_root_exists"] = plugin_root.exists()
    else:
        results["errors"].append("Cannot determine plugin root")
        return results
    
    # Check item_definitions
    item_def_path = plugin_root / "item_definitions"
    results["item_definitions_path"] = str(item_def_path)
    results["item_definitions_exists"] = item_def_path.exists()
    
    if not item_def_path.exists():
        results["errors"].append(f"item_definitions folder not found at {item_def_path}")
        return results
    
    # List files
    try:
        files = list(item_def_path.glob("*"))
        results["files_found"] = [f.name for f in files if f.is_file()]
        
        if not results["files_found"]:
            results["errors"].append("item_definitions folder is empty")
        else:
            results["structure_valid"] = True
            
    except Exception as e:
        results["errors"].append(f"Error reading item_definitions: {str(e)}")
    
    return results


# Alternative: Explicit path construction for your specific structure
def get_item_definitions_path_explicit(cat) -> Optional[Path]:
    """
    Alternative method using explicit path construction.
    Use this if the automatic method doesn't work.
    
    Assumes this file is in: Plugin/Code/tools/ or Plugin/Code/loader/
    And item_definitions is at: Plugin/item_definitions/
    """
    
    try:
        # Get current file location
        current_file = Path(__file__).resolve()
        log.info(f"📍 Current file: {current_file}")
        
        # Navigate up to plugin root
        # If in Code/tools/ → go up 2 levels
        # If in Code/loader/ → go up 2 levels
        # If in Code/ → go up 1 level
        
        # Find the plugin root by looking for plugin.json
        current = current_file.parent
        
        # Try up to 3 levels
        for i in range(3):
            plugin_json = current / "plugin.json"
            log.debug(f"  Checking for plugin.json at: {plugin_json}")
            
            if plugin_json.exists():
                plugin_root = current
                log.info(f"✅ Found plugin root: {plugin_root}")
                
                item_definitions = plugin_root / "item_definitions"
                log.info(f"🔍 item_definitions path: {item_definitions}")
                
                return item_definitions
            
            current = current.parent
        
        log.error("❌ Could not find plugin.json in parent directories")
        return None
        
    except Exception as e:
        log.error(f"❌ Error in explicit path resolution: {e}")
        return None