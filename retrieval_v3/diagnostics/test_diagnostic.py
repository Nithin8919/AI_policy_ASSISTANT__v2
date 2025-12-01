import sys
import os
import logging
from pathlib import Path
import json

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "retrieval_v3"))

from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_diagnostic():
    print("🚀 Starting Diagnostic Mode Test...")
    
    # Initialize engine
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        engine = RetrievalEngine(qdrant_client=client, enable_cache=True)
        print("✅ Retrieval Engine initialized with Qdrant")
    except Exception as e:
        print(f"⚠️ Failed to initialize Qdrant: {e}")
        print("Initializing engine without Qdrant (mock mode)")
        engine = RetrievalEngine(qdrant_client=None, enable_cache=True)

    # Test Query
    query = "What are the rules for RTE reimbursement?"
    print(f"\n📝 Testing Query: '{query}'")
    
    # Run Full Diagnostic
    print("\n🧪 Running Full Diagnostic (Single Prompt)...")
    try:
        result = engine.run_diagnostic(query, test_type="full")
        print("\n--- Diagnostic Output ---")
        print(result.get("diagnostic_output", "No output"))
        print("-------------------------")
        
        if "diagnostic_output" in result:
            print("✅ Full Diagnostic Test Passed")
        else:
            print("❌ Full Diagnostic Test Failed (No output)")
            
    except Exception as e:
        print(f"❌ Full Diagnostic Test Failed: {e}")

    # Run Individual Tests
    print("\n🧪 Running Individual Tests...")
    tests = ["sanity", "missing", "structure", "reasoning", "contradiction"]
    
    for test in tests:
        print(f"\n   Running {test} test...")
        try:
            res = engine.run_diagnostic(query, test_type=test)
            if res and res.output:
                print(f"   ✅ {test} test passed")
                # print(f"   Output: {res.output[:100]}...")
            else:
                print(f"   ❌ {test} test failed (empty result)")
        except Exception as e:
            print(f"   ❌ {test} test failed: {e}")

if __name__ == "__main__":
    test_diagnostic()
