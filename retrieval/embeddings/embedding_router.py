# Chooses embedding model per mode

"""
Embedding Router
================
Routes queries to the appropriate embedding model based on mode.
Simple, deterministic.
"""

from typing import Tuple, List

from .embedder import get_embedder
from ..config.mode_config import QueryMode, get_mode_config


class EmbeddingRouter:
    """Routes queries to appropriate embedding model"""
    
    def __init__(self):
        """Initialize router"""
        self.embedder = get_embedder()
    
    def embed_for_mode(
        self,
        query: str,
        mode: QueryMode
    ) -> Tuple[List[float], str]:
        """
        Embed query using the model appropriate for the mode.
        
        Args:
            query: Query text
            mode: Query mode
            
        Returns:
            Tuple of (embedding, model_type)
        """
        # Get mode config
        mode_config = get_mode_config(mode)
        model_type = mode_config.embedding_model
        
        # Embed
        embedding = self.embedder.embed_query(query, model_type)
        
        return embedding, model_type
    
    def embed_explicit(
        self,
        query: str,
        model_type: str = "fast"
    ) -> List[float]:
        """
        Embed query with explicit model choice.
        
        Args:
            query: Query text
            model_type: "fast" or "deep"
            
        Returns:
            Embedding vector
        """
        return self.embedder.embed_query(query, model_type)


# Global router instance
_router_instance = None


def get_embedding_router() -> EmbeddingRouter:
    """Get global embedding router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = EmbeddingRouter()
    return _router_instance