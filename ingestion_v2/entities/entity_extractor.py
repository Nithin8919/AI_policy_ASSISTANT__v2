"""
Entity Extractor
Smart entity extraction: regex for simple, LLM for complex
"""
import logging
from typing import Dict, List, Optional
from .patterns import EntityPatterns

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Smart entity extractor
    - Fast regex extraction for all documents
    - Optional LLM enhancement for important documents
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_enabled_verticals: Optional[set] = None
    ):
        """
        Initialize entity extractor
        
        Args:
            use_llm: Whether to use LLM enhancement
            llm_enabled_verticals: Verticals where LLM is enabled
        """
        self.use_llm = use_llm
        self.llm_enabled_verticals = llm_enabled_verticals or {"go", "legal", "judicial"}
        
        # Initialize pattern matcher
        self.patterns = EntityPatterns()
        
        # LLM extractor (lazy load)
        self._llm_extractor = None
        
        logger.info(f"Entity extractor initialized - LLM: {use_llm}")
    
    def extract(
        self, 
        text: str, 
        vertical: str,
        doc_id: str = ""
    ) -> Dict[str, List[str]]:
        """
        Extract entities from text
        
        Args:
            text: Text to extract from
            vertical: Document vertical
            doc_id: Document ID
            
        Returns:
            Dictionary of entity types and values
        """
        if not text or not text.strip():
            return {}
        
        # Always do regex extraction (fast and reliable)
        entities = self.patterns.extract_all(text)
        
        # Optionally enhance with LLM for important documents
        if self.use_llm and vertical in self.llm_enabled_verticals:
            if len(text) > 500:  # Only for substantial documents
                llm_entities = self._extract_with_llm(text, vertical, doc_id)
                entities = self._merge_entities(entities, llm_entities)
        
        # Clean up entities
        entities = self._clean_entities(entities)
        
        return entities
    
    def _extract_with_llm(
        self, 
        text: str, 
        vertical: str,
        doc_id: str
    ) -> Dict[str, List[str]]:
        """
        Extract entities using LLM
        This is expensive - only call for important documents
        """
        if self._llm_extractor is None:
            # Lazy load LLM extractor
            try:
                from .llm_entity_extractor import LLMEntityExtractor
                self._llm_extractor = LLMEntityExtractor()
            except Exception as e:
                logger.error(f"Failed to load LLM extractor: {e}")
                return {}
        
        try:
            return self._llm_extractor.extract(text, vertical, doc_id)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}
    
    def _merge_entities(
        self, 
        regex_entities: Dict[str, List[str]], 
        llm_entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Merge regex and LLM entities (LLM adds, doesn't replace)"""
        merged = regex_entities.copy()
        
        for entity_type, values in llm_entities.items():
            if entity_type in merged:
                # Add new values from LLM
                existing = set(merged[entity_type])
                for value in values:
                    if value not in existing:
                        merged[entity_type].append(value)
            else:
                merged[entity_type] = values
        
        return merged
    
    def _clean_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Clean up extracted entities
        Remove duplicates, empty values, etc.
        """
        cleaned = {}
        
        for entity_type, values in entities.items():
            # Remove duplicates while preserving order
            seen = set()
            unique_values = []
            for value in values:
                if value and value not in seen:
                    seen.add(value)
                    unique_values.append(value)
            
            # Only include if has values
            if unique_values:
                cleaned[entity_type] = unique_values
        
        return cleaned
    
    def extract_from_chunks(self, chunks: List[Dict], vertical: str) -> List[Dict]:
        """
        Extract entities from chunks
        
        Args:
            chunks: List of chunk dicts
            vertical: Document vertical
            
        Returns:
            Chunks with entities added
        """
        for chunk in chunks:
            content = chunk.get("content", "")
            doc_id = chunk.get("doc_id", "")
            
            if content:
                entities = self.extract(content, vertical, doc_id)
                chunk["entities"] = entities
        
        return chunks