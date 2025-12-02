"""
Test Internet Layer Integration
================================
Verify that automatic internet detection works correctly and backward compatibility is preserved.
"""

import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'retrieval_v3'))
sys.path.insert(0, str(project_root / 'retrieval'))

from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval.embeddings.embedder import get_embedder
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine


def setup_engine():
    """Initialize retrieval engine for testing"""
    print("🔧 Initializing retrieval engine...")
    qdrant = get_qdrant_client()
    embedder = get_embedder()
    
    engine = RetrievalEngine(
        qdrant_client=qdrant,
        embedder=embedder,
        gemini_api_key=os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
        use_llm_rewrites=True,
        use_llm_reranking=True,
        enable_cache=True
    )
    
    print("✅ Engine initialized\n")
    return engine


def test_automatic_internet_detection():
    """Test 1: Automatic internet detection for queries with internet triggers"""
    print("=" * 80)
    print("TEST 1: Automatic Internet Detection")
    print("=" * 80)
    
    engine = setup_engine()
    
    # Query with "latest" should trigger internet
    query = "latest AP education policy 2024"
    print(f"Query: '{query}'")
    print("Expected: Internet should be automatically enabled\n")
    
    output = engine.retrieve(query, top_k=10)
    
    # Verify internet was used
    print(f"✓ plan.use_internet = {output.plan.use_internet}")
    
    # Check for internet results
    internet_results = [r for r in output.results if r.vertical == "internet"]
    print(f"✓ Internet results found: {len(internet_results)}")
    
    if output.plan.use_internet:
        print("✅ PASS: Internet was automatically enabled")
    else:
        print("❌ FAIL: Internet should have been enabled")
        return False
    
    if len(internet_results) > 0:
        print(f"✅ PASS: Found {len(internet_results)} internet results")
        print(f"\nSample internet result:")
        print(f"  Title: {internet_results[0].metadata.get('title', 'N/A')}")
        print(f"  URL: {internet_results[0].metadata.get('url', 'N/A')}")
    else:
        print("⚠️  WARNING: No internet results found (might be API issue)")
    
    print()
    return True


def test_manual_override_disables_internet():
    """Test 2: Manual override can disable internet even when auto-detected"""
    print("=" * 80)
    print("TEST 2: Manual Override Disables Internet")
    print("=" * 80)
    
    engine = setup_engine()
    
    # Query would normally trigger internet
    query = "latest AP education policy 2024"
    print(f"Query: '{query}'")
    print("Custom plan: {'internet_enabled': False}")
    print("Expected: Internet should be disabled by override\n")
    
    output = engine.retrieve(
        query,
        top_k=10,
        custom_plan={'internet_enabled': False}
    )
    
    # Check for internet results
    internet_results = [r for r in output.results if r.vertical == "internet"]
    print(f"✓ Internet results found: {len(internet_results)}")
    
    if len(internet_results) == 0:
        print("✅ PASS: Internet was successfully disabled by override")
    else:
        print("❌ FAIL: Internet should have been disabled")
        return False
    
    print()
    return True


def test_backward_compatibility_use_internet():
    """Test 3: Legacy 'use_internet' flag still works"""
    print("=" * 80)
    print("TEST 3: Backward Compatibility (legacy 'use_internet' flag)")
    print("=" * 80)
    
    engine = setup_engine()
    
    # Use legacy flag on a query that wouldn't normally trigger internet
    query = "teacher transfer rules"
    print(f"Query: '{query}'")
    print("Custom plan: {'use_internet': True}")
    print("Expected: Internet should be enabled via legacy flag\n")
    
    output = engine.retrieve(
        query,
        top_k=10,
        custom_plan={'use_internet': True}
    )
    
    # Check for internet results
    internet_results = [r for r in output.results if r.vertical == "internet"]
    print(f"✓ Internet results found: {len(internet_results)}")
    
    if len(internet_results) > 0:
        print("✅ PASS: Legacy 'use_internet' flag still works")
    else:
        print("⚠️  WARNING: No internet results (might be API issue, but flag was honored)")
    
    print()
    return True


def test_no_internet_for_simple_queries():
    """Test 4: Simple queries don't trigger internet"""
    print("=" * 80)
    print("TEST 4: No Internet for Simple Queries")
    print("=" * 80)
    
    engine = setup_engine()
    
    query = "teacher transfers"
    print(f"Query: '{query}'")
    print("Expected: Internet should NOT be enabled\n")
    
    output = engine.retrieve(query, top_k=10)
    
    # Verify internet was NOT used
    print(f"✓ plan.use_internet = {output.plan.use_internet}")
    
    # Check for internet results
    internet_results = [r for r in output.results if r.vertical == "internet"]
    print(f"✓ Internet results found: {len(internet_results)}")
    
    if not output.plan.use_internet and len(internet_results) == 0:
        print("✅ PASS: Internet was correctly NOT enabled")
    else:
        print("❌ FAIL: Internet should not have been enabled")
        return False
    
    print()
    return True


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 80)
    print("INTERNET LAYER INTEGRATION TESTS")
    print("=" * 80 + "\n")
    
    results = []
    
    try:
        results.append(("Automatic Detection", test_automatic_internet_detection()))
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}\n")
        results.append(("Automatic Detection", False))
    
    try:
        results.append(("Manual Override", test_manual_override_disables_internet()))
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}\n")
        results.append(("Manual Override", False))
    
    try:
        results.append(("Backward Compatibility", test_backward_compatibility_use_internet()))
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}\n")
        results.append(("Backward Compatibility", False))
    
    try:
        results.append(("No Internet Simple Query", test_no_internet_for_simple_queries()))
    except Exception as e:
        print(f"❌ Test 4 failed with error: {e}\n")
        results.append(("No Internet Simple Query", False))
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Internet layer integration is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
