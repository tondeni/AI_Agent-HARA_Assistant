# core/iso26262_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
from pydantic import BaseModel
from cat.log import log

# ============================================================================
# Base Data Models (using Pydantic for validation)
# ============================================================================

class ISO26262WorkProduct(BaseModel):
    """Base class for all ISO 26262 work products"""
    id: str
    name: str
    description: str
    created_at: str
    modified_at: str
    version: str = "1.0"
    
    class Config:
        extra = "allow"  # Allow additional fields


class Function(ISO26262WorkProduct):
    """Item Function representation"""
    function_type: str = "safety_relevant"


class HazardousEvent(ISO26262WorkProduct):
    """Hazardous Event with E/S/C ratings"""
    function_id: str
    guideword: str
    malfunction: str
    hazard_description: str
    exposure: str = ""
    severity: str = ""
    controllability: str = ""
    asil: str = "QM"


class SafetyGoal(ISO26262WorkProduct):
    """Safety Goal derived from hazardous event"""
    hazard_id: str
    asil: str
    safe_state: str
    ftti: str
    
    def validate_asil(self) -> Tuple[bool, List[str]]:
        """Validate ASIL assignment"""
        issues = []
        if self.asil not in ['QM', 'A', 'B', 'C', 'D']:
            issues.append(f"Invalid ASIL: {self.asil}")
        return len(issues) == 0, issues


# ============================================================================
# Base Tool Class
# ============================================================================

class ISO26262Tool(ABC):
    """
    Abstract base class for ISO 26262 workflow tools.
    
    Provides:
    - Consistent error handling
    - Logging
    - Working memory access patterns
    - Validation
    """
    
    def __init__(self, cat):
        self.cat = cat
        self.working_memory = cat.working_memory
        self.llm = cat.llm
    
    @abstractmethod
    def execute(self, tool_input: str) -> str:
        """Execute the tool logic"""
        pass
    
    def get_workflow_data(self, key: str, default=None):
        """Safely retrieve data from working memory"""
        return self.working_memory.get(key, default)
    
    def set_workflow_data(self, key: str, value: Any):
        """Store data in working memory"""
        self.working_memory[key] = value
        log.info(f"✅ Stored {key} in working memory")
    
    def validate_prerequisites(self, required_keys: List[str]) -> Tuple[bool, List[str]]:
        """Check if required data exists in working memory"""
        missing = []
        for key in required_keys:
            if key not in self.working_memory or not self.working_memory[key]:
                missing.append(key)
        return len(missing) == 0, missing
    
    def format_error(self, error_msg: str, suggestions: List[str]) -> str:
        """Consistently format error messages"""
        output = f"❌ **Error:** {error_msg}\n\n"
        if suggestions:
            output += "**Suggestions:**\n"
            for suggestion in suggestions:
                output += f"- {suggestion}\n"
        return output
    
    def format_success(self, message: str, data: Dict = None, next_steps: List[str] = None) -> str:
        """Consistently format success messages"""
        output = f"✅ **{message}**\n\n"
        
        if data:
            for key, value in data.items():
                output += f"**{key}:** {value}\n"
        
        if next_steps:
            output += "\n**Next Steps:**\n"
            for step in next_steps:
                output += f"- {step}\n"
        
        return output
    
    def format_warning(self, message: str, details: List[str] = None) -> str:
        """Format warning messages"""
        output = f"⚠️ **Warning:** {message}\n\n"
        
        if details:
            for detail in details:
                output += f"- {detail}\n"
        
        return output


# ============================================================================
# Base Generator Class
# ============================================================================

