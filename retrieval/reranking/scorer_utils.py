# Scoring functions

"""
Scorer Utilities
================
Scoring functions for reranking.
Fast, deterministic, no LLM.
"""

import re
from typing import Dict, List
from datetime import datetime


def compute_recency_score(year: int, current_year: int = 2024) -> float:
    """
    Compute recency score based on document year.
    
    Args:
        year: Document year
        current_year: Current year
        
    Returns:
        Score from 0 to 1 (more recent = higher)
    """
    if year >= current_year:
        return 1.0
    
    age = current_year - year
    
    if age <= 1:
        return 1.0
    elif age <= 3:
        return 0.9
    elif age <= 5:
        return 0.8
    elif age <= 10:
        return 0.6
    else:
        return 0.3


def compute_term_overlap_score(query: str, text: str) -> float:
    """
    Compute term overlap between query and text.
    
    Args:
        query: Query string
        text: Document text
        
    Returns:
        Score from 0 to 1
    """
    if not query or not text:
        return 0.0
    
    # Tokenize
    query_terms = set(re.findall(r'\b\w+\b', query.lower()))
    text_terms = set(re.findall(r'\b\w+\b', text.lower()))
    
    if not query_terms:
        return 0.0
    
    # Jaccard similarity
    intersection = len(query_terms & text_terms)
    union = len(query_terms | text_terms)
    
    return intersection / union if union > 0 else 0.0


def compute_metadata_relevance_score(payload: Dict, filters: Dict) -> float:
    """
    Score how well metadata matches filters.
    
    Args:
        payload: Result payload
        filters: Query filters
        
    Returns:
        Score from 0 to 1
    """
    if not filters:
        return 0.5  # Neutral score
    
    matches = 0
    total_filters = 0
    
    for key, values in filters.items():
        total_filters += 1
        payload_value = payload.get(key)
        
        if payload_value and str(payload_value) in [str(v) for v in values]:
            matches += 1
    
    return matches / total_filters if total_filters > 0 else 0.5


def compute_position_score(position: int, total: int) -> float:
    """
    Score based on position in original results.
    Earlier = better.
    
    Args:
        position: Position (0-indexed)
        total: Total results
        
    Returns:
        Score from 0 to 1
    """
    if total <= 1:
        return 1.0
    
    return 1.0 - (position / total)


def extract_year_from_payload(payload: Dict) -> int:
    """
    Extract year from payload (multiple possible fields).
    
    Args:
        payload: Result payload
        
    Returns:
        Year as integer, or 2000 if not found
    """
    # Try different year fields
    year_fields = ["year", "document_year", "notification_year", "judgment_year"]
    
    for field in year_fields:
        if field in payload:
            try:
                year_value = payload[field]
                if isinstance(year_value, int):
                    return year_value
                elif isinstance(year_value, str):
                    # Extract year from string
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_value)
                    if year_match:
                        return int(year_match.group(1))
            except (ValueError, TypeError):
                continue
    
    return 2000  # Default fallback


def compute_authority_score(payload: Dict, vertical: str) -> float:
    """
    Score based on document authority level.
    
    Args:
        payload: Result payload
        vertical: Vertical name
        
    Returns:
        Score from 0 to 1
    """
    # Default scores by vertical (baseline authority)
    vertical_authority = {
        "legal": 1.0,      # Constitution, Acts highest authority
        "judicial": 0.95,  # Court judgments second
        "go": 0.9,         # GOs third
        "data": 0.7,       # Data reports
        "schemes": 0.6     # Schemes/programs
    }
    
    base_score = vertical_authority.get(vertical, 0.5)
    
    # Boost based on specific indicators
    if vertical == "legal":
        if "constitution" in str(payload.get("act_name", "")).lower():
            base_score = 1.0
        elif "act" in str(payload.get("act_name", "")).lower():
            base_score = 0.95
    
    elif vertical == "judicial":
        court = str(payload.get("court_name", "")).lower()
        if "supreme" in court:
            base_score = 1.0
        elif "high" in court:
            base_score = 0.95
    
    return base_score


def normalize_scores(results: List[Dict], score_field: str = "score") -> List[Dict]:
    """
    Normalize scores to [0, 1] range.
    
    Args:
        results: Results list
        score_field: Field containing score
        
    Returns:
        Results with normalized scores
    """
    if not results:
        return results
    
    scores = [r.get(score_field, 0) for r in results]
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        # All same score
        for r in results:
            r[f"{score_field}_normalized"] = 1.0
    else:
        for r in results:
            score = r.get(score_field, 0)
            normalized = (score - min_score) / (max_score - min_score)
            r[f"{score_field}_normalized"] = normalized
    
    return results