"""
Query Router V1 - Basic Vertical Routing
=========================================
Simple keyword-based routing for backward compatibility.
"""

import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    V1 Query Router - Basic keyword-based vertical routing.
    Provides backward compatibility with existing code.
    """
    
    # Basic keyword mappings
    VERTICAL_KEYWORDS = {
        "legal": [
            "act", "law", "legislation", "section", "article", "provision",
            "clause", "rule", "regulation", "rte", "constitution"
        ],
        "go": [
            "go", "government order", "notification", "circular",
            "g.o", "order", "directive"
        ],
        "judicial": [
            "judgment", "court", "case", "writ", "petition",
            "supreme court", "high court", "judicial"
        ],
        "data": [
            "statistics", "data", "report", "survey", "udise",
            "enrollment", "dropout", "percentage", "ratio"
        ],
        "schemes": [
            "scheme", "program", "initiative", "project", "mission",
            "mana badi", "naadu nedu", "infrastructure"
        ]
    }
    
    def __init__(self):
        """Initialize router"""
        pass
    
    def route(self, query: str, entities: Dict) -> List[Tuple[str, float]]:
        """
        Route query to appropriate verticals (V1 interface).
        
        Args:
            query: User query
            entities: Extracted entities
            
        Returns:
            List of (vertical, confidence) tuples
        """
        query_lower = query.lower()
        matches = {}
        
        # Keyword-based routing
        for vertical, keywords in self.VERTICAL_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 0.3
            
            if score > 0:
                matches[vertical] = min(score, 1.0)
        
        # Entity-based routing
        if entities:
            if "section" in entities or "article" in entities:
                matches["legal"] = matches.get("legal", 0.0) + 0.5
            
            if "go_number" in entities:
                matches["go"] = matches.get("go", 0.0) + 0.5
            
            if "case_number" in entities:
                matches["judicial"] = matches.get("judicial", 0.0) + 0.5
        
        # Default fallback if no matches
        if not matches:
            matches = {"legal": 0.6, "go": 0.4}
        
        # Sort by confidence and return
        sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        
        logger.info(f"🎯 V1 Router: {len(sorted_matches)} verticals matched")
        return sorted_matches


# Global instance
_router_instance = None


def get_query_router() -> QueryRouter:
    """Get global query router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = QueryRouter()
        logger.info("✅ Query Router V1 initialized")
    return _router_instance


# Export
__all__ = ["QueryRouter", "get_query_router"]