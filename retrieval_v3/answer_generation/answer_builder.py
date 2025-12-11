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
            api_key: Ignored (We use OAuth/Vertex AI now)
        """
        self.use_llm = use_llm
        # REMOVED API Key logic - STRICTLY OAUTH
        self.use_oauth = True
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
    
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
        # Ensure we have what we need for LLM
        if self.use_llm:
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
        """Build answer using Gemini via Vertex AI (OAuth)"""
        try:
            model_name = 'gemini-2.5-flash'
            import google.auth
            from google import genai as genai_new
            
            # Get credentials with proper scopes
            service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_file and os.path.exists(service_account_file):
                from google.oauth2 import service_account
                scopes = ['https://www.googleapis.com/auth/cloud-platform']
                creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
                project_id = self.project_id
                if not project_id:
                    import json
                    with open(service_account_file, 'r') as f:
                        project_id = json.load(f).get('project_id')
            else:
                creds, computed_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                project_id = self.project_id or computed_project
            
            if not project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT_ID not found for Vertex AI")

            client = genai_new.Client(
                vertexai=True,
                project=project_id,
                location=self.location,
                credentials=creds,
            )
            model = client
            
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
            
            # Optimize generation config based on mode
            # QA: Lower temperature for accuracy, moderate tokens
            # Deep Think: Balanced for analysis, more tokens
            # Policy Draft: Creative but structured, maximum tokens
            mode_configs = {
                'qa': {
                    'temperature': 0.2,  # Lower for factual accuracy
                    'max_output_tokens': 2000,  # Increased for detailed answers
                    'top_p': 0.95,
                    'top_k': 40
                },
                'deep_think': {
                    'temperature': 0.4,  # Balanced for analysis
                    'max_output_tokens': 4000,  # More tokens for comprehensive analysis
                    'top_p': 0.95,
                    'top_k': 40
                },
                'policy_draft': {
                    'temperature': 0.5,  # Slightly higher for creativity
                    'max_output_tokens': 8192,  # Maximum for policy drafts
                    'top_p': 0.95,
                    'top_k': 40
                },
                'policy_brief': {
                    'temperature': 0.3,
                    'max_output_tokens': 3000,
                    'top_p': 0.95,
                    'top_k': 40
                },
                'brainstorm': {
                    'temperature': 0.6,  # Higher for creative ideas
                    'max_output_tokens': 3000,
                    'top_p': 0.95,
                    'top_k': 40
                }
            }
            
            # Get config for mode, default to QA if mode not found
            gen_config = mode_configs.get(mode, mode_configs['qa'])
            
            # Generate answer with optimized config
            response = model.models.generate_content(
                model=model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config=gen_config,
            )
            
            # Parse response
            answer_text = response.text
            print(f"DEBUG: Policy Draft Raw Response:\n{answer_text}\n-------------------")
            
            if mode == "policy_draft":
                # START: Simplified Logic
                # Pass raw text to frontend; frontend's safeParseJSON handles markdown/extraction.
                summary = answer_text
                sections = {}
                confidence = 0.95
                # END: Simplified Logic
            else:
                # Extract summary and sections for standard modes
                summary, sections = self._parse_llm_response(answer_text)
                confidence = 0.85
            
            # Build citations
            citations = self._build_citations(results)
            
            return Answer(
                query=query,
                summary=summary,
                sections=sections,
                citations=citations,
                confidence=confidence,
                metadata={'generated_by': 'gemini_vertex', 'mode': mode}
            )
            
        except Exception as e:
            print(f"LLM answer generation failed: {e}, using template")
            
            if mode == "policy_draft":
                # Return failure JSON for Policy Crafter
                import json
                error_response = {
                    "understanding": f"I encountered an error while generating the policy: {str(e)}",
                    "actions": []
                }
                return Answer(
                    query=query,
                    summary=json.dumps(error_response),
                    sections={},
                    citations=[],
                    confidence=0.0,
                    metadata={'generated_by': 'error_fallback', 'mode': mode}
                )
            
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
            'policy_draft': 'policy_draft',
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
            vertical = result.get('vertical', 'unknown')
            
            # Extract URL - check multiple locations
            url = (
                result.get('url') or 
                metadata.get('url') or 
                metadata.get('source_url') or
                None
            )
            
            # For internet results, prioritize title and URL
            if vertical == 'internet' and url:
                # Use title from metadata or construct from URL
                display_name = metadata.get('title') or metadata.get('source') or url
                # Make it clear it's a web source
                if not display_name.startswith('http'):
                    display_name = f"{display_name} (Web)"
            else:
                # Construct a user-friendly display name from available metadata
                display_name = self._construct_display_name(result, metadata)
            
            citation = {
                'id': i,
                'doc_id': result.get('doc_id', result.get('chunk_id', 'unknown')),
                'filename': display_name,  # User-friendly name
                'vertical': vertical,
                'source': metadata.get('source', 'Unknown'),
                'relevance': result.get('score', 0.0),
                'page': metadata.get('page_number') or metadata.get('page')  # Add page number if available
            }
            
            # Always add URL if available (critical for internet results)
            if url:
                citation['url'] = url
                # For internet results, make URL the primary identifier
                if vertical == 'internet':
                    citation['source'] = url
                    citation['filename'] = metadata.get('title', url)  # Prefer title over URL for display
            
            citations.append(citation)
        
        return citations
    
    def _construct_display_name(self, result: Dict, metadata: Dict) -> str:
        """Construct a user-friendly display name from available metadata"""
        
        # Priority 0: Internet results with URL (should be handled in _build_citations, but fallback here)
        vertical = result.get('vertical', '')
        if vertical == 'internet':
            url = result.get('url') or metadata.get('url')
            title = metadata.get('title')
            if title and url:
                return f"{title} ({url})"
            elif url:
                return url
            elif title:
                return title
        
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
    
    def _extract_json_from_text(self, text: str) -> str:
        """Extract valid JSON object from text, handling markdown"""
        text = text.strip()
        
        # Remove markdown code blocks
        if "```" in text:
            # Extract everything between first ``` and last ```
            import re
            # Match ```json or ``` followed by content until the closing ```
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
                
        # Try to find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end+1]
            
        return text  # Return original if all else fails

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

