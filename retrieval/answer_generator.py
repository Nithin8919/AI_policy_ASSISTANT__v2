"""
Answer Generator - FIXED VERSION
=================================
Generates final answers with EXPLICIT citation instructions.

CRITICAL FIX: Strengthened prompts to ensure Gemini always generates citations.
"""

import logging
import os
from typing import List, Dict, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Generates final answers from retrieved context.
    Now with BATTLE-TESTED citation prompts!
    """
    
    def __init__(self):
        """Initialize answer generator"""
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        
        logger.info("✅ Answer generator initialized")
    
    def generate(
        self,
        query: str,
        results: List[Dict],
        mode: str = "qa",
        max_context_chunks: int = 5,
        external_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict:
        """
        Generate answer with proper citations.
        
        Args:
            query: User query
            results: Retrieved results
            mode: Query mode
            max_context_chunks: Max chunks to include
            external_context: Additional context (e.g. from uploaded files)
            conversation_history: Previous conversation turns for context
            
        Returns:
            Dict with answer, citations, bibliography
        """
        if not results and not external_context:
            return {
                "answer": "I couldn't find relevant information to answer your query.",
                "citations": [],
                "bibliography": [],
                "confidence": 0.0
            }
        
        # Limit context
        context_results = results[:max_context_chunks]
        
        # Format context with doc numbers
        context_text = self._format_context(context_results)
        
        # Build prompt based on mode
        prompt = self._build_prompt(query, context_text, mode, external_context, conversation_history)
        
        # Generate answer
        try:
            response = self.model.generate_content(prompt)
            answer_text = response.text
            
            # Extract citations
            citations = self._extract_citations(answer_text)
            
            # Build bibliography
            bibliography = self._build_bibliography(context_results)
            
            return {
                "answer": answer_text,
                "citations": citations,
                "bibliography": bibliography,
                "confidence": self._estimate_confidence(answer_text, citations)
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating answer: {e}")
            return {
                "answer": "I encountered an error while generating the answer.",
                "citations": [],
                "bibliography": [],
                "confidence": 0.0
            }
    
    def _format_context(self, results: List[Dict]) -> str:
        """
        Format context with clear doc numbers and GO NUMBERS EXPLICIT.
        
        CRITICAL FIX: Extract and prominently display GO numbers
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            # Get basic info
            text = result.get("text", "") or result.get("content", "")
            vertical = result.get("vertical", "")
            
            # Get metadata for GO numbers and source info
            metadata = result.get("metadata", {})
            
            # CRITICAL FIX: Extract GO number from multiple possible fields
            go_number = None
            possible_go_fields = ['go_number', 'go_num', 'go_id', 'doc_id', 'source', 'chunk_id']
            
            for field in possible_go_fields:
                value = metadata.get(field) or result.get(field)
                if value and isinstance(value, str):
                    # Check if this looks like a GO number
                    if any(pattern in value.lower() for pattern in ['ms', 'rt', 'go', '20']):
                        go_number = value
                        break
            
            # If still no GO number, try to extract from text
            if not go_number and text:
                import re
                go_matches = re.search(r'(?:G\.O\.?|GO)[\s\.]?(?:MS|RT)[\s\.]?No[\s\.]?(\d+)', text, re.IGNORECASE)
                if go_matches:
                    go_number = f"G.O.MS.No.{go_matches.group(1)}"
            
            # Get source for fallback
            source = metadata.get("source", go_number or result.get("chunk_id", "Unknown"))
            
            # CRITICAL: Format with GO number prominently displayed
            if go_number:
                doc_header = f"Doc {i}: {go_number}"
                if vertical:
                    doc_header += f" ({vertical})"
            else:
                doc_header = f"Doc {i}: {source}"
                if vertical:
                    doc_header += f" ({vertical})"
            
            # Add year if available
            year = metadata.get("year")
            if year:
                doc_header += f" - Year: {year}"
            
            context_parts.append(f"""
{doc_header}
Content: {text[:800]}{"..." if len(text) > 800 else ""}
""")
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, mode: str, external_context: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Build prompt with EXPLICIT citation instructions.
        
        This is the CRITICAL FIX - makes citations non-negotiable.
        """
        # Append external context if provided
        if external_context:
            context = f"""
{context}

---
ADDITIONAL CONTEXT FROM UPLOADED FILES:
{external_context}
---
"""
        
        # Format conversation history if provided
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            # Limit to last 5 turns (10 messages)
            recent_history = conversation_history[-10:]
            history_parts = []
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("CONVERSATION HISTORY (for context)")
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("")
            
            for msg in recent_history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    history_parts.append(f"User: {content}")
                elif role == 'assistant':
                    history_parts.append(f"Assistant: {content}")
                    history_parts.append("")  # Blank line after assistant response
            
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("")
            history_text = "\n".join(history_parts)

        if mode == "qa":
            return f"""You are a policy assistant providing precise answers from official documents.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. You MUST cite EVERY factual claim using bracketed numbers
2. Place citations IMMEDIATELY after each relevant sentence
3. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
4. If info comes from multiple sources, cite all: [1][2][3]
5. NEVER make claims without citations
6. The numbers correspond to "Doc #:" in the context below

