# ==============================================================================
# code/generators/HARA/scenarios_generator.py
# Business logic for generating operational situations
# Optimized: LLM outputs JSON directly (no template conversion)
# ==============================================================================

"""
Scenarios Generator
Generates operational situations for exposure assessment
Per ISO 26262-3:2018, Clause 6.4.4

Output: Clean, structured JSON data
"""

from typing import List, Dict, Optional
from cat.log import log
import json
import os
from datetime import datetime


class ScenariosGenerator:
    """
    Generate operational situations for HARA exposure assessment.
    
    LLM outputs JSON directly for maximum efficiency.
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
            List of operational situation dictionaries:
            [
                {
                    "scenario_id": "OS-001",
                    "name": "Urban Driving",
                    "description": "...",
                    "exposure_class": "E4",
                    "duration_percentage": 40,
                    "vehicle_state": "...",
                    "environmental_conditions": "...",
                    "rationale": "...",
                    "metadata": {...}
                },
                ...
            ]
        """
        
        log.info(f"🔍 Generating operational situations for {system_name}")
        
        # Build context from HAZOP if available
        hazop_context = ""
        if hazop_results:
            # Get sample hazardous events for context
            events = list(set([
                h.get('hazardous_event', '') 
                for h in hazop_results[:10]
            ]))[:5]
            
            if events:
                hazop_context = "\n\n**Sample Hazardous Events for Context:**\n"
                hazop_context += "\n".join([f"- {e}" for e in events])
        
        # Build prompt for LLM
        prompt = self._build_scenarios_prompt(system_name, hazop_context)
        
        try:
            # Get LLM response
            response = self.llm(prompt).strip()
            
            # Parse JSON response
            scenarios = self._parse_scenarios_response(response)
            
            if not scenarios:
                log.warning("LLM did not return valid scenarios, using fallback")
                scenarios = self._get_fallback_scenarios(system_name)
            
            # Add unique IDs and metadata
            scenarios = self._enrich_scenarios(scenarios, system_name)
            
            log.info(f"✅ Generated {len(scenarios)} operational situations")
            
            return scenarios
            
        except Exception as e:
            log.error(f"Error generating scenarios: {e}")
            return self._get_fallback_scenarios(system_name)
    
    def _build_scenarios_prompt(self, system_name: str, hazop_context: str) -> str:
        """Build prompt for LLM to generate operational situations directly as JSON."""
        
        prompt = f"""You are a Functional Safety Engineer performing HARA per ISO 26262-3:2018, Clause 6.4.4.

**Task:** Generate 6-8 distinct operational situations for exposure assessment.

**System:** {system_name}
{hazop_context}

**Instructions:**
1. Identify 6-8 typical operational situations where {system_name} operates.
2. For each situation, specify:
   - Name of the operational situation
   - Detailed description
   - **Estimated duration as percentage of operating time (0-100)**
   - **Exposure classification (E0-E4)**
   - Vehicle state during this situation
   - Environmental conditions
   - Rationale for the exposure rating

3. **CRITICAL RULE:** The `exposure_class` MUST be derived *directly* from the `duration_percentage`. You MUST follow the mapping in the "Exposure Rating Scale" section below. Your rationale must explicitly state this link.
4. Ensure situations cover main operating modes:
   - Urban/city driving
   - Highway/motorway driving
   - Parking/low-speed maneuvers
   - Adverse weather conditions (rain, snow, fog)
   - Nighttime driving
   - Vehicle stationary (idling, charging, etc.)
   - High/Low traffic density

**Exposure Rating Scale (ISO 26262-3:2018, Table 4):**
- **E4:** High probability (≥10% of average operating time)
- **E3:** Medium probability (1% to <10% of average operating time)
- **E2:** Low probability (0.1% to <1% of average operating time)
- **E1:** Very low probability (0.001% to <0.1% of average operating time)
- **E0:** Incredibly unlikely (<0.001% of average operating time)

**MANDATORY MAPPING (Duration -> Exposure):**
- `duration_percentage` >= 10: `exposure_class` MUST be **E4**
- 1 <= `duration_percentage` < 10: `exposure_class` MUST be **E3**
- 0.1 <= `duration_percentage` < 1: `exposure_class` MUST be **E2**
- 0.001 <= `duration_percentage` < 0.1: `exposure_class` MUST be **E1**
- `duration_percentage` < 0.001: `exposure_class` MUST be **E0**

**Output Format:**
You MUST output ONLY a valid JSON array. Each scenario should be a JSON object with these exact fields:
- "name": Brief name of the operational situation
- "description": Detailed description of the situation
- "exposure_class": Exposure rating ("E0", "E1", "E2", "E3", or "E4")
- "duration_percentage": Estimated percentage of operating time (0-100)
- "vehicle_state": Description of vehicle state (speed, motion, etc.)
- "environmental_conditions": Description of environmental conditions
- "rationale": Justification for the exposure rating (e.g., "Duration is 40% (>= 10%), so Exposure is E4.")

**Example JSON format:**
[
  {{
    "name": "Urban City Driving (High Traffic)",
    "description": "Driving in city traffic with frequent stops at traffic lights, pedestrian crossings, and congested areas.",
    "exposure_class": "E4",
    "duration_percentage": 40,
    "vehicle_state": "Moving at 0-50 km/h with frequent acceleration and braking.",
    "environmental_conditions": "Various weather conditions, daylight and nighttime, urban infrastructure.",
    "rationale": "This scenario accounts for ~40% of operating time (>= 10%), so the exposure class is E4."
  }},
  {{
    "name": "Driving in Heavy Rain/Storm",
    "description": "Operating the vehicle during adverse weather conditions, such as heavy rain or snow, leading to reduced visibility and road grip.",
    "exposure_class": "E3",
    "duration_percentage": 5,
    "vehicle_state": "Moving at reduced speeds (e.g., 40-80 km/h) with wipers and lights active.",
    "environmental_conditions": "Heavy rain, snow, or fog. Wet/icy roads. Low visibility.",
    "rationale": "This scenario accounts for ~5% of operating time (1% <= duration < 10%), so the exposure class is E3."
  }}
]

**CRITICAL:** - Output ONLY the JSON array, no additional text
- Use double quotes for all strings
- Ensure duration percentages sum to approximately 100%
- Adhere strictly to the MANDATORY MAPPING rule.

Provide your operational situations as JSON now:"""
        
        return prompt
    
    def _parse_scenarios_response(self, response: str) -> List[Dict]:
        """
        Parse LLM JSON response into structured scenarios.
        
        Expected format: JSON array with scenario objects
        
        Returns:
            List of scenario dictionaries
        """
        
        scenarios = []
        
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned_response = response.strip()
            
            # Remove markdown code block markers
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                lines = lines[1:]  # Skip first line
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines)
            
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            scenarios_data = json.loads(cleaned_response)
            
            # Ensure it's a list
            if not isinstance(scenarios_data, list):
                log.error(f"Expected JSON array, got {type(scenarios_data)}")
                return []
            
            # Process each scenario
            for scenario_data in scenarios_data:
                # Validate required fields
                required_fields = ['name', 'description', 'exposure_class', 
                                 'duration_percentage', 'vehicle_state', 
                                 'environmental_conditions']
                
                if not all(field in scenario_data for field in required_fields):
                    log.warning(f"Skipping incomplete scenario: {scenario_data}")
                    continue
                
                # Normalize exposure class
                exposure = scenario_data['exposure_class'].strip().upper()
                if not exposure.startswith('E'):
                    exposure = 'E' + exposure
                if exposure not in ['E0', 'E1', 'E2', 'E3', 'E4']:
                    log.warning(f"Invalid exposure '{exposure}', defaulting to E3")
                    exposure = 'E3'
                
                # Validate duration percentage
                duration = scenario_data['duration_percentage']
                if not isinstance(duration, (int, float)) or duration < 0 or duration > 100:
                    log.warning(f"Invalid duration {duration}, defaulting to 10")
                    duration = 10
                
                # Create standardized scenario dict
                scenario = {
                    'name': scenario_data['name'].strip(),
                    'description': scenario_data['description'].strip(),
                    'exposure_class': exposure,
                    'duration_percentage': float(duration),
                    'vehicle_state': scenario_data['vehicle_state'].strip(),
                    'environmental_conditions': scenario_data['environmental_conditions'].strip(),
                    'rationale': scenario_data.get('rationale', '').strip()
                }
                
                scenarios.append(scenario)
            
            log.info(f"✅ Parsed {len(scenarios)} scenarios from JSON response")
            
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.error(f"Response was: {response[:500]}...")
            
            # Fallback: try to extract JSON from response
            scenarios = self._fallback_parse(response)
        
        except Exception as e:
            log.error(f"Unexpected error parsing response: {e}")
            return []
        
        return scenarios
    
    def _fallback_parse(self, response: str) -> List[Dict]:
        """Fallback parser if JSON parsing fails."""
        
        scenarios = []
        
        try:
            # Look for JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                scenarios_data = json.loads(json_str)
                
                if isinstance(scenarios_data, list):
                    log.info("✅ Fallback parser found valid JSON array")
                    
                    for scenario_data in scenarios_data:
                        if not isinstance(scenario_data, dict):
                            continue
                        
                        # Extract fields with defaults
                        scenario = {
                            'name': scenario_data.get('name', 'Unnamed Scenario'),
                            'description': scenario_data.get('description', ''),
                            'exposure_class': scenario_data.get('exposure_class', 'E3').upper(),
                            'duration_percentage': float(scenario_data.get('duration_percentage', 10)),
                            'vehicle_state': scenario_data.get('vehicle_state', ''),
                            'environmental_conditions': scenario_data.get('environmental_conditions', ''),
                            'rationale': scenario_data.get('rationale', '')
                        }
                        
                        scenarios.append(scenario)
        
        except Exception as e:
            log.error(f"Fallback parser also failed: {e}")
        
        return scenarios
    
    def _enrich_scenarios(self, scenarios: List[Dict], system_name: str) -> List[Dict]:
        """Add unique IDs and metadata to scenarios."""
        
        timestamp = datetime.now().isoformat()
        
        for idx, scenario in enumerate(scenarios, 1):
            # Add unique scenario ID
            scenario['scenario_id'] = f"OS-{idx:03d}"
            
            # Add metadata
            scenario['metadata'] = {
                'system_name': system_name,
                'created_date': timestamp,
                'iso_standard': 'ISO 26262-3:2018',
                'clause': '6.4.4'
            }
        
        return scenarios
    
    def _get_fallback_scenarios(self, system_name: str) -> List[Dict]:
        """Return default scenarios if LLM generation fails."""
        
        log.warning("Using fallback default scenarios")
        
        default_scenarios = [
            {
                'name': 'Urban Driving',
                'description': f'City driving with {system_name} active, frequent stops, traffic lights, pedestrians',
                'exposure_class': 'E4',
                'duration_percentage': 40,
                'vehicle_state': 'Moving, 0-50 km/h, frequent braking',
                'environmental_conditions': 'Urban environment, various weather',
                'rationale': 'Urban driving represents ~40% of typical operating time'
            },
            {
                'name': 'Highway Driving',
                'description': f'Continuous highway driving with {system_name} operating at higher speeds',
                'exposure_class': 'E4',
                'duration_percentage': 35,
                'vehicle_state': 'Moving, 80-130 km/h, steady speed',
                'environmental_conditions': 'Highway conditions, various weather',
                'rationale': 'Highway usage represents ~35% of typical operating time'
            },
            {
                'name': 'Parking Maneuvers',
                'description': f'Low-speed parking with {system_name} assisting or monitoring',
                'exposure_class': 'E4',
                'duration_percentage': 10,
                'vehicle_state': 'Moving, 0-10 km/h, tight spaces',
                'environmental_conditions': 'Parking areas, confined spaces',
                'rationale': 'Parking occurs multiple times per trip, ~10% of time'
            },
            {
                'name': 'Adverse Weather',
                'description': f'Driving in rain, snow, fog with {system_name} active',
                'exposure_class': 'E3',
                'duration_percentage': 10,
                'vehicle_state': 'Moving, reduced speed',
                'environmental_conditions': 'Heavy rain, snow, fog, reduced visibility',
                'rationale': 'Adverse weather occurs 1-10% of operating time'
            },
            {
                'name': 'Stationary Idling',
                'description': f'Vehicle stationary with {system_name} systems active',
                'exposure_class': 'E3',
                'duration_percentage': 5,
                'vehicle_state': 'Stationary, engine on',
                'environmental_conditions': 'Various',
                'rationale': 'Idling at stops represents ~5% of operating time'
            }
        ]
        
        # Enrich with IDs and metadata
        return self._enrich_scenarios(default_scenarios, system_name)


