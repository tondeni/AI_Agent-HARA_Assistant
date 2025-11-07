# ==============================================================================
# code/generators/HARA/hazop_generator.py
# Business logic for HAZOP analysis
# Optimized: LLM outputs JSON directly (no table parsing)
# ==============================================================================

"""
HAZOP Generator
Applies HAZOP guide words to functions to identify malfunctioning behaviors
Per ISO 26262-3:2018, Clause 6.4.3

Output: Clean, structured JSON data
"""

from typing import List, Dict, Optional
from cat.log import log
import json
import os
from datetime import datetime


class HAZOPGenerator:
    """
    Generate HAZOP analysis for safety functions.
    
    Applies 10 standard HAZOP guide words to each function:
    - NO, MORE, LESS, EARLY, LATE, REVERSE
    - OTHER THAN, PART OF, AS WELL AS, WHERE ELSE
    
    LLM outputs JSON directly for maximum efficiency.
    """
    
    # HAZOP Guide Words
    GUIDE_WORDS = {
        'NO': 'Function not performed',
        'MORE': 'Excessive performance',
        'LESS': 'Insufficient performance',
        'EARLY': 'Too soon / premature',
        'LATE': 'Delayed / too late',
        'REVERSE': 'Opposite function',
        'OTHER THAN': 'Different function',
        'PART OF': 'Incomplete function',
        'AS WELL AS': 'Additional unintended function',
        'WHERE ELSE': 'Wrong location/target'
    }
    
    def __init__(self, llm_function, plugin_folder: str):
        """
        Initialize HAZOP generator.
        
        Args:
            llm_function: LLM function (cat.llm)
            plugin_folder: Path to plugin folder (for templates)
        """
        self.llm = llm_function
        self.plugin_folder = plugin_folder
        self.guide_words = self._load_guide_words()
    
    def _load_guide_words(self) -> Dict:
        """Load HAZOP guide words from template file."""
        template_path = os.path.join(
            self.plugin_folder, "templates", "hazop_guidewords.json"
        )
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            log.info(f"✅ Loaded HAZOP guide words from template")
            return data.get('hazop_guide_words', self.GUIDE_WORDS)
        except FileNotFoundError:
            log.warning(f"Template not found, using default guide words")
            return self.GUIDE_WORDS
        except Exception as e:
            log.error(f"Error loading guide words: {e}")
            return self.GUIDE_WORDS
    
    def generate_hazop(
        self, 
        functions: List[str], 
        system_name: str,
        item_definition: str = ""
    ) -> List[Dict]:
        """
        Generate complete HAZOP analysis.
        
        Args:
            functions: List of function descriptions
            system_name: Name of system being analyzed
            item_definition: Optional context from Item Definition
        
        Returns:
            List of HAZOP hazard dictionaries:
            [
                {
                    "hazard_id": "H-001",
                    "function_id": "F-01",
                    "function_name": "...",
                    "guide_word": "NO",
                    "malfunctioning_behavior": "...",
                    "hazardous_event": "...",
                    "severity": "S2",
                    "severity_rationale": "...",
                    "metadata": {...}
                },
                ...
            ]
        """
        
        log.info(f"🔍 Starting HAZOP analysis for {system_name}")
        log.info(f"📋 Functions: {len(functions)}")
        log.info(f"📋 Guide words: {len(self.guide_words)}")
        
        hazop_results = []
        hazard_counter = 1
        
        # Parse functions (numbered list format)
        function_list = self._parse_functions(functions)
        
        # Apply HAZOP to each function
        for idx, function in enumerate(function_list, 1):
            log.info(f"🔧 Analyzing function {idx}/{len(function_list)}: {function[:50]}...")
            
            # Generate HAZOP for this function
            function_hazop = self._analyze_function(
                function, 
                f"F-{idx:02d}",
                system_name,
                item_definition
            )
            
            # Add unique hazard IDs
            for hazard in function_hazop:
                hazard['hazard_id'] = f"H-{hazard_counter:03d}"
                hazard_counter += 1
            
            hazop_results.extend(function_hazop)
        
        # Add metadata to all results
        timestamp = datetime.now().isoformat()
        for hazard in hazop_results:
            hazard['metadata'] = {
                'system_name': system_name,
                'analysis_date': timestamp,
                'iso_standard': 'ISO 26262-3:2018',
                'clause': '6.4.3'
            }
        
        log.info(f"✅ HAZOP complete: {len(hazop_results)} malfunctioning behaviors identified")
        
        return hazop_results
    
    def _parse_functions(self, functions: str or List[str]) -> List[str]:
        """Parse functions from various formats."""
        
        if isinstance(functions, list):
            return functions
        
        # Parse numbered list
        lines = functions.strip().split('\n')
        parsed = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering (1., 2., etc.)
            if line[0].isdigit():
                line = line.split('.', 1)[-1].strip()
            
            # Remove markdown bold
            line = line.replace('**', '')
            
            if line:
                parsed.append(line)
        
        return parsed
    
    def _analyze_function(
        self, 
        function_desc: str, 
        function_id: str,
        system_name: str,
        context: str = ""
    ) -> List[Dict]:
        """
        Apply all HAZOP guide words to one function.
        
        Returns:
            List of HAZOP hazard dictionaries for this function
        """
        
        # Build prompt for LLM
        prompt = self._build_hazop_prompt(
            function_desc, 
            function_id, 
            system_name, 
            context
        )
        
        try:
            # Get LLM response
            response = self.llm(prompt).strip()
            
            # Parse JSON response
            results = self._parse_hazop_response(
                response, 
                function_id, 
                function_desc
            )
            
            return results
            
        except Exception as e:
            log.error(f"Error analyzing function {function_id}: {e}")
            return []
    
    def _build_hazop_prompt(
        self, 
        function: str, 
        function_id: str, 
        system_name: str,
        context: str
    ) -> str:
        """Build prompt for HAZOP analysis - asks for JSON output directly."""
        
        guide_words_str = '\n'.join([
            f"- **{word}:** {desc}" 
            for word, desc in self.guide_words.items()
        ])
        
        # Build context section
        context_section = ""
        if context:
            context_section = f"**Context from Item Definition:**\n{context}\n\n"
        
    def _build_hazop_prompt(
        self, 
        function: str, 
        function_id: str, 
        system_name: str,
        context: str
    ) -> str:
        """Build prompt for HAZOP analysis - asks for JSON output directly."""
        
        guide_words_str = '\n'.join([
            f"- **{word}:** {desc}" 
            for word, desc in self.guide_words.items()
        ])
        
        # Build context section
        context_section = ""
        if context:
            context_section = f"**Context from Item Definition:**\n{context}\n\n"
        
        prompt = f"""You are a Functional Safety Engineer performing HAZOP analysis per ISO 26262-3:2018, Clause 6.4.3.

        **System:** {system_name}
        **Function ID:** {function_id}
        **Function:** {function}

        {context_section}**Task:** Apply each HAZOP guide word to identify potential malfunctioning behaviors and hazardous events. Provide a *realistic, preliminary* severity rating (S0-S3).

        **HAZOP Guide Words:**
        {guide_words_str}

        **Instructions:**
        1. Apply EACH guide word systematically to the function
        2. For each guide word, identify:
           - Malfunctioning behavior (what goes wrong)
           - Hazardous event (potential harm to people)
           - Preliminary severity (S0-S3)
           - Rationale for severity classification

        3. Be realistic. The harm must be a *direct consequence* of the failure.

        **Severity Scale & Guidance:**
        * **S3 (Life-threatening):** Use for *direct, high-energy* failures (e.g., steering loss on highway, unintended acceleration, brake failure at high speed).
        * **S2 (Severe injuries):** Use for *significant* failures (e.g., brake failure at low speed, airbag failure).
        * **S1 (Light injuries):** Use for failures that are *controllable* or *low-energy* (e.g., infotainment distraction).
        * **S0 (No injuries):** Use for comfort functions.

        * **CRITICAL EXAMPLE (Wiper Failure):**
            * **Hazard:** "Loss of wiper function in heavy rain."
            * **Analysis:** This is **NOT S3**. A wiper failure does not *directly* cause fatal injuries. It reduces visibility. The driver can slow down and pull over.
            * **Correct Preliminary Severity:** S1 (light injuries, e.g., low-speed fender-bender) or S2 (severe injuries, if at high-speed in a storm). **It is almost never S3.**

        **Output Format:**
        You MUST output ONLY a valid JSON array. Each hazard should be a JSON object with these exact fields:
        - "guide_word": The HAZOP guide word (e.g., "NO", "MORE", "LATE")
        - "malfunctioning_behavior": Description of what goes wrong
        - "hazardous_event": Description of resulting hazard to people
        - "severity": Severity class as string ("S0", "S1", "S2", or "S3")
        - "severity_rationale": Justification for the severity rating

        **Example JSON format:**
        [
          {{
            "guide_word": "NO",
            "malfunctioning_behavior": "Function completely fails to execute (e.g., no braking force)",
            "hazardous_event": "Vehicle collision due to failed safety function (e.g., brake failure)",
            "severity": "S3",
            "severity_rationale": "High-speed brake failure could result in fatal injuries"
          }},
          {{
            "guide_word": "LATE",
            "malfunctioning_behavior": "Function executes with significant delay",
            "hazardous_event": "Insufficient reaction time causes accident",
            "severity": "S2",
            "severity_rationale": "Delayed response likely causes severe but survivable injuries"
          }}
        ]

        **CRITICAL:** - Output ONLY the JSON array, no additional text
        - Use double quotes for all strings
        - Include only applicable guide words
        - Ensure valid JSON syntax

        Provide your HAZOP analysis as JSON now:"""
        
        return prompt
    
    def _parse_hazop_response(
        self, 
        response: str, 
        function_id: str, 
        function_name: str
    ) -> List[Dict]:
        """
        Parse LLM JSON response into structured HAZOP results.
        
        Expected format: JSON array with objects containing:
        - guide_word
        - malfunctioning_behavior
        - hazardous_event
        - severity
        - severity_rationale
        
        Returns:
            List of hazard dictionaries with standardized fields
        """
        
        results = []
        
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned_response = response.strip()
            
            # Remove markdown code block markers
            if cleaned_response.startswith('```'):
                # Remove first line (```json or ```)
                lines = cleaned_response.split('\n')
                lines = lines[1:]  # Skip first line
                # Remove last line if it's ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines)
            
            # Remove any leading/trailing whitespace
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            hazards_data = json.loads(cleaned_response)
            
            # Ensure it's a list
            if not isinstance(hazards_data, list):
                log.error(f"Expected JSON array, got {type(hazards_data)}")
                return []
            
            # Process each hazard
            for hazard_data in hazards_data:
                # Validate required fields
                required_fields = ['guide_word', 'malfunctioning_behavior', 
                                 'hazardous_event', 'severity', 'severity_rationale']
                
                if not all(field in hazard_data for field in required_fields):
                    log.warning(f"Skipping incomplete hazard: {hazard_data}")
                    continue
                
                # Normalize severity
                severity = hazard_data['severity'].strip().upper()
                if not severity.startswith('S'):
                    severity = 'S' + severity
                if severity not in ['S0', 'S1', 'S2', 'S3']:
                    log.warning(f"Invalid severity '{severity}', defaulting to S0")
                    severity = 'S0'
                
                # Create standardized result dict
                result = {
                    'function_id': function_id,
                    'function_name': function_name,
                    'guide_word': hazard_data['guide_word'].strip(),
                    'malfunctioning_behavior': hazard_data['malfunctioning_behavior'].strip(),
                    'hazardous_event': hazard_data['hazardous_event'].strip(),
                    'severity': severity,
                    'severity_rationale': hazard_data['severity_rationale'].strip()
                }
                
                results.append(result)
            
            log.info(f"✅ Parsed {len(results)} hazards from JSON response")
            
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.error(f"Response was: {response[:500]}...")
            
            # Fallback: try to extract JSON from response
            results = self._fallback_parse(response, function_id, function_name)
        
        except Exception as e:
            log.error(f"Unexpected error parsing response: {e}")
            return []
        
        return results
    
    def _fallback_parse(
        self, 
        response: str, 
        function_id: str, 
        function_name: str
    ) -> List[Dict]:
        """
        Fallback parser if JSON parsing fails.
        Tries to find JSON array in the response text.
        """
        
        results = []
        
        try:
            # Look for JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                hazards_data = json.loads(json_str)
                
                if isinstance(hazards_data, list):
                    log.info("✅ Fallback parser found valid JSON array")
                    
                    # Process hazards
                    for hazard_data in hazards_data:
                        if not isinstance(hazard_data, dict):
                            continue
                        
                        # Try to extract fields
                        guide_word = hazard_data.get('guide_word', '')
                        malfunction = hazard_data.get('malfunctioning_behavior', '')
                        hazard = hazard_data.get('hazardous_event', '')
                        severity = hazard_data.get('severity', 'S0')
                        rationale = hazard_data.get('severity_rationale', '')
                        
                        # Skip if essential fields missing
                        if not (guide_word and malfunction and hazard):
                            continue
                        
                        # Normalize severity
                        severity = severity.strip().upper()
                        if not severity.startswith('S'):
                            severity = 'S' + severity
                        if severity not in ['S0', 'S1', 'S2', 'S3']:
                            severity = 'S0'
                        
                        result = {
                            'function_id': function_id,
                            'function_name': function_name,
                            'guide_word': guide_word.strip(),
                            'malfunctioning_behavior': malfunction.strip(),
                            'hazardous_event': hazard.strip(),
                            'severity': severity,
                            'severity_rationale': rationale.strip()
                        }
                        
                        results.append(result)
        
        except Exception as e:
            log.error(f"Fallback parser also failed: {e}")
        
        return results


