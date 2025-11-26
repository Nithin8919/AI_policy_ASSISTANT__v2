# Creative diversity ranking

"""
Brainstorm Reranker
===================
Diversity-focused reranker for Brainstorm mode.
Prioritizes novel insights and global perspectives.
"""

from typing import List, Dict, Set
from .scorer_utils import (
    compute_term_overlap_score,
    compute_recency_score,
    extract_year_from_payload
)
import re


class BrainstormReranker:
    """Diversity-focused reranker for brainstorming"""
    
    # Terms that indicate global/innovative content
    INNOVATION_KEYWORDS = {
        "finland", "singapore", "south korea", "japan", "oecd",
        "unesco", "world bank", "international", "global",
        "innovative", "novel", "creative", "experimental",
        "pilot", "best practice", "case study", "model"
    }
    
    def rerank(
        self,
        results: List[Dict],
        query: str,
        top_k: int = 15
    ) -> List[Dict]:
        """
        Rerank results for brainstorming with diversity.
        
        Scoring:
        - 30% vector similarity
        - 25% innovation/global indicators
        - 25% diversity (dissimilarity to selected)
        - 20% recency
        
        Args:
            results: Search results
            query: Query string
            top_k: Number to return
            
        Returns:
            Diverse, innovation-focused results
        """
        if not results:
            return []
        
        # Score each result
        for idx, result in enumerate(results):
            payload = result.get("payload", {})
            text = (payload.get("text", "") or payload.get("content", "")).lower()
            
            # Vector score
            vector_score = result.get("score", 0.0)
            
            # Innovation score (global perspectives)
            innovation_score = self._compute_innovation_score(text)
            
            # Recency score
            year = extract_year_from_payload(payload)
            recency_score = compute_recency_score(year)
            
            # Initial score (diversity added iteratively)
            result["innovation_score"] = innovation_score
            result["recency_score"] = recency_score
            result["base_score"] = (
                0.3 * vector_score +
                0.25 * innovation_score +
                0.2 * recency_score
            )
        
        # Select diverse results iteratively
        selected = []
        remaining = results.copy()
        
        # Start with highest base score
        remaining.sort(key=lambda x: x["base_score"], reverse=True)
        selected.append(remaining.pop(0))
        
        # Iteratively add most diverse result
        while len(selected) < top_k and remaining:
            best_idx = 0
            best_diversity_score = -1
            
            for idx, candidate in enumerate(remaining):
                # Compute diversity vs. already selected
                diversity = self._compute_diversity(candidate, selected)
                
                # Combined score
                combined = (
                    0.75 * candidate["base_score"] +
                    0.25 * diversity
                )
                
                if combined > best_diversity_score:
                    best_diversity_score = combined
                    best_idx = idx
            
            selected_result = remaining.pop(best_idx)
            selected_result["diversity_score"] = best_diversity_score
            selected_result["rerank_score"] = best_diversity_score
            selected.append(selected_result)
        
        return selected
    
    def _compute_innovation_score(self, text: str) -> float:
        """
        Score based on innovation/global keywords.
        
        Args:
            text: Document text (lowercase)
            
        Returns:
            Score from 0 to 1
        """
        if not text:
            return 0.0
        
        # Count innovation keywords
        matches = 0
        for keyword in self.INNOVATION_KEYWORDS:
            if keyword in text:
                matches += 1
        
        # Normalize
        return min(matches / 5.0, 1.0)
    
    def _compute_diversity(
        self,
        candidate: Dict,
        selected: List[Dict]
    ) -> float:
        """
        Compute diversity of candidate vs. already selected results.
        Higher = more diverse.
        
        Args:
            candidate: Candidate result
            selected: Already selected results
            
        Returns:
            Diversity score from 0 to 1
        """
        if not selected:
            return 1.0
        
        candidate_text = (
            candidate.get("payload", {}).get("text", "") or
            candidate.get("payload", {}).get("content", "")
        ).lower()
        
        candidate_terms = set(re.findall(r'\b\w+\b', candidate_text))
        
        # Compute max similarity to selected
        max_similarity = 0.0
        
        for selected_result in selected:
            selected_text = (
                selected_result.get("payload", {}).get("text", "") or
                selected_result.get("payload", {}).get("content", "")
            ).lower()
            
            selected_terms = set(re.findall(r'\b\w+\b', selected_text))
            
            if not candidate_terms or not selected_terms:
                continue
            
            # Jaccard similarity
            intersection = len(candidate_terms & selected_terms)
            union = len(candidate_terms | selected_terms)
            similarity = intersection / union if union > 0 else 0
            
            max_similarity = max(max_similarity, similarity)
        
        # Diversity is inverse of similarity
        return 1.0 - max_similarity


# Global reranker instance
_reranker_instance = None


def get_brainstorm_reranker() -> BrainstormReranker:
    """Get global brainstorm reranker instance"""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BrainstormReranker()
    return _reranker_instance