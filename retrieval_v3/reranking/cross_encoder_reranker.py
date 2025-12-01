"""
Cross-Encoder Reranker
======================
High-precision reranker using a cross-encoder model.
"""

import logging
from typing import List, Dict
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    """
    Reranks results using a Cross-Encoder model.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            logger.info(f"Loading Cross-Encoder model: {model_name}")
            self.model = CrossEncoder(model_name)
            self.is_ready = True
        except Exception as e:
            logger.error(f"Failed to load Cross-Encoder: {e}")
            self.is_ready = False
            
    def rerank(self, query: str, results: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Rerank a list of results.
        
        Args:
            query: User query
            results: List of result dicts (must have 'content' or 'text')
            top_k: Number of results to return
            
        Returns:
            Reranked list of results
        """
        if not self.is_ready or not results:
            return results[:top_k]
            
        # Prepare pairs for cross-encoder
        pairs = []
        for res in results:
            content = res.get("content") or res.get("text", "")
            # Truncate content to avoid token limits (approx 500 words)
            content = " ".join(content.split()[:500])
            pairs.append([query, content])
            
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Update scores and sort
        for i, res in enumerate(results):
            res["cross_encoder_score"] = float(scores[i])
            # We can either replace the score or keep it separate. 
            # For final ranking, we usually use the cross-encoder score.
            res["score"] = float(scores[i])
            
        # Sort by new score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
