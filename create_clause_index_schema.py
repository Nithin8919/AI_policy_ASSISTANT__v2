#!/usr/bin/env python3
"""
Create Clause Index Schema - Add required indexes for filtering
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
CLAUSE_INDEX_COLLECTION = 'ap_clause_index'


def create_indexes():
    """Create required payload indexes for clause collection"""
    
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("✅ Connected to Qdrant Cloud")
        
        # Create indexes for filterable fields
        indexes = [
            ('clause_key', PayloadSchemaType.KEYWORD),
            ('clause_text', PayloadSchemaType.KEYWORD), 
            ('vertical', PayloadSchemaType.KEYWORD),
            ('index_type', PayloadSchemaType.KEYWORD),
            ('confidence', PayloadSchemaType.FLOAT)
        ]
        
        for field_name, field_type in indexes:
            try:
                client.create_payload_index(
                    collection_name=CLAUSE_INDEX_COLLECTION,
                    field_name=field_name,
                    field_schema=field_type,
                    wait=True
                )
                print(f"✅ Created index: {field_name} ({field_type})")
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️ Index already exists: {field_name}")
                else:
                    print(f"⚠️ Could not create index {field_name}: {e}")
        
        # Test lookup now
        test_lookup(client)
        
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_lookup(client: QdrantClient):
    """Test clause lookup after indexes are created"""
    print(f"\n🔍 Testing lookup after index creation...")
    
    try:
        # Test exact match
        results = client.scroll(
            collection_name=CLAUSE_INDEX_COLLECTION,
            limit=1,
            with_payload=True,
            scroll_filter={
                "must": [
                    {
                        "key": "clause_key",
                        "match": {"value": "rte section 12"}
                    }
                ]
            }
        )
        
        points, _ = results
        
        if points:
            payload = points[0].payload
            print(f"✅ Found clause: {payload['clause_key']}")
            print(f"   Chunk ID: {payload['chunk_id']}")
            print(f"   Confidence: {payload['confidence']}")
            print(f"   Content: {payload['content'][:100]}...")
        else:
            print(f"❌ No exact match found")
            
            # Try finding any RTE clauses
            rte_results = client.scroll(
                collection_name=CLAUSE_INDEX_COLLECTION,
                limit=5,
                with_payload=True
            )
            
            rte_points, _ = rte_results
            print(f"📋 Sample clauses in collection:")
            for point in rte_points[:3]:
                print(f"   - {point.payload['clause_key']}")
        
    except Exception as e:
        print(f"❌ Test lookup failed: {e}")


if __name__ == "__main__":
    create_indexes()