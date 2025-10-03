# Enhanced HARA Assistant - Usage Guide

## Overview

The enhanced HARA Assistant now includes a comprehensive operational situations database with 40+ pre-defined scenarios covering all aspects of vehicle operation, each with ISO 26262-compliant exposure classifications based on real-world statistical data.

## Key Features

### 1. **Operational Situations Database**
- **40+ basic scenarios** across 6 categories
- **ISO 26262-compliant exposure levels** (E0-E4)
- **Statistical justification** for each scenario
- **Regional and use-case variations** documented

### 2. **Intelligent Scenario Selection**
- AI-powered analysis of hazards
- Automatic selection of relevant scenarios
- Smart combination of scenarios with exposure calculation
- Contextual recommendations

### 3. **Enhanced HARA Assessment**
- Integrated operational situation analysis
- Detailed E/S/C rationale linked to scenarios
- Comprehensive safety goal formulation
- Professional-grade documentation output

---

## Workflow

### **Standard HARA Development Process**

```
1. Extract Functions
   ↓
2. Apply HAZOP Analysis
   ↓
3. For Each Hazard:
   - Select/Combine Operational Situations
   - Assess E/S/C in Context
   - Calculate ASIL
   - Formulate Safety Goals
   ↓
4. Generate Complete HARA Table
   ↓
5. Export to Word/Excel
```

---

## Tool Reference

### **Tool 1: Extract Functions**
```
extract functions from Battery Management System
```

**What it does:**
- Finds Item Definition (working memory or plugin folders)
- Identifies all functions using AI analysis
- Stores for HAZOP analysis

---

### **Tool 2: Apply HAZOP Analysis**
```
apply hazop analysis
```

**What it does:**
- Applies 11 HAZOP guide words to each function
- Generates comprehensive hazard list
- Provides preliminary severity estimates
- Creates structured table with hazard IDs

**Output Example:**
```
| HAZ-001 | Monitor cell voltage | NO | Voltage not monitored | Overcharge → thermal runaway | S3 | ... |
| HAZ-002 | Monitor cell voltage | MORE | Voltage reading high | Over-discharge → vehicle stop | S2 | ... |
```

---

### **Tool 3: Select Operational Situation**
```
select operational situation for: Battery overcharge during charging
```

**What it does:**
- Analyzes the hazard context
- Searches 40+ scenario database
- Selects 1-3 relevant scenarios
- Combines scenarios using minimum exposure rule
- Provides detailed justification

**Example Output:**
```
Selected Scenarios:
- SPC-003: EV Fast Charging (E2)
- ENV-007: Extreme Heat (E2)

Combined Operational Situation:
Name: "Fast charging in extreme heat"
Exposure: E2 (minimum of E2 + E2)
Rationale: Fast charging occurs weekly (E2), extreme heat is seasonal (E2). 
           Their combination is less frequent than either individually.
```

---

### **Tool 4: Assess Hazard with Operational Situation**
```
assess hazard with situation: Battery thermal runaway during fast charging
```

**What it does:**
- Automatically selects operational situation
- Assesses Severity in context
- Assesses Exposure from situation database
- Assesses Controllability in context
- Calculates ASIL
- Formulates safety goal

**Output Includes:**
- Step 1: Operational Situation Selection
- Step 2: Exposure (E) Assessment with justification
- Step 3: Severity (S) Assessment with context
- Step 4: Controllability (C) Assessment
- Step 5: ASIL Calculation
- Step 6: Safety Goal Formulation

---

### **Tool 5: List Available Situations**
```
show all operational situations
```

**What it does:**
- Lists all 40+ scenarios by category
- Shows exposure levels and statistical data
- Explains combination rules
- Provides usage examples

**Filter by category:**
```
list urban scenarios
list environmental scenarios
list special operations
```

---

### **Tool 6: Create Custom Combination**
```
create custom combination: {"scenario_ids": ["HWY-001", "ENV-006"], "name": "Night highway driving"}
```

**What it does:**
- Manually combines specified scenarios
- Calculates combined exposure (minimum rule)
- Stores for use in HARA
- Useful for rare or specific combinations

