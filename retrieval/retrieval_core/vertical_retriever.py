# Retrieves from each vertical

"""
Vertical Retriever
==================
Retrieves from individual vertical collections.
Clean, focused, no duplication.
"""

from typing import List, Dict, Optional, Sequence
from .qdrant_client import get_qdrant_client
from ..config.vertical_map import get_collection_name


class VerticalRetriever:
    """Retrieves from a single vertical"""
    
    def __init__(self):
        """Initialize retriever"""
        self.qdrant = get_qdrant_client()
    
    def retrieve(
        self,
        vertical: str,
        query_vector: Sequence[float],
        top_k: int = 10,
        score_threshold: float = 0.5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve from a vertical.
        
        Args:
            vertical: Vertical name (legal, go, judicial, data, schemes)
            query_vector: Query embedding
            top_k: Number of results
            score_threshold: Minimum score
            filters: Qdrant filters
            
        Returns:
            List of results with metadata
        """
        # Get collection name
        try:
            collection_name = get_collection_name(vertical)
        except ValueError as e:
            print(f"Invalid vertical: {e}")
            return []
        
        # Check if collection exists
        if not self.qdrant.collection_exists(collection_name):
            print(f"Collection {collection_name} does not exist")
            return []
        
        # Build Qdrant filter if needed
        qdrant_filter = None
        if filters:
            qdrant_filter = self._build_qdrant_filter(filters)
        
        # Search
        results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter
        )
        
        # Add vertical metadata to each result
        for result in results:
            result["vertical"] = vertical
            result["collection"] = collection_name
        
        return results
    
    def _build_qdrant_filter(self, filters: Dict) -> Dict:
        """
        Build Qdrant filter from simple dict.
        
        Args:
            filters: Dict like {"year": ["2020", "2021"], "section": ["12"]}
            
        Returns:
            Qdrant filter dict
        """
        # Build "must" conditions
        must_conditions = []
        
        for field, values in filters.items():
            if not values:
                continue
            
            # Match any of the values (new Qdrant format)
            if len(values) == 1:
                # Single value - direct field match
                should_conditions = [{field: values[0]}]
            else:
                # Multiple values - use "should" with field matches
                should_conditions = [
                    {field: value}
                    for value in values
                ]
            
            if len(should_conditions) == 1:
                must_conditions.append(should_conditions[0])
            else:
                must_conditions.append({"should": should_conditions})
        
        if not must_conditions:
            return None
        
        if len(must_conditions) == 1:
            return must_conditions[0]
        
        return {"must": must_conditions}
    
    def retrieve_multi_vertical(
        self,
        verticals: List[str],
        query_vector: Sequence[float],
        top_k_per_vertical: int = 10,
        score_threshold: float = 0.5,
        filters: Optional[Dict] = None
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve from multiple verticals.
        
        Args:
            verticals: List of vertical names
            query_vector: Query embedding
            top_k_per_vertical: Results per vertical
            score_threshold: Minimum score
            filters: Qdrant filters
            
        Returns:
            Dict mapping vertical to results
        """
        all_results = {}
        
        for vertical in verticals:
            results = self.retrieve(
                vertical=vertical,
                query_vector=query_vector,
                top_k=top_k_per_vertical,
                score_threshold=score_threshold,
                filters=filters
            )
            all_results[vertical] = results
        
        return all_results


# Global retriever instance
_retriever_instance = None


def get_vertical_retriever() -> VerticalRetriever:
    """Get global vertical retriever instance"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = VerticalRetriever()
    return _retriever_instance