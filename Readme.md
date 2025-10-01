# ISO 26262 HARA Assistant Plugin

A Cheshire Cat AI plugin that assists in developing Hazard Analysis and Risk Assessment (HARA) for automotive systems using HAZOP (Hazard and Operability) methodology per ISO 26262-3:2018 Clause 6.

## Features

### Core Functionalities

1. **Function Extraction** - Automatically extract functions from Item Definition documents
2. **HAZOP Analysis** - Apply systematic HAZOP guide words to identify malfunctioning behaviors
3. **Operational Situations** - Define and classify driving scenarios
4. **E/S/C Assessment** - Evaluate Exposure, Severity, and Controllability
5. **ASIL Determination** - Calculate ASIL ratings per ISO 26262-3 Table 4
6. **HARA Documentation** - Generate complete, ISO-compliant HARA documents

## Installation

1. Copy the entire plugin folder to your Cheshire Cat plugins directory:
   ```
   cat/plugins/AI_Agent-HARA_Assistant/
   ```

2. Restart Cheshire Cat or reload plugins

3. The plugin is ready to use!

## Dependencies

```txt
# Add to requirements.txt if needed
(currently no external dependencies required)
```

## Workflow

### Step 1: Extract Functions from Item Definition

**Command:**
```
extract functions from [item name]
```

**Example:**
```
extract functions from Battery Management System
```

**What it does:**
- Reads the Item Definition document
- Identifies all functions of the item
- Lists functions with descriptions and normal parameters
- Stores in working memory for next steps

---

### Step 2: Apply HAZOP Analysis

**Command:**
```
apply hazop to functions
```

**What it does:**
- Takes each function identified in Step 1
- Systematically applies HAZOP guide words:
  - **NO** - Function not performed
  - **MORE** - Excessive magnitude
  - **LESS** - Insufficient magnitude
  - **EARLY** - Too soon
  - **LATE** - Too late / delayed
  - **REVERSE** - Opposite direction
  - **OTHER THAN** - Wrong function
  - **PART OF** - Incomplete function
  - **AS WELL AS** - Additional unintended action
  - **WHERE ELSE** - Wrong location/component
- Identifies malfunctioning behaviors
- Describes potential hazardous events
- Provides preliminary severity estimates

**Example Output:**
```
Function: Battery Cell Voltage Monitoring

Guide Word: NO (not performed)
- Malfunctioning Behavior: Cell voltage not monitored
- Hazardous Event: Overcharge causing thermal runaway
- Preliminary Severity: S3 (fatal - fire risk)

Guide Word: MORE (excessive reading)
- Malfunctioning Behavior: Voltage reading higher than actual
- Hazardous Event: System allows over-discharge
- Preliminary Severity: S2 (damage to battery, vehicle stops)

...
```

---

### Step 3: Define Operational Situations

**Command:**
```
define operational situations
```

**What it does:**
- Identifies relevant driving scenarios
- Categories: urban, highway, parking, adverse weather, etc.
- Provides preliminary exposure classification (E1-E4)
- Documents frequency and duration

---

### Step 4: Assess Individual Hazards (E/S/C + ASIL)

**Command:**
```
assess hazard: [hazard description]
```

**Example:**
```
assess hazard: Battery overcharge due to incorrect voltage measurement
```

**What it does:**
- Links hazard to operational situation
- **Severity (S)** assessment:
  - S0 = No injuries
  - S1 = Light/moderate injuries
  - S2 = Severe injuries (survival probable)
  - S3 = Life-threatening/fatal
- **Exposure (E)** assessment:
  - E0 = Incredible (< 0.001%)
  - E1 = Very low (0.001% - 0.1%)
  - E2 = Low (0.1% - 1%)
  - E3 = Medium (1% - 10%)
  - E4 = High (> 10%)
- **Controllability (C)** assessment:
  - C0 = Controllable in general (>99% drivers)
  - C1 = Simply controllable (>99% drivers, minor effort)
  - C2 = Normally controllable (>90% drivers)
  - C3 = Difficult/uncontrollable (<90% drivers)
- **ASIL Calculation** using ISO 26262-3 Table 4

**Example Output:**
```
Severity: S3
Justification: Thermal runaway can cause fire, leading to fatal injuries

Exposure: E3
Justification: Normal charging occurs frequently (daily), medium probability

Controllability: C3
Justification: Fire develops rapidly, driver has very limited time to exit

Calculated ASIL: D
```