# ==============================================================================
# UTILITY FUNCTIONS FOR JSON OUTPUT
# ==============================================================================

def export_scenarios_to_json(
    scenarios: List[Dict], 
    filepath: Optional[str] = None
) -> str:
    """
    Export scenarios to JSON format.
    
    Args:
        scenarios: List of scenario dictionaries
        filepath: Optional path to save JSON file
    
    Returns:
        JSON string
    """
    
    if not scenarios:
        output = {
            "status": "error",
            "message": "No scenarios to export"
        }
        return json.dumps(output, indent=2)
    
    # Build export structure
    export_data = {
        "analysis_type": "Operational Situations",
        "iso_standard": "ISO 26262-3:2018",
        "clause": "6.4.4",
        "export_timestamp": datetime.now().isoformat(),
        "total_scenarios": len(scenarios),
        "scenarios": scenarios
    }
    
    # Calculate statistics
    exposure_dist = {}
    total_duration = 0
    
    for scenario in scenarios:
        exp = scenario.get('exposure_class', 'E0')
        exposure_dist[exp] = exposure_dist.get(exp, 0) + 1
        total_duration += scenario.get('duration_percentage', 0)
    
    export_data['statistics'] = {
        'exposure_distribution': exposure_dist,
        'total_duration_covered': total_duration
    }
    
    # Convert to JSON
    json_output = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    # Save to file if requested
    if filepath:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_output)
            log.info(f"✅ Scenarios exported to {filepath}")
        except Exception as e:
            log.error(f"Failed to save JSON to {filepath}: {e}")
    
    return json_output


