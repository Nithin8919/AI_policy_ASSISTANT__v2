"""
Relation Extractor with LLM
Extracts document relationships: supersedes, amends, cites, implements
Uses Gemini for high accuracy on important documents
"""
import re
import json
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import google.generativeai as genai
from ..utils.llm_cache import get_cache

logger = logging.getLogger(__name__)


@dataclass
class Relation:
    """Represents a document relation"""
    relation_type: str  # supersedes, amends, cites, implements, governed_by
    source_id: str  # Source document/chunk ID
    target: str  # Target document identifier
    confidence: float
    context: str  # Surrounding text
    metadata: Dict = None


class RelationExtractor:
    """
    Extract document relations using hybrid approach:
    1. Fast regex patterns for clear cases
    2. LLM for complex/ambiguous cases
    """
    
    def __init__(self, use_llm: bool = True, gemini_api_key: str = ""):
        """
        Initialize relation extractor
        
        Args:
            use_llm: Whether to use LLM for complex cases
            gemini_api_key: Gemini API key
        """
        self.use_llm = use_llm
        
        # Initialize cache
        self.cache = get_cache()
        
        # Initialize Gemini if needed
        if self.use_llm and gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                self.model = genai.GenerativeModel('models/gemini-2.0-flash')
                logger.info("✅ Gemini initialized for relation extraction")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.use_llm = False
        else:
            self.use_llm = False
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for relation extraction"""
        
        # SUPERSEDES patterns
        self.supersedes_patterns = [
            re.compile(r'supersedes?\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in supersession of\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)\s+(?:is|are)\s+hereby\s+(?:rescinded|cancelled|superseded)', re.IGNORECASE)
        ]
        
        # AMENDS patterns
        self.amends_patterns = [
            re.compile(r'amends?\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in\s+(?:partial\s+)?amendment\s+(?:of|to)\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:Section|Rule)\s+(\d+)\s+(?:is|are)\s+(?:hereby\s+)?amended', re.IGNORECASE)
        ]
        
        # CITES patterns
        self.cites_patterns = [
            re.compile(r'(?:as per|under|in accordance with)\s+(?:Section|Rule)\s+(\d+)', re.IGNORECASE),
            re.compile(r'(?:Section|Rule)\s+(\d+)\s+(?:provides|states|mandates)', re.IGNORECASE),
            re.compile(r'in terms of\s+(?:Section|Rule)\s+(\d+)', re.IGNORECASE),
            re.compile(r'vide\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE)
        ]
        
        # IMPLEMENTS patterns
        self.implements_patterns = [
            re.compile(r'implement(?:s|ing|ation)?\s+(?:of\s+)?(?:the\s+)?([A-Z][A-Za-z\s,]+(?:Act|Rule|Policy|Scheme))', re.IGNORECASE),
            re.compile(r'in implementation of\s+(?:the\s+)?([A-Z][A-Za-z\s,]+(?:Act|Rule))', re.IGNORECASE),
            re.compile(r'gives effect to\s+(?:Section|Rule)\s+(\d+)', re.IGNORECASE)
        ]
        
        # GOVERNED_BY patterns
        self.governed_by_patterns = [
            re.compile(r'governed by\s+(?:the\s+)?([A-Z][A-Za-z\s,]+(?:Act|Rule))', re.IGNORECASE),
            re.compile(r'under\s+(?:the\s+)?([A-Z][A-Za-z\s,]+(?:Act|Rule))', re.IGNORECASE),
            re.compile(r'as per\s+(?:the\s+)?([A-Z][A-Za-z\s,]+(?:Act|Rule))', re.IGNORECASE)
        ]
    
    def extract_relations(
        self, 
        text: str, 
        doc_id: str, 
        doc_type: str,
        use_llm_fallback: bool = True
    ) -> List[Relation]:
        """
        Extract all relations from text
        
        Args:
            text: Document text
            doc_id: Document identifier
            doc_type: Document type (go, legal, judicial, etc.)
            use_llm_fallback: Whether to use LLM if regex finds nothing
            
        Returns:
            List of relations
        """
        relations = []
        
        # First try regex patterns (fast)
        relations.extend(self._extract_supersedes(text, doc_id))
        relations.extend(self._extract_amends(text, doc_id))
        relations.extend(self._extract_cites(text, doc_id))
        relations.extend(self._extract_implements(text, doc_id))
        relations.extend(self._extract_governed_by(text, doc_id))
        
        # If no relations found and LLM is available, try LLM
        if not relations and self.use_llm and use_llm_fallback:
            # Only use LLM for important document types
            if doc_type in ('go', 'legal', 'judicial'):
                logger.info(f"No regex relations found, trying LLM for {doc_id}")
                llm_relations = self._extract_with_llm(text, doc_id, doc_type)
                relations.extend(llm_relations)
        
        # Deduplicate
        relations = self._deduplicate_relations(relations)
        
        logger.info(f"Extracted {len(relations)} relations from {doc_id}")
        
        return relations
    
    def _extract_supersedes(self, text: str, doc_id: str) -> List[Relation]:
        """Extract supersedes relations"""
        relations = []
        
        for pattern in self.supersedes_patterns:
            for match in pattern.finditer(text):
                # Get context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Extract target
                target = f"G.O.MS.No.{match.group(1)}"
                
                relations.append(Relation(
                    relation_type="supersedes",
                    source_id=doc_id,
                    target=target,
                    confidence=0.95,
                    context=context
                ))
        
        return relations
    
    def _extract_amends(self, text: str, doc_id: str) -> List[Relation]:
        """Extract amends relations"""
        relations = []
        
        for pattern in self.amends_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Extract target
                if 'section' in match.group(0).lower() or 'rule' in match.group(0).lower():
                    target = f"Section {match.group(1)}"
                else:
                    target = f"G.O.MS.No.{match.group(1)}"
                
                relations.append(Relation(
                    relation_type="amends",
                    source_id=doc_id,
                    target=target,
                    confidence=0.90,
                    context=context
                ))
        
        return relations
    
    def _extract_cites(self, text: str, doc_id: str) -> List[Relation]:
        """Extract cites relations"""
        relations = []
        
        for pattern in self.cites_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Extract target
                target_text = match.group(1) if 'vide' not in match.group(0).lower() else f"G.O.MS.No.{match.group(1)}"
                if 'section' in match.group(0).lower():
                    target = f"Section {match.group(1)}"
                elif 'rule' in match.group(0).lower():
                    target = f"Rule {match.group(1)}"
                else:
                    target = target_text
                
                relations.append(Relation(
                    relation_type="cites",
                    source_id=doc_id,
                    target=target,
                    confidence=0.85,
                    context=context
                ))
        
        return relations
    
    def _extract_implements(self, text: str, doc_id: str) -> List[Relation]:
        """Extract implements relations"""
        relations = []
        
        for pattern in self.implements_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                target = match.group(1).strip()
                
                relations.append(Relation(
                    relation_type="implements",
                    source_id=doc_id,
                    target=target,
                    confidence=0.80,
                    context=context
                ))
        
        return relations
    
    def _extract_governed_by(self, text: str, doc_id: str) -> List[Relation]:
        """Extract governed_by relations"""
        relations = []
        
        for pattern in self.governed_by_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                target = match.group(1).strip()
                
                relations.append(Relation(
                    relation_type="governed_by",
                    source_id=doc_id,
                    target=target,
                    confidence=0.80,
                    context=context
                ))
        
        return relations
    
    def _extract_with_llm(
        self, 
        text: str, 
        doc_id: str, 
        doc_type: str
    ) -> List[Relation]:
        """
        Extract relations using LLM (Gemini)
        Only use for important documents where regex found nothing
        """
        if not self.use_llm:
            return []
        
        try:
            # Split text into candidate paragraphs for batch processing
            candidates = self._find_relation_candidates(text)
            
            if not candidates:
                return []
            
            # Check cache first
            candidates_text = "\\n".join(candidates)
            cache_key_content = f"{doc_id}|{candidates_text}"
            cached_result = self.cache.get(
                content=cache_key_content,
                model="gemini-2.0-flash",
                task_type="relation_extraction"
            )
            
            if cached_result:
                logger.debug(f"Using cached relation extraction for {doc_id}")
                # Convert cached relations back to Relation objects
                cached_relations = []
                for rel_data in cached_result["response"]:
                    cached_relations.append(Relation(
                        relation_type=rel_data["relation_type"],
                        source_id=rel_data["source_id"],
                        target=rel_data["target"],
                        confidence=rel_data["confidence"],
                        context=rel_data["context"],
                        metadata=rel_data.get("metadata")
                    ))
                return cached_relations
            
            # Build batch prompt with all candidates
            prompt = self._build_batch_llm_prompt(candidates, doc_type)
            
            # Single LLM call for all candidates
            response = self.model.generate_content(prompt)
            
            # Parse response
            relations = self._parse_llm_response(response.text, doc_id)
            
            # Cache the result
            relations_for_cache = [
                {
                    "relation_type": r.relation_type,
                    "source_id": r.source_id,
                    "target": r.target,
                    "confidence": r.confidence,
                    "context": r.context,
                    "metadata": r.metadata or {}
                }
                for r in relations
            ]
            
            self.cache.set(
                content=cache_key_content,
                response=relations_for_cache,
                model="gemini-2.0-flash",
                task_type="relation_extraction"
            )
            
            return relations
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
    def _find_relation_candidates(self, text: str) -> List[str]:
        """
        Find text segments that are likely to contain relations
        This allows us to batch process only relevant parts
        """
        candidates = []
        
        # Keywords that often appear in relation contexts
        relation_keywords = [
            'supersedes', 'amends', 'implements', 'governed by', 'under', 'vide',
            'in accordance with', 'as per', 'in terms of', 'G.O.MS', 'G.O.RT',
            'Procs.Rc.No', 'Govt.Memo', 'Section', 'Rule', 'Act,', 'dated'
        ]
        
        # Split text into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            # Check if sentence contains relation keywords
            if any(keyword.lower() in sentence.lower() for keyword in relation_keywords):
                # Include some context (previous and next sentence if available)
                candidates.append(sentence.strip())
        
        # Limit to avoid token limits (max 20 candidates)
        return candidates[:20]
    
    def _build_batch_llm_prompt(self, candidates: List[str], doc_type: str) -> str:
        """
        Build prompt for batch processing of relation candidates
        """
        candidates_text = "\n\n".join([f"SEGMENT {i+1}:\n{candidate}" for i, candidate in enumerate(candidates)])
        
        prompt = f"""You are an expert in Indian policy document relationships.

