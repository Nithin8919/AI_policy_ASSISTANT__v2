# Answer Builder - structured response + citations

"""
Answer Builder - Build structured answers with citations
Creates well-formatted responses with proper attribution
"""

import os
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Import prompt templates
try:
    from .prompt_templates import get_prompt_template, format_documents_with_metadata, format_conversation_history
except ImportError:
    # Fallback if running standalone
    from prompt_templates import get_prompt_template, format_documents_with_metadata, format_conversation_history


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
        # Prefer explicit arg, then GEMINI_API_KEY, then GOOGLE_API_KEY (used elsewhere in the project)
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    
    def build_answer(
        self,
        query: str,
        results: List[Dict],
        mode: str = "qa",
        external_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Answer:
        """
        Build structured answer from results
        
        Args:
            query: User query
            results: Retrieved results
            mode: Query mode (qa, policy, framework, etc.)
            external_context: Additional context (e.g. from uploaded files)
            conversation_history: Previous conversation turns for context
            
        Returns:
            Structured Answer object
        """
        if self.use_llm and self.api_key:
            return self._build_with_llm(query, results, mode, external_context, conversation_history)
        else:
            return self._build_template(query, results, mode)
    
    def _build_with_llm(
        self,
        query: str,
        results: List[Dict],
        mode: str,
        external_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Answer:
        """Build answer using Gemini Flash"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            # Use standard Gemini Flash model (v1beta-compatible)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            # Prepare context from results
            context = self._prepare_context(results)
            
            # Append external context if provided
            if external_context:
                context = f"""
{context}

---
ADDITIONAL CONTEXT FROM UPLOADED FILES:
{external_context}
---
"""
            
            # Build prompt based on mode
            prompt = self._build_prompt(query, context, mode, conversation_history)
            
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
        """Prepare context from results for LLM with enriched metadata"""
        # Enrich results with formatted metadata
        enriched_results = self._enrich_results_metadata(results[:10])
        
        # Use template formatter
        return format_documents_with_metadata(enriched_results)
    
    def _enrich_results_metadata(self, results: List[Dict]) -> List[Dict]:
        """Enrich results with formatted metadata for answer generation"""
        enriched = []
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            
            enriched_result = {
                'doc_index': i,
                'content': result.get('content', ''),
                'doc_id': result.get('doc_id', result.get('chunk_id', 'unknown')),
                
                # Formatted metadata
                'go_number': metadata.get('go_number', ''),
                'date_formatted': self._format_date(metadata.get('date')),
                'year': metadata.get('year'),
                'department': metadata.get('department', ''),
                'document_type': metadata.get('document_type', 'GO'),
                
                # Recency flag
                'is_recent': self._is_recent_document(metadata.get('year')),
                
                # Relations summary
                'supersedes': self._extract_supersedes(metadata.get('relations', [])),
                'amended_by': self._extract_amendments(metadata.get('relations', [])),
            }
            
            enriched.append(enriched_result)
        
        return enriched
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date to DD-MM-YYYY"""
        if not date_str:
            return ''
        
        try:
            # Try various date formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.strftime('%d-%m-%Y')
                except ValueError:
                    continue
            return str(date_str)  # Return as-is if can't parse
        except:
            return str(date_str) if date_str else ''
    
    def _is_recent_document(self, year: Optional[int]) -> bool:
        """Check if document is recent (2024-2025)"""
        if not year:
            return False
        try:
            return int(year) >= 2024
        except:
            return False
    
    def _extract_supersedes(self, relations: List[Dict]) -> List[str]:
        """Extract superseded document references"""
        supersedes = []
        for rel in relations:
            if rel.get('relation_type') == 'supersedes' or rel.get('type') == 'supersedes':
                target = rel.get('target', '')
                if target:
                    supersedes.append(target)
        return supersedes
    
    def _extract_amendments(self, relations: List[Dict]) -> List[str]:
        """Extract amending document references"""
        amendments = []
        for rel in relations:
            if rel.get('relation_type') == 'amends' or rel.get('type') == 'amends':
                target = rel.get('target', '')
                if target:
                    amendments.append(target)
        return amendments
    
    def _build_prompt(self, query: str, context: str, mode: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Build LLM prompt based on mode using templates"""
        # Map mode aliases
        mode_map = {
            'qa': 'qa',
            'policy': 'deep_think',
            'framework': 'deep_think',
            'deep_think': 'deep_think',
            'brainstorm': 'brainstorm',
            'policy_brief': 'policy_brief',
        }
        
        template_mode = mode_map.get(mode.lower(), 'qa')
        template = get_prompt_template(template_mode)
        
        # Format conversation history
        formatted_history = format_conversation_history(conversation_history) if conversation_history else ""
        
        # Fill in template
        return template.format(
            query=query,
            documents_with_metadata=context,
            conversation_history=formatted_history
        )
    
    def _parse_llm_response(self, text: str) -> tuple[str, Dict[str, str]]:
        """Parse LLM response into summary and sections"""
        text = text.strip()
        lines = text.split('\n')
        
        summary = ""
        sections = {}
        
        # Check for structured format (Scenario 2)
        # Look for "1. **Direct Answer" pattern
        direct_answer_match = re.search(r"1\.\s*\*\*Direct Answer:?\*\*\s*(.*?)(?=\n\d+\.|\n\n|\Z)", text, re.DOTALL | re.IGNORECASE)
        
        if direct_answer_match:
            summary = direct_answer_match.group(1).strip()
            
            # For the rest of the content, we want everything AFTER the direct answer
            # Find where the direct answer ends
            end_pos = direct_answer_match.end()
            remaining_text = text[end_pos:].strip()
            
            if remaining_text:
                sections['detailed_analysis'] = remaining_text
        else:
            # Fallback to first paragraph as summary
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
            sections = {'main_content': '\n'.join(section_content)} if section_content else {}
            
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
            metadata = result.get('metadata', {})
            
            # Construct a user-friendly display name from available metadata
            display_name = self._construct_display_name(result, metadata)
            
            citation = {
                'id': i,
                'doc_id': result.get('doc_id', result.get('chunk_id', 'unknown')),
                'filename': display_name,  # User-friendly name
                'vertical': result.get('vertical', 'unknown'),
                'source': metadata.get('source', 'Unknown'),
                'relevance': result.get('score', 0.0),
                'page': metadata.get('page_number') or metadata.get('page')  # Add page number if available
            }
            
            # Add URL if from internet
            if 'url' in result:
                citation['url'] = result['url']
            elif 'url' in metadata:
                 citation['url'] = metadata['url']
            
            citations.append(citation)
        
        return citations
    
    def _construct_display_name(self, result: Dict, metadata: Dict) -> str:
        """Construct a user-friendly display name from available metadata"""
        
        # Priority 1: Check for explicit filename or title (for uploaded files or web results)
        if metadata.get('filename'):
            return metadata['filename']
        if metadata.get('file_name'):
            return metadata['file_name']
        if metadata.get('title'):
            return metadata['title']
        
        # Priority 2: Construct from GO metadata (for government orders)
        go_number = metadata.get('go_number')
        if go_number:
            parts = [f"GO {go_number}"]
            
            # Add department if available
            department = metadata.get('department')
            if department:
                # Shorten department name if too long
                dept_short = department[:20] + "..." if len(department) > 20 else department
                parts.append(dept_short)
            
            # Add year if available
            year = metadata.get('year')
            if year:
                parts.append(str(year))
            
            return " - ".join(parts)
        
        # Priority 3: Use doc_id if it looks meaningful (not a UUID)
        doc_id = result.get('doc_id', result.get('chunk_id', ''))
        if doc_id and not self._is_uuid(doc_id):
            return doc_id
        
        # Priority 4: Fallback to source or generic label
        source = metadata.get('source', 'Document')
        if source and source != 'Unknown':
            return source
        
        return f"Document {result.get('doc_id', 'Unknown')[:8]}"
    
    def _is_uuid(self, text: str) -> bool:
        """Check if text looks like a UUID"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, str(text).lower()))


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