---

### Step 5: Generate HARA Document

**Command:**
```
generate hara document
```

**What it does:**
- Compiles all analysis results
- Creates ISO 26262-3:2018 compliant HARA document
- Includes:
  1. Introduction and scope
  2. Item definition summary
  3. Operational situations table
  4. Hazard identification (HAZOP results)
  5. Risk assessment (E/S/C + ASIL)
  6. Safety goals derivation
  7. HARA summary statistics
  8. Assumptions and limitations

---

## Usage Examples

### Complete HARA Development Session

```
User: Start HARA for Battery Management System

Agent: I'll help you develop the HARA. First, let me extract the functions.

User: extract functions from Battery Management System

Agent: [Lists all BMS functions...]

User: apply hazop to functions

Agent: [Performs systematic HAZOP analysis...]

User: define operational situations

Agent: [Identifies driving scenarios...]

User: assess hazard: Cell overvoltage leading to thermal runaway

Agent: [Performs E/S/C assessment and calculates ASIL D...]

User: assess hazard: Loss of communication with vehicle controller

Agent: [Performs E/S/C assessment and calculates ASIL B...]

User: generate hara document

Agent: [Creates complete HARA document...]
```

### Quick Assessment

```
User: What ASIL for: Loss of braking, highway driving, driver cannot stop?

Agent: Let me assess this hazard...
- Severity: S3 (fatal collision at high speed)
- Exposure: E3 (highway driving is common)
- Controllability: C3 (cannot stop = uncontrollable)
- ASIL: D
```

## File Structure

```
AI_Agent-HARA_Assistant/
├── plugin.json                          # Plugin metadata
├── README.md                            # This file
├── requirements.txt                     # Python dependencies
├── hara_hazop_tool.py                   # Main HAZOP tools
├── asil_calculator.py                   # ASIL calculation utility
│
└── templates/
    ├── hazop_guidewords.json            # HAZOP guide words catalog
    ├── esc_rating_tables.json           # E/S/C classification criteria
    ├── hara_structure.json              # HARA document template
    └── hazard_categories.json           # Common automotive hazards
```

## HAZOP Guide Words Reference

| Guide Word | Meaning | Example |
|------------|---------|---------|
| NO | Not performed | Brake doesn't activate |
| MORE | Excessive | Too much brake force |
| LESS | Insufficient | Weak braking |
| EARLY | Too soon | Airbag deploys before impact |
| LATE | Delayed | Brake response delayed |
| REVERSE | Opposite | Acceleration instead of braking |
| OTHER THAN | Wrong function | Horn instead of wipers |
| PART OF | Incomplete | Only front brakes work |
| AS WELL AS | Additional | Brakes + unintended steering |
| WHERE ELSE | Wrong location | Brake on wrong wheel |

## Tips for Effective HARA

1. **Be Systematic** - Don't skip guide words, each reveals different failure modes
2. **Think Worst-Case** - Consider most severe reasonable scenarios for Severity
3. **Use Data** - Base Exposure on actual driving statistics when available
4. **Average Driver** - Controllability is for typical drivers, not experts
5. **Document Assumptions** - Always record what you assumed
6. **Iterate** - HARA is iterative; refine as design evolves

## ISO 26262 Compliance

This plugin implements:
- ✅ ISO 26262-3:2018 Clause 6.4.2 - Situation analysis
- ✅ ISO 26262-3:2018 Clause 6.4.3 - Hazard identification
- ✅ ISO 26262-3:2018 Clause 6.4.4 - Risk assessment (E/S/C)
- ✅ ISO 26262-3:2018 Clause 6.4.5 - ASIL determination
- ✅ ISO 26262-3:2018 Clause 6.4.6 - Safety goals derivation

## Future Enhancements

- [ ] Integration with Item Definition Developer plugin
- [ ] HARA review checklist tool
- [ ] Export to Excel/Word formats
- [ ] Hazard library with reusable templates
- [ ] Traceability matrix generation
- [ ] Safety goal decomposition support

## Support

For issues or questions:
- GitHub: https://github.com/tondeni/AI_Agent-HARA_Assistant
- Documentation: [Link to docs]

## License

[Your license here]

---

**Version:** 0.1.0  
**Author:** Tonino De Nigris  
**Last Updated:** 2025