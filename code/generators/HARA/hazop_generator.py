# ==============================================================================
# code/generators/HARA/hazop_generator.py
# Business logic for HAZOP analysis
# ==============================================================================

"""
HAZOP Generator
Applies HAZOP guide words to functions to identify malfunctioning behaviors
Per ISO 26262-3:2018, Clause 6.4.3
"""

from typing import List, Dict
from cat.log import log
import json
import os


class HAZOPGenerator:
    """
    Generate HAZOP analysis for safety functions.
    
    Applies 10 standard HAZOP guide words to each function:
    - NO, MORE, LESS, EARLY, LATE, REVERSE
    - OTHER THAN, PART OF, AS WELL AS, WHERE ELSE
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
            List of HAZOP results (dicts)
        """
        
        log.info(f"🔍 Starting HAZOP analysis for {system_name}")
        log.info(f"📋 Functions: {len(functions)}")
        log.info(f"📋 Guide words: {len(self.guide_words)}")
        
        hazop_results = []
        
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
            
            hazop_results.extend(function_hazop)
        
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
            List of HAZOP results for this function
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
            
            # Parse response into structured data
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
        """Build prompt for HAZOP analysis."""
        
        guide_words_str = '\n'.join([
            f"- **{word}:** {desc}" 
            for word, desc in self.guide_words.items()
        ])
        
        prompt = f"""You are a Functional Safety Engineer performing HAZOP analysis per ISO 26262-3:2018, Clause 6.4.3.

**System:** {system_name}
**Function ID:** {function_id}
**Function:** {function}

{f"**Context from Item Definition:**\n{context}\n" if context else ""}

**Task:** Apply each HAZOP guide word to identify potential malfunctioning behaviors and hazardous events.

**HAZOP Guide Words:**
{guide_words_str}

**Instructions:**
1. Apply EACH guide word systematically
2. For each guide word, identify:
   - Malfunctioning behavior (what goes wrong)
   - Hazardous event (potential harm)
   - Preliminary severity (S0-S3)
   - Rationale for severity

3. Skip guide words that don't apply (mark as "N/A")
4. Be specific and technical

**Severity Scale:**
- **S0:** No injuries
- **S1:** Light to moderate injuries
- **S2:** Severe injuries (survival probable)
- **S3:** Life-threatening to fatal injuries

**Output Format:**

| Guide Word | Malfunctioning Behavior | Hazardous Event | Severity | Rationale |
|------------|------------------------|-----------------|----------|-----------|
| NO | [Description] | [Event] | S2 | [Why S2?] |
| MORE | [Description] | [Event] | S1 | [Why S1?] |
...

Provide HAZOP analysis now:"""
        
        return prompt
    
    def _parse_hazop_response(
        self, 
        response: str, 
        function_id: str, 
        function_name: str
    ) -> List[Dict]:
        """
        Parse LLM response into structured HAZOP results.
        
        Expected format: Markdown table with columns:
        | Guide Word | Malfunctioning Behavior | Hazardous Event | Severity | Rationale |
        """
        
        results = []
        
        # Split into lines
        lines = response.strip().split('\n')
        
        # Find table start (first line with '|')
        table_start = 0
        for i, line in enumerate(lines):
            if '|' in line and 'Guide Word' in line:
                table_start = i + 2  # Skip header and separator
                break
        
        # Parse table rows
        for line in lines[table_start:]:
            if not line.strip() or '|' not in line:
                continue
            
            # Split by |
            parts = [p.strip() for p in line.split('|')]
            
            # Remove empty first/last elements (from leading/trailing |)
            parts = [p for p in parts if p]
            
            # Need at least 5 columns
            if len(parts) < 5:
                continue
            
            guide_word = parts[0]
            malfunction = parts[1]
            hazard = parts[2]
            severity = parts[3]
            rationale = parts[4]
            
            # Skip N/A or empty rows
            if 'n/a' in malfunction.lower() or not malfunction:
                continue
            
            # Create result dict
            result = {
                'function_id': function_id,
                'function_name': function_name,
                'guide_word': guide_word,
                'malfunctioning_behavior': malfunction,
                'hazardous_event': hazard,
                'severity': severity.upper(),
                'rationale': rationale
            }
            
            results.append(result)
        
        return results


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_hazop_table(hazop_results: List[Dict]) -> str:
    """Format HAZOP results as markdown table."""
    
    if not hazop_results:
        return "No HAZOP results available."
    
    # Build table
    table = "| Function | Guide Word | Malfunctioning Behavior | Hazardous Event | Severity |\n"
    table += "|----------|------------|------------------------|-----------------|----------|\n"
    
    for result in hazop_results:
        table += f"| {result['function_id']} | {result['guide_word']} | "
        table += f"{result['malfunctioning_behavior'][:50]}... | "
        table += f"{result['hazardous_event'][:50]}... | {result['severity']} |\n"
    
    return table


def get_hazop_statistics(hazop_results: List[Dict]) -> Dict:
    """Calculate HAZOP statistics."""
    
    total = len(hazop_results)
    
    # Count by severity
    severity_counts = {'S0': 0, 'S1': 0, 'S2': 0, 'S3': 0}
    for result in hazop_results:
        severity = result.get('severity', 'S0')
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Count by guide word
    guide_word_counts = {}
    for result in hazop_results:
        gw = result.get('guide_word', 'UNKNOWN')
        guide_word_counts[gw] = guide_word_counts.get(gw, 0) + 1
    
    return {
        'total': total,
        'severity_distribution': severity_counts,
        'guide_word_distribution': guide_word_counts
    }