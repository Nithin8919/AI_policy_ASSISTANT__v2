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
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size: int = 32):
        try:
            logger.info(f"Loading Cross-Encoder model: {model_name}")
            self.model = CrossEncoder(model_name)
            self.batch_size = batch_size
            self.is_ready = True
            logger.info(f"✅ Cross-Encoder ready with batch_size={batch_size}")
        except Exception as e:
            logger.error(f"Failed to load Cross-Encoder: {e}")
            self.is_ready = False
            
    def rerank(self, query: str, results: List[Dict], top_k: int = 10, max_candidates: int = 50, mode: str = "qa") -> List[Dict]:
        """
        Rerank a list of results with timeout protection and smart batching.
        
        Args:
            query: User query
            results: List of result dicts (must have 'content' or 'text')
            top_k: Number of results to return
            max_candidates: Maximum number of candidates to process (default: 50, increased from 25)
            mode: Query mode (qa, policy, etc.) - affects candidate limit
            
        Returns:
            Reranked list of results
        """
        if not self.is_ready or not results:
            return results[:top_k]
        
        # OPTIMIZATION: Reduce candidates based on mode for faster processing
        # QA mode: 25 candidates (was 50), Policy mode: 30 candidates
        if max_candidates == 50:  # Only adjust if using default
            if mode == "qa":
                max_candidates = 25
            elif mode in ["policy", "framework", "brainstorm"]:
                max_candidates = 30
            else:
                max_candidates = 25  # Default to conservative for other modes
        
        # Smart candidate selection: process up to max_candidates
        num_to_process = min(len(results), max_candidates)
        if len(results) > num_to_process:
            logger.info(f"Processing top {num_to_process} candidates (out of {len(results)}) for cross-encoder")
            candidates = results[:num_to_process]
            remaining = results[num_to_process:]
        else:
            candidates = results
            remaining = []
            
        try:
            # Prepare pairs for cross-encoder
            pairs = []
            for res in candidates:
                content = res.get("content") or res.get("text", "")
                # Truncate content to avoid token limits (approx 500 words)
                content = " ".join(content.split()[:500])
                pairs.append([query, content])
                
            # Predict scores with timeout protection (8 seconds, reduced from 15s)
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Cross-encoder timeout")
            
            # Set 8-second timeout for faster failure detection
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(8)
            
            try:
                # Process in batches for better performance
                logger.info(f"Cross-encoder processing {len(pairs)} pairs in batches of {self.batch_size}")
                scores = self.model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
                signal.alarm(0)  # Cancel alarm
                logger.info(f"✅ Cross-encoder completed successfully")
            except TimeoutError:
                logger.warning("⏱️ Cross-encoder timeout (8s), returning original ranking")
                signal.alarm(0)
                return results[:top_k]
            
            # Update scores and sort
            for i, res in enumerate(candidates):
                res["cross_encoder_score"] = float(scores[i])
                res["score"] = float(scores[i])
                
            # Sort by new score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Combine reranked candidates with remaining results
            final_results = candidates + remaining
            
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Cross-encoder failed: {e}, returning original ranking")
            return results[:top_k]

