# For Deep Think (legal-first ordering)

"""
Policy Reranker
===============
Deep Think mode reranker with policy-aware scoring.
Legal → GO → Judicial → Data hierarchy.
"""

from typing import List, Dict
from .scorer_utils import (
    compute_term_overlap_score,
    compute_metadata_relevance_score,
    compute_recency_score,
    compute_authority_score,
    extract_year_from_payload,
    normalize_scores
)


class PolicyReranker:
    """Policy-aware reranker for Deep Think mode"""
    
    def rerank(
        self,
        results: List[Dict],
        query: str,
        filters: Dict = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Rerank results with policy reasoning hierarchy.
        
        Scoring:
        - 40% vector similarity
        - 20% authority (vertical priority)
        - 15% recency
        - 15% term overlap
        - 10% metadata relevance
        
        Args:
            results: Search results
            query: Query string
            filters: Query filters
            top_k: Number to return
            
        Returns:
            Reranked results with policy ordering
        """
        if not results:
            return []
        
        # Score each result
        for idx, result in enumerate(results):
            payload = result.get("payload", {})
            text = payload.get("text", "") or payload.get("content", "")
            vertical = result.get("vertical", "")
            
            # Vector score
            vector_score = result.get("score", 0.0)
            
            # Authority score (legal > go > judicial > data)
            authority_score = compute_authority_score(payload, vertical)
            
            # Recency score
            year = extract_year_from_payload(payload)
            recency_score = compute_recency_score(year)
            
            # Term overlap
            term_score = compute_term_overlap_score(query, text)
            
            # Metadata relevance
            metadata_score = compute_metadata_relevance_score(payload, filters or {})
            
            # Combine with policy weights
            final_score = (
                0.4 * vector_score +
                0.2 * authority_score +
                0.15 * recency_score +
                0.15 * term_score +
                0.1 * metadata_score
            )
            
            result["rerank_score"] = final_score
            result["authority_score"] = authority_score
            result["recency_score"] = recency_score
            result["term_overlap"] = term_score
            result["metadata_relevance"] = metadata_score
        
        # Sort by rerank score
        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Ensure vertical diversity in top results
        results = self._ensure_vertical_diversity(results, top_k)
        
        return results[:top_k]
    
    def _ensure_vertical_diversity(
        self,
        results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Ensure top results have representation from multiple verticals.
        While maintaining score-based ranking.
        """
        if len(results) <= top_k:
            return results
        
        # Group by vertical
        by_vertical = {}
        for r in results:
            vertical = r.get("vertical", "unknown")
            if vertical not in by_vertical:
                by_vertical[vertical] = []
            by_vertical[vertical].append(r)
        
        # If we have good coverage already, return as-is
        top_verticals = {r.get("vertical") for r in results[:top_k]}
        if len(top_verticals) >= min(3, len(by_vertical)):
            return results
        
        # Otherwise, ensure at least one from each vertical in top K
        diverse_results = []
        used_indices = set()
        
        # First, add top result from each vertical
        for vertical, vertical_results in by_vertical.items():
            if diverse_results and len(diverse_results) >= top_k:
                break
            
            # Find highest scoring unused result from this vertical
            for r in vertical_results:
                idx = results.index(r)
                if idx not in used_indices:
                    diverse_results.append(r)
                    used_indices.add(idx)
                    break
        
        # Fill remaining slots by score
        for idx, r in enumerate(results):
            if len(diverse_results) >= top_k:
                break
            if idx not in used_indices:
                diverse_results.append(r)
                used_indices.add(idx)
        
        return diverse_results


# Global reranker instance
_reranker_instance = None


def get_policy_reranker() -> PolicyReranker:
    """Get global policy reranker instance"""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = PolicyReranker()
    return _reranker_instance