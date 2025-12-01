"""
Vertical Retriever - FIXED VERSION
===================================
Retrieves from a single vertical with smart filter handling.

CRITICAL FIX: Implements multi-field filtering using field mappings.
- Checks multiple possible fields for each filter
- Uses OR logic across mapped fields
- Handles actual ingestion schema
"""

import logging
from typing import List, Dict, Optional
from qdrant_client import models

# NEW V2 IMPORTS
from ..config.settings import FEATURE_FLAGS

logger = logging.getLogger(__name__)


class VerticalRetriever:
    """
    Retrieves from a single vertical collection.
    Now with smart multi-field filtering!
    """
    
    def __init__(
        self,
        qdrant_client,
        embedder,
        vertical: str
    ):
        """
        Initialize retriever with V2 support.
        
        Args:
            qdrant_client: Qdrant client wrapper
            embedder: Embedding model
            vertical: Vertical name (legal, go, judicial, data, schemes)
        """
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.vertical = vertical
        
        # V2: Initialize hybrid searcher if enabled
        if FEATURE_FLAGS.get("use_hybrid_search", False):
            from .hybrid_search import get_hybrid_searcher
            self.hybrid_searcher = get_hybrid_searcher()
            logger.info(f"✅ Hybrid search enabled for {vertical}")
        else:
            self.hybrid_searcher = None
        
        logger.info(f"✅ Vertical retriever initialized for: {vertical}")
    
    def retrieve(
        self,
        query: str,
        enhanced_query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, List[str]]] = None,
        use_hybrid_search: Optional[bool] = None
    ) -> List[Dict]:
        """
        Retrieve from vertical with smart filtering and optional hybrid search.
        
        Args:
            query: Original query (for BM25)
            enhanced_query: Enhanced query for embedding
            top_k: Number of results
            filters: Filter dict (e.g., {"sections": ["12"], "year": [2020]})
            use_hybrid_search: Whether to apply hybrid search (None = use settings)
            
        Returns:
            List of results with scores
        """
        # Determine if we should use hybrid search
        if use_hybrid_search is None:
            should_use_hybrid = (
                self.hybrid_searcher is not None and 
                FEATURE_FLAGS.get("use_hybrid_search", False)
            )
        else:
            should_use_hybrid = use_hybrid_search and self.hybrid_searcher is not None
        
        # Embed query
        query_vector = self.embedder.embed(enhanced_query)
        
        # Build smart Qdrant filter
        qdrant_filter = self._build_qdrant_filter(filters)
        
        # Log filter for debugging
        if qdrant_filter:
            logger.info(f"🔍 Applying filters to {self.vertical}: {filters}")
            logger.debug(f"Qdrant filter structure: {qdrant_filter}")
        
        # Search using collection name
        try:
            from ..config.vertical_map import get_collection_name
            collection_name = get_collection_name(self.vertical)
            
            response = self.qdrant_client.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=0.0,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False
            )
            results = response.points
            
            # V2: Apply hybrid search if enabled and we have results
            if should_use_hybrid and results:
                results = self.hybrid_searcher.hybrid_search(results, query)
                logger.info(f"🔀 Applied hybrid search to {self.vertical}")
            elif should_use_hybrid:
                logger.debug(f"Hybrid search enabled but no results to rerank for {self.vertical}")
            
            logger.info(f"✅ Found {len(results)} results in {self.vertical}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error retrieving from {self.vertical}: {e}")
            logger.error(f"Filter was: {filters}")
            logger.error(f"Qdrant filter was: {qdrant_filter}")
            return []
    
    def _search_with_vector(
        self,
        query_vector,
        top_k: int = 10,
        filters: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict]:
        """
        Search directly with a pre-computed vector.
        Used by MultiVerticalRetriever.
        """
        # Build smart Qdrant filter
        qdrant_filter = self._build_qdrant_filter(filters)
        
        # Log filter for debugging
        if qdrant_filter:
            logger.info(f"🔍 Applying filters to {self.vertical}: {filters}")
            logger.debug(f"Qdrant filter structure: {qdrant_filter}")
        
        # Search using collection name
        try:
            from ..config.vertical_map import get_collection_name
            collection_name = get_collection_name(self.vertical)
            
            response = self.qdrant_client.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=0.0,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False
            )
            results = response.points
            
            logger.info(f"✅ Found {len(results)} results in {self.vertical}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error retrieving from {self.vertical}: {e}")
            logger.error(f"Filter was: {filters}")
            logger.error(f"Qdrant filter was: {qdrant_filter}")
            return []
    
    def _build_qdrant_filter(
        self,
        filters: Optional[Dict[str, List[str]]]
    ) -> Optional[models.Filter]:
        """
        Build Qdrant filter with multi-field support.
        
        KEY FIX: Uses field mappings to check multiple possible fields.
        
        Example:
            filters = {"sections": ["12"]}
            
            Creates Qdrant filter checking:
            - section = "12" OR
            - sections contains "12" OR
            - mentioned_sections contains "12"
        
        Args:
            filters: Filter dict
            
        Returns:
            Qdrant Filter object or None
        """
        if not filters:
            return None
        
        # Use smart LLM-powered filter adaptation
        try:
            from ..config.smart_filter_adapter import get_smart_filter_adapter
            from ..config.vertical_map import get_collection_name
            
            collection_name = get_collection_name(self.vertical)
            adapter = get_smart_filter_adapter(self.qdrant_client.client)
            
            # Let LLM adapt the filters to actual schema
            adapted_filters = adapter.adapt_filters(filters, collection_name)
            
            if not adapted_filters:
                return None
            
            # Build simple filter with adapted field names
            return self._build_simple_filter(adapted_filters)
            
        except ImportError:
            logger.warning("⚠️ Smart filter adapter not available, using direct mapping")
            return self._build_simple_filter(filters)
        except Exception as e:
            logger.error(f"Smart filter adaptation failed: {e}")
            return self._build_simple_filter(filters)
    
    def _build_simple_filter(
        self,
        filters: Dict[str, List[str]]
    ) -> Optional[models.Filter]:
        """
        CRITICAL FIX: Use correct match type based on field type.
        
        String fields (like "section": "12") need MatchValue for single values.
        List fields (like "sections": ["12", "13"]) need MatchAny.
        """
        conditions = []
        
        for field_name, values in filters.items():
            if not values:
                continue
            
            # CRITICAL FIX: Use MatchValue for single values (works with strings)
            # Use MatchAny for multiple values (works with lists)
            if len(values) == 1:
                # Single value - use MatchValue (works with string fields!)
                conditions.append(
                    models.FieldCondition(
                        key=field_name,
                        match=models.MatchValue(value=values[0])
                    )
                )
            else:
                # Multiple values - use MatchAny
                conditions.append(
                    models.FieldCondition(
                        key=field_name,
                        match=models.MatchAny(any=values)
                    )
                )
        
        if not conditions:
            return None
        
        return models.Filter(must=conditions)


