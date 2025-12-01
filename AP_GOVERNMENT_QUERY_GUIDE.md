# AP Government Query Engineering Guide

## Purpose
This guide helps you ask the RIGHT questions to get policy-grade answers from the AP Policy Assistant.

---

## The 4-Layer Framework

Every query goes through 4 layers. Weak queries fail at one of these:

1. **Retrieval**: Are the right documents found?
2. **Context**: Is the retrieved content relevant?
3. **Structure**: Is the answer formatted for policy use?
4. **Quality**: Is the output factual and actionable?

---

## Query Patterns for AP Government

### Pattern 1: Recent Policy Updates

**WEAK**: "What are the recent GOs?"
**STRONG**: "List all GOs issued by School Education Department in the last 6 months, with dates, key provisions, and implementation status."

**Why**: Specific timeframe, department, and required output format.

---

### Pattern 2: Implementation Guidance

**WEAK**: "How to implement NEP 2020?"
**STRONG**: "Provide step-by-step implementation guide for NEP 2020 in AP government schools, including timeline, responsible bodies, budget requirements, and compliance checklist."

**Why**: Asks for structured implementation details, not just general information.

---

### Pattern 3: Compliance Checks

**WEAK**: "Are we following the rules?"
**STRONG**: "Check compliance with G.O.Ms.No.45 dated 15-03-2024 regarding teacher transfers. List requirements, current status, gaps, and corrective actions needed."

**Why**: Specific GO, clear compliance framework requested.

---

### Pattern 4: Policy Comparison

**WEAK**: "What changed in the new GO?"
**STRONG**: "Compare G.O.Ms.No.123 (2024) with G.O.Ms.No.89 (2023) on teacher recruitment. Highlight: what's new, what's removed, what's modified, and implementation implications."

**Why**: Specific GOs, structured comparison requested.

---

### Pattern 5: Decision Support

**WEAK**: "Should we do this?"
**STRONG**: "Prepare decision memo on implementing AI labs in 100 schools. Include: options analysis, cost-benefit, legal basis, risks, timeline, and recommendation with rationale."

**Why**: Asks for decision-ready format with all necessary components.

---

## Query Rewriting Rules

### Rule 1: Always specify TIME
- ❌ "Recent GOs"
- ✅ "GOs from January 2024 to present"

### Rule 2: Always specify SCOPE
- ❌ "School policies"
- ✅ "Policies for government high schools in rural areas"

### Rule 3: Always specify OUTPUT FORMAT
- ❌ "Tell me about..."
- ✅ "Provide a policy brief with background, current rules, gaps, and recommendations on..."

### Rule 4: Always specify DEPARTMENT
- ❌ "Education policies"
- ✅ "School Education Department policies"

### Rule 5: Always cite SPECIFIC GOs when known
- ❌ "The transfer policy"
- ✅ "G.O.Ms.No.45 dated 15-03-2024 on teacher transfers"

---

## Example Queries with Expected Outputs

### Example 1: Policy Brief Request

**Query**:
"Prepare policy brief on midday meal scheme implementation in AP. Include current GOs, budget allocation, coverage statistics, gaps, and recommendations for improvement."

**Expected Output**:
- Executive summary
- Current GO framework
- Budget and coverage data
- Implementation gaps
- Actionable recommendations
- Citations

---

### Example 2: Implementation Guide

**Query**:
"Create implementation guide for G.O.Ms.No.78 on digital classrooms. Include phases, timelines, responsible bodies, resource requirements, compliance checklist, and monitoring process."

**Expected Output**:
- Phased implementation plan
- Role-responsibility matrix
- Resource breakdown
- Compliance checklist
- Monitoring framework

---

### Example 3: Compliance Analysis

**Query**:
"Analyze compliance with RTE Act Section 12(1)(c) in AP. List requirements, current status, gaps, high-risk areas, and compliance roadmap with timelines."

**Expected Output**:
- Requirements matrix
- Compliance status per requirement
- Gap analysis
- Risk assessment
- Remediation roadmap

---

## Diagnostic Queries

Use these to test system quality:

