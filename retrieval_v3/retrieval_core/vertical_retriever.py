"""
Vertical Retriever - Vector search in Qdrant collections
Simple wrapper around Qdrant client for vertical-specific search
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Single search result from Qdrant"""
    chunk_id: str
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    vertical: str


class VerticalRetriever:
    """Retrieve from specific Qdrant vertical collections"""
    
    def __init__(self, qdrant_client, embedder):
        """
        Initialize retriever
        
        Args:
            qdrant_client: QdrantClient instance
            embedder: Embedding model
        """
        self.client = qdrant_client
        self.embedder = embedder
    
    def vector_search(
        self,
        vertical: str,
        query: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Vector search in a specific vertical
        
        Args:
            vertical: Collection name (e.g., 'ap_legal_documents')
            query: Query text
            top_k: Number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional Qdrant filters
            
        Returns:
            List of SearchResult objects
        """
        # Embed query
        query_vector = self.embedder.embed_single(query)
        
        # Build search request
        search_params = {
            'collection_name': vertical,
            'query_vector': query_vector,
            'limit': top_k,
            'score_threshold': score_threshold,
        }
        
        if filter_conditions:
            search_params['query_filter'] = filter_conditions
        
        # Execute search - FIXED API CALL
        try:
            # Use correct Qdrant API
            response = self.client.query_points(
                collection_name=vertical,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
                with_payload=True,
                with_vectors=False
            )
            
            hits = response.points
            
            # Convert to SearchResult objects
            results = []
            for hit in hits:
                results.append(SearchResult(
                    chunk_id=str(hit.id),
                    doc_id=hit.payload.get('doc_id', 'unknown'),
                    content=hit.payload.get('content', ''),
                    score=hit.score,
                    metadata=hit.payload,
                    vertical=vertical.replace('ap_', '')
                ))
            
            return results
            
        except Exception as e:
            print(f"Error searching {vertical}: {e}")
            return []
    
    def search_multiple_verticals(
        self,
        verticals: List[str],
        query: str,
        top_k_per_vertical: int = 20
    ) -> List[SearchResult]:
        """
        Search across multiple verticals
        
        Args:
            verticals: List of collection names
            query: Query text
            top_k_per_vertical: Results per vertical
            
        Returns:
            Combined list of SearchResult objects
        """
        all_results = []
        
        for vertical in verticals:
            results = self.vector_search(
                vertical=vertical,
                query=query,
                top_k=top_k_per_vertical
            )
            all_results.extend(results)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        return all_results
    
    def search_with_filter(
        self,
        vertical: str,
        query: str,
        filters: Dict,
        top_k: int = 20
    ) -> List[SearchResult]:
        """
        Search with metadata filters
        
        Args:
            vertical: Collection name
            query: Query text
            filters: Qdrant filter conditions
            top_k: Number of results
            
        Returns:
            Filtered search results
        """
        return self.vector_search(
            vertical=vertical,
            query=query,
            top_k=top_k,
            filter_conditions=filters
        )


if __name__ == "__main__":
    print("Vertical Retriever - requires Qdrant client and embedder")
    print("Example usage:")
    print("""
    from qdrant_client import QdrantClient
    from embedder import Embedder
    
    client = QdrantClient(url="http://localhost:6333")
    embedder = Embedder()
    
    retriever = VerticalRetriever(client, embedder)
    
    # Search single vertical
    results = retriever.vector_search(
        vertical='ap_legal_documents',
        query='RTE Section 12',
        top_k=10
    )
    
    # Search multiple verticals
    results = retriever.search_multiple_verticals(
        verticals=['ap_legal_documents', 'ap_government_orders'],
        query='teacher transfers',
        top_k_per_vertical=15
    )
    """)




















