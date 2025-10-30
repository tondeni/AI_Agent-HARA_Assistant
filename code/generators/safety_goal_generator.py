# ==============================================================================
# code/generators/safety_goal_generator.py
# LLM-based Safety Goal derivation per ISO 26262-3:2018, Clause 6.4.6
# ==============================================================================

"""
Safety Goal Generator

Derives safety goals from hazardous events with ASIL ratings per
ISO 26262-3:2018 Clause 6.4.6. Uses LLM to create clear, measurable,
and verifiable safety goals.

Safety Goal Requirements (ISO 26262-3:2018, 6.4.6):
- Shall be formulated at vehicle level
- Shall specify the condition to avoid or mitigate hazard
- Shall inherit ASIL from hazardous event
- Shall reference safe state and FTTI
- Shall be verifiable through testing/analysis
"""

from typing import List, Dict, Optional
from cat.log import log
import json


class SafetyGoal:
    """Data model for Safety Goal per ISO 26262-3."""
    
    def __init__(self, **kwargs):
        self.sg_id: str = kwargs.get('sg_id', '')
        self.statement: str = kwargs.get('statement', '')
        self.asil: str = kwargs.get('asil', 'QM')
        self.hazard_id: str = kwargs.get('hazard_id', '')
        self.hazardous_event: str = kwargs.get('hazardous_event', '')
        self.safe_state: str = kwargs.get('safe_state', 'TBD')
        self.ftti_ms: str = kwargs.get('ftti_ms', 'TBD')
        self.severity: str = kwargs.get('severity', '')
        self.exposure: str = kwargs.get('exposure', '')
        self.controllability: str = kwargs.get('controllability', '')
        self.rationale: str = kwargs.get('rationale', '')
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'sg_id': self.sg_id,
            'statement': self.statement,
            'asil': self.asil,
            'hazard_id': self.hazard_id,
            'hazardous_event': self.hazardous_event,
            'safe_state': self.safe_state,
            'ftti_ms': self.ftti_ms,
            'severity': self.severity,
            'exposure': self.exposure,
            'controllability': self.controllability,
            'rationale': self.rationale
        }
    
    def __repr__(self):
        return f"SafetyGoal({self.sg_id}: {self.statement[:50]}...)"


