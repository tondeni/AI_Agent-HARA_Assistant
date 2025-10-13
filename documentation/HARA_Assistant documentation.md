# HARA Assistant Plugin
**ISO 26262-3:2018, Clause 6 - Hazard Analysis and Risk Assessment**

**Version:** 0.1.0  
**Author:** Tonino De Nigris  
**Repository:** https://github.com/tondeni/AI_Agent-HARA_Assistant

---

## OVERVIEW

The HARA Assistant plugin enables AI agents to develop Hazard Analysis and Risk Assessment (HARA) for automotive systems using HAZOP (Hazard and Operability) methodology per ISO 26262-3:2018 Clause 6. It systematically identifies hazards, evaluates risks, and derives safety goals with appropriate ASIL (Automotive Safety Integrity Level) ratings.

**Key Capabilities:**
- Extract safety-relevant functions from Item Definitions
- Apply systematic HAZOP analysis with 10 guide words
- Define operational situations for hazard scenarios
- Assess Exposure, Severity, and Controllability (E/S/C)
- Calculate ASIL ratings per ISO 26262-3 Table 4
- Derive safety goals for ASIL-rated hazards
- Generate complete ISO-compliant HARA documentation

**Purpose:**
HARA is the foundation of automotive functional safety. It identifies what can go wrong with a system, how bad it could be, and what safety measures are needed. This plugin automates the systematic HAZOP process, ensuring comprehensive hazard coverage and consistent risk assessment per ISO 26262 requirements.

---

## WORKFLOW

### Internal Workflow

The HARA Assistant follows a 6-step structured process:

```
1. Extract Functions from Item Definition
    ↓
2. Apply HAZOP Analysis (10 guide words per function)
    ↓
3. Define Operational Situations
    ↓
4. Assess E/S/C for Each Hazard
    ↓
5. Determine ASIL (ISO 26262-3 Table 4)
    ↓
6. Derive Safety Goals & Generate HARA Document
```

**Step Details:**

**Step 1: Function Extraction**
- Reads Item Definition from working memory or file
- Identifies 4-5 safety-relevant functions
- Stores functions for HAZOP analysis

**Step 2: HAZOP Analysis**
- Applies 10 HAZOP guide words to each function
- Identifies malfunctioning behaviors
- Describes hazardous events
- Provides preliminary severity estimates

**Step 3: Operational Situations**
- Defines driving scenarios (urban, highway, parking, etc.)
- Characterizes environmental conditions
- Links situations to specific hazards

**Step 4: E/S/C Assessment**
- Evaluates Severity (S0-S3) based on injury potential
- Evaluates Exposure (E0-E4) based on situation probability
- Evaluates Controllability (C0-C3) based on driver capability
- Documents rationale for each rating

**Step 5: ASIL Determination**
- Applies ISO 26262-3 Table 4 logic
- Assigns ASIL (QM, A, B, C, or D)
- Validates rating consistency

**Step 6: Safety Goals & Documentation**
- Derives safety goals for ASIL A-D hazards
- Generates Word document with complete HARA
- Creates Excel traceability matrix

### Integration with Other Plugins

**Upstream Integration:**

1. **Item Definition Developer Plugin**
   - **Data Flow:** Item Definition → Function Extraction
   - **Method:** Working memory or file-based
   - **Use Case:** HARA reads Item Definition to extract functions
   - **Workflow:**
     ```
     Item Definition Developer
         ↓
     [Working Memory: item_definition_content]
         ↓
     HARA Assistant (extract functions)
     ```

**Downstream Integration:**

2. **FSC Developer Plugin**
   - **Data Flow:** Safety Goals → FSC Development
   - **Method:** Working memory or HARA file export
   - **Use Case:** FSC reads safety goals to derive functional requirements
   - **Workflow:**
     ```
     HARA Assistant (generate HARA)
         ↓
     [Working Memory: hara_safety_goals]
         ↓
     FSC Developer (load HARA)
     ```

**Complete Safety Lifecycle Chain:**
```
Item Definition Developer
    ↓
HARA Assistant
    ↓
FSC Developer
    ↓
Technical Safety Concept
    ↓
...
```

### Typical Usage Scenarios

**Scenario 1: Full HARA Development**
```
1. "extract functions from Battery Management System"
2. "apply hazop to functions"
3. "define operational situations"
4. "assess ESC for all hazards"
5. "determine ASIL"
6. "generate HARA document"
```

**Scenario 2: Chained from Item Definition**
```
1. Generate Item Definition (Developer plugin)
2. "extract functions from [System]" (auto-reads from memory)
3. Continue HARA workflow
4. "generate HARA document"
5. "load HARA for FSC" (FSC Developer plugin)
```

**Scenario 3: Iterative HAZOP**
```
1. Extract functions
2. Apply HAZOP for first 2 functions
3. Review results
4. Apply HAZOP for remaining functions
5. Complete E/S/C assessment
```

---

## FUNCTIONALITIES

### 1. Extract Functions from Item Definition
**Description:** Extracts 4-5 safety-relevant functions from the Item Definition document. Functions are identified based on their safety criticality and potential for hazardous malfunction.

