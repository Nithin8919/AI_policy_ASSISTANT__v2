"""
Query Enhancer - FIXED VERSION with Domain Expansion
=====================================================
Enhances queries with synonyms, entity boosting, domain expansion, and builds filters.

NEW: Query expansion for education domain terms - fixes retrieval failures
for queries like "AI integration" → expands to "Atal Tinkering Labs", "ICT", etc.

CRITICAL FIX: Uses correct field names that match ingestion schema.
- sections (not section_number)
- go_number (not go_id)
- year (correct)
"""

import logging
import re
from typing import Dict, List, Set
from dataclasses import dataclass
from .entity_extractor import EntityExtractor, get_entity_extractor

logger = logging.getLogger(__name__)


@dataclass
class ExpansionResult:
    """Result of query expansion."""
    original_query: str
    expanded_query: str
    keywords_added: List[str]
    expansion_method: str
    confidence: float


class EducationDomainExpander:
    """
    Expands education-related queries with domain-specific keywords.
    
    Solves the semantic mismatch problem where users say "AI integration"
    but documents use "Atal Tinkering Lab", "ICT", "technology integration".
    """
    
    def __init__(self):
        """Initialize with education domain knowledge."""
        
        # AI/Technology synonyms
        self.AI_TECH_KEYWORDS = [
            'artificial intelligence', 'machine learning', 'AI', 'ML',
            'technology integration', 'digital education', 'ICT',
            'information technology', 'computer science', 'coding',
            'robotics', 'automation', 'STEM', 'STEAM',
            'innovation', 'tinkering', 'computational thinking'
        ]
        
        # Government programs (CRITICAL for AP education)
        self.AP_EDUCATION_PROGRAMS = [
            'Atal Tinkering Lab', 'ATL', 'Atal Innovation Mission',
            'NEP 2020', 'National Education Policy 2020',
            'Samagra Shiksha', 'Samagra Shiksha ICT',
            'Mana Badi Nadu-Nedu', 'Mana Badi infrastructure',
            'DIKSHA platform', 'DIKSHA digital platform',
            'PM eVIDYA', 'smart classroom', 'digital infrastructure'
        ]
        
        # Infrastructure terms
        self.INFRASTRUCTURE_KEYWORDS = [
            'smart classroom', 'digital infrastructure', 'ICT lab',
            'computer lab', 'technology lab', 'innovation lab',
            'digital learning tools', 'educational technology'
        ]
        
        # Expansion rules
        self.EXPANSION_RULES = {
            'ai_integration': {
                'triggers': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'technology integration', 'digital'],
                'add_keywords': self.AI_TECH_KEYWORDS + self.AP_EDUCATION_PROGRAMS,
                'weight': 1.0
            },
            'curriculum_change': {
                'triggers': ['syllabus', 'curriculum', 'course', 'change', 'integrate', 'integrating'],
                'add_keywords': ['curriculum framework', 'NEP 2020', 'educational standards'] + self.AP_EDUCATION_PROGRAMS,
                'weight': 1.0
            },
            'technology_education': {
                'triggers': ['coding', 'programming', 'computer', 'robotics', 'stem'],
                'add_keywords': self.INFRASTRUCTURE_KEYWORDS + self.AP_EDUCATION_PROGRAMS,
                'weight': 0.8
            }
        }
    
    def expand_query(self, query: str, mode: str = 'qa', max_keywords: int = 8) -> ExpansionResult:
        """
        Expand query with relevant domain keywords.
        
        Args:
            query: Original user query
            mode: Query mode (qa, deep_think, brainstorm)
            max_keywords: Maximum keywords to add
            
        Returns:
            ExpansionResult with expanded query
        """
        query_lower = query.lower()
        keywords_to_add: Set[str] = set()
        triggered_rules: List[str] = []
        
        # Check which expansion rules are triggered
        for rule_name, rule_config in self.EXPANSION_RULES.items():
            for trigger in rule_config['triggers']:
                if trigger in query_lower:
                    # Add keywords from this rule
                    for keyword in rule_config['add_keywords'][:max_keywords]:
                        keywords_to_add.add(keyword)
                    triggered_rules.append(rule_name)
                    break
        
        # Special case: AI curriculum integration (most common user issue)
        is_ai_curriculum = (
            any(kw in query_lower for kw in ['ai', 'technology', 'digital']) and
            any(kw in query_lower for kw in ['syllabus', 'curriculum', 'integrate', 'change'])
        )
        
        if is_ai_curriculum:
            # Add ALL critical programs for AI curriculum queries
            keywords_to_add.update([
                'Atal Tinkering Lab', 'ATL', 'Atal Innovation Mission',
                'NEP 2020', 'Samagra Shiksha ICT', 'DIKSHA platform',
                'technology integration', 'digital education', 'ICT'
            ])
            triggered_rules.append('ai_curriculum_special')
        
        # Build expanded query
        keywords_list = list(keywords_to_add)[:max_keywords]
        if keywords_list:
            expanded_query = query + " " + " ".join(keywords_list)
        else:
            expanded_query = query
        
        # Calculate confidence
        confidence = min(1.0, len(triggered_rules) * 0.4)
        
        result = ExpansionResult(
            original_query=query,
            expanded_query=expanded_query,
            keywords_added=keywords_list,
            expansion_method='domain_expansion',
            confidence=confidence
        )
        
        if keywords_list:
            logger.info(f"🔍 Domain Expansion: Added {len(keywords_list)} keywords")
        
        return result


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
        """Initialize enhancer with domain expander"""
        self.entity_extractor = get_entity_extractor()
        self.domain_expander = EducationDomainExpander()
    
    def enhance(
        self,
        query: str,
        entities: Dict,
        mode: str = "qa"
    ) -> str:
        """
        Enhance query with domain expansion, synonyms, and entity context.
        
        Args:
            query: Original query
            entities: Extracted entities
            mode: Query mode
            
        Returns:
            Enhanced query string
        """
        # STEP 1: Domain expansion (NEW - most important for education queries)
        expansion_result = self.domain_expander.expand_query(query, mode, max_keywords=8)
        enhanced = expansion_result.expanded_query
        
        # Log domain expansion
        if expansion_result.keywords_added:
            logger.info(f"🔍 Domain expansion added: {', '.join(expansion_result.keywords_added[:3])}...")
        
        # STEP 2: Add key synonyms (selective, not all)
        enhanced = self._add_synonyms(enhanced, max_additions=3)
        
        # STEP 3: Boost with entity context
        if entities:
            entity_string = self.entity_extractor.build_entity_string(entities)
            if entity_string:
                enhanced = f"{enhanced} {entity_string}"
        
        # STEP 4: Mode-specific enhancement
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
            returns = {"section": ["12"], "year": ["2020"]}
        """
        filters = {}
        
        # ✅ Section filter - CRITICAL FIX: use "section" (singular) to match actual data
        sections = self.entity_extractor.get_entity_values(entities, "section")
        if sections:
            filters["section"] = sections  # 🔧 FIXED: Use singular "section" not "sections"
        
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
__all__ = ["QueryEnhancer", "EducationDomainExpander", "ExpansionResult", "get_query_enhancer"]