class SafetyGoalGenerator:
    """
    Generate safety goals from ASIL-rated hazardous events.
    
    Uses LLM to create clear, measurable safety goals per ISO 26262-3:2018
    Clause 6.4.6 requirements.
    """
    
    def __init__(self, llm):
        """
        Initialize generator with LLM.
        
        Args:
            llm: Cheshire Cat LLM instance (cat.llm)
        """
        self.llm = llm
    
    def generate_from_hazards(self, hazards: List[Dict], 
                             system_name: str = "System") -> List[SafetyGoal]:
        """
        Generate safety goals from hazardous events.
        
        Args:
            hazards: List of hazardous events with ASIL ratings
            system_name: Name of the system/item
            
        Returns:
            List of SafetyGoal objects
        """
        
        log.info(f"🎯 Generating safety goals for {len(hazards)} hazards")
        
        safety_goals = []
        
        # Filter for ASIL A-D hazards only (QM doesn't need safety goals)
        asil_hazards = [h for h in hazards 
                       if h.get('asil', 'QM') in ['A', 'B', 'C', 'D']]
        
        if not asil_hazards:
            log.warning("⚠️ No ASIL-rated hazards found (only QM)")
            return []
        
        log.info(f"📋 Processing {len(asil_hazards)} ASIL-rated hazards")
        
        for idx, hazard in enumerate(asil_hazards, 1):
            log.info(f"   Generating safety goal {idx}/{len(asil_hazards)}")
            
            safety_goal = self._generate_single_goal(hazard, system_name, idx)
            safety_goals.append(safety_goal)
        
        log.info(f"✅ Generated {len(safety_goals)} safety goals")
        
        return safety_goals
    
    def _generate_single_goal(self, hazard: Dict, system_name: str, 
                             index: int) -> SafetyGoal:
        """
        Generate a single safety goal from a hazardous event.
        
        Args:
            hazard: Hazardous event data
            system_name: System name
            index: Goal index number
            
        Returns:
            SafetyGoal object
        """
        
        # Extract hazard information
        hazard_id = hazard.get('id', f'H-{index:03d}')
        hazardous_event = hazard.get('event', hazard.get('hazardous_event', ''))
        malfunction = hazard.get('malfunction', '')
        asil = hazard.get('asil', 'QM')
        severity = hazard.get('severity', '')
        exposure = hazard.get('exposure', '')
        controllability = hazard.get('controllability', '')
        
        # Create prompt for LLM
        prompt = f"""You are a Functional Safety Engineer expert in ISO 26262-3:2018.

Generate a Safety Goal from this hazardous event per ISO 26262-3:2018, Clause 6.4.6.

**System:** {system_name}

**Hazardous Event ({hazard_id}):**
{hazardous_event}

**Malfunctioning Behavior:**
{malfunction}

**Risk Assessment:**
- ASIL: {asil}
- Severity: {severity}
- Exposure: {exposure}
- Controllability: {controllability}

**ISO 26262-3:2018, Clause 6.4.6 Requirements:**
1. Safety goal shall be formulated at vehicle level
2. Shall specify the condition to avoid or mitigate the hazard
3. Shall be clear, measurable, and verifiable
4. Shall use "shall" mandatory language
5. Shall be a single, atomic requirement

**Generate:**
Return ONLY a valid JSON object (no markdown, no code blocks):

{{
  "statement": "The [System] shall [action to prevent/mitigate hazard]",
  "safe_state": "Define the safe state (e.g., System off, Hold last valid value)",
  "ftti_ms": "Estimate fault tolerant time interval in milliseconds (10-1000ms based on ASIL {asil})",
  "rationale": "Brief explanation of how this goal addresses the hazard"
}}

**Example Format:**
{{
  "statement": "The Wiper System shall prevent unintended activation during all operating conditions",
  "safe_state": "Wiper system shall remain in OFF state",
  "ftti_ms": "100",
  "rationale": "Prevents unexpected wiper movement that could distract driver"
}}

Return ONLY valid JSON (no extra text):"""
        
        # Call LLM
        try:
            response = self.llm(prompt)
            
            # Parse JSON response
            goal_data = self._parse_llm_response(response)
            
            # Create SafetyGoal object
            sg_id = f"SG-{index:03d}"
            
            safety_goal = SafetyGoal(
                sg_id=sg_id,
                statement=goal_data.get('statement', f'TBD - Safety goal for {hazard_id}'),
                asil=asil,
                hazard_id=hazard_id,
                hazardous_event=hazardous_event,
                safe_state=goal_data.get('safe_state', 'To be specified per ISO 26262-3:2018, 7.4.2.5'),
                ftti_ms=goal_data.get('ftti_ms', 'To be determined per ISO 26262-3:2018, 7.4.2.4'),
                severity=severity,
                exposure=exposure,
                controllability=controllability,
                rationale=goal_data.get('rationale', '')
            )
            
            log.info(f"   ✓ {sg_id}: {safety_goal.statement[:60]}...")
            
            return safety_goal
            
        except Exception as e:
            log.error(f"❌ Error generating safety goal: {e}")
            
            # Return fallback safety goal
            sg_id = f"SG-{index:03d}"
            return SafetyGoal(
                sg_id=sg_id,
                statement=f"The {system_name} shall prevent {hazardous_event}",
                asil=asil,
                hazard_id=hazard_id,
                hazardous_event=hazardous_event,
                safe_state='To be specified',
                ftti_ms='To be determined',
                severity=severity,
                exposure=exposure,
                controllability=controllability,
                rationale='Fallback goal - LLM generation failed'
            )
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse LLM JSON response, handling various formats.
        
        Args:
            response: LLM response text
            
        Returns:
            Dictionary with parsed data
        """
        
        # Clean response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            # Find JSON content between code blocks
            lines = response.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith('```'):
                    if not in_json:
                        in_json = True
                    else:
                        break
                elif in_json:
                    json_lines.append(line)
            
            response = '\n'.join(json_lines)
        
        # Try to parse JSON
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            log.warning(f"⚠️ JSON parse error: {e}")
            log.warning(f"   Response: {response[:200]}")
            
            # Return empty dict if parsing fails
            return {}
    
    def validate_safety_goal(self, goal: SafetyGoal) -> tuple[bool, List[str]]:
        """
        Validate safety goal per ISO 26262-3 requirements.
        
        Args:
            goal: SafetyGoal to validate
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        
        issues = []
        
        # Check mandatory fields
        if not goal.statement or goal.statement == 'TBD':
            issues.append(f"{goal.sg_id}: Missing safety goal statement")
        
        if 'shall' not in goal.statement.lower():
            issues.append(f"{goal.sg_id}: Safety goal must use 'shall' (mandatory)")
        
        if not goal.asil or goal.asil not in ['A', 'B', 'C', 'D']:
            issues.append(f"{goal.sg_id}: Invalid or missing ASIL")
        
        # Check safe state
        if 'TBD' in goal.safe_state or 'To be specified' in goal.safe_state:
            issues.append(f"{goal.sg_id}: Safe state not fully specified")
        
        # Check FTTI
        if 'TBD' in goal.ftti_ms or 'To be determined' in goal.ftti_ms:
            issues.append(f"{goal.sg_id}: FTTI not specified")
        
        is_valid = len(issues) == 0
        
        return is_valid, issues
    
    def generate_goal_summary(self, goals: List[SafetyGoal]) -> str:
        """
        Generate a summary of safety goals.
        
        Args:
            goals: List of safety goals
            
        Returns:
            Formatted summary string
        """
        
        if not goals:
            return "No safety goals generated."
        
        summary = f"**Safety Goals Summary ({len(goals)} goals)**\n\n"
        
        # ASIL distribution
        asil_counts = {'D': 0, 'C': 0, 'B': 0, 'A': 0}
        for goal in goals:
            asil = goal.asil
            asil_counts[asil] = asil_counts.get(asil, 0) + 1
        
        summary += "**ASIL Distribution:**\n"
        for asil in ['D', 'C', 'B', 'A']:
            if asil_counts[asil] > 0:
                summary += f"- ASIL {asil}: {asil_counts[asil]} goals\n"
        
        summary += "\n**Safety Goals:**\n\n"
        
        for goal in goals:
            summary += f"**{goal.sg_id}** (ASIL {goal.asil})\n"
            summary += f"{goal.statement}\n"
            summary += f"*Safe State:* {goal.safe_state}\n"
            summary += f"*FTTI:* {goal.ftti_ms} ms\n\n"
        
        return summary


def test_generator():
    """Test the safety goal generator with sample data."""
    
    # Mock LLM for testing
    class MockLLM:
        def __call__(self, prompt):
            return json.dumps({
                "statement": "The Wiper System shall prevent unintended activation during all operating conditions",
                "safe_state": "Wiper system shall remain in OFF state",
                "ftti_ms": "100",
                "rationale": "Prevents driver distraction from unexpected wiper movement"
            })
    
    # Test hazards
    test_hazards = [
        {
            'id': 'H-001',
            'event': 'Unintended wiper activation causes driver distraction',
            'malfunction': 'Wiper activates without driver input',
            'asil': 'B',
            'severity': 'S2',
            'exposure': 'E4',
            'controllability': 'C2'
        }
    ]
    
    generator = SafetyGoalGenerator(MockLLM())
    goals = generator.generate_from_hazards(test_hazards, "Wiper System")
    
    print(generator.generate_goal_summary(goals))


if __name__ == "__main__":
    test_generator()