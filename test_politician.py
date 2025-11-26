#!/usr/bin/env python3
"""
Payload Loss Diagnostic
=======================
Find where the payload is being stripped in the retrieval pipeline.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment, but don't crash if .env is not readable in some environments
try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

# Ensure local packages are importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "ingestion_v2"))

from retrieval import RetrievalRouter
from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from ingestion_v2.embedding.google_embedder import get_embedder

def trace_payload_loss():
    """Trace where payload gets lost"""
    
    print("="*100)
    print("🔍 PAYLOAD LOSS DIAGNOSTIC")
    print("="*100)
    
    query = "What are the rules for SC category teacher transfers?"
    
    # Step 1: Direct Qdrant (we know this works)
    print("\n[Step 1] Direct Qdrant query...")
    client = get_qdrant_client()
    embedder = get_embedder()
    
    query_vector = embedder.embed_texts([query])[0]
    if hasattr(query_vector, 'tolist'):
        query_vector = query_vector.tolist()
    
    # Our QdrantClientWrapper exposes .search(), not .query_points()
    direct_results = client.search(
        collection_name="ap_government_orders",
        query_vector=query_vector,
        limit=3,
        score_threshold=None,
        query_filter=None,
    )
    
    print(f"✅ Direct Qdrant returned {len(direct_results)} results")
    if direct_results:
        first = direct_results[0]
        payload = first.get("payload", {}) or {}
        print(f"   Payload keys: {list(payload.keys())}")
        print(f"   Has 'text': {'text' in payload}")
        print(f"   Has 'vertical': {'vertical' in payload}")
        print(f"   Text length: {len(payload.get('text', ''))}")
    
    # Step 2: Through RetrievalRouter
    print("\n[Step 2] Through RetrievalRouter...")
    router = RetrievalRouter()
    
    router_response = router.query(query, mode="qa", top_k=3)
    
    print(f"✅ Router returned success: {router_response.get('success')}")
    
    if router_response.get('success'):
        results = router_response.get('results', [])
        print(f"   Results count: {len(results)}")
        
        if results:
            first_result = results[0]
            print(f"   Result type: {type(first_result)}")
            print(f"   Result keys: {list(first_result.keys())}")
            
            # Check payload
            if 'payload' in first_result:
                payload = first_result['payload']
                print(f"   Payload type: {type(payload)}")
                print(f"   Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'NOT A DICT'}")
                
                if isinstance(payload, dict):
                    print(f"   Has 'text': {'text' in payload}")
                    print(f"   Has 'vertical': {'vertical' in payload}")
                    
                    if 'text' in payload:
                        print(f"   Text length: {len(payload['text'])}")
                    else:
                        print("   ❌ TEXT MISSING FROM PAYLOAD!")
                        print(f"   Available keys: {list(payload.keys())}")
            else:
                print("   ❌ NO PAYLOAD KEY IN RESULT!")
                print(f"   Available keys: {list(first_result.keys())}")
    else:
        print(f"   ❌ Router failed: {router_response.get('error')}")
    
    # Step 3: Check vertical retriever directly
    print("\n[Step 3] Testing VerticalRetriever directly...")
    
    try:
        from retrieval.retrieval_core.vertical_retriever import get_vertical_retriever
        
        v_retriever = get_vertical_retriever()
        retriever_results = v_retriever.retrieve(
            vertical="go",
            query_vector=query_vector,
            top_k=3,
            score_threshold=0.0,
            filters=None,
        )
        
        print(f"✅ VerticalRetriever returned {len(retriever_results)} results")
        
        if retriever_results:
            first = retriever_results[0]
            print(f"   Result type: {type(first)}")
            print(f"   Result keys: {list(first.keys())}")
            
            payload = first.get("payload", {})
            if isinstance(payload, dict):
                print(f"   Payload keys: {list(payload.keys())}")
                print(f"   Has 'text': {'text' in payload}")
            else:
                print(f"   ❌ NO PAYLOAD dict in result from VerticalRetriever!")
    
    except Exception as e:
        print(f"   ❌ Error testing VerticalRetriever: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)
    print("DIAGNOSIS")
    print("="*100)
    print("""
The payload is being lost somewhere in the pipeline:
1. Direct Qdrant: Has payload ✅
2. VerticalRetriever: Check above
3. RetrievalRouter: Check above

Look for code that:
- Converts Qdrant points to dicts
- Filters/transforms results
- Strips payload fields

Common culprits:
- retrieval/retrieval_core/vertical_retriever.py (search method)
- retrieval/router.py (query method)
- retrieval/output_formatting/formatter.py (format_response method)
""")

if __name__ == "__main__":
    trace_payload_loss()