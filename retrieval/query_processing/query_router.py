# Chooses verticals by query

"""
Query Router
============
Determines which verticals to search based on query content.
Rule-based, fast, deterministic.
"""

import re
from typing import List, Dict, Tuple
from ..config.vertical_map import get_all_verticals, VERTICAL_METADATA


class QueryRouter:
    """Routes queries to appropriate verticals"""
    
    # Keywords that indicate each vertical
    VERTICAL_KEYWORDS = {
        "legal": [
            "act", "section", "article", "rule", "provision", "clause",
            "statute", "legislation", "amendment", "constitution",
            "legal", "law", "rights", "fundamental", "directive"
        ],
        "go": [
            "go", "government order", "notification", "circular",
            "memo", "office memorandum", "department", "directorate",
            "issued", "sanctioned", "approved", "g.o", "g.o.ms"
        ],
        "judicial": [
            "judgment", "case", "court", "petition", "writ",
            "high court", "supreme court", "tribunal", "bench",
            "petitioner", "respondent", "appeal", "ruling"
        ],
        "data": [
            "statistics", "data", "report", "survey", "study",
            "udise", "aser", "enrollment", "dropout", "metrics",
            "figures", "numbers", "percentage", "trend", "analysis"
        ],
        "schemes": [
            "scheme", "program", "initiative", "mission",
            "sarva shiksha abhiyan", "ssa", "rmsa", "pmshri",
            "midday meal", "scholarship", "international", "global"
        ]
    }
    
    def route(
        self,
        query: str,
        entities: Dict = None
    ) -> List[Tuple[str, float]]:
        """
        Route query to appropriate verticals with confidence scores.
        
        Args:
            query: Query text
            entities: Extracted entities (optional)
            
        Returns:
            List of (vertical, confidence) tuples, sorted by confidence
        """
        query_lower = query.lower()
        
        # Score each vertical
        scores = {}
        for vertical in get_all_verticals():
            scores[vertical] = self._score_vertical(query_lower, vertical, entities)
        
        # Sort by score
        sorted_verticals = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Filter to only include verticals with score > 0
        relevant_verticals = [
            (v, s) for v, s in sorted_verticals if s > 0
        ]
        
        # If no verticals matched, return all with equal low confidence
        if not relevant_verticals:
            return [(v, 0.2) for v in get_all_verticals()]
        
        return relevant_verticals
    
    def _score_vertical(
        self,
        query: str,
        vertical: str,
        entities: Dict = None
    ) -> float:
        """Score how relevant a vertical is to the query"""
        score = 0.0
        
        # Keyword matching
        keywords = self.VERTICAL_KEYWORDS.get(vertical, [])
        for keyword in keywords:
            if keyword in query:
                score += 1.0
        
        # Entity-based scoring
        if entities:
            if vertical == "legal":
                if "section" in entities or "article" in entities or "rule" in entities:
                    score += 2.0
                if "act_name" in entities:
                    score += 1.5
            
            elif vertical == "go":
                if "go_number" in entities:
                    score += 3.0  # Strong signal
            
            elif vertical == "judicial":
                if "case_number" in entities:
                    score += 3.0  # Strong signal
            
            elif vertical == "data" or vertical == "schemes":
                if "year" in entities:
                    score += 0.5
        
        # Normalize score
        if score > 0:
            score = min(score / 5.0, 1.0)  # Cap at 1.0
        
        return score
    
    def get_primary_vertical(
        self,
        query: str,
        entities: Dict = None
    ) -> str:
        """
        Get the single most relevant vertical.
        
        Args:
            query: Query text
            entities: Extracted entities
            
        Returns:
            Vertical name
        """
        routed = self.route(query, entities)
        if routed:
            return routed[0][0]
        return "legal"  # Default fallback
    
    def get_top_verticals(
        self,
        query: str,
        entities: Dict = None,
        top_k: int = 3,
        min_confidence: float = 0.1
    ) -> List[str]:
        """
        Get top K relevant verticals.
        
        Args:
            query: Query text
            entities: Extracted entities
            top_k: Number of verticals to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of vertical names
        """
        routed = self.route(query, entities)
        
        # Filter by confidence and take top K
        relevant = [
            v for v, conf in routed
            if conf >= min_confidence
        ][:top_k]
        
        return relevant if relevant else ["legal"]  # Default fallback


# Global router instance
_router_instance = None


def get_query_router() -> QueryRouter:
    """Get global query router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = QueryRouter()
    return _router_instance