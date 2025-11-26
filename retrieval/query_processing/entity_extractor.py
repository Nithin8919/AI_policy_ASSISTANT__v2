# Extract acts, sections, GOs etc.

"""
Entity Extractor
================
Extracts structured entities from queries using regex.
No spaCy, no LLM - just fast, deterministic patterns.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ExtractedEntity:
    """An extracted entity"""
    type: str
    value: str
    normalized: str
    start: int
    end: int


class EntityExtractor:
    """Extract entities using regex patterns"""
    
    # Entity patterns (compiled for speed)
    PATTERNS = {
        "section": [
            re.compile(r'\bsection\s+(\d+[A-Za-z]*(?:\(\d+\))?(?:\([a-z]\))?)', re.IGNORECASE),
            re.compile(r'\bsec\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE),
            re.compile(r'\bs\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE)
        ],
        "article": [
            re.compile(r'\barticle\s+(\d+[A-Za-z]*)', re.IGNORECASE),
            re.compile(r'\bart\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE)
        ],
        "rule": [
            re.compile(r'\brule\s+(\d+[A-Za-z]*(?:\(\d+\))?)', re.IGNORECASE),
            re.compile(r'\br\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE)
        ],
        "go_number": [
            re.compile(r'\bG\.?O\.?\s*(?:No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'\bGO\s*MS\s*No\.?\s*(\d+)', re.IGNORECASE),
            re.compile(r'\bNotification\s*No\.?\s*(\d+)', re.IGNORECASE)
        ],
        "year": [
            re.compile(r'\b(19\d{2}|20\d{2})\b'),
            re.compile(r'\b(\d{4})-(\d{2,4})\b')  # Year ranges like 2020-21
        ],
        "case_number": [
            re.compile(r'\bW\.?P\.?\s*No\.?\s*(\d+)\s*of\s*(\d{4})', re.IGNORECASE),
            re.compile(r'\bW\.?A\.?\s*No\.?\s*(\d+)\s*of\s*(\d{4})', re.IGNORECASE),
            re.compile(r'\bC\.?A\.?\s*No\.?\s*(\d+)\s*of\s*(\d{4})', re.IGNORECASE)
        ],
        "act_name": [
            re.compile(r'\b([A-Z][A-Za-z\s]+Act(?:,?\s*\d{4})?)', re.IGNORECASE),
            re.compile(r'\bRTE\s*Act\b', re.IGNORECASE),
            re.compile(r'\bRight\s*to\s*Education\s*Act\b', re.IGNORECASE)
        ]
    }
    
    def extract(self, query: str) -> Dict[str, List[ExtractedEntity]]:
        """
        Extract all entities from query.
        
        Args:
            query: Query text
            
        Returns:
            Dict mapping entity type to list of entities
        """
        entities = {}
        
        for entity_type, patterns in self.PATTERNS.items():
            entity_list = []
            
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entity = ExtractedEntity(
                        type=entity_type,
                        value=match.group(0),
                        normalized=self._normalize_entity(entity_type, match),
                        start=match.start(),
                        end=match.end()
                    )
                    entity_list.append(entity)
            
            if entity_list:
                entities[entity_type] = entity_list
        
        return entities
    
    def _normalize_entity(self, entity_type: str, match: re.Match) -> str:
        """Normalize extracted entity"""
        if entity_type in ["section", "article", "rule"]:
            # Extract just the number/identifier
            return match.group(1)
        
        elif entity_type == "go_number":
            # Normalize to GO number only
            return match.group(1)
        
        elif entity_type == "year":
            # Return year as-is
            if match.lastindex == 2:
                # Year range
                return f"{match.group(1)}-{match.group(2)}"
            else:
                return match.group(1)
        
        elif entity_type == "case_number":
            # Format: WP 123 of 2020
            return f"{match.group(1)}/{match.group(2)}"
        
        elif entity_type == "act_name":
            # Title case the act name
            return match.group(1).title()
        
        return match.group(0)
    
    def get_entity_values(
        self,
        entities: Dict[str, List[ExtractedEntity]],
        entity_type: str
    ) -> List[str]:
        """
        Get normalized values for an entity type.
        
        Args:
            entities: Extracted entities dict
            entity_type: Type to get
            
        Returns:
            List of normalized values
        """
        if entity_type not in entities:
            return []
        
        return [e.normalized for e in entities[entity_type]]
    
    def has_entity_type(
        self,
        entities: Dict[str, List[ExtractedEntity]],
        entity_type: str
    ) -> bool:
        """Check if entity type was found"""
        return entity_type in entities and len(entities[entity_type]) > 0
    
    def build_entity_string(
        self,
        entities: Dict[str, List[ExtractedEntity]]
    ) -> str:
        """
        Build a string representation of entities for query enhancement.
        
        Returns:
            String like "Section 12 GO 123 Year 2020"
        """
        parts = []
        
        for entity_type in ["section", "article", "rule", "go_number", "year"]:
            if entity_type in entities:
                values = [e.normalized for e in entities[entity_type]]
                type_label = entity_type.replace("_", " ").title()
                parts.append(f"{type_label} {', '.join(values)}")
        
        return " ".join(parts)


# Global extractor instance
_extractor_instance = None


def get_entity_extractor() -> EntityExtractor:
    """Get global entity extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = EntityExtractor()
    return _extractor_instance