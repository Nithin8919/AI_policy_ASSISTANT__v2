# Answer Builder - structured response + citations

"""
Answer Builder - Build structured answers with citations
Creates well-formatted responses with proper attribution
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Answer:
    """Structured answer with citations"""
    query: str
    summary: str
    sections: Dict[str, str] = field(default_factory=dict)
    citations: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)


class AnswerBuilder:
    """Build structured answers from retrieval results"""
    
    def __init__(self, use_llm: bool = True, api_key: Optional[str] = None):
        """
        Initialize answer builder
        
        Args:
            use_llm: Use Gemini for answer generation
            api_key: Gemini API key
        """
        self.use_llm = use_llm
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
    
    def build_answer(
        self,
        query: str,
        results: List[Dict],
        mode: str = "qa"
    ) -> Answer:
        """
        Build structured answer from results
        
        Args:
            query: User query
            results: Retrieved results
            mode: Query mode (qa, policy, framework, etc.)
            
        Returns:
            Structured Answer object
        """
        if self.use_llm and self.api_key:
            return self._build_with_llm(query, results, mode)
        else:
            return self._build_template(query, results, mode)
    
    def _build_with_llm(
        self,
        query: str,
        results: List[Dict],
        mode: str
    ) -> Answer:
        """Build answer using Gemini Flash"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-8b')
            
            # Prepare context from results
            context = self._prepare_context(results)
            
            # Build prompt based on mode
            prompt = self._build_prompt(query, context, mode)
            
            # Generate answer
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 1000,
                }
            )
            
            # Parse response
            answer_text = response.text
            
            # Extract summary and sections
            summary, sections = self._parse_llm_response(answer_text)
            
            # Build citations
            citations = self._build_citations(results)
            
            return Answer(
                query=query,
                summary=summary,
                sections=sections,
                citations=citations,
                confidence=0.85,  # LLM-generated
                metadata={'generated_by': 'gemini', 'mode': mode}
            )
            
        except Exception as e:
            print(f"LLM answer generation failed: {e}, using template")
            return self._build_template(query, results, mode)
    
    def _build_template(
        self,
        query: str,
        results: List[Dict],
        mode: str
    ) -> Answer:
        """Build answer using templates (no LLM)"""
        # Create summary from top results
        summary = self._create_summary(results[:3])
        
        # Group by category/vertical
        sections = self._group_by_category(results)
        
        # Build citations
        citations = self._build_citations(results)
        
        return Answer(
            query=query,
            summary=summary,
            sections=sections,
            citations=citations,
            confidence=0.70,  # Template-based
            metadata={'generated_by': 'template', 'mode': mode}
        )
    
    def _prepare_context(self, results: List[Dict]) -> str:
        """Prepare context from results for LLM"""
        context_parts = []
        
        for i, result in enumerate(results[:10], 1):
            content = result.get('content', '')
            vertical = result.get('vertical', 'unknown')
            context_parts.append(f"[{i}] [{vertical}] {content[:300]}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, mode: str) -> str:
        """Build LLM prompt based on mode"""
        if mode == "qa":
            return f"""Answer this question using the provided context. Be concise and accurate.

Question: {query}

Context:
{context}

Answer (2-3 paragraphs, cite sources with [1], [2], etc.):"""
        
        elif mode == "policy":
            return f"""Explain this policy using the provided context. Include key provisions, requirements, and implementation details.

Query: {query}

Context:
{context}

Policy Explanation (organized with sections, cite sources):"""
        
        elif mode == "framework":
            return f"""Design a comprehensive framework addressing: {query}

Use the provided context for guidelines and requirements.

Context:
{context}

Framework (structured with sections):"""
        
        else:
            return f"""Provide a detailed response to: {query}

Context:
{context}

Response:"""
    
    def _parse_llm_response(self, text: str) -> tuple[str, Dict[str, str]]:
        """Parse LLM response into summary and sections"""
        lines = text.strip().split('\n')
        
        # First paragraph as summary
        summary_lines = []
        section_content = []
        in_summary = True
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_summary and summary_lines:
                    in_summary = False
                continue
            
            if in_summary:
                summary_lines.append(line)
            else:
                section_content.append(line)
        
        summary = ' '.join(summary_lines)
        
        # Parse sections (simple - can be enhanced)
        sections = {'main_content': ' '.join(section_content)} if section_content else {}
        
        return summary, sections
    
    def _create_summary(self, results: List[Dict]) -> str:
        """Create summary from top results"""
        if not results:
            return "No relevant information found."
        
        # Combine top 3 results
        summaries = []
        for result in results[:3]:
            content = result.get('content', '')
            # First sentence or 200 chars
            summary = content[:200] + "..." if len(content) > 200 else content
            summaries.append(summary)
        
        return " ".join(summaries)
    
    def _group_by_category(self, results: List[Dict]) -> Dict[str, str]:
        """Group results by category/vertical"""
        grouped = {}
        
        for result in results:
            vertical = result.get('vertical', 'general')
            content = result.get('content', '')
            
            if vertical not in grouped:
                grouped[vertical] = []
            
            grouped[vertical].append(content[:200])
        
        # Combine each group
        sections = {}
        for vertical, contents in grouped.items():
            sections[vertical] = " ".join(contents)
        
        return sections
    
    def _build_citations(self, results: List[Dict]) -> List[Dict]:
        """Build citation list from results"""
        citations = []
        
        for i, result in enumerate(results[:10], 1):
            citation = {
                'id': i,
                'doc_id': result.get('doc_id', result.get('chunk_id', 'unknown')),
                'vertical': result.get('vertical', 'unknown'),
                'source': result.get('metadata', {}).get('source', 'Unknown'),
                'relevance': result.get('score', 0.0)
            }
            
            # Add URL if from internet
            if 'url' in result:
                citation['url'] = result['url']
            
            citations.append(citation)
        
        return citations


# Convenience function
def build_answer(query: str, results: List[Dict], mode: str = "qa") -> Answer:
    """Quick answer building"""
    builder = AnswerBuilder()
    return builder.build_answer(query, results, mode)


if __name__ == "__main__":
    print("Answer Builder")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.answer_generation import AnswerBuilder

builder = AnswerBuilder(use_llm=True)

# Build answer from results
answer = builder.build_answer(
    query="What is RTE Section 12?",
    results=retrieved_results,
    mode="qa"
)

print(answer.summary)
for section, content in answer.sections.items():
    print(f"\\n{section}:")
    print(content)

print("\\nCitations:")
for citation in answer.citations:
    print(f"[{citation['id']}] {citation['source']}")
""")

