# ==============================================================================
# code/generators/HARA/asil_calculator.py
# ASIL determination logic - migrated and improved
# ==============================================================================

"""
ASIL Calculator
Determines ASIL based on ISO 26262-3:2018 Table 4
Combines Exposure (E), Severity (S), and Controllability (C)
"""

from typing import List, Dict, Tuple
from cat.log import log
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class ASILCalculator:
    """
    Calculate ASIL based on E/S/C combinations per ISO 26262-3:2018 Table 4.
    
    The ASIL (Automotive Safety Integrity Level) is determined by:
    - Severity (S0-S3): Potential for injuries
    - Exposure (E0-E4): Probability of operational situation
    - Controllability (C0-C3): Ability to avoid harm
    """
    
    # ISO 26262-3:2018 Table 4 ASIL Matrix
    # Structure: ASIL_MATRIX[S][E][C] = ASIL
    # E0-E4 mapped to 0-4, S0-S3 mapped to 0-3, C0-C3 mapped to 0-3
    ASIL_MATRIX = {
        # S0: No injuries → Always QM
        0: {
            0: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            1: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            2: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            3: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            4: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'}
        },
        # S1: Light to moderate injuries
        1: {
            0: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            1: {0: 'QM', 1: 'A', 2: 'A', 3: 'A'},
            2: {0: 'QM', 1: 'A', 2: 'B', 3: 'B'},
            3: {0: 'QM', 1: 'A', 2: 'B', 3: 'C'},
            4: {0: 'QM', 1: 'A', 2: 'B', 3: 'C'}
        },
        # S2: Severe injuries (survival probable)
        2: {
            0: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            1: {0: 'QM', 1: 'A', 2: 'B', 3: 'C'},
            2: {0: 'QM', 1: 'B', 2: 'C', 3: 'C'},
            3: {0: 'QM', 1: 'B', 2: 'C', 3: 'D'},
            4: {0: 'QM', 1: 'B', 2: 'C', 3: 'D'}
        },
        # S3: Life-threatening to fatal injuries
        3: {
            0: {0: 'QM', 1: 'QM', 2: 'QM', 3: 'QM'},
            1: {0: 'QM', 1: 'B', 2: 'C', 3: 'D'},
            2: {0: 'QM', 1: 'C', 2: 'D', 3: 'D'},
            3: {0: 'QM', 1: 'C', 2: 'D', 3: 'D'},
            4: {0: 'QM', 1: 'C', 2: 'D', 3: 'D'}
        }
    }
    
    def __init__(self):
        """Initialize ASIL calculator."""
        pass
    
    def calculate_asil(
        self,
        severity: str,
        exposure: str,
        controllability: str
    ) -> Tuple[str, str]:
        """
        Calculate ASIL for a single E/S/C combination.
        
        Args:
            severity: S0, S1, S2, or S3
            exposure: E0, E1, E2, E3, or E4
            controllability: C0, C1, C2, or C3
        
        Returns:
            Tuple of (ASIL, rationale)
        """
        
        # Parse ratings to integers
        try:
            s = int(severity.replace('S', ''))
            e = int(exposure.replace('E', ''))
            c = int(controllability.replace('C', ''))
        except (ValueError, AttributeError):
            return 'INVALID', f"Invalid E/S/C format: {exposure}/{severity}/{controllability}"
        
        # Validate ranges
        if not (0 <= s <= 3):
            return 'INVALID', f"Severity {severity} out of range (S0-S3)"
        if not (0 <= e <= 4):
            return 'INVALID', f"Exposure {exposure} out of range (E0-E4)"
        if not (0 <= c <= 3):
            return 'INVALID', f"Controllability {controllability} out of range (C0-C3)"
        
        # Lookup ASIL in matrix
        asil = self.ASIL_MATRIX[s][e][c]
        
        # Build rationale
        rationale = self._build_asil_rationale(s, e, c, asil)
        
        return asil, rationale
    
    def _build_asil_rationale(
        self,
        s: int,
        e: int,
        c: int,
        asil: str
    ) -> str:
        """Build rationale for ASIL determination."""
        
        # Special cases
        if s == 0:
            return "ASIL QM: No injuries possible (S0)"
        
        if c == 0:
            return "ASIL QM: Hazard controllable in general (C0)"
        
        if e == 0:
            return "ASIL QM: Incredibly unlikely exposure (E0)"
        
        # Standard cases
        severity_desc = ['No injuries', 'Light/moderate injuries', 'Severe injuries', 'Life-threatening/fatal'][s]
        exposure_desc = ['Incredibly unlikely', 'Very low', 'Low', 'Medium', 'High'][e]
        control_desc = ['Controllable', 'Simply controllable', 'Normally controllable', 'Difficult/uncontrollable'][c]
        
        rationale = f"ASIL {asil}: Combination of {severity_desc} (S{s}), "
        rationale += f"{exposure_desc} exposure (E{e}), "
        rationale += f"and {control_desc} (C{c}) "
        rationale += f"per ISO 26262-3:2018 Table 4"
        
        return rationale
    
    def determine_asil_for_hazards(self, hazards: List[Dict]) -> List[Dict]:
        """
        Determine ASIL for all hazards in list.
        
        Args:
            hazards: List of hazard dicts with E/S/C ratings
        
        Returns:
            Updated list with ASIL and rationale added
        """
        
        log.info(f"🔍 Determining ASIL for {len(hazards)} hazards")
        
        updated_hazards = []
        
        for hazard in hazards:
            # Get E/S/C ratings
            severity = hazard.get('severity', 'S2')
            exposure = hazard.get('exposure', 'E3')
            controllability = hazard.get('controllability', 'C2')
            
            # Calculate ASIL
            asil, rationale = self.calculate_asil(severity, exposure, controllability)
            
            # Add to hazard
            hazard['asil'] = asil
            hazard['asil_rationale'] = rationale
            
            updated_hazards.append(hazard)
        
        log.info(f"✅ ASIL determination complete")
        
        return updated_hazards
    
    def calculate_asil_statistics(self, hazards: List[Dict]) -> Dict:
        """
        Calculate ASIL distribution statistics.
        
        Args:
            hazards: List of hazards with ASIL ratings
        
        Returns:
            Statistics dict with counts and percentages
        """
        
        total = len(hazards)
        
        # Count each ASIL level
        asil_counts = {
            'QM': 0,
            'A': 0,
            'B': 0,
            'C': 0,
            'D': 0
        }
        
        for hazard in hazards:
            asil = hazard.get('asil', 'QM')
            if asil in asil_counts:
                asil_counts[asil] += 1
        
        # Calculate percentages
        asil_percentages = {
            level: (count / total * 100) if total > 0 else 0
            for level, count in asil_counts.items()
        }
        
        # Calculate high-priority count (ASIL C-D)
        high_priority = asil_counts['C'] + asil_counts['D']
        
        # Calculate ASIL-rated count (A-D, excluding QM)
        asil_rated = asil_counts['A'] + asil_counts['B'] + asil_counts['C'] + asil_counts['D']
        
        return {
            'total_hazards': total,
            'asil_counts': asil_counts,
            'asil_percentages': asil_percentages,
            'high_priority_count': high_priority,
            'asil_rated_count': asil_rated,
            'qm_percentage': asil_percentages['QM']
        }
    
    def validate_esc_ratings(self, hazard: Dict) -> Tuple[bool, List[str]]:
        """
        Validate E/S/C ratings in a hazard.
        
        Args:
            hazard: Hazard dict with E/S/C ratings
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        
        errors = []
        
        # Check required fields exist
        required = ['severity', 'exposure', 'controllability']
        for field in required:
            if field not in hazard:
                errors.append(f"Missing {field} rating")
        
        if errors:
            return False, errors
        
        # Validate format
        severity = hazard['severity']
        exposure = hazard['exposure']
        controllability = hazard['controllability']
        
        # Check severity
        if not (severity.startswith('S') and severity[1:].isdigit()):
            errors.append(f"Invalid severity format: {severity} (expected S0-S3)")
        elif int(severity[1:]) > 3:
            errors.append(f"Severity out of range: {severity} (expected S0-S3)")
        
        # Check exposure
        if not (exposure.startswith('E') and exposure[1:].isdigit()):
            errors.append(f"Invalid exposure format: {exposure} (expected E0-E4)")
        elif int(exposure[1:]) > 4:
            errors.append(f"Exposure out of range: {exposure} (expected E0-E4)")
        
        # Check controllability
        if not (controllability.startswith('C') and controllability[1:].isdigit()):
            errors.append(f"Invalid controllability format: {controllability} (expected C0-C3)")
        elif int(controllability[1:]) > 3:
            errors.append(f"Controllability out of range: {controllability} (expected C0-C3)")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_asil_distribution(stats: Dict) -> str:
    """Format ASIL statistics as text summary."""
    
    output = f"Total Hazards: {stats['total_hazards']}\n\n"
    output += "ASIL Distribution:\n"
    
    for level in ['D', 'C', 'B', 'A', 'QM']:
        count = stats['asil_counts'][level]
        pct = stats['asil_percentages'][level]
        output += f"  ASIL {level}: {count} ({pct:.1f}%)\n"
    
    output += f"\nHigh Priority (C-D): {stats['high_priority_count']}\n"
    output += f"ASIL-rated (A-D): {stats['asil_rated_count']}"
    
    return output


def get_asil_level_description(asil: str) -> str:
    """Get description of ASIL level."""
    
    descriptions = {
        'QM': 'Quality Management - No ASIL required',
        'A': 'ASIL A - Lowest safety integrity level',
        'B': 'ASIL B - Low to medium safety integrity',
        'C': 'ASIL C - Medium to high safety integrity',
        'D': 'ASIL D - Highest safety integrity level'
    }
    
    return descriptions.get(asil, 'Unknown ASIL level')