# ==============================================================================
# code/generators/HARA/esc_generator.py
# Business logic for E/S/C assessment
# ==============================================================================

"""
ESC Generator
Assesses Exposure, Severity, and Controllability for hazards
Per ISO 26262-3:2018, Clause 6.4.4
"""

from typing import List, Dict
from cat.log import log
import json
import os


class ESCGenerator:
    """
    Generate E/S/C assessments for HARA hazards.
    
    Evaluates:
    - Exposure (E0-E4): Probability of operational situation
    - Severity (S0-S3): Potential for injuries
    - Controllability (C0-C3): Ability of driver to avoid harm
    """
    
    # Rating scales
    SEVERITY_SCALE = {
        'S0': 'No injuries',
        'S1': 'Light to moderate injuries',
        'S2': 'Severe injuries (survival probable)',
        'S3': 'Life-threatening to fatal injuries'
    }
    
    EXPOSURE_SCALE = {
        'E0': 'Incredibly unlikely (<0.001%)',
        'E1': 'Very low probability (0.001-0.1%)',
        'E2': 'Low probability (0.1-1%)',
        'E3': 'Medium probability (1-10%)',
        'E4': 'High probability (≥10%)'
    }
    
    CONTROLLABILITY_SCALE = {
        'C0': 'Controllable in general (>99% drivers)',
        'C1': 'Simply controllable (≥99% drivers)',
        'C2': 'Normally controllable (≥90% drivers)',
        'C3': 'Difficult/uncontrollable (<90% drivers)'
    }
    
    def __init__(self, llm_function, plugin_folder: str):
        """
        Initialize ESC generator.
        
        Args:
            llm_function: LLM function (cat.llm)
            plugin_folder: Path to plugin folder (for templates)
        """
        self.llm = llm_function
        self.plugin_folder = plugin_folder
        self.rating_tables = self._load_rating_tables() if plugin_folder else {}
    
    def _load_rating_tables(self) -> Dict:
        """Load E/S/C rating tables from template file."""
        template_path = os.path.join(
            self.plugin_folder, "templates", "esc_rating_tables.json"
        )
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            log.info(f"✅ Loaded E/S/C rating tables")
            return data
        except FileNotFoundError:
            log.warning(f"E/S/C template not found, using defaults")
            return {}
        except Exception as e:
            log.error(f"Error loading rating tables: {e}")
            return {}
    
    def assess_esc(
        self,
        hazop_results: List[Dict],
        scenarios: List[Dict],
        system_name: str
    ) -> List[Dict]:
        """
        Perform E/S/C assessment for all HAZOP hazards.
        
        Args:
            hazop_results: HAZOP analysis results
            scenarios: Operational situations
            system_name: Name of system
        
        Returns:
            List of hazard dicts with E/S/C ratings
        """
        
        log.info(f"🔍 Assessing E/S/C for {len(hazop_results)} hazards")
        
        hazards = []
        
        # Process hazards in batches for efficiency
        batch_size = 5
        for i in range(0, len(hazop_results), batch_size):
            batch = hazop_results[i:i+batch_size]
            
            log.info(f"📋 Processing batch {i//batch_size + 1}/{(len(hazop_results)-1)//batch_size + 1}")
            
            batch_hazards = self._assess_batch(batch, scenarios, system_name)
            hazards.extend(batch_hazards)
        
        log.info(f"✅ E/S/C assessment complete: {len(hazards)} hazards")
        
        return hazards
    
    def _assess_batch(
        self,
        hazop_batch: List[Dict],
        scenarios: List[Dict],
        system_name: str
    ) -> List[Dict]:
        """Assess a batch of hazards."""
        
        # Build prompt for batch assessment
        prompt = self._build_esc_prompt(hazop_batch, scenarios, system_name)
        
        try:
            # Get LLM assessment
            response = self.llm(prompt).strip()
            
            # Parse response
            hazards = self._parse_esc_response(response, hazop_batch)
            
            return hazards
            
        except Exception as e:
            log.error(f"Error assessing batch: {e}")
            # Return hazards with default ratings
            return self._create_default_hazards(hazop_batch)
    
    def _build_esc_prompt(
        self,
        hazop_batch: List[Dict],
        scenarios: List[Dict],
        system_name: str
    ) -> str:
        """Build prompt for E/S/C assessment."""
        
        # Format scenarios
        scenarios_text = "\n".join([
            f"- {s.get('name', 'N/A')} ({s.get('exposure_class', 'E?')}): {s.get('description', 'N/A')}"
            for s in scenarios
        ])
        
        # Format hazards
        hazards_text = ""
        for idx, hazop in enumerate(hazop_batch, 1):
            hazards_text += f"\n{idx}. **{hazop.get('function_name', 'Unknown')}** / {hazop.get('guide_word', 'N/A')}\n"
            hazards_text += f"   Malfunction: {hazop.get('malfunctioning_behavior', 'N/A')}\n"
            hazards_text += f"   Hazard: {hazop.get('hazardous_event', 'N/A')}\n"
            hazards_text += f"   Preliminary S: {hazop.get('severity', 'S?')}\n"
        
        prompt = f"""You are a Functional Safety Engineer performing E/S/C assessment per ISO 26262-3:2018, Clause 6.4.4.

**System:** {system_name}

**Operational Situations:**
{scenarios_text}

**Hazards to Assess:**
{hazards_text}

**Task:** For each hazard, assess:

1. **Exposure (E0-E4):** Which operational situation(s) apply? How frequent?
   - E4: ≥10% of operating time
   - E3: 1-10% of operating time
   - E2: 0.1-1% of operating time
   - E1: 0.001-0.1% of operating time
   - E0: <0.001% of operating time

2. **Severity (S0-S3):** Worst-case injuries to occupants or road users?
   - S3: Life-threatening to fatal
   - S2: Severe injuries (survival probable)
   - S1: Light to moderate injuries
   - S0: No injuries

3. **Controllability (C0-C3):** Can average drivers avoid harm?
   - C3: Difficult/uncontrollable (<90% of drivers)
   - C2: Normally controllable (≥90% of drivers)
   - C1: Simply controllable (≥99% of drivers)
   - C0: Controllable in general (>99% of drivers)

**Critical:** Provide detailed rationale for each rating.

**Output Format:**

For each hazard, provide:

---
## Hazard {idx}: [Brief description]

**Exposure:** E[0-4]
**Rationale:** [Why this exposure? Which scenarios? How frequent?]

**Severity:** S[0-3]
**Rationale:** [Worst-case consequences? Why this severity?]

**Controllability:** C[0-3]
**Rationale:** [Can drivers avoid? Response time? Warnings available?]

**Operational Situation:** [Most relevant scenario name]
---

Provide E/S/C assessment now:"""
        
        return prompt
    
    def _parse_esc_response(
        self,
        response: str,
        hazop_batch: List[Dict]
    ) -> List[Dict]:
        """Parse LLM response into hazard dicts with E/S/C ratings."""
        
        hazards = []
        
        # Split into hazard sections
        sections = response.split('## Hazard')
        
        for idx, hazop in enumerate(hazop_batch):
            # Find corresponding section
            section_text = ""
            for section in sections[1:]:  # Skip first empty split
                if section.strip().startswith(f"{idx + 1}"):
                    section_text = section
                    break
            
            # Parse E/S/C from section
            exposure = self._extract_rating(section_text, 'Exposure', 'E')
            severity = self._extract_rating(section_text, 'Severity', 'S')
            controllability = self._extract_rating(section_text, 'Controllability', 'C')
            
            # Extract rationales
            exp_rationale = self._extract_rationale(section_text, 'Exposure')
            sev_rationale = self._extract_rationale(section_text, 'Severity')
            con_rationale = self._extract_rationale(section_text, 'Controllability')
            
            # Extract operational situation
            op_situation = self._extract_operational_situation(section_text)
            
            # Create hazard dict
            hazard = {
                'id': f"H-{idx + 1:03d}",
                'function_id': hazop.get('function_id', 'F-??'),
                'function_name': hazop.get('function_name', 'Unknown'),
                'guide_word': hazop.get('guide_word', 'N/A'),
                'malfunctioning_behavior': hazop.get('malfunctioning_behavior', 'N/A'),
                'hazardous_event': hazop.get('hazardous_event', 'N/A'),
                'operational_situation': op_situation,
                
                # E/S/C ratings
                'exposure': exposure,
                'exposure_rationale': exp_rationale,
                'severity': severity,
                'severity_rationale': sev_rationale,
                'controllability': controllability,
                'controllability_rationale': con_rationale
            }
            
            hazards.append(hazard)
        
        return hazards
    
    def _extract_rating(self, text: str, rating_type: str, prefix: str) -> str:
        """Extract rating (E/S/C) from text."""
        import re
        
        # Look for pattern like "**Exposure:** E4" or "Exposure: E4"
        pattern = rf'\*\*{rating_type}:\*\*\s*{prefix}(\d)'
        match = re.search(pattern, text)
        
        if match:
            return f"{prefix}{match.group(1)}"
        
        # Try without asterisks
        pattern = rf'{rating_type}:\s*{prefix}(\d)'
        match = re.search(pattern, text)
        
        if match:
            return f"{prefix}{match.group(1)}"
        
        # Default
        return f"{prefix}2"
    
    def _extract_rationale(self, text: str, rating_type: str) -> str:
        """Extract rationale for a rating."""
        import re
        
        # Look for "**Rationale:** [text]" after the rating type
        pattern = rf'{rating_type}:.*?\*\*Rationale:\*\*\s*(.*?)(?=\n\*\*|\n\n|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return "Rationale not provided"
    
    def _extract_operational_situation(self, text: str) -> str:
        """Extract operational situation name from text."""
        import re
        
        pattern = r'\*\*Operational Situation:\*\*\s*(.*?)(?=\n---|\n\n|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return "General operation"
    
    def _create_default_hazards(self, hazop_batch: List[Dict]) -> List[Dict]:
        """Create hazards with default E/S/C ratings as fallback."""
        
        hazards = []
        for idx, hazop in enumerate(hazop_batch):
            hazard = {
                'id': f"H-{idx + 1:03d}",
                'function_id': hazop.get('function_id', 'F-??'),
                'function_name': hazop.get('function_name', 'Unknown'),
                'guide_word': hazop.get('guide_word', 'N/A'),
                'malfunctioning_behavior': hazop.get('malfunctioning_behavior', 'N/A'),
                'hazardous_event': hazop.get('hazardous_event', 'N/A'),
                'operational_situation': 'General operation',
                'exposure': 'E3',
                'exposure_rationale': 'Default rating - requires manual review',
                'severity': hazop.get('severity', 'S2'),
                'severity_rationale': 'From HAZOP preliminary assessment',
                'controllability': 'C2',
                'controllability_rationale': 'Default rating - requires manual review'
            }
            hazards.append(hazard)
        
        return hazards
    
    def calculate_esc_statistics(self, hazards: List[Dict]) -> Dict:
        """Calculate E/S/C distribution statistics."""
        
        stats = {
            'total': len(hazards),
            'severity': {'S0': 0, 'S1': 0, 'S2': 0, 'S3': 0},
            'exposure': {'E0': 0, 'E1': 0, 'E2': 0, 'E3': 0, 'E4': 0},
            'controllability': {'C0': 0, 'C1': 0, 'C2': 0, 'C3': 0}
        }
        
        for hazard in hazards:
            # Count severity
            severity = hazard.get('severity', 'S2')
            if severity in stats['severity']:
                stats['severity'][severity] += 1
            
            # Count exposure
            exposure = hazard.get('exposure', 'E3')
            if exposure in stats['exposure']:
                stats['exposure'][exposure] += 1
            
            # Count controllability
            controllability = hazard.get('controllability', 'C2')
            if controllability in stats['controllability']:
                stats['controllability'][controllability] += 1
        
        return stats


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_esc_table(hazards: List[Dict]) -> str:
    """Format E/S/C assessment as markdown table."""
    
    if not hazards:
        return "No hazards available."
    
    table = "| ID | Hazardous Event | E | S | C | Situation |\n"
    table += "|----|----------------|---|---|---|----------|\n"
    
    for hazard in hazards:
        table += f"| {hazard.get('id', 'H-???')} | "
        table += f"{hazard.get('hazardous_event', 'N/A')[:40]}... | "
        table += f"{hazard.get('exposure', 'E?')} | "
        table += f"{hazard.get('severity', 'S?')} | "
        table += f"{hazard.get('controllability', 'C?')} | "
        table += f"{hazard.get('operational_situation', 'N/A')[:20]}... |\n"
    
    return table