class ISO26262Generator(ABC):
    """Base class for document generators"""
    
    def __init__(self, llm=None):
        self.llm = llm
    
    @abstractmethod
    def generate(self, data: Dict) -> str:
        """Generate document and return file path"""
        pass
    
    def validate_data(self, data: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate input data"""
        missing = [field for field in required_fields if field not in data or not data[field]]
        return len(missing) == 0, missing
    
    def get_output_filename(self, system_name: str, doc_type: str, extension: str) -> str:
        """Generate standardized filename"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = system_name.replace(' ', '_')
        return f"{clean_name}_{doc_type}_{timestamp}.{extension}"


# ============================================================================
# Workflow State Manager
# ============================================================================

class WorkflowManager:
    """
    Manages HARA workflow state and validation.
    
    Tracks:
    - Current workflow stage
    - Completion status of each step
    - Data quality indicators
    """
    
    WORKFLOW_STAGES = [
        'not_started',
        'functions_extracted',
        'hazop_complete',
        'situations_defined',
        'esc_assessed',
        'asil_determined',
        'safety_goals_derived',
        'documents_generated'
    ]
    
    STAGE_NAMES = {
        'not_started': 'Not Started',
        'functions_extracted': 'Functions Extracted',
        'hazop_complete': 'HAZOP Complete',
        'situations_defined': 'Operational Situations Defined',
        'esc_assessed': 'E/S/C Assessment Complete',
        'asil_determined': 'ASIL Determined',
        'safety_goals_derived': 'Safety Goals Derived',
        'documents_generated': 'Documents Generated'
    }
    
    def __init__(self, cat):
        self.cat = cat
        self.wm = cat.working_memory
    
    def get_current_stage(self) -> str:
        """Get current workflow stage"""
        return self.wm.get('hara_workflow_stage', 'not_started')
    
    def advance_stage(self, new_stage: str):
        """Move to next workflow stage"""
        if new_stage in self.WORKFLOW_STAGES:
            self.wm['hara_workflow_stage'] = new_stage
            self.wm['hara_stage'] = new_stage  # Backwards compatibility
            log.info(f"📍 Workflow advanced to: {new_stage}")
    
    def get_completion_status(self) -> Dict:
        """Return workflow completion status"""
        return {
            'functions_extracted': bool(self.wm.get('item_functions')),
            'hazop_complete': bool(self.wm.get('hazop_results')),
            'situations_defined': bool(self.wm.get('hara_operational_situations') or self.wm.get('operational_situations')),
            'esc_assessed': self._check_esc_complete(),
            'asil_determined': self._check_asil_complete(),
            'safety_goals_derived': bool(self.wm.get('hara_safety_goals')),
        }
    
    def get_progress_percentage(self) -> int:
        """Calculate workflow completion percentage"""
        status = self.get_completion_status()
        completed = sum(1 for v in status.values() if v)
        total = len(status)
        return int((completed / total) * 100)
    
    def get_next_step(self) -> Optional[str]:
        """Get next recommended workflow step"""
        status = self.get_completion_status()
        
        if not status['functions_extracted']:
            return "extract functions from [Item Name]"
        elif not status['hazop_complete']:
            return "apply hazop analysis"
        elif not status['situations_defined']:
            return "define operational situations"
        elif not status['esc_assessed']:
            return "assess esc for all hazards"
        elif not status['asil_determined']:
            return "determine asil"
        elif not status['safety_goals_derived']:
            return "derive safety goals"
        else:
            return "generate hara documents"
    
    def _check_esc_complete(self) -> bool:
        """Check if all hazards have E/S/C ratings"""
        hazards = self.wm.get('hara_hazardous_events', []) or self.wm.get('complete_hara_table', [])
        if not hazards:
            return False
        return any(
            h.get('exposure') and h.get('severity') and h.get('controllability')
            for h in hazards
        )
    
    def _check_asil_complete(self) -> bool:
        """Check if all hazards have ASIL ratings"""
        hazards = self.wm.get('hara_hazardous_events', []) or self.wm.get('complete_hara_table', [])
        if not hazards:
            return False
        return any(h.get('asil') and h.get('asil') != 'QM' for h in hazards)
    
    def is_ready_for_document_generation(self) -> Tuple[bool, List[str]]:
        """Check if workflow is complete enough for document generation"""
        status = self.get_completion_status()
        minimum_required = [
            'functions_extracted',
            'hazop_complete',
            'safety_goals_derived'
        ]
        missing = [step for step in minimum_required if not status.get(step)]
        return len(missing) == 0, missing
    
    def get_status_summary(self) -> str:
        """Get formatted status summary"""
        status = self.get_completion_status()
        current_stage = self.get_current_stage()
        progress = self.get_progress_percentage()
        next_step = self.get_next_step()
        
        output = f"**Workflow Progress:** {progress}%\n"
        output += f"**Current Stage:** {self.STAGE_NAMES.get(current_stage, current_stage)}\n\n"
        
        output += "**Step Completion:**\n"
        for step, complete in status.items():
            icon = "✅" if complete else "❌"
            step_name = step.replace('_', ' ').title()
            output += f"{icon} {step_name}\n"
        
        if next_step:
            output += f"\n**Next Step:** {next_step}\n"
        
        return output


# ============================================================================
# Common Utilities
# ============================================================================

def parse_item_name(tool_input: Any) -> str:
    """Parse item name from various input formats"""
    if isinstance(tool_input, str):
        # Remove common prefixes
        name = tool_input.strip()
        prefixes = [
            'extract functions from',
            'extract from',
            'analyze',
            'for',
            'item:',
            'system:',
            'name:'
        ]
        
        for prefix in prefixes:
            if name.lower().startswith(prefix):
                name = name[len(prefix):].strip()
        
        return name
    
    elif isinstance(tool_input, dict):
        return tool_input.get('item_name', tool_input.get('name', 'Unknown System'))
    
    return 'Unknown System'


def validate_rating_format(rating: str, rating_type: str, max_value: int) -> Tuple[bool, str]:
    """Validate E/S/C rating format"""
    prefix = rating_type[0].upper()  # E, S, or C
    
    if not rating or not isinstance(rating, str):
        return False, f"Missing {rating_type}"
    
    if not rating.startswith(prefix):
        return False, f"Invalid {rating_type} format: {rating} (expected {prefix}0-{prefix}{max_value})"
    
    try:
        value = int(rating[1:])
        if value < 0 or value > max_value:
            return False, f"{rating_type} out of range: {rating} (expected {prefix}0-{prefix}{max_value})"
    except ValueError:
        return False, f"Invalid {rating_type} format: {rating}"
    
    return True, ""


def load_json_template(plugin_folder: str, template_name: str) -> Optional[Dict]:
    """Load JSON template file"""
    import os
    import json
    
    template_path = os.path.join(plugin_folder, 'templates', template_name)
    
    if not os.path.exists(template_path):
        log.warning(f"Template not found: {template_path}")
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Error loading template {template_name}: {e}")
        return None


def calculate_statistics(hazards: List[Dict], field: str) -> Dict[str, int]:
    """Calculate distribution statistics for a field"""
    stats = {}
    
    for hazard in hazards:
        value = hazard.get(field, 'Unknown')
        stats[value] = stats.get(value, 0) + 1
    
    return stats


# ============================================================================
# Export
# ============================================================================

__all__ = [
    'ISO26262WorkProduct',
    'Function',
    'HazardousEvent',
    'SafetyGoal',
    'ISO26262Tool',
    'ISO26262Generator',
    'WorkflowManager',
    'parse_item_name',
    'validate_rating_format',
    'load_json_template',
    'calculate_statistics'
]