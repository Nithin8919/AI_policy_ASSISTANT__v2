# Mode-aware enhancement

"""
Query Enhancer
==============
Mode-aware query enhancement with synonym expansion and entity boosting.
Simple, deterministic, no LLM.
"""

from typing import Dict, List, Set
from ..config.mode_config import QueryMode
from .entity_extractor import get_entity_extractor


class QueryEnhancer:
    """Enhance queries based on mode"""
    
    # Domain-specific synonyms
    SYNONYMS = {
        # Education terms
        "teacher": ["teacher", "faculty", "educator", "instructor"],
        "student": ["student", "pupil", "learner"],
        "school": ["school", "institution", "educational institution"],
        "transfer": ["transfer", "posting", "shifting", "relocation"],
        "salary": ["salary", "pay", "remuneration", "wages"],
        "qualification": ["qualification", "eligibility", "credentials"],
        
        # Administrative terms
        "budget": ["budget", "finance", "allocation", "expenditure"],
        "policy": ["policy", "guideline", "directive", "framework"],
        "scheme": ["scheme", "program", "initiative", "project"],
        "department": ["department", "directorate", "ministry"],
        
        # Legal terms
        "provision": ["provision", "clause", "section", "article"],
        "mandate": ["mandate", "requirement", "obligation"],
        "amendment": ["amendment", "modification", "revision"],
        
        # Data terms
        "statistics": ["statistics", "data", "metrics", "figures"],
        "enrollment": ["enrollment", "admission", "intake"],
        "dropout": ["dropout", "attrition", "leaving"]
    }
    
    # Global context terms for brainstorm mode
    GLOBAL_TERMS = [
        "Finland", "Singapore", "South Korea", "Japan", "OECD",
        "UNESCO", "World Bank", "international", "global best practices",
        "comparative", "benchmarking", "innovation"
    ]
    
    def __init__(self):
        """Initialize enhancer"""
        self.entity_extractor = get_entity_extractor()
    
    def enhance(
        self,
        query: str,
        mode: QueryMode,
        expand_synonyms: bool = True,
        extract_entities: bool = True
    ) -> str:
        """
        Enhance query based on mode.
        
        Args:
            query: Original query
            mode: Query mode
            expand_synonyms: Whether to expand synonyms
            extract_entities: Whether to extract and boost entities
            
        Returns:
            Enhanced query string
        """
        enhanced_parts = [query]
        
        # Extract entities if enabled
        entities = {}
        if extract_entities:
            entities = self.entity_extractor.extract(query)
            
            # Add entity string to boost these terms
            entity_str = self.entity_extractor.build_entity_string(entities)
            if entity_str:
                enhanced_parts.append(entity_str)
        
        # Expand synonyms if enabled
        if expand_synonyms:
            synonyms = self._get_synonyms(query)
            if synonyms:
                enhanced_parts.append(" ".join(synonyms))
        
        # Mode-specific enhancements
        if mode == QueryMode.BRAINSTORM:
            # Add global context terms
            enhanced_parts.append("global best practices international models")
        
        elif mode == QueryMode.DEEP_THINK:
            # Add policy analysis terms
            enhanced_parts.append("legal framework constitutional judicial administrative")
        
        # Combine all parts
        enhanced_query = " ".join(enhanced_parts)
        
        return enhanced_query
    
    def _get_synonyms(self, query: str) -> List[str]:
        """Get relevant synonyms for query terms"""
        query_lower = query.lower()
        synonyms = []
        
        for term, syn_list in self.SYNONYMS.items():
            if term in query_lower:
                # Add synonyms not already in query
                for syn in syn_list:
                    if syn.lower() not in query_lower:
                        synonyms.append(syn)
        
        return synonyms
    
    def build_filter_dict(
        self,
        entities: Dict
    ) -> Dict[str, List[str]]:
        """
        Build filter dictionary for Qdrant from extracted entities.
        
        Args:
            entities: Extracted entities
            
        Returns:
            Dict for Qdrant filters
        """
        filters = {}
        
        # Year filter
        years = self.entity_extractor.get_entity_values(entities, "year")
        if years:
            filters["year"] = years
        
        # GO number filter
        go_numbers = self.entity_extractor.get_entity_values(entities, "go_number")
        if go_numbers:
            filters["go_number"] = go_numbers
        
        # Section filter
        sections = self.entity_extractor.get_entity_values(entities, "section")
        if sections:
            filters["section_number"] = sections
        
        return filters


# Global enhancer instance
_enhancer_instance = None


def get_query_enhancer() -> QueryEnhancer:
    """Get global query enhancer instance"""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = QueryEnhancer()
    return _enhancer_instance