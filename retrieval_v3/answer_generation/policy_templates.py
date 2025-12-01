"""
Policy-Grade Answer Templates
==============================
Structured templates for different policy use cases.
"""

POLICY_BRIEF_TEMPLATE = """
You are a senior policy analyst for Andhra Pradesh School Education Department.

Prepare a POLICY BRIEF on: {query}

Use this structure:

# POLICY BRIEF: {title}

## EXECUTIVE SUMMARY (2-3 sentences)
- What is this about?
- What's the key decision/action needed?

## BACKGROUND & CONTEXT
- Current situation
- Why this matters now
- Historical context (if relevant)

## CURRENT POLICY FRAMEWORK
### Governing Documents
- List relevant GOs with dates
- Cite Acts/Rules

### Key Provisions
- What do the policies actually say?
- Quote specific sections

## IMPLEMENTATION STATUS
- What's been done
- What's pending
- Timeline

## GAPS & CHALLENGES
- What's unclear or missing
- Implementation obstacles
- Resource constraints

## RECOMMENDATIONS
1. **Immediate Actions** (0-3 months)
2. **Short-term** (3-6 months)
3. **Long-term** (6-12 months)

## RESPONSIBLE BODIES
- Who implements what
- Coordination needed

## CITATIONS
- Full list of GOs/documents referenced

---

**Retrieved Documents**:
{documents}

**Your Policy Brief**:
"""

IMPLEMENTATION_GUIDE_TEMPLATE = """
You are creating an IMPLEMENTATION GUIDE for: {query}

Structure your answer as:

# IMPLEMENTATION GUIDE: {title}

## OBJECTIVE
What needs to be implemented and why?

## LEGAL BASIS
- Governing GO/Act/Rule
- Date of issuance
- Issuing authority

## SCOPE & APPLICABILITY
- Who does this apply to?
- Geographic scope
- Effective dates

## STEP-BY-STEP IMPLEMENTATION

### Phase 1: Preparation (Timeline)
1. Action item
   - Who: Responsible party
   - What: Specific task
   - When: Deadline
   - Resources: What's needed

### Phase 2: Execution (Timeline)
[Same structure]

### Phase 3: Monitoring (Timeline)
[Same structure]

## ROLES & RESPONSIBILITIES
| Role | Responsibility | Deliverable |
|------|---------------|-------------|
|      |               |             |

## RESOURCES REQUIRED
- Budget
- Personnel
- Infrastructure
- Training

## COMPLIANCE CHECKLIST
- [ ] Requirement 1
- [ ] Requirement 2

## MONITORING & REPORTING
- What to track
- Reporting frequency
- To whom

## ESCALATION PROCESS
- Issues to escalate
- To whom
- Timeline

## FAQS
Common questions and answers

---

**Retrieved Documents**:
{documents}

**Your Implementation Guide**:
"""

COMPLIANCE_CHECK_TEMPLATE = """
You are conducting a COMPLIANCE CHECK for: {query}

Structure:

# COMPLIANCE ANALYSIS: {title}

## REQUIREMENTS MATRIX

### Requirement 1: [From GO X]
- **What's Required**: Exact requirement
- **Current Status**: Compliant / Partially / Non-compliant
- **Evidence**: What shows compliance/non-compliance
- **Gap**: What's missing (if any)
- **Action Needed**: To achieve compliance

[Repeat for each requirement]

## COMPLIANCE SUMMARY
| Requirement | Status | Priority | Deadline |
|-------------|--------|----------|----------|
|             |        |          |          |

## HIGH-RISK GAPS
1. **Gap**: Description
   - **Impact**: What happens if not addressed
   - **Mitigation**: How to fix
   - **Timeline**: When to fix by

## COMPLIANCE ROADMAP
- **Immediate** (0-1 month): Critical gaps
- **Short-term** (1-3 months): Important gaps
- **Medium-term** (3-6 months): Standard gaps

## VERIFICATION PROCESS
- How to verify compliance
- Who verifies
- Documentation needed

---

**Retrieved Documents**:
{documents}

**Your Compliance Analysis**:
"""

DECISION_MEMO_TEMPLATE = """
You are preparing a DECISION MEMO for: {query}

Structure:

# DECISION MEMORANDUM

**TO**: [Decision Maker]
**FROM**: Policy Analysis Team
**DATE**: {date}
**RE**: {title}

## DECISION REQUIRED
[One sentence: What needs to be decided?]

## RECOMMENDATION
[One sentence: What do you recommend?]

## BACKGROUND
- Current situation (2-3 sentences)
- Why this decision is needed now

## OPTIONS ANALYSIS

### Option 1: [Name]
**Pros**:
- Benefit 1
- Benefit 2

**Cons**:
- Risk 1
- Risk 2

**Cost**: Estimate
**Timeline**: Duration
**Legal Basis**: GO/Act reference

### Option 2: [Name]
[Same structure]

### Option 3: Do Nothing
**Implications**: What happens if no action taken

## COMPARISON MATRIX
| Criteria | Option 1 | Option 2 | Option 3 |
|----------|----------|----------|----------|
| Cost     |          |          |          |
| Time     |          |          |          |
| Risk     |          |          |          |
| Impact   |          |          |          |

## RECOMMENDED OPTION
**Choice**: Option X

**Rationale**: 
- Why this is best
- What it achieves
- Why others are less suitable

## IMPLEMENTATION REQUIREMENTS
- Resources needed
- Timeline
- Responsible parties

## RISKS & MITIGATION
- Key risks
- How to mitigate

## NEXT STEPS
1. Immediate action
2. Follow-up action
3. Review point

---

**Retrieved Documents**:
{documents}

**Your Decision Memo**:
"""

# Template selector
def get_policy_template(mode: str, query: str, documents: str, **kwargs):
    """
    Get appropriate policy template
    
    Args:
        mode: 'brief', 'implementation', 'compliance', 'decision'
        query: User query
        documents: Retrieved documents
        **kwargs: Additional parameters (title, date, etc.)
    
    Returns:
        Formatted template
    """
    templates = {
        'brief': POLICY_BRIEF_TEMPLATE,
        'implementation': IMPLEMENTATION_GUIDE_TEMPLATE,
        'compliance': COMPLIANCE_CHECK_TEMPLATE,
        'decision': DECISION_MEMO_TEMPLATE
    }
    
    template = templates.get(mode, POLICY_BRIEF_TEMPLATE)
    
    return template.format(
        query=query,
        documents=documents,
        title=kwargs.get('title', query),
        date=kwargs.get('date', 'Today')
    )