Analyze these {doc_type} document segments and extract ALL relationships to other documents.

Document segments:
{candidates_text}

Extract the following types of relationships:
1. SUPERSEDES - This document replaces/cancels another document
2. AMENDS - This document modifies another document
3. CITES - This document references another document as authority
4. IMPLEMENTS - This document implements a law/policy/scheme
5. GOVERNED_BY - This document is governed by a law/act

Return ONLY a JSON array in this EXACT format:
[
  {{
    "relation_type": "supersedes",
    "target": "G.O.MS.No.123",
    "confidence": 0.95,
    "context": "This order supersedes G.O.MS.No.123 dated 15.08.2023"
  }}
]

If NO relations found, return an empty array: []

Important:
- Extract specific document numbers (G.O.MS.No.XXX, Section XXX, Procs.Rc.No.XXX)
- Include brief context (max 100 characters)
- Confidence between 0.7-0.95

JSON only, no explanation:"""
        
        return prompt
    
    def _build_llm_prompt(self, text: str, doc_type: str) -> str:
        """Build prompt for LLM relation extraction (legacy - use batch version)"""
        
        # Truncate text if too long (Gemini has token limits)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""You are an expert in Indian policy document relationships.

Analyze this {doc_type} document and extract ALL relationships to other documents.

Document text:
{text}

Extract the following types of relationships:
1. SUPERSEDES - This document replaces/cancels another document
2. AMENDS - This document modifies another document
3. CITES - This document references another document as authority
4. IMPLEMENTS - This document implements a law/policy/scheme
5. GOVERNED_BY - This document is governed by a law/act

Return ONLY a JSON array in this EXACT format:
[
  {{
    "relation_type": "supersedes",
    "target": "G.O.MS.No.123",
    "confidence": 0.95,
    "context": "This order supersedes G.O.MS.No.123 dated 15.08.2023"
  }}
]

If NO relations found, return an empty array: []

Important:
- Extract specific document numbers (G.O.MS.No.XXX, Section XXX, Procs.Rc.No.XXX)
- Include brief context (max 100 characters)
- Confidence between 0.7-0.95

JSON only, no explanation:"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, doc_id: str) -> List[Relation]:
        """Parse LLM JSON response into Relation objects"""
        try:
            # Clean response (remove markdown if present)
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            if not isinstance(data, list):
                logger.error("LLM response is not a list")
                return []
            
            # Convert to Relation objects
            relations = []
            for item in data:
                try:
                    relation = Relation(
                        relation_type=item.get('relation_type', '').lower(),
                        source_id=doc_id,
                        target=item.get('target', ''),
                        confidence=float(item.get('confidence', 0.8)),
                        context=item.get('context', '')
                    )
                    
                    # Validate
                    if relation.relation_type and relation.target:
                        relations.append(relation)
                
                except Exception as e:
                    logger.warning(f"Skipping invalid relation: {e}")
                    continue
            
            return relations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return []
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """Remove duplicate relations"""
        seen = set()
        unique_relations = []
        
        for rel in relations:
            # Create key from relation type and target
            key = (rel.relation_type, rel.target.lower().strip())
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
        
        return unique_relations
    
    def relations_to_dict(self, relations: List[Relation]) -> List[Dict]:
        """Convert relations to dictionary format for JSON"""
        return [
            {
                "relation_type": r.relation_type,
                "source_id": r.source_id,
                "target": r.target,
                "confidence": r.confidence,
                "context": r.context,
                "metadata": r.metadata or {}
            }
            for r in relations
        ]