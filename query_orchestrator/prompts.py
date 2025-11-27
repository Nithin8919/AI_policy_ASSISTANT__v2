"""
Prompt Templates
================
Templates for combining local RAG, internet, and theory contexts.
Clear, structured, citation-friendly.
"""

from typing import List, Dict


def build_fusion_prompt(
    query: str,
    local_results: List[Dict],
    internet_results: List[Dict] = None,
    theory_results: List[Dict] = None,
    mode: str = "qa"
) -> str:
    """
    Build prompt that fuses multiple context sources.
    
    Args:
        query: User query
        local_results: Results from local RAG
        internet_results: Results from internet (optional)
        theory_results: Results from theory corpus (optional)
        mode: Query mode
        
    Returns:
        Complete prompt with all contexts
    """
    
    # Start with system instructions
    prompt = _get_system_instructions(mode)
    
    # Add local context (ALWAYS PRIORITY)
    if local_results:
        prompt += "\n\n" + _format_local_context(local_results)
    
    # Add internet context (if available)
    if internet_results:
        prompt += "\n\n" + _format_internet_context(internet_results)
    
    # Add theory context (if available)
    if theory_results:
        prompt += "\n\n" + _format_theory_context(theory_results)
    
    # Add source priority rules
    prompt += "\n\n" + _get_source_priority_rules()
    
    # Add the actual query
    prompt += f"\n\n**USER QUERY:**\n{query}\n\n"
    
    # Add mode-specific instructions
    prompt += _get_mode_instructions(mode)
    
    return prompt


def _get_system_instructions(mode: str) -> str:
    """System-level instructions"""
    
    return """You are an expert policy assistant for Andhra Pradesh education policy.

Your job is to provide accurate, well-cited answers using the context provided below.

CRITICAL RULES:
1. **Always cite your sources** - Use [1], [2], [3] format
2. **Prioritize local context** - AP policy documents are most authoritative
3. **Use internet only for recent/external info** - When local context is missing
4. **Be precise** - Quote exact sections, article numbers, dates
5. **Admit uncertainty** - Say "not found in available documents" if needed
"""


def _format_local_context(results: List[Dict]) -> str:
    """Format local RAG results"""
    
    context = "=== LOCAL CONTEXT (AP Policy Documents) ===\n"
    context += "These are the MOST AUTHORITATIVE sources. Prioritize these.\n\n"
    
    for i, result in enumerate(results, 1):
        text = result.get("text", "")
        metadata = result.get("metadata", {})
        
        source = metadata.get("document_name", "Unknown")
        vertical = metadata.get("vertical", "policy")
        
        context += f"[{i}] Source: {source} ({vertical})\n"
        context += f"{text}\n\n"
    
    return context


def _format_internet_context(results: List[Dict]) -> str:
    """Format internet search results"""
    
    if not results:
        return ""
    
    context = "=== INTERNET CONTEXT (External Sources) ===\n"
    context += "Use these for recent updates or external comparisons.\n\n"
    
    # Determine starting index (after local results)
    start_idx = 100  # Use [101], [102], etc for internet
    
    for i, result in enumerate(results, start_idx + 1):
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")
        domain = result.get("domain", "")
        
        context += f"[{i}] URL: {url}\n"
        context += f"Title: {title}\n"
        context += f"Domain: {domain}\n"
        context += f"{content}\n\n"
    
    return context


def _format_theory_context(results: List[Dict]) -> str:
    """Format theory corpus results"""
    
    if not results:
        return ""
    
    context = "=== THEORY CONTEXT (Educational Foundations) ===\n"
    context += "Use these for pedagogical insights and global best practices.\n\n"
    
    # Use [201], [202], etc for theory
    start_idx = 200
    
    for i, result in enumerate(results, start_idx + 1):
        text = result.get("text", "")
        metadata = result.get("metadata", {})
        
        title = metadata.get("title", "Theory")
        author = metadata.get("author", "")
        
        context += f"[{i}] Theory: {title}"
        if author:
            context += f" (by {author})"
        context += f"\n{text}\n\n"
    
    return context


def _get_source_priority_rules() -> str:
    """Source priority instructions"""
    
    return """=== SOURCE PRIORITY RULES ===

1. **Local Context [1-99]**: HIGHEST PRIORITY
   - AP Government Orders, Legal Acts, Judicial decisions
   - Always check here first
   - Most authoritative for AP-specific questions

2. **Internet Context [101-199]**: Use for recency/external info
   - Recent developments, current status
   - Other states/countries comparisons
   - Supplementary information

3. **Theory Context [201-299]**: Use for pedagogical insights
   - Educational theory and frameworks
   - Global best practices
   - Research-backed approaches

**CITATION FORMAT:**
- Single source: "According to the RTE Act [3]..."
- Multiple sources: "Multiple documents [1][2][5] confirm..."
- Internet source: "Recent reports [101] indicate..."
- Theory: "Educational research [201] suggests..."
"""


def _get_mode_instructions(mode: str) -> str:
    """Mode-specific instructions"""
    
    if mode == "qa":
        return """**RESPONSE STYLE (QA Mode):**
- Direct, concise answer (2-4 paragraphs)
- Cite specific sections/articles
- Focus on answering the exact question
"""
    
    elif mode == "deep_think":
        return """**RESPONSE STYLE (Deep Think Mode):**
- Comprehensive analysis (5-10 paragraphs)
- Cover multiple dimensions (legal, implementation, data)
- Cross-reference between sources
- Identify gaps or conflicts
"""
    
    elif mode == "brainstorm":
        return """**RESPONSE STYLE (Brainstorm Mode):**
- Creative, strategic thinking
- Combine local policies + global best practices
- Suggest improvements or alternatives
- Use theory to support recommendations
- Think beyond current constraints
"""
    
    return ""


def build_simple_prompt(query: str, context: str) -> str:
    """
    Simple prompt for backward compatibility.
    Used when only local RAG is available.
    """
    
    return f"""You are an expert policy assistant for Andhra Pradesh education.

**CONTEXT:**
{context}

**QUERY:**
{query}

**INSTRUCTIONS:**
Provide an accurate, well-cited answer using the context above.
Cite sources as [1], [2], etc.
"""