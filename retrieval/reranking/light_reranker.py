# For QA (fast)

"""
Light Reranker
==============
Fast reranking for QA mode.
Optimized for speed and precision.
"""

from typing import List, Dict
from .scorer_utils import (
    compute_term_overlap_score,
    compute_metadata_relevance_score,
    compute_position_score,
    normalize_scores
)


class LightReranker:
    """Fast reranker for QA mode"""
    
    def rerank(
        self,
        results: List[Dict],
        query: str,
        filters: Dict = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank results for QA mode.
        
        Scoring:
        - 70% vector similarity (original score)
        - 20% term overlap
        - 10% metadata relevance
        
        Args:
            results: Search results
            query: Query string
            filters: Query filters
            top_k: Number to return
            
        Returns:
            Reranked results
        """
        if not results:
            return []
        
        # Score each result
        for idx, result in enumerate(results):
            payload = result.get("payload", {})
            text = payload.get("text", "") or payload.get("content", "")
            
            # Original vector score (already 0-1)
            vector_score = result.get("score", 0.0)
            
            # Term overlap score
            term_score = compute_term_overlap_score(query, text)
            
            # Metadata relevance
            metadata_score = compute_metadata_relevance_score(payload, filters or {})
            
            # Position score (less important for QA)
            position_score = compute_position_score(idx, len(results))
            
            # Combine scores
            final_score = (
                0.7 * vector_score +
                0.2 * term_score +
                0.1 * metadata_score
            )
            
            result["rerank_score"] = final_score
            result["term_overlap"] = term_score
            result["metadata_relevance"] = metadata_score
        
        # Sort by rerank score
        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Return top K
        return results[:top_k]


# Global reranker instance
_reranker_instance = None


def get_light_reranker() -> LightReranker:
    """Get global light reranker instance"""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = LightReranker()
    return _reranker_instance