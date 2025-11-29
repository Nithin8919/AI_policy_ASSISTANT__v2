#!/usr/bin/env python3
"""
Store Clause Index in Qdrant - Production Solution
Store the clause index directly in Qdrant for production deployments
"""

import json
import os
import uuid
from typing import Dict, List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Collection name for clause index
CLAUSE_INDEX_COLLECTION = 'ap_clause_index'


def create_clause_index_collection(client: QdrantClient):
    """Create dedicated collection for clause index"""
    try:
        # Check if collection exists
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if CLAUSE_INDEX_COLLECTION in existing:
            print(f"✅ Collection {CLAUSE_INDEX_COLLECTION} already exists")
            return
        
        # Create collection with minimal vector (we don't need embeddings for index)
        client.create_collection(
            collection_name=CLAUSE_INDEX_COLLECTION,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE)  # Minimal vector
        )
        
        print(f"✅ Created collection: {CLAUSE_INDEX_COLLECTION}")
        
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        raise


def store_clause_index_in_qdrant():
    """Store clause index from JSON file into Qdrant"""
    
    print("🚀 Storing Clause Index in Qdrant for Production")
    print("=" * 60)
    
    # Connect to Qdrant
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("✅ Connected to Qdrant Cloud")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Load clause index from JSON
    try:
        with open('clause_index.json', 'r', encoding='utf-8') as f:
            clause_index = json.load(f)
        print(f"📂 Loaded {len(clause_index)} clauses from clause_index.json")
    except Exception as e:
        print(f"❌ Failed to load clause_index.json: {e}")
        return
    
    # Create collection
    create_clause_index_collection(client)
    
    # Convert clause index to Qdrant points
    points = []
    
    for clause_key, clause_data in clause_index.items():
        # Create unique ID for each clause
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, clause_key))
        
        # Store all clause data in payload
        payload = {
            'clause_key': clause_key,                    # "rte section 12"
            'clause_text': clause_data['clause_text'],  # "section 12"
            'chunk_id': clause_data['chunk_id'],        # Original chunk ID
            'doc_id': clause_data['doc_id'],            # Document ID
            'content': clause_data['content'],          # Content preview
            'confidence': clause_data['confidence'],    # Match confidence
            'vertical': clause_data['vertical'],        # legal/go/etc
            'index_type': 'clause_lookup'               # Identifier
        }
        
        points.append(PointStruct(
            id=point_id,
            vector=[0.0],  # Dummy vector (we don't need embeddings)
            payload=payload
        ))
    
    # Upload to Qdrant in batches
    batch_size = 100
    uploaded = 0
    
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        
        try:
            client.upsert(
                collection_name=CLAUSE_INDEX_COLLECTION,
                points=batch
            )
            uploaded += len(batch)
            print(f"✅ Uploaded batch {i//batch_size + 1} ({len(batch)} clauses)")
            
        except Exception as e:
            print(f"❌ Failed to upload batch {i//batch_size + 1}: {e}")
    
    print(f"\n🎉 Successfully stored {uploaded} clauses in Qdrant!")
    print(f"📍 Collection: {CLAUSE_INDEX_COLLECTION}")
    print(f"🔍 Each clause can now be retrieved by clause_key")
    
    # Test lookup
    test_lookup_clause(client, "rte section 12")


def test_lookup_clause(client: QdrantClient, clause_key: str):
    """Test clause lookup from Qdrant"""
    print(f"\n🔍 Testing lookup: '{clause_key}'")
    
    try:
        # Search for clause by key
        results = client.scroll(
            collection_name=CLAUSE_INDEX_COLLECTION,
            limit=5,
            with_payload=True,
            scroll_filter={
                "must": [
                    {
                        "key": "clause_key",
                        "match": {"value": clause_key}
                    }
                ]
            }
        )
        
        points, _ = results
        
        if points:
            for point in points:
                payload = point.payload
                print(f"✅ Found: {payload['clause_key']}")
                print(f"   Chunk ID: {payload['chunk_id']}")
                print(f"   Confidence: {payload['confidence']}")
                print(f"   Vertical: {payload['vertical']}")
                print(f"   Content: {payload['content'][:100]}...")
        else:
            print(f"❌ No results found for '{clause_key}'")
            
    except Exception as e:
        print(f"❌ Lookup failed: {e}")


def create_production_clause_indexer():
    """Create a production-ready clause indexer class"""
    
    code = '''
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
            results = self.qdrant_client.scroll(
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
            results = self.qdrant_client.scroll(
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
'''
    
    # Write the production class to file
    with open('production_clause_indexer.py', 'w') as f:
        f.write(code)
    
    print(f"\n📝 Created production_clause_indexer.py")
    print(f"🔧 This class can be used in your retrieval engine")


if __name__ == "__main__":
    # Store clause index in Qdrant
    store_clause_index_in_qdrant()
    
    # Create production indexer class
    create_production_clause_indexer()
    
    print(f"\n🚀 Production setup complete!")
    print(f"✅ Clause index stored in Qdrant collection: {CLAUSE_INDEX_COLLECTION}")
    print(f"✅ Production indexer class created: production_clause_indexer.py") 
    print(f"🔧 Update your retrieval engine to use ProductionClauseIndexer")