def format_scenarios_table(scenarios: List[Dict]) -> str:
    """Format operational situations as markdown table."""
    
    if not scenarios:
        return "No operational situations available."
    
    table = "| ID | Scenario | Exposure | Duration | Description |\n"
    table += "|:---|:---------|:--------:|:--------:|:------------|\n"
    
    for scenario in scenarios:
        table += f"| {scenario.get('scenario_id', 'N/A')} | "
        table += f"{scenario.get('name', 'N/A')} | "
        table += f"**{scenario.get('exposure_class', 'N/A')}** | "
        table += f"{scenario.get('duration_percentage', 0)}% | "
        table += f"{scenario.get('description', 'N/A')[:60]}... |\n"
    
    return table


def calculate_exposure_statistics(scenarios: List[Dict]) -> Dict:
    """Calculate exposure statistics from scenarios."""
    
    if not scenarios:
        return {
            "status": "error",
            "message": "No scenarios available"
        }
    
    total_duration = sum(s.get('duration_percentage', 0) for s in scenarios)
    
    exposure_counts = {'E0': 0, 'E1': 0, 'E2': 0, 'E3': 0, 'E4': 0}
    for scenario in scenarios:
        exposure = scenario.get('exposure_class', 'E0')
        if exposure in exposure_counts:
            exposure_counts[exposure] += 1
    
    return {
        'status': 'success',
        'total_scenarios': len(scenarios),
        'total_duration_covered': total_duration,
        'exposure_distribution': exposure_counts,
        'average_duration_per_scenario': total_duration / len(scenarios) if scenarios else 0
    }