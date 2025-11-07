# HARA Assistant Plugin

**ISO 26262-3:2018 Hazard Analysis and Risk Assessment Tool for Cheshire Cat AI**

Automates HARA development using HAZOP methodology with systematic hazard identification, risk assessment (E/S/C), ASIL determination, and safety goal derivation.

---

## Features

- ✅ **Function Extraction** from Item Definitions (PDF/DOCX/TXT)
- ✅ **HAZOP Analysis** with 10 guide words per function
- ✅ **E/S/C Assessment** using statistical databases
- ✅ **ASIL Calculation** per ISO 26262-3 Table 4
- ✅ **Safety Goal Generation** for ASIL A-D hazards
- ✅ **Document Export** to Word/Excel

---

## Installation

1. Copy plugin folder to Cheshire Cat plugins directory:
   ```
   cat/plugins/AI_Agent-HARA_Assistant/
   ```

2. Install dependencies:
   ```bash
   pip install openpyxl>=3.1.0
   ```

3. Add Item Definition files to:
   ```
   AI_Agent-HARA_Assistant/item_definitions/
   ```

4. Restart Cheshire Cat

---

## Quick Start

```
User: extract functions from Battery Management System
Agent: ✅ 5 functions extracted

User: apply hazop to functions
Agent: ✅ 47 hazards identified

User: assess exposure for all hazards
Agent: ✅ Exposure ratings assigned

User: assess ESC for all hazards
Agent: ✅ Severity and Controllability assessed

User: determine ASIL for all hazards
Agent: ✅ ASIL D: 3, ASIL C: 5, ASIL B: 9, ASIL A: 12

User: derive safety goals
Agent: ✅ 29 safety goals created

User: generate HARA document
Agent: ✅ HARA_BMS_20251107.docx and .xlsx created
```

---

## Workflow

```
1. Extract Functions          → Identifies 4-5 safety-relevant functions
2. Apply HAZOP               → Generates ~47 hazards (10 guide words × functions)
3. Assess Exposure (E0-E4)   → Uses statistical database
4. Assess Severity (S0-S3)   → Evaluates injury potential
5. Assess Controllability    → Driver's ability to avoid (C0-C3)
6. Determine ASIL            → Calculates QM/A/B/C/D per ISO 26262-3 Table 4
7. Derive Safety Goals       → Creates top-level safety requirements
8. Generate Documentation    → Exports Word report + Excel matrix
```

---

## Commands

| Command | Description |
|---------|-------------|
| `extract functions from [System]` | Extract functions from Item Definition |
| `apply hazop to functions` | Generate hazards using HAZOP guide words |
| `assess exposure for all hazards` | Assign exposure ratings (E0-E4) |
| `assess ESC for all hazards` | Rate severity and controllability |
| `determine ASIL for all hazards` | Calculate ASIL per ISO 26262-3 |
| `derive safety goals` | Create safety goals for ASIL A-D |
| `generate HARA document` | Export to Word/Excel |

---

## File Structure

```
AI_Agent-HARA_Assistant/
├── plugin.json
├── README.md
├── code/
│   ├── tools/              # 7 Cheshire Cat tools
│   ├── generators/         # HAZOP, ASIL, document generators
│   ├── loaders/            # Item Definition parsers
│   └── utils/              # Fuzzy matching, path utilities
├── templates/
│   ├── hazop_guidewords.json
│   ├── operational_situations_db.json
│   └── esc_rating_tables.json
├── item_definitions/       # USER: Place Item Definitions here
└── generated_documents/    # OUTPUT: HARA reports generated here
```

---

## HAZOP Guide Words

| Guide Word | Meaning | Example |
|------------|---------|---------|
| NO | Not performed | Brake doesn't activate |
| MORE | Excessive | Too much brake force |
| LESS | Insufficient | Weak braking |
| EARLY | Too soon | Premature deployment |
| LATE | Delayed | Slow response |
| REVERSE | Opposite | Wrong direction |
| OTHER THAN | Wrong function | Horn instead of wipers |
| PART OF | Incomplete | Partial operation |
| AS WELL AS | Additional | Unintended side effect |
| WHERE ELSE | Wrong location | Wrong component |

---

## ISO 26262 Compliance

Implements:
- ✅ ISO 26262-3:2018, Clause 6.4.2 - Situation analysis
- ✅ ISO 26262-3:2018, Clause 6.4.3 - Hazard identification
- ✅ ISO 26262-3:2018, Clause 6.4.4 - E/S/C classification
- ✅ ISO 26262-3:2018, Clause 6.4.5 - ASIL determination
- ✅ ISO 26262-3:2018, Clause 6.4.6 - Safety goal derivation
- ✅ ISO 26262-3:2018, Table 4 - ASIL matrix

---

## Integration

### Upstream: Item Definition Developer Plugin
- Automatically reads Item Definition documents
- Extracts safety-relevant functions

### Parallel: Output Formatter Plugin
- Formats HARA data into professional documents
- Creates Word/Excel exports

### Downstream: FSC Developer Plugin (Future)
- Uses HARA safety goals as input
- Decomposes ASIL requirements to system elements

---

## Dependencies (in requirements.txt)

```txt
openpyxl>=3.1.0        # Required: Excel generation
python-docx>=0.8.11    # Optional: Word generation
PyPDF2>=3.0.0          # Optional: PDF parsing
```

---

## Troubleshooting

**"No item definition found"**
- Ensure file is in `item_definitions/` folder
- Check file extension: .pdf, .docx, .txt
- Try exact filename or use fuzzy matching

**"Cannot perform HAZOP - missing functions"**
- Run `extract functions from [System]` first
- Don't skip Step 1

**"ASIL seems incorrect"**
- Verify E/S/C ratings are accurate
- Reference ISO 26262-3 Table 4
- Check operational situation selection

---

**HARA Document:**
- Complete hazard analysis with E/S/C rationale
- ASIL determination per ISO 26262-3 Table 4
- Safety goals with traceability
- Operational situations mapping

---
