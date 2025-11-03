# ==============================================================================
# code/utils/__init__.py
# Utilities module initialization
# ==============================================================================

"""
HARA Assistant Utilities Module

Provides reusable utility functions and classes for:
- Fuzzy name matching
- String normalization
- Configuration management
"""
from .path_utils import (
    get_plugin_root,
    get_item_definitions_path,
    validate_plugin_structure
)

from .fuzzy_name_matcher import (
    FuzzyNameMatcher,
    create_default_aliases,
    save_aliases_to_file
)

__version__ = "1.0.0"

__all__ = [
    'FuzzyNameMatcher',
    'create_default_aliases',
    'save_aliases_to_file',
    'get_item_definitions_path', 
    'validate_plugin_structure',
    'get_plugin_root',
    'get_item_definitions_path',
    'validate_plugin_structure'
]