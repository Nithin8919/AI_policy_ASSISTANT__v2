#!/usr/bin/env python3
"""
Investigate Real Qdrant Data Structure
Check what's actually in the Government Orders collection
"""

import sys
import os
import json
sys.path.append('.')
sys.path.append('retrieval_v3')

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient

def investigate_real_data():
    """Investigate actual data structure in Qdrant collections"""
    
    print("🔍 INVESTIGATING REAL QDRANT DATA")
    print("=" * 60)
    
    # Get Qdrant connection
    QDRANT_URL = os.getenv('QDRANT_URL')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌ Missing Qdrant credentials")
        return
    
    try:
        # Connect to production Qdrant
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("✅ Connected to Qdrant Cloud")
        
        # Get collections info
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        print(f"📊 Available collections: {collection_names}")
        
        # Focus on Government Orders collection
        print(f"\n🏛️ INVESTIGATING: ap_government_orders")
        print("-" * 50)
        
        # Get collection info
        try:
            collection_info = client.get_collection("ap_government_orders")
            print(f"📈 Vectors count: {collection_info.vectors_count}")
            print(f"📐 Vector size: {collection_info.config.params.vectors.size}")
        except Exception as e:
            print(f"⚠️ Collection info error: {e}")
        
        # Sample some real documents
        print(f"\n🔍 SAMPLING REAL DOCUMENTS:")
        print("-" * 40)
        
        results, _ = client.scroll(
            collection_name="ap_government_orders",
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        for i, point in enumerate(results, 1):
            print(f"\n📄 DOCUMENT {i}:")
            print(f"   ID: {point.id}")
            
            payload = point.payload
            
            # Check payload keys
            print(f"   📋 Payload keys: {list(payload.keys())}")
            
            # Check content
            content = payload.get('content', '')
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"   📝 Content: {content_preview}")
            
            # Check for relations
            relations = payload.get('relations', [])
            print(f"   🔗 Relations: {len(relations)} found")
            if relations:
                for j, rel in enumerate(relations[:3]):  # Show first 3
                    print(f"      {j+1}. {rel}")
            
            # Check for entities
            entities = payload.get('entities', {})
            print(f"   🏷️ Entities: {len(entities)} types")
            if entities:
                for entity_type, values in entities.items():
                    value_preview = values[:2] if isinstance(values, list) else values
                    print(f"      {entity_type}: {value_preview}")
            
            # Check other important metadata
            doc_id = payload.get('doc_id', 'N/A')
            vertical = payload.get('vertical', 'N/A')
            print(f"   🆔 Doc ID: {doc_id}")
            print(f"   📂 Vertical: {vertical}")
            
            print("   " + "─" * 40)
        
        # Look for GO documents with relations specifically
        print(f"\n🔍 SEARCHING FOR GO DOCUMENTS WITH RELATIONS:")
        print("-" * 50)
        
        # Try to find documents that have relations
        try:
            results_with_relations, _ = client.scroll(
                collection_name="ap_government_orders",
                scroll_filter={
                    "must": [
                        {
                            "key": "vertical",
                            "match": {"value": "go"}
                        }
                    ]
                },
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            print(f"📊 Found {len(results_with_relations)} GO documents")
            
            relation_count = 0
            entity_count = 0
            
            for point in results_with_relations:
                payload = point.payload
                relations = payload.get('relations', [])
                entities = payload.get('entities', {})
                
                if relations:
                    relation_count += 1
                    print(f"\n🔗 RELATIONS FOUND in {payload.get('doc_id', point.id)}:")
                    for rel in relations[:3]:  # Show first 3 relations
                        print(f"   - {rel}")
                
                if entities:
                    entity_count += 1
                    if relation_count <= 2:  # Show entities for first few docs
                        print(f"\n🏷️ ENTITIES FOUND in {payload.get('doc_id', point.id)}:")
                        for entity_type, values in entities.items():
                            print(f"   - {entity_type}: {values}")
            
            print(f"\n📊 SUMMARY:")
            print(f"   🔗 Documents with relations: {relation_count}/{len(results_with_relations)}")
            print(f"   🏷️ Documents with entities: {entity_count}/{len(results_with_relations)}")
            
        except Exception as e:
            print(f"❌ Error querying GO documents: {e}")
        
        # Test a specific GO query that should have relations
        print(f"\n🎯 TESTING SPECIFIC GO QUERY:")
        print("-" * 40)
        
        test_queries = [
            "GO MS No",
            "Government Order",
            "supersedes",
            "amends"
        ]
        
        for query in test_queries:
            try:
                # Try searching by content containing the query
                search_results = client.search(
                    collection_name="ap_government_orders",
                    query_vector=[0.1] * 1536,  # Dummy vector for search
                    query_filter={
                        "must": [
                            {
                                "key": "vertical", 
                                "match": {"value": "go"}
                            }
                        ]
                    },
                    limit=3,
                    with_payload=True
                )
                
                content_matches = []
                for result in search_results:
                    content = result.payload.get('content', '')
                    if query.lower() in content.lower():
                        content_matches.append(result)
                
                print(f"\n🔍 Query '{query}':")
                print(f"   📊 Total results: {len(search_results)}")
                print(f"   ✅ Content matches: {len(content_matches)}")
                
                for match in content_matches[:2]:  # Show first 2 matches
                    doc_id = match.payload.get('doc_id', 'N/A')
                    relations = match.payload.get('relations', [])
                    content_snippet = match.payload.get('content', '')[:150]
                    print(f"   📄 {doc_id}: {len(relations)} relations")
                    print(f"      Content: {content_snippet}...")
                
            except Exception as e:
                print(f"   ❌ Query '{query}' failed: {e}")
        
        print(f"\n🎯 INVESTIGATION COMPLETE")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_real_data()