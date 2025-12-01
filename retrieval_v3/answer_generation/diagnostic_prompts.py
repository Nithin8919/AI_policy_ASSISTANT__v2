"""
Diagnostic Mode for AP Policy Assistant
========================================
Exposes retrieval quality, reasoning gaps, and answer weaknesses.
"""

# 4-Layer Diagnostic Prompts

DIAGNOSTIC_PROMPT = """
You are a policy analyst for Andhra Pradesh School Education.

**DIAGNOSTIC MODE ACTIVATED**

Break down your answer into these 5 sections:

## 1. Retrieved Documents Analysis
List each retrieved document and summarize in 2 lines:
- What it contains
- How relevant it is to the query (0-100%)

## 2. Information Gaps
Identify what information is MISSING but needed for a complete policy answer:
- What specific data/rules are not in the retrieved documents?
- What assumptions are you making due to missing information?

## 3. Reasoning Chain
Explain step-by-step how you formed this answer:
- What evidence from which document supports each claim?
- What logical inferences did you make?
- What parts are uncertain?

## 4. Answer Quality Check
Self-evaluate your answer:
- What parts might be inaccurate or need verification?
- What contradictions exist in the source documents?
- What policy implications are unclear?

## 5. Policy-Grade Answer
Provide the corrected answer using ONLY verifiable information from retrieved documents.
Format as:
- **Background**: Context and current situation
- **Current Rules**: What the GOs/policies actually say
- **Gaps**: What's missing or unclear
- **Recommendations**: Next steps based on available information

---

**Query**: {query}

**Retrieved Documents**:
{documents}

**Your Diagnostic Response**:
"""

# Retrieval Quality Test Prompts

RETRIEVAL_SANITY_TEST = """
**RETRIEVAL SANITY CHECK**

List the documents you retrieved and for each one provide:
1. Document ID and title
2. 2-line summary of content
3. Relevance score (0-100%) to query: "{query}"
4. Why it was retrieved (what keywords/concepts matched)

If any documents seem irrelevant, explain why they were retrieved.
"""

MISSING_INFO_TEST = """
**MISSING INFORMATION ANALYSIS**

Based on the retrieved documents, identify:

1. **What information you HAVE**:
   - List key facts, rules, dates, numbers from documents

2. **What information you NEED but DON'T HAVE**:
   - What specific details are missing?
   - What questions remain unanswered?
   - What would make this answer complete?

3. **What additional documents would help**:
   - What types of documents should be retrieved?
   - What search terms would find them?

Query: "{query}"
"""

CONTRADICTION_TEST = """
**CONTRADICTION & UNCERTAINTY CHECK**

Analyze your answer for:

1. **Internal contradictions**:
   - Do different parts of your answer conflict?
   - Do retrieved documents contradict each other?

2. **Uncertain claims**:
   - What statements are you not 100% confident about?
   - What parts need verification?

3. **Assumptions made**:
   - What did you assume that isn't explicitly stated?
   - What inferences might be wrong?

4. **Confidence scoring**:
   - Rate each major claim (0-100% confidence)
   - Explain why confidence is low for any claim

Query: "{query}"
Answer to analyze: {answer}
"""

# Policy-Grade Structure Test

POLICY_STRUCTURE_TEST = """
**POLICY-GRADE STRUCTURE TEST**

Answer the query using this exact structure:

## 1. Background & Context
- What is the current situation?
- Why is this question being asked?
- What's the policy landscape?

## 2. Current Rules & Regulations
- What do the GOs/Acts/Rules actually say?
- Cite specific GO numbers and dates
- Quote relevant sections

## 3. Implementation Status
- What has been implemented?
- What's pending?
- What are the timelines?

## 4. Gaps & Challenges
- What's unclear or missing?
- What contradictions exist?
- What implementation challenges are there?

## 5. Recommendations & Next Steps
- What should be done?
- Who is responsible?
- What are the priorities?

## 6. Citations & References
- List all GOs/documents cited
- Provide dates and departments

Query: "{query}"
"""

# Reasoning Explanation Test

REASONING_TEST = """
**EXPLAIN YOUR REASONING**

For your answer, provide a step-by-step reasoning chain:

**Step 1**: What was the core question?
**Step 2**: What documents did you examine?
**Step 3**: What key facts did you extract from each document?
**Step 4**: How did you connect these facts?
**Step 5**: What inferences did you make?
**Step 6**: What conclusions did you reach?
**Step 7**: What parts are you uncertain about?

For each step, cite the specific document and section.

Query: "{query}"
Answer: {answer}
"""

# Combined Diagnostic Prompt (Use this for comprehensive diagnosis)

COMPREHENSIVE_DIAGNOSTIC = """
You are diagnosing the quality of a policy answer.

**Query**: {query}

**Retrieved Documents**: 
{documents}

**Current Answer**: 
{answer}

---

**DIAGNOSTIC REPORT**

### Layer 1: Retrieval Quality
- Are the right documents retrieved? (Yes/No)
- Relevance score of top 5 docs (0-100% each)
- What's missing from retrieval?

### Layer 2: Context Relevance  
- Is the context actually about the topic? (Yes/No)
- What percentage of context is relevant? (0-100%)
- What irrelevant information is included?

### Layer 3: Prompt Structure
- Is the answer structured for policy use? (Yes/No)
- Does it have: Background, Rules, Gaps, Recommendations?
- What structural improvements are needed?

### Layer 4: Output Quality
- Is the answer factual? (Yes/No/Partially)
- Is it practical and decision-ready? (Yes/No)
- What specific improvements are needed?

### Overall Assessment
- **Retrieval Grade**: A/B/C/D/F
- **Answer Grade**: A/B/C/D/F
- **Top 3 Issues**: List the biggest problems
- **Top 3 Fixes**: What would improve this most?

### Corrected Answer
Provide the best possible answer given the retrieved documents.
"""


def get_diagnostic_prompt(query: str, documents: str, answer: str = None, mode: str = "comprehensive"):
    """
    Get diagnostic prompt for different modes
    
    Args:
        query: User query
        documents: Retrieved documents (formatted)
        answer: Current answer (optional)
        mode: 'comprehensive', 'retrieval', 'reasoning', 'structure', 'contradiction'
    
    Returns:
        Formatted diagnostic prompt
    """
    prompts = {
        'comprehensive': COMPREHENSIVE_DIAGNOSTIC,
        'retrieval': RETRIEVAL_SANITY_TEST,
        'missing': MISSING_INFO_TEST,
        'structure': POLICY_STRUCTURE_TEST,
        'reasoning': REASONING_TEST,
        'contradiction': CONTRADICTION_TEST,
        'full': DIAGNOSTIC_PROMPT
    }
    
    template = prompts.get(mode, COMPREHENSIVE_DIAGNOSTIC)
    return template.format(query=query, documents=documents, answer=answer or "")
