"""
Item Definition Loader
======================
Manages loading and caching of ISO 26262 item definitions.

Location: Plugin/Code/loader/item_definition_loader.py
"""

"""
Item Definition Loader
======================
Manages loading and caching of ISO 26262 item definitions.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# ✅ CORRECT - Import from parent directory using relative import
from ..utils import get_item_definitions_path


@dataclass
class ItemDefinition:
    """Represents an ISO 26262 Item Definition document"""
    system_name: str
    file_path: Path
    file_type: str
    last_modified: datetime
    functions: List[Dict] = None
    is_loaded: bool = False
    
    def __repr__(self):
        return f"ItemDefinition(system='{self.system_name}', file='{self.file_path.name}')"


class ItemDefinitionLoader:
    """
    Manages loading and caching of item definitions.
    
    Features:
    - Discovers available item definitions
    - Caches loaded documents
    - Tracks modifications
    - Provides search capabilities
    """
    
    def __init__(self, cat):
        """
        Initialize the loader.
        
        Args:
            cat: StrayCat instance
        """
        self.cat = cat
        self.cache: Dict[str, ItemDefinition] = {}
        self.item_definitions_path = None
        self._load_available_definitions()
    
    def _load_available_definitions(self):
        """Discover all available item definitions in the folder."""
        self.cat.log.info("🔍 Discovering available item definitions...")
        
        self.item_definitions_path = get_item_definitions_path(self.cat)
        
        if not self.item_definitions_path:
            self.cat.log.error("❌ Could not locate item_definitions folder")
            return
        
        supported_extensions = ['.docx', '.pdf', '.txt', '.doc']
        
        for ext in supported_extensions:
            for file_path in self.item_definitions_path.glob(f"*{ext}"):
                if file_path.is_file():
                    # Extract system name from filename
                    system_name = self._extract_system_name(file_path.name)
                    
                    # Get file metadata
                    last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    # Create ItemDefinition object
                    item_def = ItemDefinition(
                        system_name=system_name,
                        file_path=file_path,
                        file_type=ext,
                        last_modified=last_modified
                    )
                    
                    # Add to cache (use file path as key for uniqueness)
                    cache_key = str(file_path)
                    self.cache[cache_key] = item_def
                    
                    self.cat.log.info(f"  ✅ Discovered: {item_def}")
        
        self.cat.log.info(f"📚 Total item definitions found: {len(self.cache)}")
    
    def _extract_system_name(self, filename: str) -> str:
        """
        Extract system name from filename.
        
        Handles formats like:
        - "Item Definition_wiper.pdf" → "wiper"
        - "BMS_Item_Definition.docx" → "BMS"
        - "ADAS_System.pdf" → "ADAS"
        """
        import re
        
        # Remove extension
        name_no_ext = Path(filename).stem
        
        # Handle "Item Definition_system" format
        if "item definition" in name_no_ext.lower() or "item_definition" in name_no_ext.lower():
            parts = re.split(r'item[_\s-]+definition[_\s-]+', name_no_ext, flags=re.IGNORECASE)
            if len(parts) > 1:
                return parts[1].strip('_- ').title()
        
        # Handle "system_Item_Definition" format
        if "item" in name_no_ext.lower() and "definition" in name_no_ext.lower():
            parts = re.split(r'[_\s-]+item[_\s-]+definition', name_no_ext, flags=re.IGNORECASE)
            if len(parts) > 0:
                return parts[0].strip('_- ').title()
        
        # Default: use filename without extension
        return name_no_ext.replace('_', ' ').replace('-', ' ').title()
    
    def get_all_systems(self) -> List[str]:
        """
        Get list of all available system names.
        
        Returns:
            List of system names
        """
        systems = set()
        for item_def in self.cache.values():
            systems.add(item_def.system_name)
        return sorted(list(systems))
    
    def find_by_system_name(self, system_name: str, fuzzy: bool = True) -> List[ItemDefinition]:
        """
        Find item definitions matching a system name.
        
        Args:
            system_name: The system name to search for
            fuzzy: Whether to use fuzzy matching (default: True)
            
        Returns:
            List of matching ItemDefinition objects
        """
        from difflib import SequenceMatcher
        
        matches = []
        system_normalized = system_name.lower().strip()
        
        for item_def in self.cache.values():
            item_normalized = item_def.system_name.lower()
            
            # Exact match
            if system_normalized == item_normalized:
                matches.append(item_def)
                continue
            
            # Substring match
            if system_normalized in item_normalized or item_normalized in system_normalized:
                matches.append(item_def)
                continue
            
            # Fuzzy match (if enabled)
            if fuzzy:
                similarity = SequenceMatcher(None, system_normalized, item_normalized).ratio()
                if similarity >= 0.6:  # 60% similarity threshold
                    matches.append(item_def)
        
        return matches
    
    def get_by_file_path(self, file_path: Path) -> Optional[ItemDefinition]:
        """
        Get item definition by file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ItemDefinition if found, None otherwise
        """
        cache_key = str(file_path)
        return self.cache.get(cache_key)
    
    def reload_cache(self):
        """Reload the cache by rediscovering all item definitions."""
        self.cat.log.info("🔄 Reloading item definitions cache...")
        self.cache.clear()
        self._load_available_definitions()
    
    def get_summary(self) -> Dict:
        """
        Get a summary of loaded item definitions.
        
        Returns:
            Dictionary with summary information
        """
        file_types = {}
        for item_def in self.cache.values():
            file_types[item_def.file_type] = file_types.get(item_def.file_type, 0) + 1
        
        return {
            'total_definitions': len(self.cache),
            'unique_systems': len(set(item.system_name for item in self.cache.values())),
            'file_types': file_types,
            'systems': self.get_all_systems()
        }


# ============================================================================
# HELPER FUNCTIONS FOR HOOKS
# ============================================================================

def preload_item_definitions(cat):
    """
    Preload all item definitions at plugin startup.
    Can be called from plugin hooks.
    
    Args:
        cat: StrayCat instance
        
    Returns:
        ItemDefinitionLoader instance
    """
    loader = ItemDefinitionLoader(cat)
    summary = loader.get_summary()
    
    cat.log.info(f"📚 Item definitions loaded:")
    cat.log.info(f"  • Total: {summary['total_definitions']}")
    cat.log.info(f"  • Unique systems: {summary['unique_systems']}")
    cat.log.info(f"  • Systems: {', '.join(summary['systems'])}")
    
    return loader


def get_loader_instance(cat):
    """
    Get or create ItemDefinitionLoader instance.
    
    This can be cached in working memory to avoid recreating.
    
    Args:
        cat: StrayCat instance
        
    Returns:
        ItemDefinitionLoader instance
    """
    # Check if loader exists in working memory
    if not hasattr(cat.working_memory, 'item_definition_loader'):
        cat.working_memory['item_definition_loader'] = ItemDefinitionLoader(cat)
    
    return cat.working_memory['item_definition_loader']