**Input:**
- `item_name` (string) - Name of the automotive system (e.g., "Battery Management System", "Brake System")
- Item Definition must be in working memory or in `item_definitions/` folder

**Output:**
- Numbered list of 4-5 critical functions with descriptions and normal parameters
- Stored in working memory under `item_functions`
- Ready for HAZOP analysis in Step 2

---

### 2. Apply HAZOP Analysis
**Description:** Systematically applies 10 HAZOP guide words (NO, MORE, LESS, EARLY, LATE, REVERSE, OTHER THAN, PART OF, AS WELL AS, WHERE ELSE) to each extracted function. Identifies malfunctioning behaviors and potential hazardous events.

**Input:**
- Extracted functions from Step 1 (stored in working memory)
- Optional: Specific function to analyze (otherwise analyzes all)

**Output:**
- HAZOP table with malfunctioning behaviors and hazardous events for each function × guide word combination
- Preliminary severity estimates (S0-S3)
- Stored in working memory under `hazop_results`
- Typically generates 40-50 potential hazards

---

### 3. Define Operational Situations
**Description:** Identifies and characterizes driving scenarios where hazards could occur. Defines operational situations by speed range, traffic conditions, environmental factors, and driver attention levels.

**Input:**
- HAZOP results from Step 2
- System type and typical use cases

**Output:**
- List of operational situations (typically 4-8 scenarios)
- Each situation includes: speed range, traffic density, environmental conditions, driver state
- Linked to relevant hazards
- Stored in working memory under `operational_situations`

---

### 4. Assess E/S/C (Exposure, Severity, Controllability)
**Description:** Evaluates each hazardous event according to ISO 26262-3 risk classification criteria. Assesses potential injury severity (S0-S3), probability of operational situation (E0-E4), and driver's ability to prevent harm (C0-C3).

**Input:**
- Hazardous events from HAZOP analysis
- Operational situations from Step 3
- Optional: Specific hazard to assess

**Output:**
- E/S/C ratings for each hazard with detailed rationale
- Severity: S0 (no injuries) to S3 (fatal injuries)
- Exposure: E0 (<0.001%) to E4 (≥10%)
- Controllability: C0 (controllable) to C3 (uncontrollable)
- Stored in working memory under `esc_assessments`

---

### 5. Determine ASIL
**Description:** Calculates ASIL rating for each hazard by applying ISO 26262-3 Table 4 logic to the E/S/C ratings. Assigns ASIL QM (Quality Management only), A, B, C, or D based on risk level.

**Input:**
- E/S/C assessments from Step 4
- ISO 26262-3:2018 Table 4 mapping

**Output:**
- ASIL rating (QM, A, B, C, D) for each hazard
- ASIL distribution summary
- Justification for each ASIL assignment
- Stored in working memory under `asil_ratings`

---

### 6. Derive Safety Goals
**Description:** Automatically derives safety goals for all hazards rated ASIL A, B, C, or D. Safety goals specify the top-level safety requirement to prevent or mitigate each hazard.

**Input:**
- ASIL-rated hazards from Step 5
- Hazard descriptions and operational contexts

**Output:**
- Safety goal for each ASIL A-D hazard
- Safe state definition
- Fault Tolerant Time Interval (FTTI) specification
- Stored in working memory under `safety_goals`

---

### 7. Generate HARA Document
**Description:** Creates complete ISO 26262-3 compliant HARA documentation including all analysis results, E/S/C rationale, ASIL calculations, and safety goals. Generates both Word document and Excel traceability matrix.

**Input:**
- All analysis results from Steps 1-6 (stored in working memory)
- System name and metadata

**Output:**
- Word document (.docx): Complete HARA report with all sections, tables, and references
- Excel spreadsheet (.xlsx): Traceability matrix with functions, hazards, E/S/C, ASIL, and safety goals
- Files saved in plugin folder with timestamp
- Ready for review and integration with FSC Developer

---

## HAZOP GUIDE WORDS

The plugin applies these 10 standard HAZOP guide words:

| Guide Word | Meaning | Example |
|------------|---------|---------|
| **NO** | Not performed | Brake doesn't activate |
| **MORE** | Excessive | Too much brake force |
| **LESS** | Insufficient | Weak braking |
| **EARLY** | Too soon | Airbag deploys before impact |
| **LATE** | Delayed | Brake response delayed |
| **REVERSE** | Opposite | Acceleration instead of braking |
| **OTHER THAN** | Wrong function | Horn instead of wipers |
| **PART OF** | Incomplete | Only front brakes work |
| **AS WELL AS** | Additional unintended | Brakes + unintended steering |
| **WHERE ELSE** | Wrong location | Brake on wrong wheel |

---

## E/S/C RATING SCALES

### Severity (S0-S3)
- **S0:** No injuries
- **S1:** Light to moderate injuries
- **S2:** Severe injuries (survival probable)
- **S3:** Life-threatening to fatal injuries

### Exposure (E0-E4)
- **E0:** Incredibly unlikely (<0.001%)
- **E1:** Very low probability (<0.1%)
- **E2:** Low probability (<1%)
- **E3:** Medium probability (<10%)
- **E4:** High probability (≥10%)

