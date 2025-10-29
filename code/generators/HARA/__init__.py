# ==============================================================================
# code/generators/HARA/__init__.py
# HARA-specific generators
# ==============================================================================

"""
HARA Generators

ISO 26262-3:2018 compliant generators for:
- HAZOP analysis (Clause 6.4.3)
- E/S/C assessment (Clause 6.4.4)
- ASIL determination (Clause 6.4.5)
- Safety goal derivation (Clause 6.4.6)
- Document generation
"""

from .hazop_generator import HAZOPGenerator, format_hazop_table, get_hazop_statistics

# Other generators to be added:
# from .esc_generator import ESCGenerator
# from .asil_calculator import ASILCalculator
# from .safety_goal_generator import SafetyGoalGenerator
# from .hara_word_generator import HARAWordGenerator
# from .hara_excel_generator import HARAExcelGenerator

__all__ = [
    'HAZOPGenerator',
    'format_hazop_table',
    'get_hazop_statistics',
    # 'ESCGenerator',
    # 'ASILCalculator',
    # 'SafetyGoalGenerator',
    # 'HARAWordGenerator',
    # 'HARAExcelGenerator'
]