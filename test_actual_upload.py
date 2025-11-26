#!/usr/bin/env python3
"""
Actual Upload Test - Tests Real Upload to Qdrant
=================================================
Tests the complete workflow with actual Qdrant upload.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append('ingestion_v2')
sys.path.append('retrieval')

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

def test_actual_upload():
    """Test actual upload of a few chunks"""
    print("=" * 70)
    print("ACTUAL UPLOAD TEST")
    print("=" * 70)
    
    # Find smallest test file
    test_file = Path("ingestion_v2/output/scheme/minorites/chunks.jsonl")
    if not test_file.exists():
        print(f"❌ Test file not found")
        return False
    
    # Load 2 chunks
    chunks = []
    with open(test_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= 2:
                break
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"📊 Testing with {len(chunks)} chunks")
    
    try:
        # Setup
        from embedding.google_embedder import get_embedder
        from embed_and_upload_flagship import (
            ensure_metadata_store, save_full_metadata,
            create_lightweight_payload, validate_embedding_quality,
            generate_stable_id
        )
        from config.vertical_map import get_collection_name
        
        embedder = get_embedder()
        ensure_metadata_store()
        
        # Embed
        print("\n🧠 Embedding...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = embedder.embed_texts(texts)
        
        if hasattr(embeddings, "tolist"):
            embeddings = embeddings.tolist()
        embeddings = [[float(x) for x in emb] for emb in embeddings]
        
        print(f"✅ Generated {len(embeddings)} embeddings ({len(embeddings[0])} dim)")
        
        # Validate quality
        print("\n🔍 Validating quality...")
        for i, emb in enumerate(embeddings):
            is_valid, reason = validate_embedding_quality(emb)
            if not is_valid:
                print(f"❌ Embedding {i} failed: {reason}")
                return False
        print("✅ All embeddings valid")
        
        # Create payloads and save metadata
        print("\n📦 Creating payloads...")
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            # Save full metadata
            save_full_metadata(
                chunk['doc_id'],
                chunk['chunk_id'],
                chunk.get('metadata', {})
            )
            
            # Create lightweight payload
            payload = create_lightweight_payload(chunk)
            
            # Generate ID
            point_id = generate_stable_id(chunk['doc_id'], chunk['chunk_id'])
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)
            
            print(f"   ✅ {chunk['chunk_id']}:")
            print(f"      Payload: {len(json.dumps(payload)):,} bytes")
            print(f"      Has metadata_ref: {payload.get('metadata_ref', 'N/A')}")
            print(f"      Text preview: {len(payload.get('text', ''))} chars")
        
        # Upload to Qdrant
        print("\n☁️ Uploading to Qdrant...")
        client = QdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY'),
            check_compatibility=False
        )
        
        collection_name = get_collection_name("schemes")
        
        # Ensure collection exists
        collections = client.get_collections()
        if collection_name not in [c.name for c in collections.collections]:
            from config.vertical_map import build_vector_params
            vector_params = build_vector_params("schemes")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_params
            )
            print(f"✅ Created collection: {collection_name}")
        
        # Upload
        client.upsert(collection_name=collection_name, points=points)
        print(f"✅ Uploaded {len(points)} points to {collection_name}")
        
        # Verify upload
        print("\n🔍 Verifying upload...")
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10
        )
        
        uploaded_points = scroll_result[0]
        print(f"✅ Found {len(uploaded_points)} points in collection")
        
        # Check structure
        if uploaded_points:
            point = uploaded_points[0]
            payload = point.payload
            print(f"\n📋 Sample payload structure:")
            print(f"   Keys: {len(payload)} fields")
            print(f"   Has metadata_ref: {'metadata_ref' in payload}")
            print(f"   Has has_full_metadata: {'has_full_metadata' in payload}")
            print(f"   Payload size: {len(json.dumps(payload)):,} bytes")
            print(f"   Text length: {len(payload.get('text', ''))}")
        
        # Test metadata retriever
        print("\n🔍 Testing metadata retrieval...")
        from metadata.metadata_retreiver import get_metadata_retriever
        
        retriever = get_metadata_retriever()
        
        for chunk in chunks:
            full_metadata = retriever.get_full_metadata(
                chunk['doc_id'],
                chunk['chunk_id']
            )
            if full_metadata:
                print(f"   ✅ Retrieved full metadata for {chunk['chunk_id']}")
                print(f"      Fields: {len(full_metadata)}")
            else:
                print(f"   ❌ Failed to retrieve metadata for {chunk['chunk_id']}")
                return False
        
        # Test enrichment
        mock_result = {
            'id': 'test',
            'score': 0.95,
            'payload': {
                'doc_id': chunks[0]['doc_id'],
                'chunk_id': chunks[0]['chunk_id']
            }
        }
        
        enriched = retriever.enrich_qdrant_results([mock_result])
        if 'full_metadata' in enriched[0]:
            print(f"   ✅ Enriched result with full metadata")
        else:
            print(f"   ❌ Failed to enrich result")
            return False
        
        print("\n✅ ALL TESTS PASSED!")
        print("\n📊 Summary:")
        print(f"   - Embeddings: {len(embeddings)} ({len(embeddings[0])} dim)")
        print(f"   - Quality: All valid")
        print(f"   - Payload size: ~{len(json.dumps(payload)):,} bytes (lightweight)")
        print(f"   - Metadata store: Working")
        print(f"   - Metadata retriever: Working")
        print(f"   - Qdrant upload: Successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_actual_upload()
    sys.exit(0 if success else 1)

