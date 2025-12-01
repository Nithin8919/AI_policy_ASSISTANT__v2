import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from pipeline.retrieval_engine import RetrievalEngine
from qdrant_client import QdrantClient

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_diagnostics():
    print("🚀 Starting Retrieval System Diagnostics...")
    
    # Initialize engine (mock client if needed, but try real one first)
    try:
        client = QdrantClient(host="localhost", port=6333)
        engine = RetrievalEngine(qdrant_client=client, enable_cache=True)
        print("✅ Retrieval Engine initialized")
    except Exception as e:
        print(f"❌ Failed to initialize engine: {e}")
        return

    # 1. Test Cache Performance
    print("\n🧪 Testing Cache Performance...")
    query = "recent GOs on school education"
    
    start = time.time()
    res1 = engine.retrieve(query)
    t1 = time.time() - start
    print(f"   Query 1 (Cold): {t1:.4f}s")
    
    start = time.time()
    res2 = engine.retrieve(query)
    t2 = time.time() - start
    print(f"   Query 2 (Cached): {t2:.4f}s")
    
    if t2 < t1 * 0.5:
        print("   ✅ Cache is working (significant speedup)")
    else:
        print(f"   ⚠️ Cache might not be working efficiently (Speedup: {t1/t2:.2f}x)")

    # 2. Test Cross-Encoder Timeout
    print("\n🧪 Testing Cross-Encoder...")
    # We can't easily force a timeout without mocking, but we can check if it runs
    try:
        # Create dummy results for reranking
        results = [{"content": "test content " * 100, "score": 0.5, "id": i} for i in range(10)]
        if engine.cross_encoder:
            reranked = engine.cross_encoder.rerank("test query", results)
            print(f"   ✅ Cross-encoder ran successfully on {len(reranked)} items")
        else:
            print("   ⚠️ Cross-encoder not enabled")
    except Exception as e:
        print(f"   ❌ Cross-encoder failed: {e}")

    # 3. Test Relation Expansion
    print("\n🧪 Testing Relation Expansion...")
    # This requires actual data in Qdrant. We'll check if the method exists and runs.
    if engine.relation_entity_processor:
        print("   ✅ Relation processor is initialized")
    else:
        print("   ⚠️ Relation processor not initialized")

if __name__ == "__main__":
    run_diagnostics()