---

### **Tool 7: Generate Enhanced HARA Table**
```
generate enhanced hara table
```

**What it does:**
- Compiles all assessments
- Creates comprehensive HARA table with:
  - Hazard IDs and descriptions
  - Operational situation details
  - E/S/C values with detailed rationale
  - ASIL calculations
  - Safety goals with safe states and FTTI
- Professional formatting for export

---

## Operational Situations Categories

### **Urban Driving (5 scenarios)**
- City traffic stop-and-go (E4)
- Urban parking operations (E3)
- Pedestrian crossings (E4)
- Traffic light intersections (E4)
- Residential street driving (E3)

### **Highway Driving (5 scenarios)**
- Highway cruising (E4)
- Highway lane changes (E4)
- Highway entry/merge (E3)
- Highway exit/deceleration (E3)
- Highway heavy traffic (E3)

### **Environmental Conditions (8 scenarios)**
- Light rain (E3)
- Heavy rain (E2)
- Light snow/slush (E2)
- Ice/black ice (E1)
- Fog/low visibility (E2)
- Night driving (E3)
- Extreme heat >35°C (E2)
- Extreme cold <-20°C (E1)

### **Special Operations (8 scenarios)**
- Vehicle startup - cold (E4)
- Vehicle startup - hot (E3)
- EV fast charging (E2)
- EV slow/home charging (E4)
- Towing/heavy load (E1)
- Off-road driving (E1)
- Long-term parking (E2)
- Diagnostics/service mode (E1)

### **Critical Maneuvers (4 scenarios)**
- Emergency braking (E1)
- Evasive steering (E1)
- Loss of traction event (E1)
- Collision event (E0)

### **Vehicle States (5 scenarios)**
- Normal operation - optimal (E4)
- Degraded mode operation (E1)
- Low state of charge <20% (E2)
- Battery thermal stress (E2)
- System initialization (E4)

---

## Scenario Combination Rules

### **Exposure Calculation Method**
**Rule:** Combined Exposure = MINIMUM of constituent scenario exposures

**Rationale:** Combined scenarios represent the *intersection* of conditions, which is inherently less frequent than any individual condition.

### **Examples:**

1. **Urban Traffic in Light Rain**
   - URB-001 (City traffic, E4) + ENV-001 (Light rain, E3)
   - Combined: E3
   - Logic: While city traffic is very common (E4), it rains less often (E3), so the combination is limited by rain frequency

2. **Highway Driving at Night**
   - HWY-001 (Highway cruising, E4) + ENV-006 (Night, E3)
   - Combined: E3
   - Logic: Highway driving is common (E4), but only a portion occurs at night (E3)

3. **Parking on Ice**
   - URB-002 (Parking, E3) + ENV-004 (Ice, E1)
   - Combined: E1
   - Logic: Parking is common (E3), but icy conditions are rare (E1), so combination is very rare

### **Combination Constraints**
- Maximum 3 scenarios per combination (for clarity)
- Scenarios must be logically compatible
- Consider both likelihood and severity impact
- Document rationale for selection

---

## Example: Complete HARA Development Session

### **Scenario: Battery Management System HARA**