# ==============================================================================
# UTILITY FUNCTIONS FOR JSON OUTPUT
# ==============================================================================

def export_hazop_to_json(
    hazop_results: List[Dict], 
    filepath: Optional[str] = None
) -> str:
    """
    Export HAZOP results to JSON format.
    
    Args:
        hazop_results: List of hazard dictionaries
        filepath: Optional path to save JSON file
    
    Returns:
        JSON string
    """
    
    if not hazop_results:
        output = {
            "status": "error",
            "message": "No HAZOP results to export"
        }
        return json.dumps(output, indent=2)
    
    # Build export structure
    export_data = {
        "analysis_type": "HAZOP",
        "iso_standard": "ISO 26262-3:2018",
        "clause": "6.4.3",
        "export_timestamp": datetime.now().isoformat(),
        "total_hazards": len(hazop_results),
        "hazards": hazop_results
    }
    
    # Calculate statistics
    severity_dist = {}
    function_dist = {}
    guide_word_dist = {}
    
    for hazard in hazop_results:
        sev = hazard.get('severity', 'S0')
        severity_dist[sev] = severity_dist.get(sev, 0) + 1
        
        func = hazard.get('function_id', 'Unknown')
        function_dist[func] = function_dist.get(func, 0) + 1
        
        gw = hazard.get('guide_word', 'Unknown')
        guide_word_dist[gw] = guide_word_dist.get(gw, 0) + 1
    
    export_data['statistics'] = {
        'severity_distribution': severity_dist,
        'function_distribution': function_dist,
        'guide_word_distribution': guide_word_dist
    }
    
    # Convert to JSON
    json_output = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    # Save to file if requested
    if filepath:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_output)
            log.info(f"✅ HAZOP results exported to {filepath}")
        except Exception as e:
            log.error(f"Failed to save JSON to {filepath}: {e}")
    
    return json_output


