# Thin client wrapper

"""
Qdrant Client
=============
Thin wrapper around Qdrant client.
Handles connection caching, no BS.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Optional, Sequence

from ..config.settings import QDRANT_CONFIG


class QdrantClientWrapper:
    """Thin wrapper around Qdrant client"""
    
    def __init__(self):
        """Initialize client (connection cached)"""
        self._client = None
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client"""
        if self._client is None:
            self._client = QdrantClient(
                url=QDRANT_CONFIG.url,
                api_key=QDRANT_CONFIG.api_key,
                timeout=QDRANT_CONFIG.timeout,
                prefer_grpc=QDRANT_CONFIG.prefer_grpc
            )
        return self._client
    
    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search in a collection.
        
        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Number of results
            score_threshold: Minimum score
            query_filter: Qdrant filter dict
            
        Returns:
            List of search results
        """
        try:
            vector_payload = (
                query_vector.tolist()
                if hasattr(query_vector, "tolist")
                else list(query_vector)
            )
            results = self.client.query_points(
                collection_name=collection_name,
                query=vector_payload,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True
            ).points
            
            # Convert to dict format
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                    "vector": hit.vector if hasattr(hit, 'vector') else None
                }
                for hit in results
            ]
        
        except Exception as e:
            print(f"Error searching collection {collection_name}: {e}")
            return []
    
    def get_collections(self):
        """Expose underlying client's get_collections"""
        try:
            return self.client.get_collections()
        except Exception as e:
            print(f"Error retrieving collections: {e}")
            raise
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        try:
            collections = self.client.get_collections()
            return collection_name in [c.name for c in collections.collections]
        except Exception as e:
            print(f"Error checking collection existence: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get collection information"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return None
    
    def count(self, collection_name: str):
        """Count points in collection"""
        try:
            return self.client.count(collection_name)
        except Exception as e:
            print(f"Error counting collection {collection_name}: {e}")
            return None
    
    def upsert(self, collection_name: str, points: List[PointStruct]):
        """Upsert points to collection"""
        try:
            return self.client.upsert(
                collection_name=collection_name,
                points=points
            )
        except Exception as e:
            print(f"Error upserting to collection {collection_name}: {e}")
            raise


# Global client instance
_client_instance = None


def get_qdrant_client() -> QdrantClientWrapper:
    """Get global Qdrant client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = QdrantClientWrapper()
    return _client_instance