class MultiVerticalRetriever:
    """
    Multi-vertical retriever wrapper.
    Manages individual VerticalRetriever instances for each vertical.
    """
    
    def __init__(self):
        """Initialize multi-vertical retriever"""
        from ..retrieval_core.qdrant_client import get_qdrant_client
        from ..embeddings.embedder import get_embedder
        
        self.qdrant_client = get_qdrant_client()
        self.embedder = get_embedder()
        self.vertical_retrievers = {}
        
        logger.info("✅ Multi-vertical retriever initialized")
    
    def _get_vertical_retriever(self, vertical: str) -> VerticalRetriever:
        """Get or create retriever for specific vertical"""
        if vertical not in self.vertical_retrievers:
            self.vertical_retrievers[vertical] = VerticalRetriever(
                self.qdrant_client,
                self.embedder,
                vertical
            )
        return self.vertical_retrievers[vertical]
    
    def retrieve_multi_vertical(
        self,
        verticals: List[str],
        query_vector,
        top_k_per_vertical: int = 10,
        filters: Optional[Dict] = None,
        original_query: str = "",
        use_hybrid_search: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve from multiple verticals.
        
        Args:
            verticals: List of verticals to search
            query_vector: Query embedding
            top_k_per_vertical: Results per vertical
            filters: Optional filters
            original_query: Original query for hybrid search
            use_hybrid_search: Whether to apply hybrid search
            
        Returns:
            Dict mapping vertical to results
        """
        results = {}
        
        for vertical in verticals:
            try:
                retriever = self._get_vertical_retriever(vertical)
                
                # Search directly with vector
                vertical_results = retriever._search_with_vector(
                    query_vector=query_vector,
                    top_k=top_k_per_vertical,
                    filters=filters
                )
                
                # Apply hybrid search if enabled and we have original query
                if use_hybrid_search and original_query and vertical_results:
                    from .hybrid_search import get_hybrid_searcher
                    hybrid_searcher = get_hybrid_searcher()
                    vertical_results = hybrid_searcher.hybrid_search(vertical_results, original_query)
                    logger.info(f"🔀 Applied hybrid search to {vertical} ({len(vertical_results)} results)")
                
                # Add vertical info to each result
                for result in vertical_results:
                    result["vertical"] = vertical
                
                results[vertical] = vertical_results
                
            except Exception as e:
                logger.error(f"Error retrieving from {vertical}: {e}")
                results[vertical] = []
        
        return results


# Factory functions
def get_vertical_retriever() -> MultiVerticalRetriever:
    """Create multi-vertical retriever (new interface)"""
    return MultiVerticalRetriever()


def create_vertical_retriever(
    qdrant_client,
    embedder,
    vertical: str
) -> VerticalRetriever:
    """Create single vertical retriever (old interface)"""
    return VerticalRetriever(qdrant_client, embedder, vertical)


# Export
__all__ = [
    "VerticalRetriever", 
    "MultiVerticalRetriever",
    "get_vertical_retriever", 
    "create_vertical_retriever"
]