```
User: Start HARA for Battery Management System

Agent: I'll help develop the HARA. First, let me extract functions.

User: extract functions from Battery Management System

Agent: [Lists 10 BMS functions including voltage monitoring, SoC calculation, etc.]

User: apply hazop analysis

Agent: [Generates table with 50+ hazards using all HAZOP guide words]
HAZ-001 through HAZ-050 identified...

User: Let me assess the critical ones. assess hazard with situation: Cell overvoltage leading to thermal runaway

Agent: [Performs comprehensive assessment]

Step 1: Operational Situation Selection
Selected Scenarios:
- SPC-004: EV Slow/Home Charging (E4) - Most charging occurs at home
- ENV-007: Extreme Heat (E2) - Increases thermal risk
- STA-001: Normal Operation (E4) - Baseline state

Combined: "Home charging during extreme heat" - Exposure E2

Step 2: Exposure Assessment
Exposure Level: E2 (0.1% - 1% of operating time)
Justification: Home charging is daily (E4), but extreme heat is seasonal (E2). 
Combined situation limited by heat exposure = E2.

Step 3: Severity Assessment
Severity Level: S3 (Life-threatening/fatal)
Justification: Thermal runaway can cause fire in residential setting. 
Risk to vehicle occupants, residents, and property. Limited escape routes.

Step 4: Controllability Assessment
Controllability Level: C3 (Difficult to control)
Justification: Thermal runaway develops rapidly (<2 minutes). 
Smoke/fire in enclosed garage. Most occupants cannot control effectively.

Step 5: ASIL Calculation
Calculated ASIL: D (from S3, E2, C3 per ISO 26262-3 Table 4)

Step 6: Safety Goal
"The system shall prevent cell overvoltage to avoid thermal runaway during all charging operations. 
(ASIL D, Safe State: Battery electrically isolated, FTTI: 100ms)"

User: assess hazard with situation: Loss of communication with vehicle controller

Agent: [Another complete assessment with different operational situation]
...

User: generate enhanced hara table

Agent: [Creates comprehensive table with all assessments]
```

---

## Best Practices

### **1. Scenario Selection**
✅ **DO:**
- Select scenarios where the hazard is most likely
- Consider scenarios that increase severity
- Use combinations when multiple conditions apply
- Document rationale clearly

❌ **DON'T:**
- Combine incompatible scenarios (e.g., parking + highway)
- Exceed 3 scenarios per combination
- Ignore regional/use-case variations
- Guess exposure without data

### **2. Exposure Assessment**
✅ **DO:**
- Use database values as starting point
- Adjust for specific item/vehicle type
- Consider regional climate differences
- Document any deviations from database

❌ **DON'T:**
- Override database without justification
- Underestimate exposure to reduce ASIL
- Ignore statistical data
- Use optimistic assumptions

### **3. Safety Goals**
✅ **DO:**
- State WHAT to achieve (prevent hazard)
- Include ASIL designation
- Specify safe state when applicable
- Include FTTI for time-critical scenarios

❌ **DON'T:**
- Prescribe HOW to achieve goal
- Include implementation details
- Combine multiple goals
- Use vague language

---

## Integration with Other Tools

### **Item Definition Developer Plugin**
- Automatically finds Item Definition
- Extracts functions for HAZOP
- Uses system context for assessments

### **Output Formatter Plugin**
- Exports HARA table to Word/Excel
- Professional formatting
- Includes operational situation details
- Audit-ready documentation

### **Future: FSC Developer Plugin**
- Use HARA safety goals as input
- Decompose ASIL levels
- Allocate requirements to elements
- Maintain traceability

---

## Troubleshooting

### **Issue: "No operational situation found for hazard"**
**Solution:**
1. Check if hazard description is clear
2. Try manual selection: `list all operational situations`
3. Create custom combination if needed
4. Provide more context about when hazard occurs

### **Issue: "Exposure level seems too high/low"**
**Solution:**
1. Review selected scenarios - are they appropriate?
2. Check if combination rule was applied correctly
3. Consider regional/use-case variations
4. Document justification if overriding database

### **Issue: "ASIL calculation doesn't match expectation"**
**Solution:**
1. Verify S/E/C assessments are accurate
2. Reference ISO 26262-3 Table 4 directly
3. Check if operational situation affects severity/controllability
4. Consider if conservative approach is warranted

---

## References

- **ISO 26262-3:2018** - Clause 6: Hazard Analysis and Risk Assessment
- **ISO 26262-3:2018** - Table 4: ASIL Determination
- **NHTSA Statistical Data** - Vehicle crash and exposure statistics
- **EURO NCAP** - Real-world driving scenarios
- **Insurance Institute for Highway Safety (IIHS)** - Crash data

---

## Version Information

- **Plugin Version:** 1.0
- **Database Version:** 1.0
- **Last Updated:** 2025
- **ISO 26262 Edition:** 2018 (2nd Edition)

---

## Support

For issues or enhancements:
- GitHub: [Repository URL]
- Documentation: [Docs URL]
- Contact: [Author]