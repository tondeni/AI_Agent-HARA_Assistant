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
    
    def generate_from_hazards(self, hazards: List[Dict], system_name: str) -> List[SafetyGoal]:
        """
        Generate safety goals for a list of ASIL-rated hazards.
        
        Args:
            hazards: List of ASIL-rated hazard dictionaries
            system_name: Name of the system
            
        Returns:
            List of SafetyGoal objects
        """
        log.info(f"Generating safety goals for {len(hazards)} hazards...")
        safety_goals = []
        
        for idx, hazard in enumerate(hazards, 1):
            # Pass the full hazard dictionary
            goal = self._generate_single_goal(
                hazard=hazard,
                system_name=system_name,
                index=idx
            )
            safety_goals.append(goal)
            
        log.info(f"Successfully generated {len(safety_goals)} safety goals.")
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
        hazardous_event = hazard.get('hazardous_event', '')
        malfunction = hazard.get('malfunctioning_behavior', '') # Use the correct key
        asil = hazard.get('asil', 'QM')
        severity = hazard.get('severity', '')
        exposure = hazard.get('exposure', '')
        controllability = hazard.get('controllability', '')
        
        # Create prompt for LLM
        prompt = f"""You are a Functional Safety Engineer expert in ISO 26262-3:2018.

Generate a Safety Goal, Safe State, and FTTI from this hazardous event per ISO 26262-3:2018, Clause 6.4.6.

**System (for context, do NOT name in goal):** {system_name}

**Hazardous Event ({hazard_id}):**
{hazardous_event}

**Malfunctioning Behavior (System-level fault):**
{malfunction}

**Risk Assessment:**
- ASIL: {asil}
- Severity: {severity}
- Exposure: {exposure}
- Controllability: {controllability}

---
### 1. Safety Goal Guidance (Vehicle Level)
* **Formulate at VEHICLE LEVEL:** Describe a state of the *vehicle* to be avoided.
* **BE CONCISE:** The goal must be a direct negation of the hazardous event, stated as an "Avoid" requirement.
* **DO NOT** mention the system ({system_name}).

---
### 2. Safe State Guidance (Correlate with ASIL)
* The Safe State is the state the vehicle enters *after* a fault is detected to prevent the hazard.
* **The ASIL dictates the required robustness of the safe state.**
* **ASIL C / ASIL D (This Hazard is {asil}):** High risk. Safe state MUST be robust (e.g., 'Inhibit Function', 'Degraded Mode', 'Emergency Position'). **'Warn Driver' alone is NOT an acceptable safe state.**
* **ASIL A / ASIL B (This Hazard is {asil}):** Lower risk. Safe state can be less disruptive (e.g., 'Warn Driver', 'Degraded Mode').
* **Options:**
    1.  **Warn Driver:** (Lowest intervention - OK for ASIL A/B)
    2.  **Degraded Mode:** (Reduced performance - Good for ASIL A/B/C, e.g., "Limp-home mode")
    3.  **Inhibit Function:** (Stops the faulty function - Good for ASIL B/C/D, e.g., "Disable adaptive cruise")
    4.  **Emergency Position:** (Highest intervention - For ASIL D, e.g., "Shut down")

---
### 3. FTTI (Fault Tolerant Time Interval) Guidance (Correlate with ASIL)
* FTTI is the time from fault detection to reaching the Safe State.
* **The ASIL dictates the time budget. This hazard is {asil}.**
* **ASIL D:** Very Short FTTI (e.g., 10-100ms). Reaction must be immediate.
* **ASIL C:** Short FTTI (e.g., 100-500ms). Reaction must be very fast.
* **ASIL B:** Medium FTTI (e.g., 500-2000ms). Driver has some time.
* **ASIL A:** Long FTTI (e.g., 2000-5000ms). Driver has several seconds.
* **Use the hazard's physics to refine the estimate:**
    * A steering failure (ASIL D) needs a 10ms FTTI.
    * A wiper failure (ASIL B) can have a 2000ms FTTI.

---
**Generate JSON Output:**
Return ONLY a valid JSON object (no markdown, no code blocks).

{{
  "statement": "Avoid [concise hazardous state]",
  "safe_state": "Define the Safe State based on the {asil} risk (e.g., 'Inhibit function and warn driver')",
  "ftti_ms": "Estimate FTTI in milliseconds based on the {asil} risk (e.g., 250)",
  "rationale": "Brief rationale for FTTI/Safe State. (e.g., 'ASIL C requires a fast FTTI and a robust safe state.')"
}}

---
**CRITICAL EXAMPLES:**

**Example 1 (Wiper System)**
* **Hazard:** Loss of visibility from wiper failure
* **Malfunction:** Wipers fail to activate
* **CORRECT (Concise):** "Avoid missing wiper activation."

**Example 2 (Brake System)**
* **Hazard:** Collision from unintended braking
* **Malfunction:** Brakes apply without command
* **CORRECT (Concise):** "Avoid unintended braking."

Return ONLY valid JSON (no extra text):"""
        
        # Call LLM
        try:
            response = self.llm(prompt)
            
            # Parse JSON response
            goal_data = self._parse_llm_response(response)
            
            # Create SafetyGoal object
            sg_id = f"SG-{index:03d}"
            
            # Get ftti_ms and ensure it's a string
            ftti_value = goal_data.get('ftti_ms', 'TBD')
            if isinstance(ftti_value, (int, float)):
                ftti_value = str(ftti_value)
            
            safety_goal = SafetyGoal(
                sg_id=sg_id,
                statement=goal_data.get('statement', f'TBD - Safety goal for {hazard_id}'),
                asil=asil,
                hazard_id=hazard_id,
                hazardous_event=hazardous_event,
                safe_state=goal_data.get('safe_state', 'To be specified per ISO 26262-3:2018, 7.4.2.5'),
                ftti_ms=ftti_value, # Use the string-converted value
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
                statement=f"Avoid {malfunction}", # Fallback to malfunction
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
        if not goal.statement or 'TBD' in goal.statement or 'prevent' not in goal.statement.lower():
            issues.append(f"{goal.sg_id}: Missing or placeholder safety goal statement")
        
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
    
    def calculate_goal_statistics(self, goals: List[SafetyGoal]) -> Dict:
        """
        Calculate statistics for the generated safety goals.
        
        Args:
            goals: List of SafetyGoal objects
            
        Returns:
            Dictionary with statistics
        """
        
        if not goals:
            return {
                "total_goals": 0,
                "asil_distribution": {'D': 0, 'C': 0, 'B': 0, 'A': 0}
            }
            
        stats = {
            'total_goals': len(goals),
            'asil_distribution': {'D': 0, 'C': 0, 'B': 0, 'A': 0}
        }
        
        for goal in goals:
            asil = goal.asil
            if asil in stats['asil_distribution']:
                stats['asil_distribution'][asil] += 1
        
        return stats


def test_generator():
    """Test the safety goal generator with sample data."""
    
    # Mock LLM for testing
    class MockLLM:
        def __call__(self, prompt):
            return json.dumps({
                "statement": "The vehicle shall prevent unintended activation of wipers during normal driving",
                "safe_state": "Wiper system function is inhibited and driver is warned",
                "ftti_ms": "1000",
                "rationale": "Prevents driver distraction from unexpected wiper movement. 1000ms is sufficient."
            })
    
    # Test hazards
    test_hazards = [
        {
            'id': 'H-001',
            'hazardous_event': 'Unintended wiper activation causes driver distraction',
            'malfunctioning_behavior': 'Wiper activates without driver input',
            'asil': 'B',
            'severity': 'S2',
            'exposure': 'E4',
            'controllability': 'C2'
        }
    ]
    
    generator = SafetyGoalGenerator(MockLLM())
    # Test the new generate_from_hazards method
    goals = generator.generate_from_hazards(test_hazards, "Wiper System")
    
    # Test the new calculate_goal_statistics method
    stats = generator.calculate_goal_statistics(goals)
    
    print("--- Test Results ---")
    print(f"Stats: {stats}")
    print("\nGoals:")
    for goal in goals:
        print(json.dumps(goal.to_dict(), indent=2))


if __name__ == "__main__":
    test_generator()