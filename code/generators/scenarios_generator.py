# ==============================================================================
# code/generators/HARA/scenarios_generator.py
# Business logic for generating operational situations
# ==============================================================================

"""
Scenarios Generator
Generates operational situations for exposure assessment
Per ISO 26262-3:2018, Clause 6.4.4
"""

from typing import List, Dict
from cat.log import log
import json
import os


class ScenariosGenerator:
    """
    Generate operational situations for HARA exposure assessment.
    
    Operational situations represent driving scenarios where the system
    operates and where hazardous events could occur.
    """
    
    # Standard automotive operational situation categories
    SITUATION_CATEGORIES = {
        'urban': 'City/urban driving with frequent stops',
        'highway': 'Highway/motorway continuous driving',
        'parking': 'Parking and low-speed maneuvers',
        'adverse_weather': 'Rain, snow, fog, ice conditions',
        'night': 'Nighttime driving conditions',
        'emergency': 'Emergency braking or evasive maneuvers',
        'startup_shutdown': 'Vehicle startup and shutdown sequences'
    }
    
    def __init__(self, llm_function, plugin_folder: str):
        """
        Initialize scenarios generator.
        
        Args:
            llm_function: LLM function (cat.llm)
            plugin_folder: Path to plugin folder (for templates)
        """
        self.llm = llm_function
        self.plugin_folder = plugin_folder
        self.template_scenarios = self._load_template_scenarios()
    
    def _load_template_scenarios(self) -> Dict:
        """Load operational situations template from JSON."""
        template_path = os.path.join(
            self.plugin_folder, "templates", "operational_situations.json"
        )
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            log.info(f"✅ Loaded operational situations template")
            return data
        except FileNotFoundError:
            log.warning(f"Template not found, using defaults")
            return self._get_default_scenarios()
        except Exception as e:
            log.error(f"Error loading template: {e}")
            return self._get_default_scenarios()
    
    def _get_default_scenarios(self) -> Dict:
        """Return default operational situations if template not available."""
        return {
            "operational_situations": [
                {
                    "id": "OS-01",
                    "name": "Urban Driving",
                    "description": "City driving with frequent stops, traffic lights, pedestrians",
                    "exposure_class": "E4",
                    "duration_percentage": 40,
                    "vehicle_state": "Moving, 0-50 km/h",
                    "environmental_conditions": "Various weather, daylight"
                },
                {
                    "id": "OS-02",
                    "name": "Highway Driving",
                    "description": "Continuous highway driving at higher speeds",
                    "exposure_class": "E4",
                    "duration_percentage": 35,
                    "vehicle_state": "Moving, 80-130 km/h",
                    "environmental_conditions": "Various weather, day and night"
                },
                {
                    "id": "OS-03",
                    "name": "Parking Maneuvers",
                    "description": "Low-speed parking, reversing, maneuvering",
                    "exposure_class": "E4",
                    "duration_percentage": 10,
                    "vehicle_state": "Moving, 0-10 km/h",
                    "environmental_conditions": "Various, confined spaces"
                },
                {
                    "id": "OS-04",
                    "name": "Adverse Weather Driving",
                    "description": "Rain, snow, fog, reduced visibility",
                    "exposure_class": "E3",
                    "duration_percentage": 10,
                    "vehicle_state": "Moving, reduced speed",
                    "environmental_conditions": "Heavy rain, snow, fog"
                },
                {
                    "id": "OS-05",
                    "name": "Stationary with Engine On",
                    "description": "Vehicle stationary but systems active",
                    "exposure_class": "E3",
                    "duration_percentage": 5,
                    "vehicle_state": "Stationary, engine on",
                    "environmental_conditions": "Various"
                }
            ]
        }
    
    def generate_scenarios(
        self, 
        system_name: str,
        hazop_results: List[Dict] = None
    ) -> List[Dict]:
        """
        Generate operational situations tailored to the system.
        
        Args:
            system_name: Name of system being analyzed
            hazop_results: Optional HAZOP results for context
        
        Returns:
            List of operational situation dictionaries
        """
        
        log.info(f"🔍 Generating operational situations for {system_name}")
        
        # Start with template scenarios
        base_scenarios = self.template_scenarios.get('operational_situations', [])
        
        # Customize for this system using LLM
        customized_scenarios = self._customize_scenarios(
            base_scenarios,
            system_name,
            hazop_results
        )
        
        log.info(f"✅ Generated {len(customized_scenarios)} operational situations")
        
        return customized_scenarios
    
    def _customize_scenarios(
        self,
        base_scenarios: List[Dict],
        system_name: str,
        hazop_results: List[Dict] = None
    ) -> List[Dict]:
        """
        Customize scenarios for the specific system.
        
        Uses LLM to adjust scenarios based on system characteristics.
        """
        
        # Build context from HAZOP if available
        hazop_context = ""
        if hazop_results:
            # Get unique hazardous events
            events = list(set([h.get('hazardous_event', '') for h in hazop_results[:10]]))
            hazop_context = f"\n\n**Sample Hazardous Events:**\n" + "\n".join([f"- {e}" for e in events])
        
        # Build scenarios summary
        scenarios_text = ""
        for scenario in base_scenarios:
            scenarios_text += f"\n{scenario['id']}: {scenario['name']} (E{scenario['exposure_class'][-1]})\n"
            scenarios_text += f"   {scenario['description']}\n"
        
        prompt = f"""You are a Functional Safety Engineer performing HARA per ISO 26262-3:2018.

**Task:** Review and customize operational situations for the system.

**System:** {system_name}

**Base Operational Situations:**
{scenarios_text}
{hazop_context}

**Instructions:**
1. Review the base scenarios
2. Adjust descriptions to be specific to {system_name}
3. Verify exposure ratings (E0-E4) are appropriate
4. Add system-specific scenarios if needed (max 7 total scenarios)
5. Ensure scenarios cover the main operating modes

**Exposure Rating Scale:**
- E4: High probability (≥10% of operating time)
- E3: Medium probability (1-10% of operating time)
- E2: Low probability (0.1-1% of operating time)
- E1: Very low probability (0.001-0.1% of operating time)
- E0: Incredibly unlikely (<0.001% of operating time)

**Output Format:**

Return a JSON array of operational situations:

```json
[
  {{
    "id": "OS-01",
    "name": "Scenario Name",
    "description": "Detailed description specific to {system_name}",
    "exposure_class": "E4",
    "duration_percentage": 40,
    "vehicle_state": "State description",
    "environmental_conditions": "Conditions description"
  }},
  ...
]
```

Provide the customized operational situations now (JSON only):"""
        
        try:
            # Get LLM response
            response = self.llm(prompt).strip()
            
            # Extract JSON from response
            scenarios = self._parse_scenarios_response(response)
            
            # Validate and return
            if scenarios:
                return scenarios
            else:
                log.warning("LLM did not return valid scenarios, using base scenarios")
                return base_scenarios
                
        except Exception as e:
            log.error(f"Error customizing scenarios: {e}")
            return base_scenarios
    
    def _parse_scenarios_response(self, response: str) -> List[Dict]:
        """Parse LLM response to extract scenarios JSON."""
        
        # Try to find JSON in response
        import re
        
        # Look for JSON array
        json_match = re.search(r'\[[\s\S]*\]', response)
        
        if json_match:
            try:
                scenarios = json.loads(json_match.group(0))
                
                # Validate structure
                if isinstance(scenarios, list) and len(scenarios) > 0:
                    # Check first scenario has required fields
                    required_fields = ['id', 'name', 'description', 'exposure_class']
                    if all(field in scenarios[0] for field in required_fields):
                        log.info(f"✅ Parsed {len(scenarios)} scenarios from LLM")
                        return scenarios
            except json.JSONDecodeError as e:
                log.error(f"JSON parsing error: {e}")
        
        return []


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_scenarios_table(scenarios: List[Dict]) -> str:
    """Format operational situations as markdown table."""
    
    if not scenarios:
        return "No operational situations available."
    
    table = "| ID | Scenario | Exposure | Duration | Description |\n"
    table += "|----|----------|----------|----------|-------------|\n"
    
    for scenario in scenarios:
        table += f"| {scenario.get('id', 'N/A')} | "
        table += f"{scenario.get('name', 'N/A')} | "
        table += f"{scenario.get('exposure_class', 'N/A')} | "
        table += f"{scenario.get('duration_percentage', 0)}% | "
        table += f"{scenario.get('description', 'N/A')[:50]}... |\n"
    
    return table


def calculate_total_exposure(scenarios: List[Dict]) -> Dict:
    """Calculate exposure statistics from scenarios."""
    
    total_duration = sum(s.get('duration_percentage', 0) for s in scenarios)
    
    exposure_counts = {'E0': 0, 'E1': 0, 'E2': 0, 'E3': 0, 'E4': 0}
    for scenario in scenarios:
        exposure = scenario.get('exposure_class', 'E0')
        if exposure in exposure_counts:
            exposure_counts[exposure] += 1
    
    return {
        'total_scenarios': len(scenarios),
        'total_duration_covered': total_duration,
        'exposure_distribution': exposure_counts
    }