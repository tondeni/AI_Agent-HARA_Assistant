# ==============================================================================
# code/loaders/item_definition_loader.py
# Load Item Definition from multiple sources
# ==============================================================================

import os
from cat.log import log
from typing import Optional


class ItemDefinitionLoader:
    """
    Load Item Definition for HARA analysis from multiple sources.
    
    Search priority:
    1. Working memory (most recent - after ItemDefinition_Developer)
    2. HARA plugin item_definitions/ folder
    3. ItemDefinition_Developer plugin folders
    4. OutputFormatter plugin generated_documents/
    """
    
    def __init__(self, plugin_folder: str):
        """
        Initialize loader with plugin folder path.
        
        Args:
            plugin_folder: Path to HARA_Assistant plugin root
        """
        self.plugin_folder = plugin_folder
        self.item_definitions_folder = os.path.join(plugin_folder, "item_definitions")
        
        # External plugin paths
        self.output_formatter_path = os.path.join(
            plugin_folder, "..", "AI_Agent-OutputFormatter", 
            "generated_documents", "01_Item_Definition"
        )
    
    def load_item_definition(self, item_name: str, cat) -> Optional[str]:
        """
        Find and load Item Definition content.
        
        Args:
            item_name: Name of the item/system
            cat: Cheshire Cat instance (for working memory access)
        
        Returns:
            Item Definition content as string, or None if not found
        """
        
        # SOURCE 1: Working Memory (highest priority)
        content = self._load_from_working_memory(cat, item_name)
        if content:
            log.info("✅ Loaded Item Definition from working memory")
            return content
        
        # SOURCE 2: HARA plugin item_definitions/ folder
        content = self._load_from_folder(self.item_definitions_folder, item_name)
        if content:
            log.info(f"✅ Loaded Item Definition from {self.item_definitions_folder}")
            return content
        
        # SOURCE 3: OutputFormatter generated documents
        content = self._load_from_folder(self.output_formatter_path, item_name)
        if content:
            log.info(f"✅ Loaded Item Definition from OutputFormatter")
            return content
        
        log.warning(f"❌ No Item Definition found for '{item_name}'")
        return None
    
    def _load_from_working_memory(self, cat, item_name: str) -> Optional[str]:
        """
        Load from cat.working_memory (after ItemDefinition_Developer).
        
        Keys checked:
        - item_definition_content
        - item_def_content
        """
        
        # Check standard key
        if "item_definition_content" in cat.working_memory:
            content = cat.working_memory["item_definition_content"]
            if item_name.lower() in content.lower():
                return content
        
        # Check alternative key
        if "item_def_content" in cat.working_memory:
            content = cat.working_memory["item_def_content"]
            if item_name.lower() in content.lower():
                return content
        
        return None
    
    def _load_from_folder(self, folder_path: str, item_name: str) -> Optional[str]:
        """
        Search folder for Item Definition file.
        
        Supports:
        - .txt
        - .md
        - .docx (if available)
        """
        
        if not os.path.exists(folder_path):
            return None
        
        log.info(f"🔍 Searching: {folder_path}")
        
        try:
            for filename in os.listdir(folder_path):
                # Check text files
                if filename.lower().endswith(('.txt', '.md')):
                    if item_name.lower().replace(' ', '_') in filename.lower():
                        file_path = os.path.join(folder_path, filename)
                        return self._read_text_file(file_path)
                
                # Check DOCX files
                elif filename.lower().endswith('.docx'):
                    if item_name.lower().replace(' ', '_') in filename.lower():
                        file_path = os.path.join(folder_path, filename)
                        return self._read_docx_file(file_path)
        
        except Exception as e:
            log.error(f"Error searching folder {folder_path}: {e}")
        
        return None
    
    def _read_text_file(self, file_path: str) -> Optional[str]:
        """Read plain text or markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            log.info(f"✅ Read text file: {os.path.basename(file_path)}")
            return content
        except Exception as e:
            log.error(f"Error reading text file {file_path}: {e}")
            return None
    
    def _read_docx_file(self, file_path: str) -> Optional[str]:
        """Read Word document if python-docx available."""
        try:
            import docx
            doc = docx.Document(file_path)
            content = '\n'.join([para.text for para in doc.paragraphs])
            log.info(f"✅ Read DOCX file: {os.path.basename(file_path)}")
            return content
        except ImportError:
            log.warning("python-docx not installed - cannot read .docx files")
            return None
        except Exception as e:
            log.error(f"Error reading DOCX file {file_path}: {e}")
            return None


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_item_definition(content: str, required_sections: list = None) -> tuple[bool, list]:
    """
    Validate Item Definition content.
    
    Args:
        content: Item Definition text
        required_sections: Optional list of required section names
    
    Returns:
        (is_valid, missing_sections)
    """
    
    if required_sections is None:
        required_sections = [
            'purpose',
            'functions',
            'interfaces',
            'operating environment'
        ]
    
    missing = []
    content_lower = content.lower()
    
    for section in required_sections:
        if section.lower() not in content_lower:
            missing.append(section)
    
    is_valid = len(missing) == 0
    
    return is_valid, missing