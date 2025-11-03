# ==============================================================================
# core/__init__.py
# Core module initialization
# ==============================================================================

"""
ISO 26262 HARA Core Components

This module provides reusable base classes and utilities for ISO 26262-3:2018
HARA workflow implementation.
"""

from .iso26262_base import (
    ISO26262WorkProduct,
    Function,
    HazardousEvent,
    SafetyGoal,
    ISO26262Tool,
    ISO26262Generator,
    WorkflowManager
)

__version__ = "1.0.0"

__all__ = [
    'ISO26262WorkProduct',
    'Function',
    'HazardousEvent',
    'SafetyGoal',
    'OperationalSituation',
    'ISO26262Tool',
    'ISO26262Generator',
    'WorkflowManager',
    'parse_item_name',
    'validate_rating_format',
    'load_json_template',
    'calculate_statistics'
]