def format_hazop_plain_text(hazop_results: List[Dict]) -> str:
    """
    Format HAZOP results as plain text (CSV-like format).
    
    Args:
        hazop_results: List of hazard dictionaries
    
    Returns:
        Plain text string with tab-separated values
    """
    
    if not hazop_results:
        return "No HAZOP results available."
    
    # Header
    output = "HAZARD_ID\tFUNCTION_ID\tFUNCTION_NAME\tGUIDE_WORD\t"
    output += "MALFUNCTIONING_BEHAVIOR\tHAZARDOUS_EVENT\tSEVERITY\tRATIONALE\n"
    
    # Data rows
    for hazard in hazop_results:
        row = [
            hazard.get('hazard_id', ''),
            hazard.get('function_id', ''),
            hazard.get('function_name', ''),
            hazard.get('guide_word', ''),
            hazard.get('malfunctioning_behavior', ''),
            hazard.get('hazardous_event', ''),
            hazard.get('severity', ''),
            hazard.get('severity_rationale', '')
        ]
        output += '\t'.join(row) + '\n'
    
    return output


def get_hazop_summary(hazop_results: List[Dict]) -> Dict:
    """
    Generate summary statistics from HAZOP results.
    
    Args:
        hazop_results: List of hazard dictionaries
    
    Returns:
        Dictionary with summary data
    """
    
    if not hazop_results:
        return {
            "status": "error",
            "message": "No HAZOP results available"
        }
    
    # Calculate distributions
    severity_dist = {}
    function_dist = {}
    guide_word_dist = {}
    
    for hazard in hazop_results:
        # Severity distribution
        sev = hazard.get('severity', 'S0')
        severity_dist[sev] = severity_dist.get(sev, 0) + 1
        
        # Function distribution
        func = hazard.get('function_id', 'Unknown')
        function_dist[func] = function_dist.get(func, 0) + 1
        
        # Guide word distribution
        gw = hazard.get('guide_word', 'Unknown')
        guide_word_dist[gw] = guide_word_dist.get(gw, 0) + 1
    
    summary = {
        "status": "success",
        "total_hazards": len(hazop_results),
        "severity_distribution": severity_dist,
        "function_distribution": function_dist,
        "guide_word_distribution": guide_word_dist,
        "unique_functions": len(function_dist),
        "guide_words_applied": len(guide_word_dist)
    }
    
    return summary