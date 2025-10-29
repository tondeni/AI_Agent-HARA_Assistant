# ==============================================================================
# code/models/__init__.py
# Models module - Data structures for HARA
# ==============================================================================

"""
HARA Models Module

Defines data structures for ISO 26262-3:2018 HARA:
- HAZOP results
- Operational situations
- Hazards with E/S/C ratings
- Safety goals
- Complete HARA dataset
"""

from .hara_models import (
    HazopResult,
    OperationalSituation,
    Hazard,
    SafetyGoal,
    HARAData,
    validate_asil,
    validate_severity,
    validate_exposure,
    validate_controllability
)

__all__ = [
    'HazopResult',
    'OperationalSituation',
    'Hazard',
    'SafetyGoal',
    'HARAData',
    'validate_asil',
    'validate_severity',
    'validate_exposure',
    'validate_controllability'
]