"""
Query Enhancer - FIXED VERSION
===============================
Enhances queries with synonyms, entity boosting, and builds filters.

CRITICAL FIX: Uses correct field names that match ingestion schema.
- sections (not section_number)
- go_number (not go_id)
- year (correct)
"""

import logging
from typing import Dict, List
from .entity_extractor import EntityExtractor, get_entity_extractor

logger = logging.getLogger(__name__)


class QueryEnhancer:
    """
    Enhances queries for better retrieval.
    Keeps it simple - no LLM, just rule-based enhancement.
    """
    
    # Synonym mappings for domain terms
    SYNONYMS = {
        "teacher": ["educator", "faculty", "instructor"],
        "student": ["pupil", "learner"],
        "school": ["educational institution"],
        "education": ["learning", "schooling"],
        "policy": ["guideline", "directive", "order"],
        "transfer": ["posting", "relocation"],
        "salary": ["pay", "remuneration", "wages"],
        "leave": ["absence", "time off"],
        "promotion": ["advancement", "elevation"],
        "GO": ["government order", "notification"],
        "section": ["provision", "clause"],
        "act": ["legislation", "law"],
        "amendment": ["modification", "revision"]
    }
    
    def __init__(self):
        """Initialize enhancer"""
        self.entity_extractor = get_entity_extractor()
    
    def enhance(
        self,
        query: str,
        entities: Dict,
        mode: str = "qa"
    ) -> str:
        """
        Enhance query with synonyms and entity context.
        
        Args:
            query: Original query
            entities: Extracted entities
            mode: Query mode
            
        Returns:
            Enhanced query string
        """
        # Start with original query
        enhanced = query
        
        # Add key synonyms (selective, not all)
        enhanced = self._add_synonyms(enhanced, max_additions=3)
        
        # Boost with entity context
        if entities:
            entity_string = self.entity_extractor.build_entity_string(entities)
            if entity_string:
                enhanced = f"{enhanced} {entity_string}"
        
        # Mode-specific enhancement
        if mode == "deep_think":
            enhanced = f"{enhanced} policy implications legal framework"
        elif mode == "brainstorm":
            enhanced = f"{enhanced} innovative approaches solutions"
        
        return enhanced.strip()
    
    def _add_synonyms(self, query: str, max_additions: int = 3) -> str:
        """
        Add relevant synonyms to query.
        Selective - only add most relevant ones.
        """
        query_lower = query.lower()
        added = []
        
        for term, synonyms in self.SYNONYMS.items():
            if term.lower() in query_lower and len(added) < max_additions:
                # Add first synonym only (avoid bloat)
                added.append(synonyms[0])
        
        if added:
            return f"{query} {' '.join(added)}"
        return query
    
    def build_filter_dict(self, entities: Dict) -> Dict[str, List[str]]:
        """
        Build filter dictionary from entities.
        
        CRITICAL: Uses field names that MATCH the ingestion schema.
        
        Args:
            entities: Extracted entities
            
        Returns:
            Dict for Qdrant filters with CORRECT field names
            
        Example:
            entities = {"section": [Entity("12")], "year": [Entity("2020")]}
            returns = {"sections": ["12"], "year": ["2020"]}
        """
        filters = {}
        
        # ✅ Section filter - use "sections" (plural) to match ingestion
        sections = self.entity_extractor.get_entity_values(entities, "section")
        if sections:
            filters["sections"] = sections  # ✅ CORRECT FIELD NAME
        
        # ✅ Year filter - use "year" (matches ingestion)
        years = self.entity_extractor.get_entity_values(entities, "year")
        if years:
            # Convert to integers for proper filtering
            filters["year"] = [int(y) for y in years if y.isdigit()]
        
        # ✅ GO number filter - use "go_number" (matches ingestion)
        go_numbers = self.entity_extractor.get_entity_values(entities, "go_number")
        if go_numbers:
            filters["go_number"] = go_numbers  # ✅ CORRECT FIELD NAME
        
        # ✅ Case number filter - use "case_number" (matches ingestion)
        case_numbers = self.entity_extractor.get_entity_values(entities, "case_number")
        if case_numbers:
            filters["case_number"] = case_numbers
        
        # ✅ Act name filter - use "act_name" (matches ingestion)
        act_names = self.entity_extractor.get_entity_values(entities, "act_name")
        if act_names:
            filters["act_name"] = act_names
        
        logger.debug(f"Built filters: {filters}")
        return filters


# Global enhancer instance
_enhancer_instance = None


def get_query_enhancer() -> QueryEnhancer:
    """Get global query enhancer instance"""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = QueryEnhancer()
        logger.info("✅ Query enhancer initialized")
    return _enhancer_instance


# Export
__all__ = ["QueryEnhancer", "get_query_enhancer"]