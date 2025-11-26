"""
Answer Generation Module
=========================
LLM-based final answer synthesis from retrieved documents.
This is where the MAIN LLM usage happens.

Mode-Specific Synthesis:
- QA Mode: Quick factual answer with citations (Claude Haiku)
- Deep Think Mode: Comprehensive policy analysis (Claude Sonnet)
- Brainstorm Mode: Creative synthesis with global ideas (Claude Sonnet)
"""

from typing import List, Dict, Optional
import json


class AnswerGenerator:
    """Generate final answers using LLM synthesis"""
    
    def __init__(self, llm_client=None):
        """
        Initialize answer generator.
        
        Args:
            llm_client: Anthropic client
        """
        self.llm_client = llm_client
        self._ensure_client()
    
    def _ensure_client(self):
        """Ensure LLM client is initialized"""
        if self.llm_client is None:
            try:
                import google.generativeai as genai
                import os
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    self.llm_client = genai
                    print("✅ Gemini API configured for answer generation")
                else:
                    raise ValueError("No Google API key found")
            except Exception as e:
                print(f"Warning: Could not initialize Gemini client: {e}")
                self.llm_client = None
    
    def generate_qa_answer(
        self,
        query: str,
        results: List[Dict],
        max_tokens: int = 500
    ) -> Dict:
        """
        Generate quick QA answer (1-2 paragraphs).
        
        Uses Claude Haiku for speed.
        
        Args:
            query: User query
            results: Top retrieved results
            max_tokens: Max response length
            
        Returns:
            Answer dict with text and citations
        """
        if not self.llm_client:
            return self._fallback_answer(query, results)
        
        context = self._prepare_context(results, max_results=5, max_length=300)
        
        prompt = f"""You are a policy information assistant. Answer the question concisely based on the provided documents.

Question: {query}

Relevant Documents:
{context}

Instructions:
1. Provide a direct, factual answer (1-2 paragraphs)
2. Cite sources using [Doc X] format
3. If information is not in documents, say so
4. Be precise and accurate

Answer:"""

        try:
            model = self.llm_client.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': max_tokens,
                    'temperature': 0.1,
                }
            )
            
            answer_text = response.text.strip()
            
            return {
                "answer": answer_text,
                "mode": "qa",
                "model": "gemini-2.0-flash",
                "sources_used": len(results),
                "citations": self._extract_citations(answer_text)
            }
            
        except Exception as e:
            print(f"Answer generation failed: {e}")
            return self._fallback_answer(query, results)
    
    def generate_deep_think_answer(
        self,
        query: str,
        results: List[Dict],
        max_tokens: int = 3000
    ) -> Dict:
        """
        Generate comprehensive Deep Think answer.
        
        Uses Claude Sonnet for quality analysis.
        Includes:
        - Legal framework
        - Current implementation (GOs)
        - Judicial constraints
        - Data insights
        - Scheme delivery
        - Policy recommendations
        
        Args:
            query: User query
            results: Top retrieved results
            max_tokens: Max response length
            
        Returns:
            Comprehensive answer with structured analysis
        """
        if not self.llm_client:
            return self._fallback_answer(query, results)
        
        # Organize results by vertical
        by_vertical = self._organize_by_vertical(results)
        context = self._prepare_structured_context(by_vertical)
        
        prompt = f"""You are a senior policy analyst. Provide a comprehensive 360° analysis of this policy question.

Question: {query}

Retrieved Policy Documents (organized by type):
{context}

Provide a structured analysis covering:

1. **Legal Framework**
   - Constitutional provisions and Acts
   - Key sections and rules
   - Legal constraints and requirements

2. **Current Implementation**
   - Government orders and notifications
   - Administrative guidelines
   - Implementation status

3. **Judicial Guidance**
   - Relevant court judgments
   - Legal precedents
   - Binding directions

4. **Empirical Evidence**
   - Statistical data and trends
   - Performance metrics
   - Ground realities

5. **Delivery Mechanisms**
   - Current schemes and programs
   - International best practices
   - Successful models

6. **Key Insights & Recommendations**
   - Main findings
   - Policy gaps
   - Actionable recommendations

Use [Doc X] citations for all claims. Be comprehensive but clear.

Analysis:"""

        try:
            model = self.llm_client.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': max_tokens,
                    'temperature': 0.2,
                }
            )
            
            answer_text = response.text.strip()
            
            return {
                "answer": answer_text,
                "mode": "deep_think",
                "model": "gemini-2.0-flash",
                "sources_used": len(results),
                "verticals_covered": list(by_vertical.keys()),
                "citations": self._extract_citations(answer_text),
                "structure": "comprehensive_analysis"
            }
            
        except Exception as e:
            print(f"Deep Think answer generation failed: {e}")
            return self._fallback_answer(query, results)
    
    def generate_brainstorm_answer(
        self,
        query: str,
        results: List[Dict],
        max_tokens: int = 2000
    ) -> Dict:
        """
        Generate creative Brainstorm answer.
        
        Uses Claude Sonnet for creative synthesis.
        Focuses on:
        - Innovative ideas
        - Global best practices
        - Creative solutions
        - Out-of-box thinking
        
        Args:
            query: User query
            results: Top retrieved results
            max_tokens: Max response length
            
        Returns:
            Creative answer with diverse ideas
        """
        if not self.llm_client:
            return self._fallback_answer(query, results)
        
        context = self._prepare_context(results, max_results=15, max_length=250)
        
        prompt = f"""You are a creative policy innovation consultant. Brainstorm innovative solutions based on global best practices.

Challenge: {query}

Relevant Resources (schemes, international models, data):
{context}

Provide:

1. **Innovative Ideas** (3-4 creative approaches)
   - Fresh perspectives
   - Technology integration
   - Novel implementations

2. **Global Best Practices** (3-4 successful models)
   - International examples
   - What made them work
   - Adaptation potential for India

3. **Quick Wins** (2-3 immediate actions)
   - Low-hanging fruits
   - Pilot opportunities
   - Fast-track solutions

4. **Long-term Vision** (1-2 transformative ideas)
   - Systemic changes
   - Paradigm shifts
   - Future-ready approaches

Be creative, practical, and cite sources [Doc X]. Think beyond conventional solutions.

Ideas:"""

        try:
            model = self.llm_client.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': max_tokens,
                    'temperature': 0.7,  # Higher temperature for creativity
                }
            )
            
            answer_text = response.text.strip()
            
            return {
                "answer": answer_text,
                "mode": "brainstorm",
                "model": "gemini-2.0-flash",
                "sources_used": len(results),
                "citations": self._extract_citations(answer_text),
                "structure": "creative_synthesis"
            }
            
        except Exception as e:
            print(f"Brainstorm answer generation failed: {e}")
            return self._fallback_answer(query, results)
    
    def _prepare_context(
        self,
        results: List[Dict],
        max_results: int = 10,
        max_length: int = 300
    ) -> str:
        """Prepare context for LLM from results"""
        context_parts = []
        
        for i, result in enumerate(results[:max_results], 1):
            text = result.get("text", "")[:max_length]
            vertical = result.get("vertical", "unknown")
            metadata = result.get("metadata", {})
            
            # Add source information
            source_info = self._format_source_info(vertical, metadata)
            
            context_parts.append(
                f"[Doc {i}] ({vertical.upper()}{source_info})\n{text}..."
            )
        
        return "\n\n".join(context_parts)
    
    def _organize_by_vertical(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """Organize results by vertical"""
        by_vertical = {}
        
        for result in results:
            vertical = result.get("vertical", "unknown")
            if vertical not in by_vertical:
                by_vertical[vertical] = []
            by_vertical[vertical].append(result)
        
        return by_vertical
    
    def _prepare_structured_context(self, by_vertical: Dict[str, List[Dict]]) -> str:
        """Prepare structured context organized by vertical"""
        sections = []
        doc_counter = 1
        
        vertical_names = {
            "legal": "LEGAL DOCUMENTS (Acts, Rules, Sections)",
            "go": "GOVERNMENT ORDERS & NOTIFICATIONS",
            "judicial": "JUDICIAL PRECEDENTS (Court Judgments)",
            "data": "DATA & STATISTICS (UDISE, ASER, Reports)",
            "schemes": "SCHEMES & PROGRAMS (Indian & International)"
        }
        
        for vertical in ["legal", "go", "judicial", "data", "schemes"]:
            if vertical in by_vertical:
                sections.append(f"\n### {vertical_names.get(vertical, vertical.upper())}\n")
                
                for result in by_vertical[vertical]:
                    text = result.get("text", "")[:300]
                    metadata = result.get("metadata", {})
                    source_info = self._format_source_info(vertical, metadata)
                    
                    sections.append(
                        f"[Doc {doc_counter}]{source_info}\n{text}...\n"
                    )
                    doc_counter += 1
        
        return "\n".join(sections)
    
    def _format_source_info(self, vertical: str, metadata: Dict) -> str:
        """Format source information from metadata"""
        if vertical == "legal":
            act = metadata.get("act_name", "")
            section = metadata.get("section_number", "")
            if act and section:
                return f" {act}, Section {section}"
            elif act:
                return f" {act}"
        
        elif vertical == "go":
            go_num = metadata.get("go_number", "")
            year = metadata.get("year", "")
            if go_num:
                return f" GO {go_num}, {year}"
        
        elif vertical == "judicial":
            case = metadata.get("case_number", "")
            if case:
                return f" {case}"
        
        elif vertical == "data":
            source = metadata.get("source", "")
            year = metadata.get("year", "")
            if source and year:
                return f" {source} {year}"
        
        elif vertical == "schemes":
            scheme = metadata.get("scheme_name", "")
            country = metadata.get("country", "")
            if scheme:
                return f" {scheme}" + (f" ({country})" if country else "")
        
        return ""
    
    def _extract_citations(self, text: str) -> List[int]:
        """Extract document citations from answer text"""
        import re
        pattern = r'\[Doc (\d+)\]'
        matches = re.findall(pattern, text)
        return sorted(list(set(int(m) for m in matches)))
    
    def _fallback_answer(self, query: str, results: List[Dict]) -> Dict:
        """Fallback answer when LLM is not available"""
        if len(results) == 0:
            answer = f"No relevant documents found for: {query}"
        else:
            # Simple concatenation of top results
            texts = [r.get("text", "")[:200] for r in results[:3]]
            answer = "Top relevant excerpts:\n\n" + "\n\n".join(
                f"[{i+1}] {text}..." for i, text in enumerate(texts)
            )
        
        return {
            "answer": answer,
            "mode": "fallback",
            "model": "none",
            "sources_used": len(results),
            "citations": []
        }


# Global singleton
_answer_generator_instance = None


def get_answer_generator() -> AnswerGenerator:
    """Get global answer generator instance"""
    global _answer_generator_instance
    if _answer_generator_instance is None:
        _answer_generator_instance = AnswerGenerator()
    return _answer_generator_instance