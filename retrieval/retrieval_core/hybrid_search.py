"""
Hybrid Search Integration
=========================
Combines dense (vector) + sparse (BM25) search for better recall.

CRITICAL UPGRADE: Wires up existing BM25 code that was never used.
"""

import logging
from typing import List, Dict, Optional
from collections import Counter
import re

logger = logging.getLogger(__name__)


class HybridSearcher:
    """
    Combines dense vector search with sparse BM25 search.
    
    Uses existing code from multi_vector_search.py that was never wired up.
    """
    
    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        Initialize hybrid searcher.
        
        Args:
            vector_weight: Weight for vector similarity (0.7 = 70%)
            keyword_weight: Weight for keyword matching (0.3 = 30%)
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    def hybrid_search(
        self,
        vector_results: List[Dict],
        query: str
    ) -> List[Dict]:
        """
        Re-score results using hybrid approach.
        
        Args:
            vector_results: Results from pure vector search
            query: Original query
            
        Returns:
            Re-ranked results with hybrid scores
        """
        if not vector_results:
            return []
        
        logger.info(f"🔀 Applying hybrid search (vector: {self.vector_weight}, "
                   f"keyword: {self.keyword_weight})")
        
        # Calculate average document length (for BM25)
        total_length = 0
        doc_count = 0
        
        for result in vector_results:
            payload = result.get("payload", {})
            text = payload.get("text", "") or payload.get("content", "")
            total_length += len(text.split())
            doc_count += 1
        
        avg_doc_length = total_length / max(doc_count, 1)
        
        # Compute keyword scores
        for result in vector_results:
            # Get document text
            payload = result.get("payload", {})
            text = payload.get("text", "") or payload.get("content", "")
            
            # Compute BM25 score
            keyword_score = self._compute_bm25_score(
                query, text, avg_doc_length=avg_doc_length
            )
            
            # Store original scores
            result["vector_score"] = result["score"]
            result["keyword_score"] = keyword_score
            
            # Normalize scores to [0, 1] range
            # Vector scores from Qdrant are already normalized
            vector_score_normalized = result["score"]
            keyword_score_normalized = min(keyword_score / 10.0, 1.0)  # Scale BM25
            
            # Combine scores
            combined_score = (
                self.vector_weight * vector_score_normalized +
                self.keyword_weight * keyword_score_normalized
            )
            
            result["combined_score"] = combined_score
            result["score"] = combined_score  # Update primary score
        
        # Sort by combined score
        vector_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        logger.info(f"✅ Hybrid search complete, top score: {vector_results[0]['combined_score']:.3f}")
        
        return vector_results
    
    def _compute_bm25_score(
        self,
        query: str,
        document: str,
        k1: float = 1.5,
        b: float = 0.75,
        avg_doc_length: float = 500.0
    ) -> float:
        """
        Compute BM25 score between query and document.
        
        Args:
            query: Query string
            document: Document string
            k1: BM25 parameter (term saturation)
            b: BM25 parameter (length normalization)
            avg_doc_length: Average document length
            
        Returns:
            BM25 score
        """
        # Tokenize (simple word splitting)
        query_terms = re.findall(r'\b\w+\b', query.lower())
        doc_terms = re.findall(r'\b\w+\b', document.lower())
        
        if not query_terms or not doc_terms:
            return 0.0
        
        # Term frequencies
        doc_tf = Counter(doc_terms)
        doc_length = len(doc_terms)
        
        # BM25 score
        score = 0.0
        for term in query_terms:
            if term in doc_tf:
                tf = doc_tf[term]
                # Simplified BM25 (without IDF, as we don't have corpus stats)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
                term_score = numerator / denominator
                score += term_score
        
        return score
    
    def explain_scores(self, result: Dict) -> str:
        """Explain hybrid scoring for a result"""
        vector_score = result.get("vector_score", 0.0)
        keyword_score = result.get("keyword_score", 0.0)
        combined_score = result.get("combined_score", 0.0)
        
        return (f"Vector: {vector_score:.3f} | "
                f"Keyword: {keyword_score:.3f} | "
                f"Combined: {combined_score:.3f}")


# Global instance
_hybrid_searcher_instance = None


def get_hybrid_searcher(
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> HybridSearcher:
    """Get global hybrid searcher instance"""
    global _hybrid_searcher_instance
    if _hybrid_searcher_instance is None:
        _hybrid_searcher_instance = HybridSearcher(vector_weight, keyword_weight)
        logger.info(f"✅ Hybrid Searcher initialized (vector: {vector_weight}, keyword: {keyword_weight})")
    return _hybrid_searcher_instance


# Export
__all__ = ["HybridSearcher", "get_hybrid_searcher"]