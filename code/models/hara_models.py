# ==============================================================================
# code/models/hara_models.py
# Data models for HARA workflow - ISO 26262-3:2018 compliant
# ==============================================================================

"""
Data models for HARA Assistant
Defines structures for hazards, operational situations, and safety goals
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class HazopResult:
    """Single HAZOP analysis result (function + guide word)"""
    function_id: str
    function_name: str
    guide_word: str
    malfunctioning_behavior: str
    hazardous_event: str
    severity: str  # S0-S3
    rationale: str
    
    def to_dict(self) -> Dict:
        return {
            'function_id': self.function_id,
            'function_name': self.function_name,
            'guide_word': self.guide_word,
            'malfunctioning_behavior': self.malfunctioning_behavior,
            'hazardous_event': self.hazardous_event,
            'severity': self.severity,
            'rationale': self.rationale
        }


@dataclass
class OperationalSituation:
    """Operational situation for exposure assessment"""
    id: str
    name: str
    description: str
    exposure_class: str  # E0-E4
    duration_percentage: float
    vehicle_state: str
    environmental_conditions: str
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'exposure_class': self.exposure_class,
            'duration_percentage': self.duration_percentage,
            'vehicle_state': self.vehicle_state,
            'environmental_conditions': self.environmental_conditions
        }


@dataclass
class Hazard:
    """Complete hazard with E/S/C and ASIL"""
    id: str
    hazardous_event: str
    malfunctioning_behavior: str
    function_name: str
    operational_situation: str
    
    # E/S/C ratings
    severity: str  # S0-S3
    severity_rationale: str
    exposure: str  # E0-E4
    exposure_rationale: str
    controllability: str  # C0-C3
    controllability_rationale: str
    
    # ASIL determination
    asil: str  # QM, A, B, C, D
    asil_rationale: str
    
    # Optional safety goal
    safety_goal: Optional[str] = None
    safe_state: Optional[str] = None
    ftti: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'hazardous_event': self.hazardous_event,
            'malfunctioning_behavior': self.malfunctioning_behavior,
            'function_name': self.function_name,
            'operational_situation': self.operational_situation,
            'severity': self.severity,
            'severity_rationale': self.severity_rationale,
            'exposure': self.exposure,
            'exposure_rationale': self.exposure_rationale,
            'controllability': self.controllability,
            'controllability_rationale': self.controllability_rationale,
            'asil': self.asil,
            'asil_rationale': self.asil_rationale,
            'safety_goal': self.safety_goal,
            'safe_state': self.safe_state,
            'ftti': self.ftti
        }


@dataclass
class SafetyGoal:
    """ISO 26262 Safety Goal"""
    id: str
    hazard_id: str
    description: str
    asil: str
    safe_state: str
    ftti: Optional[str] = None
    verification_criteria: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'hazard_id': self.hazard_id,
            'description': self.description,
            'asil': self.asil,
            'safe_state': self.safe_state,
            'ftti': self.ftti,
            'verification_criteria': self.verification_criteria,
            'assumptions': self.assumptions
        }


@dataclass
class HARAData:
    """Complete HARA dataset"""
    system_name: str
    functions: List[str]
    hazop_results: List[HazopResult]
    operational_situations: List[OperationalSituation]
    hazards: List[Hazard]
    safety_goals: List[SafetyGoal]
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'system_name': self.system_name,
            'functions': self.functions,
            'hazop_results': [h.to_dict() for h in self.hazop_results],
            'operational_situations': [os.to_dict() for os in self.operational_situations],
            'hazards': [h.to_dict() for h in self.hazards],
            'safety_goals': [sg.to_dict() for sg in self.safety_goals],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_working_memory(cls, cat):
        """Load HARA data from cat.working_memory"""
        return cls(
            system_name=cat.working_memory.get('hara_item_name', 'System'),
            functions=cat.working_memory.get('item_functions', '').split('\n'),
            hazop_results=[HazopResult(**h) for h in cat.working_memory.get('hazop_results', [])],
            operational_situations=[OperationalSituation(**os) for os in cat.working_memory.get('operational_situations', [])],
            hazards=[Hazard(**h) for h in cat.working_memory.get('complete_hara_table', [])],
            safety_goals=[SafetyGoal(**sg) for sg in cat.working_memory.get('hara_safety_goals', [])],
            metadata=cat.working_memory.get('hara_metadata', {})
        )


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_asil(asil: str) -> bool:
    """Validate ASIL value"""
    return asil.upper() in ['QM', 'A', 'B', 'C', 'D']


def validate_severity(severity: str) -> bool:
    """Validate severity value"""
    return severity.upper() in ['S0', 'S1', 'S2', 'S3']


def validate_exposure(exposure: str) -> bool:
    """Validate exposure value"""
    return exposure.upper() in ['E0', 'E1', 'E2', 'E3', 'E4']


def validate_controllability(controllability: str) -> bool:
    """Validate controllability value"""
    return controllability.upper() in ['C0', 'C1', 'C2', 'C3']