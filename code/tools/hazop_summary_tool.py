# ==============================================================================
# code/tools/hazop_summary_tool.py
# Tool to generate summary of most relevant HAZOP hazards
# FIXED VERSION - Works with hazop_results list format
# ==============================================================================

from cat.mad_hatter.decorators import tool
from cat.log import log
import re
from typing import List, Dict


@tool(
    return_direct=True,
    examples=[
        "show hazop summary",
        "summarize hazop results",
        "show most critical hazards",
        "hazop critical summary"
    ]
)
def show_hazop_summary(tool_input, cat):
    """
    Generate a concise summary table of most critical hazards from HAZOP analysis.
    
    This tool filters and presents the most safety-relevant hazards based on:
    - Severity level (prioritizes S3, S2)
    - Guide word criticality (prioritizes NO, LATE, REVERSE)
    - System criticality
    
    The summary helps focus on high-priority hazards before proceeding to 
    exposure assessment.
    
    Args:
        tool_input: Optional - filter criteria ("all", "S3 only", "top 20")
        cat: Cheshire Cat instance
        
    Returns:
        Concise summary table with most relevant hazards
        
    Example:
        User: "show hazop summary"
        Output: Top 15-20 critical hazards in compact table format
    """
    
    log.info("🔧 TOOL CALLED: show_hazop_summary")
    
    # Get HAZOP results from working memory (LIST format)
    hazop_results = cat.working_memory.get('hazop_results', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Analysis Available**

**Action Required:** Complete HAZOP analysis first

Use: `apply hazop analysis`

**Then run:** `show hazop summary`"""
    
    log.info(f"📊 Analyzing {len(hazop_results)} HAZOP hazards")
    
    # Convert list format to structured hazards
    hazards = _convert_hazop_results(hazop_results)
    
    if not hazards:
        return """❌ **Could not parse HAZOP results**

**Issue:** HAZOP data format unexpected

**Debug:** Check that hazop_results contains proper dict entries"""
    
    log.info(f"📋 Processed {len(hazards)} hazards from HAZOP")
    
    # Categorize hazards by severity
    s3_hazards = [h for h in hazards if h['severity'] == 'S3']
    s2_hazards = [h for h in hazards if h['severity'] == 'S2']
    s1_hazards = [h for h in hazards if h['severity'] == 'S1']
    s0_hazards = [h for h in hazards if h['severity'] == 'S0']
    
    # Prioritize critical hazards
    critical_hazards = _prioritize_hazards(hazards)
    
    # Build summary output
    result = f"""# 📋 **HAZOP Summary: {item_name}**

## Overview Statistics

**Total Hazards Identified:** {len(hazards)}

**Severity Distribution:**
- 🔴 **S3 (Life-threatening/Fatal):** {len(s3_hazards)} hazards
- 🟠 **S2 (Severe injuries):** {len(s2_hazards)} hazards
- 🟡 **S1 (Light/moderate):** {len(s1_hazards)} hazards
- 🟢 **S0 (No injuries):** {len(s0_hazards)} hazards

**High Priority (S3 + S2):** {len(s3_hazards) + len(s2_hazards)} hazards

---

## 🔴 Top Critical Hazards (Priority for Exposure Assessment)

"""
    
    # Show top 20 most critical hazards
    top_hazards = critical_hazards[:20]
    
    result += _format_summary_table(top_hazards)
    
    result += f"""

---

## 📊 Detailed Breakdown

### S3 Hazards (Life-threatening)
**Count:** {len(s3_hazards)}
"""
    
    if s3_hazards:
        result += _format_compact_list(s3_hazards[:10])
        if len(s3_hazards) > 10:
            result += f"\n... and {len(s3_hazards) - 10} more S3 hazards\n"
    else:
        result += "- None identified\n"
    
    result += f"""
### S2 Hazards (Severe Injuries)
**Count:** {len(s2_hazards)}
"""
    
    if s2_hazards:
        result += _format_compact_list(s2_hazards[:10])
        if len(s2_hazards) > 10:
            result += f"\n... and {len(s2_hazards) - 10} more S2 hazards\n"
    else:
        result += "- None identified\n"
    
    result += f"""
---

## 🎯 Recommendations

"""
    
    if len(s3_hazards) > 0:
        result += f"""⚠️ **CRITICAL:** {len(s3_hazards)} life-threatening hazards identified
   - These require immediate attention
   - Expect ASIL C or D ratings for many of these
   - Consider design changes to mitigate S3 hazards
"""
    
    if len(s3_hazards) + len(s2_hazards) > 30:
        result += f"""
⚠️ **HIGH HAZARD COUNT:** {len(s3_hazards) + len(s2_hazards)} high-severity hazards
   - Consider system architecture review
   - May indicate overly complex or safety-critical design
   - Review for potential hazard consolidation
"""
    
    result += f"""
---

## 📍 Next Steps

**1. Review Critical Hazards**
   - Focus on S3 and S2 hazards above
   - Verify severity assessments
   - Consider early mitigation strategies

**2. Assess Exposure for All Hazards**
   Use: `assess exposure for all hazards`
   
   This will:
   - Select relevant operational situations from database
   - Combine scenarios using MIN rule
   - Calculate exposure (E0-E4) for each hazard
   - Generate complete exposure assessment table

**3. Optional: Filter Specific Hazards**
   - `show s3 hazards only` - View only life-threatening
   - `show hazards for [function]` - Filter by function

**Workflow Progress:** 2/5 Complete
- ✅ Step 1: Functions extracted
- ✅ Step 2: HAZOP analysis (Severity assessed)
- ➡️ Step 3: Assess exposure for all hazards
- ❓ Step 4: Generate HARA table
- ❓ Step 5: Derive safety goals
"""
    
    # Store summary statistics in working memory
    cat.working_memory['hazop_summary_stats'] = {
        'total': len(hazards),
        's3_count': len(s3_hazards),
        's2_count': len(s2_hazards),
        's1_count': len(s1_hazards),
        's0_count': len(s0_hazards),
        'critical_count': len(s3_hazards) + len(s2_hazards)
    }
    
    return result


def _convert_hazop_results(hazop_results: List[Dict]) -> List[Dict]:
    """
    Convert HAZOP results from plugin format to summary format.
    
    Plugin stores as list of dicts with keys:
    - function_id, function_name, guide_word, malfunctioning_behavior,
      hazardous_event, severity, rationale
    """
    hazards = []
    
    for idx, result in enumerate(hazop_results, 1):
        # Generate hazard ID if not present
        hazard_id = result.get('id', f"HAZ-{idx:03d}")
        
        # Get function name and clean it
        raw_function = result.get('function_name', result.get('function', 'Unknown'))
        clean_function = _clean_function_name(raw_function)
        
        hazard = {
            'id': hazard_id,
            'function': clean_function,
            'guideword': result.get('guide_word', 'UNKNOWN'),
            'malfunction': result.get('malfunctioning_behavior', 'Unknown malfunction'),
            'hazardous_event': result.get('hazardous_event', 'Unknown hazard'),
            'severity': result.get('severity', 'S1').upper(),
            'rationale': result.get('rationale', '')
        }
        
        # Ensure severity has S prefix
        if not hazard['severity'].startswith('S'):
            hazard['severity'] = 'S' + hazard['severity']
        
        hazards.append(hazard)
    
    return hazards


def _clean_function_name(function_text: str) -> str:
    """
    Clean function name from potential preamble text.
    
    Handles cases where function_name contains:
    - Full function extraction output
    - Numbered list items
    - Markdown formatting
    """
    
    if not function_text or function_text == 'Unknown':
        return 'Unknown Function'
    
    # Remove common preambles
    preambles = [
        'Here are',
        'Below are',
        'The following',
        'safety-relevant functions',
        'functions:',
        'Function list:',
        'Extracted functions:'
    ]
    
    for preamble in preambles:
        if function_text.lower().startswith(preamble.lower()):
            # This is likely the full extraction output, not a function name
            return 'Function (see details)'
    
    # If it's a numbered list item, extract just the function name
    # Format: "1. **Function Name:** Description"
    if function_text.strip()[0].isdigit():
        # Remove number prefix
        parts = function_text.split('.', 1)
        if len(parts) > 1:
            function_text = parts[1].strip()
    
    # Remove markdown bold
    function_text = function_text.replace('**', '')
    
    # If there's a colon, take everything before it (that's usually the function name)
    if ':' in function_text:
        function_text = function_text.split(':')[0].strip()
    
    # Truncate if too long (but keep reasonable length)
    if len(function_text) > 50:
        function_text = function_text[:47] + '...'
    
    return function_text


def _prioritize_hazards(hazards: List[Dict]) -> List[Dict]:
    """
    Prioritize hazards based on severity and criticality.
    
    Priority order:
    1. S3 hazards (life-threatening)
    2. S2 hazards (severe)
    3. Critical guide words (NO, LATE, REVERSE) for S1
    4. Remaining S1 hazards
    5. S0 hazards
    """
    
    def priority_score(hazard):
        severity = hazard['severity']
        guideword = hazard['guideword'].upper()
        
        # Base score by severity
        severity_score = {
            'S3': 1000,
            'S2': 500,
            'S1': 100,
            'S0': 10
        }.get(severity, 0)
        
        # Bonus for critical guide words
        critical_guidewords = ['NO', 'LATE', 'REVERSE', 'EARLY']
        guideword_bonus = 50 if any(gw in guideword for gw in critical_guidewords) else 0
        
        return severity_score + guideword_bonus
    
    # Sort by priority score (descending)
    prioritized = sorted(hazards, key=priority_score, reverse=True)
    
    return prioritized


def _format_summary_table(hazards: List[Dict]) -> str:
    """Format hazards into a compact summary table."""
    
    if not hazards:
        return "No hazards to display.\n"
    
    table = """
| ID | Severity | Guide Word | Hazardous Event | Function |
|----|----------|------------|-----------------|----------|
"""
    
    for hazard in hazards:
        # Truncate long descriptions with proper ellipsis
        event = hazard['hazardous_event']
        if len(event) > 50:
            event = event[:47] + "..."
        
        function = hazard['function']
        if len(function) > 35:
            function = function[:32] + "..."
        
        severity_icon = {
            'S3': '🔴 S3',
            'S2': '🟠 S2',
            'S1': '🟡 S1',
            'S0': '🟢 S0'
        }.get(hazard['severity'], hazard['severity'])
        
        # Ensure proper spacing in table
        table += f"| {hazard['id']} | {severity_icon} | {hazard['guideword']} | {event} | {function} |\n"
    
    return table


def _format_compact_list(hazards: List[Dict]) -> str:
    """Format hazards as compact bullet list."""
    
    if not hazards:
        return "- None\n"
    
    output = ""
    for hazard in hazards:
        output += f"- **{hazard['id']}**: {hazard['hazardous_event'][:80]}...\n"
    
    return output


@tool(
    return_direct=True,
    examples=[
        "show s3 hazards",
        "show only life-threatening hazards",
        "filter s3 hazards"
    ]
)
def show_s3_hazards_only(tool_input, cat):
    """
    Display only S3 (life-threatening/fatal) hazards from HAZOP analysis.
    
    Filters the HAZOP results to show only the most critical hazards
    that could result in life-threatening or fatal injuries.
    
    Args:
        tool_input: Not used
        cat: Cheshire Cat instance
        
    Returns:
        Table of S3 hazards only
    """
    
    log.info("🔧 TOOL CALLED: show_s3_hazards_only")
    
    hazop_results = cat.working_memory.get('hazop_results', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Analysis Available**

Use: `apply hazop analysis`"""
    
    # Convert and filter
    hazards = _convert_hazop_results(hazop_results)
    s3_hazards = [h for h in hazards if h['severity'] == 'S3']
    
    if not s3_hazards:
        return f"""✅ **No S3 Hazards Identified: {item_name}**

**Good News:** No life-threatening hazards found in HAZOP analysis.

**Total Hazards:** {len(hazards)}

This suggests a relatively low-risk system or effective inherent safety design.

**Next Step:** `assess exposure for all hazards`"""
    
    result = f"""# 🔴 **S3 Hazards Only: {item_name}**

**Life-Threatening / Fatal Injury Hazards**

**Count:** {len(s3_hazards)} out of {len(hazards)} total hazards

---

## S3 Hazards Detail

"""
    
    result += _format_summary_table(s3_hazards)
    
    result += f"""

---

## ⚠️ Critical Attention Required

These {len(s3_hazards)} hazards have potential for **life-threatening or fatal injuries**.

**Implications:**
- High likelihood of ASIL C or D ratings
- Rigorous safety measures required
- Consider design modifications to reduce severity
- May require redundancy or fail-safe mechanisms

**Next Steps:**
1. Review each S3 hazard carefully
2. Consider if severity can be reduced through design
3. Proceed to exposure assessment: `assess exposure for all hazards`
4. Expect stringent safety requirements for high-exposure S3 hazards

**Note:** A single S3 hazard with high exposure (E3/E4) and difficult controllability (C3)
will result in ASIL D, requiring the highest level of safety integrity.
"""
    
    return result


@tool(
    return_direct=True,
    examples=[
        "show hazards for battery monitoring",
        "filter hazards by function",
        "show voltage monitoring hazards"
    ]
)
def show_hazards_by_function(tool_input, cat):
    """
    Filter and display hazards for a specific function.
    
    Useful for reviewing all malfunctions associated with a particular
    system function.
    
    Args:
        tool_input: Function name or keyword
        cat: Cheshire Cat instance
        
    Returns:
        Filtered table of hazards for specified function
        
    Example:
        User: "show hazards for battery monitoring"
        Output: All hazards related to battery monitoring function
    """
    
    log.info("🔧 TOOL CALLED: show_hazards_by_function")
    
    # Parse input
    function_keyword = ""
    if isinstance(tool_input, str):
        function_keyword = tool_input.strip().lower()
    
    if not function_keyword:
        return """❌ **Please specify a function**

**Usage:**
```
show hazards for [function name]
```

**Examples:**
- show hazards for voltage monitoring
- show hazards for battery cell balancing
- show hazards for contactor control"""
    
    hazop_results = cat.working_memory.get('hazop_results', [])
    item_name = cat.working_memory.get('hara_item_name', 'System')
    
    if not hazop_results:
        return """❌ **No HAZOP Analysis Available**

Use: `apply hazop analysis`"""
    
    # Convert and filter
    hazards = _convert_hazop_results(hazop_results)
    
    # Filter by function keyword
    filtered_hazards = [
        h for h in hazards 
        if function_keyword in h['function'].lower()
    ]
    
    if not filtered_hazards:
        return f"""❌ **No hazards found for: "{function_keyword}"**

**Available functions:**
{_list_unique_functions(hazards)}

**Try:**
- Use partial function name: "voltage" instead of "voltage monitoring"
- Check spelling
- Use: `show hazop summary` to see all hazards"""
    
    result = f"""# 📋 **Hazards for Function: "{function_keyword}"**

**System:** {item_name}
**Matching Hazards:** {len(filtered_hazards)} out of {len(hazards)} total

---

## Filtered Hazards

"""
    
    result += _format_summary_table(filtered_hazards)
    
    # Statistics
    s3_count = len([h for h in filtered_hazards if h['severity'] == 'S3'])
    s2_count = len([h for h in filtered_hazards if h['severity'] == 'S2'])
    
    result += f"""

---

## Function Risk Profile

**Severity Distribution:**
- S3 (Life-threatening): {s3_count}
- S2 (Severe): {s2_count}
- S1 (Moderate): {len([h for h in filtered_hazards if h['severity'] == 'S1'])}
- S0 (None): {len([h for h in filtered_hazards if h['severity'] == 'S0'])}

**Risk Level:** {"🔴 HIGH" if s3_count > 0 else "🟠 MEDIUM" if s2_count > 0 else "🟡 LOW"}

**Next Steps:**
1. Review all malfunctions for this function
2. Consider design improvements if risk is high
3. Proceed to exposure assessment for these hazards
"""
    
    return result


def _list_unique_functions(hazards: List[Dict]) -> str:
    """List unique functions from hazards."""
    functions = set(h['function'] for h in hazards)
    return '\n'.join(f"- {func}" for func in sorted(functions))