SPECIAL INSTRUCTION FOR GOVERNMENT ORDERS:
7. When mentioning Government Orders, ALWAYS include the specific GO number from the document header
8. Format as: "G.O.MS.No.XXX" or the exact format shown in the document
9. Include the year when available

GOOD EXAMPLE:
"Recent Government Orders include G.O.MS.No.190 (2022) regarding teacher transfers [1] and G.O.MS.No.155 (2022) on educational policies [2]."

BAD EXAMPLE (DO NOT DO THIS):
"Recent government orders include various policies on education."

{history_text}

Context Documents:
{context}

Question: {query}

Provide a concise, accurate answer with mandatory bracketed citations and specific GO numbers:
"""
        
        elif mode == "deep_think":
            return f"""You are a policy analyst providing comprehensive analysis with legal citations.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. You MUST cite EVERY factual claim, legal provision, and policy reference using bracketed numbers
2. Place citations IMMEDIATELY after each sentence or claim
3. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
4. If analyzing multiple sources, cite all relevant ones: [1][2][3]
5. NEVER make claims without citations
6. The numbers correspond to "Doc #:" in the context below

Structure your analysis:
- Overview (with bracketed citations)
- Key provisions (with bracketed citations for each)
- Legal framework (with bracketed citations)
- Implications (with bracketed citations)
- Related policies (with bracketed citations)

{history_text}

Context Documents:
{context}

Question: {query}

Provide comprehensive policy analysis with mandatory bracketed citations:
"""
        
        else:  # brainstorm
            return f"""You are a creative policy advisor suggesting innovative approaches.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. When referencing existing policies or examples, cite using bracketed numbers
2. Place citations after each reference to existing policy/practice
3. Clearly distinguish between:
   - Existing approaches (MUST be cited with bracketed numbers)
   - Your new suggestions (no citation needed)
4. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]

Example:
"Current policy focuses on infrastructure [1]. However, we could also consider:
- Teacher training programs
- Community engagement initiatives"

{history_text}

Context Documents (existing approaches):
{context}

Question: {query}

Suggest innovative approaches, citing existing policies with bracketed numbers where relevant:
"""
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citation numbers from text (bracketed format).
        
        Returns:
            List of cited doc numbers (e.g., ["1", "2", "3"])
        """
        import re
        
        # Pattern: [1] [2] [3] etc.
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        
        return sorted(set(matches), key=lambda x: int(x))
    
    def _build_bibliography(self, results: List[Dict]) -> List[Dict]:
        """
        Build bibliography from results.
        
        FIXED: Use correct result structure - data is directly on result, not in 'payload'
        
        Returns:
            List of bibliography entries
        """
        bibliography = []
        
        for i, result in enumerate(results, 1):
            # FIXED: Get metadata from correct location
            metadata = result.get("metadata", {})
            
            entry = {
                "number": i,
                "source": metadata.get("source", result.get("chunk_id", "Unknown Source")),
                "vertical": result.get("vertical", ""),
                "doc_type": metadata.get("doc_type", ""),
                "year": metadata.get("year", ""),
                "url": metadata.get("url")
            }
            
            # Add vertical-specific fields from metadata
            if result.get("vertical") == "legal":
                entry["section"] = metadata.get("section", "")
            elif result.get("vertical") == "go":
                entry["go_number"] = metadata.get("go_number", "")
            elif result.get("vertical") == "judicial":
                entry["case_number"] = metadata.get("case_number", "")
            
            bibliography.append(entry)
        
        return bibliography
    
    def _estimate_confidence(self, answer: str, citations: List[str]) -> float:
        """
        Estimate confidence based on answer quality.
        
        Returns:
            Confidence score 0-1
        """
        # Base confidence
        confidence = 0.5
        
        # Boost if has citations
        if citations:
            confidence += 0.3
        
        # Boost if answer is substantial
        if len(answer) > 200:
            confidence += 0.1
        
        # Boost if has multiple citations
        if len(citations) >= 3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    # Backward compatibility aliases
    def generate_qa_answer(self, query: str, results: List[Dict], max_tokens: int = 500) -> Dict:
        """Alias for QA mode generation (backward compatibility)"""
        return self.generate(query, results, "qa", max_context_chunks=5)
    
    def generate_deep_think_answer(self, query: str, results: List[Dict], max_tokens: int = 3000) -> Dict:
        """Alias for Deep Think mode generation (backward compatibility)"""
        return self.generate(query, results, "deep_think", max_context_chunks=20)
    
    def generate_brainstorm_answer(self, query: str, results: List[Dict], max_tokens: int = 2000) -> Dict:
        """Alias for Brainstorm mode generation (backward compatibility)"""
        return self.generate(query, results, "brainstorm", max_context_chunks=15)


# Global instance
_generator_instance = None


def get_answer_generator() -> AnswerGenerator:
    """Get global answer generator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AnswerGenerator()
    return _generator_instance


# Export
__all__ = ["AnswerGenerator", "get_answer_generator"]