
# Production Clause Indexer - Uses Qdrant instead of JSON file

import os
from typing import List, Optional
from dataclasses import dataclass
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
CLAUSE_INDEX_COLLECTION = 'ap_clause_index'


@dataclass
class ClauseMatch:
    """A matched clause from Qdrant"""
    clause_text: str
    chunk_id: str
    doc_id: str
    content: str
    confidence: float
    vertical: str


class ProductionClauseIndexer:
    """Production clause indexer using Qdrant storage"""
    
    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """Initialize with Qdrant client"""
        if qdrant_client:
            self.qdrant_client = qdrant_client
        else:
            self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    def lookup_clause(self, query: str) -> List[ClauseMatch]:
        """
        Look up clause matches for a query using Qdrant
        
        Args:
            query: User query like "RTE Section 12"
            
        Returns:
            List of matching ClauseMatch objects
        """
        try:
            query_lower = query.lower()
            matches = []
            
            # Try exact key matches first
            exact_results = self._search_by_clause_key(query_lower)
            matches.extend(exact_results)
            
            # Try partial matches if no exact matches
            if not matches:
                partial_results = self._search_partial_matches(query_lower)
                matches.extend(partial_results)
            
            # Sort by confidence and return top matches
            matches.sort(key=lambda x: x.confidence, reverse=True)
            return matches[:5]
            
        except Exception as e:
            print(f"Clause indexer lookup failed: {e}")
            return []
    
    def _search_by_clause_key(self, query: str) -> List[ClauseMatch]:
        """Search by exact clause key"""
        try:
            results = self.qdrant_client.client.scroll if hasattr(self.qdrant_client, "client") else self.qdrant_client.scroll(
                collection_name=CLAUSE_INDEX_COLLECTION,
                limit=10,
                with_payload=True,
                scroll_filter={
                    "must": [
                        {
                            "key": "clause_key",
                            "match": {"value": query}
                        }
                    ]
                }
            )
            
            points, _ = results
            matches = []
            
            for point in points:
                payload = point.payload
                matches.append(ClauseMatch(
                    clause_text=payload['clause_text'],
                    chunk_id=payload['chunk_id'],
                    doc_id=payload['doc_id'],
                    content=payload['content'],
                    confidence=payload['confidence'],
                    vertical=payload['vertical']
                ))
            
            return matches
            
        except Exception:
            return []
    
    def _search_partial_matches(self, query: str) -> List[ClauseMatch]:
        """Search for partial matches using contains"""
        try:
            # Get all clause index entries
            results = self.qdrant_client.client.scroll if hasattr(self.qdrant_client, "client") else self.qdrant_client.scroll(
                collection_name=CLAUSE_INDEX_COLLECTION,
                limit=100,  # Get more for partial matching
                with_payload=True,
                scroll_filter={
                    "must": [
                        {
                            "key": "index_type",
                            "match": {"value": "clause_lookup"}
                        }
                    ]
                }
            )
            
            points, _ = results
            matches = []
            
            # Manual filtering for partial matches
            for point in points:
                payload = point.payload
                clause_key = payload['clause_key'].lower()
                
                # Check if query terms are in clause key
                if any(term in clause_key for term in query.split()):
                    matches.append(ClauseMatch(
                        clause_text=payload['clause_text'],
                        chunk_id=payload['chunk_id'],
                        doc_id=payload['doc_id'],
                        content=payload['content'],
                        confidence=payload['confidence'],
                        vertical=payload['vertical']
                    ))
            
            return matches
            
        except Exception:
            return []
