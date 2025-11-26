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
        Initialize retriever.
        
        Args:
            qdrant_client: Qdrant client wrapper
            embedder: Embedding model
            vertical: Vertical name (legal, go, judicial, data, schemes)
        """
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.vertical = vertical
        
        logger.info(f"✅ Vertical retriever initialized for: {vertical}")
    
    def retrieve(
        self,
        query: str,
        enhanced_query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict]:
        """
        Retrieve from vertical with smart filtering.
        
        Args:
            query: Original query
            enhanced_query: Enhanced query for embedding
            top_k: Number of results
            filters: Filter dict (e.g., {"sections": ["12"], "year": [2020]})
            
        Returns:
            List of results with scores
        """
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
            
            results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter
            )
            
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
        
        # Import field mappings
        try:
            from ..config.field_mappings import (
                build_multi_field_condition,
                validate_filter,
                get_mapped_fields
            )
        except ImportError:
            logger.warning("⚠️ Field mappings not available, using direct mapping")
            return self._build_simple_filter(filters)
        
        must_conditions = []
        
        for filter_field, values in filters.items():
            if not values:
                continue
            
            # Validate filter for this vertical
            if not validate_filter(filter_field, self.vertical):
                logger.warning(
                    f"⚠️ Filter '{filter_field}' not applicable to vertical '{self.vertical}', skipping"
                )
                continue
            
            # Get mapped fields
            mapped_fields = get_mapped_fields(filter_field, self.vertical)
            logger.debug(
                f"Filter '{filter_field}' maps to fields: {mapped_fields} in {self.vertical}"
            )
            
            # Build multi-field conditions (OR logic)
            field_conditions = build_multi_field_condition(
                filter_field,
                values,
                self.vertical
            )
            
            if not field_conditions:
                continue
            
            # If multiple conditions, connect with OR
            if len(field_conditions) == 1:
                must_conditions.append(field_conditions[0])
            else:
                # Wrap in Filter with "should" (OR logic)
                must_conditions.append(
                    models.Filter(should=field_conditions)
                )
        
        if not must_conditions:
            return None
        
        # Connect all filters with AND logic
        return models.Filter(must=must_conditions)
    
    def _build_simple_filter(
        self,
        filters: Dict[str, List[str]]
    ) -> Optional[models.Filter]:
        """
        Fallback: Simple filter without field mappings.
        Assumes direct field name mapping.
        """
        conditions = []
        
        for field_name, values in filters.items():
            if not values:
                continue
            
            if len(values) == 1:
                conditions.append(
                    models.FieldCondition(
                        key=field_name,
                        match=models.MatchValue(value=values[0])
                    )
                )
            else:
                conditions.append(
                    models.FieldCondition(
                        key=field_name,
                        match=models.MatchAny(any=values)
                    )
                )
        
        if not conditions:
            return None
        
        return models.Filter(must=conditions)


# Factory function
def get_vertical_retriever(
    qdrant_client,
    embedder,
    vertical: str
) -> VerticalRetriever:
    """Create vertical retriever"""
    return VerticalRetriever(qdrant_client, embedder, vertical)


# Export
__all__ = ["VerticalRetriever", "get_vertical_retriever"]