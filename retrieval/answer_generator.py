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
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        
        logger.info("✅ Answer generator initialized")
    
    def generate(
        self,
        query: str,
        results: List[Dict],
        mode: str = "qa",
        max_context_chunks: int = 5
    ) -> Dict:
        """
        Generate answer with proper citations.
        
        Args:
            query: User query
            results: Retrieved results
            mode: Query mode
            max_context_chunks: Max chunks to include
            
        Returns:
            Dict with answer, citations, bibliography
        """
        if not results:
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
        prompt = self._build_prompt(query, context_text, mode)
        
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
        Format context with clear doc numbers.
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            payload = result.get("payload", {})
            text = payload.get("text", "")
            source = payload.get("source", "Unknown")
            vertical = result.get("vertical", "")
            
            context_parts.append(f"""
Doc {i}:
Source: {source} ({vertical})
Content: {text}
""")
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, mode: str) -> str:
        """
        Build prompt with EXPLICIT citation instructions.
        
        This is the CRITICAL FIX - makes citations non-negotiable.
        """
        if mode == "qa":
            return f"""You are a policy assistant providing precise answers from official documents.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. You MUST cite EVERY factual claim using [Doc X] format
2. Place citations IMMEDIATELY after each relevant sentence
3. Use square brackets: [Doc 1], [Doc 2], [Doc 3]
4. If info comes from multiple sources, cite all: [Doc 1][Doc 2]
5. NEVER make claims without citations
6. The Doc numbers correspond to "Doc #:" in the context below

GOOD EXAMPLE:
"Section 12 mandates free education for children aged 6-14. [Doc 1] The implementation is monitored by state authorities. [Doc 2]"

BAD EXAMPLE (DO NOT DO THIS):
"Section 12 mandates free education. Implementation is monitored by state authorities."

Context Documents:
{context}

Question: {query}

Provide a concise, accurate answer with mandatory citations after every claim:
"""
        
        elif mode == "deep_think":
            return f"""You are a policy analyst providing comprehensive analysis with legal citations.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. You MUST cite EVERY factual claim, legal provision, and policy reference using [Doc X] format
2. Place citations IMMEDIATELY after each sentence or claim
3. Use square brackets: [Doc 1], [Doc 2], [Doc 3]
4. If analyzing multiple sources, cite all relevant ones
5. NEVER make claims without citations
6. The Doc numbers correspond to "Doc #:" in the context below

Structure your analysis:
- Overview (with citations)
- Key provisions (with citations for each)
- Legal framework (with citations)
- Implications (with citations)
- Related policies (with citations)

Context Documents:
{context}

Question: {query}

Provide comprehensive policy analysis with mandatory citations:
"""
        
        else:  # brainstorm
            return f"""You are a creative policy advisor suggesting innovative approaches.

CRITICAL INSTRUCTIONS FOR CITATIONS (NON-NEGOTIABLE):

1. When referencing existing policies or examples, cite using [Doc X] format
2. Place citations after each reference to existing policy/practice
3. Clearly distinguish between:
   - Existing approaches (MUST be cited)
   - Your new suggestions (no citation needed)
4. Use square brackets: [Doc 1], [Doc 2]

Example:
"Current policy focuses on infrastructure. [Doc 1] However, we could also consider:
- Teacher training programs
- Community engagement initiatives"

Context Documents (existing approaches):
{context}

Question: {query}

Suggest innovative approaches, citing existing policies where relevant:
"""
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citation numbers from text.
        
        Returns:
            List of cited doc numbers (e.g., ["1", "2", "3"])
        """
        import re
        
        # Pattern: [Doc X] or [Doc X][Doc Y]
        pattern = r'\[Doc\s+(\d+)\]'
        matches = re.findall(pattern, text)
        
        return sorted(set(matches), key=lambda x: int(x))
    
    def _build_bibliography(self, results: List[Dict]) -> List[Dict]:
        """
        Build bibliography from results.
        
        Returns:
            List of bibliography entries
        """
        bibliography = []
        
        for i, result in enumerate(results, 1):
            payload = result.get("payload", {})
            
            entry = {
                "number": i,
                "source": payload.get("source", "Unknown Source"),
                "vertical": result.get("vertical", ""),
                "doc_type": payload.get("doc_type", ""),
                "year": payload.get("year", ""),
                "url": payload.get("url")
            }
            
            # Add vertical-specific fields
            if result.get("vertical") == "legal":
                entry["section"] = payload.get("section", "")
            elif result.get("vertical") == "go":
                entry["go_number"] = payload.get("go_number", "")
            elif result.get("vertical") == "judicial":
                entry["case_number"] = payload.get("case_number", "")
            
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