### Controllability (C0-C3)
- **C0:** Controllable in general
- **C1:** Simply controllable (≥99% drivers)
- **C2:** Normally controllable (≥90% drivers)
- **C3:** Difficult/uncontrollable (<90% drivers)

---

## USAGE EXAMPLES

### Example 1: Complete HARA Workflow
```
User: extract functions from Windscreen Wiper System

Agent: ✅ Functions Extracted: 5
1. Wiper Blade Movement Control
2. Washer Fluid Delivery
3. Speed Control
[...]

User: apply hazop to functions

Agent: ✅ HAZOP Analysis Complete
Total Malfunctioning Behaviors: 47
[Detailed HAZOP results...]

User: define operational situations

Agent: ✅ Operational Situations Defined: 6
OS-1: Urban Driving in Light Rain
OS-2: Highway Driving in Heavy Rain
[...]

User: assess ESC for all hazards

Agent: ✅ E/S/C Assessment Complete
Hazard H-001: E4 + S2 + C2
Hazard H-002: E3 + S3 + C3
[...]

User: determine ASIL

Agent: ✅ ASIL Determination Complete
ASIL Distribution:
├─ ASIL D: 3 hazards
├─ ASIL C: 5 hazards
├─ ASIL B: 9 hazards
└─ ASIL A: 12 hazards

User: generate HARA document

Agent: ✅ HARA Document Generated
Files Created:
- Windscreen_Wiper_System_HARA_20251007.docx
- Windscreen_Wiper_System_HARA_Traceability_20251007.xlsx
```

---

## FILE STRUCTURE

```
AI_Agent-HARA_Assistant/
├── plugin.json
├── README.md
├── hara_hazop_tool.py              # Main HAZOP tools
├── asil_calculator.py              # ASIL determination logic
├── setup_folders.py                # Folder initialization
├── templates/
│   ├── hazop_guidewords.json       # HAZOP guide words catalog
│   ├── esc_rating_tables.json      # E/S/C classification criteria
│   ├── hara_structure.json         # HARA document template
│   └── hazard_categories.json      # Common automotive hazards
├── item_definitions/               # Item Definition files
└── generated_documents/            # HARA outputs
```

---

## ISO 26262 COMPLIANCE

This plugin implements:

- ✅ **ISO 26262-3:2018, Clause 6.4.2** - Situation analysis and classification
- ✅ **ISO 26262-3:2018, Clause 6.4.3** - Hazard identification
- ✅ **ISO 26262-3:2018, Clause 6.4.4** - Classification of hazardous events (E/S/C)
- ✅ **ISO 26262-3:2018, Clause 6.4.5** - ASIL determination
- ✅ **ISO 26262-3:2018, Clause 6.4.6** - Safety goal determination
- ✅ **ISO 26262-3:2018, Table 4** - ASIL determination table

**Work Products Generated:**
- Hazard analysis and risk assessment
- Safety goals with ASIL assignments
- Traceability from functions to safety goals

---

## BEST PRACTICES

1. **Be Systematic:** Don't skip HAZOP guide words - each reveals different failure modes
2. **Think Worst-Case:** Consider most severe reasonable scenarios for Severity
3. **Use Data:** Base Exposure on actual driving statistics when available
4. **Average Driver:** Assess Controllability for typical drivers, not experts
5. **Document Rationale:** Always record assumptions and reasoning for E/S/C ratings
6. **Iterate:** HARA is iterative - refine as system design evolves
7. **Chain Workflows:** Complete Item Definition before starting HARA

---

## INTEGRATION TIPS

**With Item Definition Developer:**
- Generate Item Definition first
- Keep in working memory for automatic function extraction
- Use exact system name in both plugins

**With FSC Developer:**
- Complete HARA before starting FSC
- Generate HARA document to create file for FSC input
- Alternatively, chain directly through working memory

**For Manual Integration:**
- Export HARA Excel file
- Place in FSC Developer's `hara_inputs/` folder
- Continue with FSC development workflow

---

## LIMITATIONS

- HAZOP analysis generates many potential hazards; expert review required to filter
- E/S/C ratings should be validated by safety engineers with domain knowledge
- ASIL calculations are automated but assumptions must be verified
- Not a replacement for expert safety analysis, but an acceleration tool

---

## TIPS FOR EFFECTIVE HARA

**Hazard Identification:**
- Start with well-defined Item Definition
- Consider all operating modes
- Include foreseeable misuse scenarios

**Risk Assessment:**
- Use conservative estimates when uncertain
- Consider entire operational lifetime
- Account for environmental factors

**ASIL Determination:**
- Follow ISO 26262-3 Table 4 strictly
- Document any deviations with justification
- Consider ASIL decomposition for ASIL D

---

## SUPPORT

**GitHub:** https://github.com/tondeni/AI_Agent-HARA_Assistant  
**Issues:** Report issues via GitHub Issues  
**Author:** Tonino De Nigris

---

**Document Version:** 1.0  
**Last Updated:** October 2025  
**ISO 26262 Edition:** 2018 (2nd Edition)