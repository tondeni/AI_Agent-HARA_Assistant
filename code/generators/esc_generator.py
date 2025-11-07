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
    
    def _determine_asil(self, severity: str, exposure: str, controllability: str) -> str:
        """
        Determine ASIL from E, S, C ratings per ISO 26262-3:2018, Table 4.
        """
        
        s = severity
        e = exposure
        c = controllability
        
        # S0, E0, or C0 always result in QM (Quality Management)
        if s == 'S0' or e == 'E0' or c == 'C0':
            return 'QM'
        
        # S1
        if s == 'S1':
            if e in ['E1', 'E2']:
                if c in ['C1', 'C2', 'C3']:
                    return 'QM'
            elif e == 'E3':
                if c in ['C1', 'C2']:
                    return 'QM'
                elif c == 'C3':
                    return 'A'
            elif e == 'E4':
                if c == 'C1':
                    return 'QM'
                elif c == 'C2':
                    return 'A'
                elif c == 'C3':
                    return 'B'
        
        # S2
        elif s == 'S2':
            if e in ['E1', 'E2']:
                if c in ['C1', 'C2', 'C3']:
                    return 'QM'
            elif e == 'E3':
                if c in ['C1', 'C2']:
                    return 'A'
                elif c == 'C3':
                    return 'B'
            elif e == 'E4':
                if c == 'C1':
                    return 'A'
                elif c == 'C2':
                    return 'B'
                elif c == 'C3':
                    return 'C'
        
        # S3
        elif s == 'S3':
            if e in ['E1', 'E2']:
                if c == 'C1':
                    return 'QM' # Note: ISO 26262:2018 recommends QM
                elif c == 'C2':
                    return 'A'
                elif c == 'C3':
                    return 'B'
            elif e == 'E3':
                if c == 'C1':
                    return 'A'
                elif c == 'C2':
                    return 'B'
                elif c == 'C3':
                    return 'C'
            elif e == 'E4':
                if c == 'C1':
                    return 'B'
                elif c == 'C2':
                    return 'C'
                elif c == 'C3':
                    return 'D'
                    
        # Fallback
        return 'QM'
    
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
            # --- THIS IS THE FIX ---
            # We must pass 'scenarios' to the parser so it can
            # look up the Exposure (E) rating.
            hazards = self._parse_esc_response(response, hazop_batch, scenarios)
            
            return hazards
            
        except Exception as e:
            log.error(f"Error assessing batch: {e}")
            # Return hazards with default ratings
            # We must also pass 'scenarios' to the fallback function
            return self._create_default_hazards(hazop_batch, scenarios)
    
    def _build_esc_prompt(
        self,
        hazop_batch: List[Dict],
        scenarios: List[Dict],
        system_name: str
    ) -> str:
        """Build prompt for E/S/C assessment."""
        
        # Format scenarios
        scenarios_text = "\n".join([
            f"- {s.get('name', 'N/A')} (Exposure: {s.get('exposure_class', 'E?')})"
            for s in scenarios
        ])
        
        # Format hazards
        hazards_text = ""
        for idx, hazop in enumerate(hazop_batch, 1):
            hazards_text += f"\n{idx}. **{hazop.get('function_name', 'Unknown')}** / {hazop.get('guide_word', 'N/A')}\n"
            hazards_text += f"   Malfunction: {hazop.get('malfunctioning_behavior', 'N/A')}\n"
            hazards_text += f"   Hazard: {hazop.get('hazardous_event', 'N/A')}\n"
            # This is now presented as a fixed, non-negotiable value
            hazards_text += f"   Given Severity: {hazop.get('severity', 'S?')} (This rating is fixed from HAZOP)\n"
        
        prompt = f"""You are an expert Functional Safety Engineer performing E/S/C assessment per ISO 26262-3:2018.
Your goal is to be realistic and pragmatic.

**System:** {system_name}

**Available Operational Situations (Source for Exposure):**
{scenarios_text}

**Hazards to Assess:**
{hazards_text}

**Task:** For each hazard, you must:
1.  **Link to Situation:** Select the *one* most relevant 'Operational Situation' from the list above.
2.  **Assess Controllability (C):** Critically assess the controllability of the hazard.

The **Severity (S)** is already determined by the HAZOP analysis and **must not be changed**.
The **Exposure (E)** is determined by the situation you select.
Your **only** assessment task is **Controllability (C)**.

---
### 1. Severity (S) & Exposure (E)
* **Severity (S):** ACCEPT the 'Given Severity' from the hazard. This is fixed.
* **Exposure (E):** SELECT the *one* most relevant 'Operational Situation' from the list. The E-rating for the hazard will be the one from that situation.

### 2. Controllability (C0-C3) - YOUR MAIN TASK
Can an *average driver* avoid harm *when the hazard occurs*? How much time do they have?
* **Rule:** Assume a non-expert, "average" driver.
* **Example (Wiper Failure):**
    * **Hazard:** "Loss of wiper function in heavy rain."
    * **Analysis:** The failure is obvious. The driver has many seconds (or minutes) to react. The standard response is to slow down, turn on hazard lights, and pull over.
    * **Correct Controllability:** **C1 (Simply controllable)** or **C2 (Normally controllable)**. It is **NOT C3**.
* **C3 (Difficult/uncontrollable):** Use for failures with < 1-2 seconds of reaction time OR failures that require expert skill (e.g., sudden steering lock, brake loss on a steep downhill).
* **C2 (Normally controllable):** Use for failures that are obvious and give the driver several seconds to react (e.g., engine power loss, gradual brake fade, wiper failure).
* **C1 (Simply controllable):** Use for failures that are non-critical or have very simple recovery actions (e.g., HVAC failure, radio failure).
* **C0 (Controllable in general):** Use for trivial faults.

---
**Output Format:** Return ONLY a valid JSON array. Each hazard must be a JSON object. Provide **strong, clear rationale** for your Controllability choice.

```json
[
  {{
    "hazard_index": 1,
    "selected_situation_name": "Driving in heavy storm",
    "controllability": "C2",
    "controllability_rationale": "Driver has sufficient time (many seconds) to react to a loss of wipers. The standard response is to slow down and find a safe place to stop. This is 'normally controllable' by >90% of drivers. It is not C3."
  }}
]
```
Return the JSON array now (no markdown, no explanatory text, ONLY the JSON array):"""
        
        return prompt
    
    def _parse_esc_response(
        self,
        response: str,
        hazop_batch: List[Dict],
        scenarios: List[Dict]
    ) -> List[Dict]:
        """Parse LLM JSON response into hazard dicts with E/S/C ratings."""
        import json
        import re
        
        hazards = []
        
        try:
            # Try to extract JSON array from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response
            
            # Parse JSON
            assessments = json.loads(json_str)
            
            # Match assessments to hazop batch
            for idx, hazop in enumerate(hazop_batch):
                # Find matching assessment
                assessment = None
                if idx < len(assessments):
                    assessment = assessments[idx]
                else:
                    log.warning(f"No assessment found for hazard {idx+1}")
                    assessment = {}
                
                # 1. Get data from LLM (Controllability + Situation Name)
                c_rating = assessment.get('controllability', 'C2')
                c_rationale = assessment.get('controllability_rationale', 'Default - requires review')
                selected_situation_name = assessment.get('selected_situation_name', 'General operation')

                # 2. Get data from HAZOP input (Severity)
                s_rating = hazop.get('severity', 'S2')
                s_rationale = hazop.get('severity_rationale', 'From HAZOP preliminary assessment')

                # 3. Get data from Scenarios (Exposure)
                e_rating = 'E3' # Default
                e_rationale = 'Default - requires review'
                
                # Find the selected scenario to get its E-rating
                selected_scenario = next((s for s in scenarios if s.get('name') == selected_situation_name), None)
                
                if selected_scenario:
                    e_rating = selected_scenario.get('exposure_class', 'E3')
                    e_rationale = selected_scenario.get('rationale', 'Rationale from selected operational situation')
                else:
                    log.warning(f"Could not find matching scenario '{selected_situation_name}' for hazard {hazop.get('id')}")
                    e_rationale = f"Could not find matching scenario '{selected_situation_name}'. Defaulting to E3."
                    selected_situation_name = f"ERROR: Not Found ('{selected_situation_name}')"

                # 4. Create hazard dict (combine S, E, C)
                hazard = {
                    'id': f"H-{idx + 1:03d}", # Note: This ID will be overwritten by the tool
                    'function_id': hazop.get('function_id', 'F-??'),
                    'function_name': hazop.get('function_name', 'Unknown'),
                    'guide_word': hazop.get('guide_word', 'N/A'),
                    'malfunctioning_behavior': hazop.get('malfunctioning_behavior', 'N/A'),
                    'hazardous_event': hazop.get('hazardous_event', 'N/A'),
                    
                    'operational_situation': selected_situation_name,
                    
                    'severity': s_rating,
                    'severity_rationale': s_rationale,
                    'exposure': e_rating,
                    'exposure_rationale': e_rationale,
                    'controllability': c_rating,
                    'controllability_rationale': c_rationale,
                }
                
                hazards.append(hazard)
        
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.warning(f"LLM Response: {response[:500]}...")
            # Fallback to default hazards
            return self._create_default_hazards(hazop_batch)
        
        except Exception as e:
            log.error(f"Error parsing E/S/C response: {e}")
            return self._create_default_hazards(hazop_batch)
        
        return hazards
    
    def _create_default_hazards(self, hazop_batch: List[Dict], scenarios: List[Dict]) -> List[Dict]:
        """Create hazards with default E/S/C ratings as fallback."""
        
        hazards = []
        
        # Try to get a default scenario
        default_scenario_name = "General operation"
        default_exposure = "E3"
        if scenarios:
            default_scenario_name = scenarios[0].get('name', 'General operation')
            default_exposure = scenarios[0].get('exposure_class', 'E3')

        for idx, hazop in enumerate(hazop_batch):
            hazard = {
                'id': f"H-{idx + 1:03d}",
                'function_id': hazop.get('function_id', 'F-??'),
                'function_name': hazop.get('function_name', 'Unknown'),
                'guide_word': hazop.get('guide_word', 'N/A'),
                'malfunctioning_behavior': hazop.get('malfunctioning_behavior', 'N/A'),
                'hazardous_event': hazop.get('hazardous_event', 'N/A'),
                'operational_situation': default_scenario_name,
                'exposure': default_exposure,
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