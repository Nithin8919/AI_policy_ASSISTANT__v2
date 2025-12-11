# LLM Reranker - DEPRECATED (Use cross-encoder instead)

"""
LLM Reranker - DEPRECATED
This module is deprecated. Use CrossEncoderReranker instead for better performance.
"""

import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class LLMReranker:
    """DEPRECATED: Rerank using Gemini Flash - Use CrossEncoderReranker instead"""
    
    def __init__(self, api_key: str = None):
        """
        DEPRECATED: This class is no longer functional.
        Use CrossEncoderReranker from reranking.cross_encoder_reranker instead.
        """
        logger.warning("⚠️ LLMReranker is deprecated. Use CrossEncoderReranker instead.")
        self.api_key = None  # Disabled
    
    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 20
    ) -> List[Dict]:
        """
        DEPRECATED: Returns results sorted by score only.
        
        Args:
            query: User query
            results: Initial results
            top_k: Final count
            
        Returns:
            Results sorted by score (no LLM reranking)
        """
        logger.warning("⚠️ LLMReranker.rerank() is deprecated. Returning score-sorted results.")
        return sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:top_k]