### Test 1: Retrieval Quality
"List the exact documents you retrieved for [query]. For each, provide: title, date, 2-line summary, and relevance score."

### Test 2: Gap Detection
"Based on retrieved documents, what information is MISSING to fully answer [query]? What additional documents would help?"

### Test 3: Reasoning Chain
"Explain step-by-step how you formed your answer, citing specific documents and sections for each claim."

### Test 4: Self-Verification
"Review your answer and identify: (1) uncertain claims, (2) assumptions made, (3) contradictions, (4) parts needing verification."

### Test 5: Structure Check
"Reformat your answer using: Background, Current Rules, Gaps, Recommendations, Citations."

---

## Common Mistakes to Avoid

### Mistake 1: Vague Time References
- ❌ "Recent", "Latest", "Current"
- ✅ "Last 6 months", "2024", "After 01-01-2024"

### Mistake 2: No Output Structure
- ❌ "Tell me about X"
- ✅ "Provide policy brief on X with [specific sections]"

### Mistake 3: Missing Context
- ❌ "Teacher transfers"
- ✅ "Teacher transfers in government schools under G.O.Ms.No.45"

### Mistake 4: No Action Focus
- ❌ "What is the policy?"
- ✅ "What actions are required to implement the policy?"

### Mistake 5: Single-Layer Queries
- ❌ "List GOs"
- ✅ "List GOs with dates, key provisions, implementation status, and compliance requirements"

---

## Advanced Query Techniques

### Technique 1: Multi-Stage Queries

**Stage 1**: "Retrieve all GOs on teacher recruitment from 2023-2024"
**Stage 2**: "From these GOs, extract: eligibility criteria, selection process, timeline, and responsible bodies"
**Stage 3**: "Create compliance checklist for recruitment process"

### Technique 2: Constraint-Based Queries

"Answer using ONLY information from GOs issued after 01-01-2024. If information is missing, explicitly state what's not available."

### Technique 3: Comparative Analysis

"Compare implementation of [policy X] across 3 districts: Guntur, Krishna, Visakhapatnam. Highlight best practices and challenges."

### Technique 4: Scenario-Based Queries

"If a school wants to implement digital classrooms, what are the: (1) legal requirements, (2) budget needed, (3) approval process, (4) timeline, (5) compliance checks?"

---

## Query Templates

### Template 1: Policy Brief
"Prepare policy brief on [TOPIC] covering: background, current GOs, implementation status, gaps, and recommendations."

### Template 2: Implementation Guide
"Create implementation guide for [GO/POLICY] with: phases, timeline, responsibilities, resources, compliance checklist, monitoring."

### Template 3: Compliance Check
"Analyze compliance with [GO/ACT] including: requirements, current status, gaps, risks, and remediation plan."

### Template 4: Decision Memo
"Prepare decision memo on [DECISION] with: options analysis, pros/cons, cost-benefit, recommendation, and rationale."

### Template 5: Diagnostic
"Debug retrieval for [QUERY]: list documents retrieved, relevance scores, gaps, and recommendations for improvement."

---

## Success Criteria

A good query should:
1. ✅ Specify exact timeframe
2. ✅ Name specific department/scope
3. ✅ Request structured output format
4. ✅ Cite specific GOs/Acts when known
5. ✅ Ask for actionable information
6. ✅ Include success criteria or expected output

---

## Quick Reference

| Use Case | Query Pattern |
|----------|---------------|
| Recent updates | "[DEPT] GOs from [DATE] to [DATE] with [DETAILS]" |
| Implementation | "Implementation guide for [GO] with phases, timeline, resources" |
| Compliance | "Compliance check for [GO/ACT]: requirements, status, gaps, plan" |
| Comparison | "Compare [GO1] vs [GO2]: changes, implications, actions" |
| Decision | "Decision memo on [TOPIC]: options, analysis, recommendation" |
| Debug | "Debug retrieval: documents, relevance, gaps, recommendations" |

---

## Remember

**The system is only as good as your questions.**

Weak question = Weak answer
Strong question = Policy-grade answer

Use this guide to engineer questions that force the system to produce decision-ready outputs.
