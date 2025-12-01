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
        Rerank a list of results with timeout protection.
        
        Args:
            query: User query
            results: List of result dicts (must have 'content' or 'text')
            top_k: Number of results to return
            
        Returns:
            Reranked list of results
        """
        if not self.is_ready or not results:
            return results[:top_k]
        
        # LIMIT INPUT SIZE to prevent timeout (max 75 results for faster processing)
        if len(results) > 75:
            logger.warning(f"Too many results ({len(results)}), limiting to 75 for cross-encoder")
            results = results[:75]
            
        try:
            # Prepare pairs for cross-encoder
            pairs = []
            for res in results:
                content = res.get("content") or res.get("text", "")
                # Truncate content to avoid token limits (approx 500 words)
                content = " ".join(content.split()[:500])
                pairs.append([query, content])
                
            # Predict scores with timeout protection (5 seconds)
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Cross-encoder timeout")
            
            # Set 5-second timeout (increased from 3s)
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                scores = self.model.predict(pairs)
                signal.alarm(0)  # Cancel alarm
            except TimeoutError:
                logger.warning("⏱️ Cross-encoder timeout (5s), returning original ranking")
                signal.alarm(0)
                return results[:top_k]
            
            # Update scores and sort
            for i, res in enumerate(results):
                res["cross_encoder_score"] = float(scores[i])
                res["score"] = float(scores[i])
                
            # Sort by new score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Cross-encoder failed: {e}, returning original ranking")
            return results[:top_k]

