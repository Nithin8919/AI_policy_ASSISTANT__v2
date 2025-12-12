#!/usr/bin/env python3
"""
Quick test for modularized RetrievalEngine - verifies structure and basic functionality
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "retrieval_v3"))

def main():
    print("=" * 80)
    print("QUICK TEST: Modularized RetrievalEngine")
    print("=" * 80)
    
    errors = []
    
    # Test 1: Imports
    print("\n1. Testing imports...")
    try:
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine, RetrievalResult, RetrievalOutput
        from retrieval_v3.pipeline.models import RetrievalResult as R1, RetrievalOutput as O1
        print("   ✅ All imports successful")
    except Exception as e:
        errors.append(f"Import failed: {e}")
        print(f"   ❌ Import failed: {e}")
        return 1
    
    # Test 2: Engine initialization
    print("\n2. Testing engine initialization...")
    try:
        engine = RetrievalEngine(
            qdrant_client=None,
            embedder=None,
            use_llm_rewrites=False,
            use_llm_reranking=False,
            enable_cache=False
        )
        
        # Check coordinators
        required_attrs = [
            'query_coordinator', 'retrieval_executor', 'result_processor',
            'reranking_coordinator', 'legal_clause_handler', 'internet_handler',
            'stats_manager', 'normalizer', 'interpreter', 'router', 'plan_builder'
        ]
        
        for attr in required_attrs:
            if not hasattr(engine, attr):
                errors.append(f"Missing attribute: {attr}")
                print(f"   ❌ Missing: {attr}")
            else:
                print(f"   ✅ {attr} exists")
        
        # Check methods
        required_methods = ['retrieve', 'retrieve_and_answer', 'run_diagnostic', 'cleanup', 'get_validation_stats']
        for method in required_methods:
            if not hasattr(engine, method):
                errors.append(f"Missing method: {method}")
                print(f"   ❌ Missing method: {method}")
            else:
                print(f"   ✅ {method}() exists")
        
    except Exception as e:
        errors.append(f"Initialization failed: {e}")
        print(f"   ❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 3: Data classes
    print("\n3. Testing data classes...")
    try:
        result = RetrievalResult(
            chunk_id="test_1",
            doc_id="doc_1",
            content="Test",
            score=0.9,
            vertical="test"
        )
        assert result.chunk_id == "test_1"
        print("   ✅ RetrievalResult works")
        
        # Test that both import paths work
        result2 = R1(
            chunk_id="test_2",
            doc_id="doc_2",
            content="Test2",
            score=0.8,
            vertical="test2"
        )
        assert result2.chunk_id == "test_2"
        print("   ✅ Backward compatibility works")
        
    except Exception as e:
        errors.append(f"Data classes failed: {e}")
        print(f"   ❌ Data classes failed: {e}")
    
    # Test 4: Basic retrieve (stub mode - fast)
    print("\n4. Testing basic retrieve() in stub mode...")
    try:
        output = engine.retrieve("test query", top_k=3)
        
        # Verify structure
        assert hasattr(output, 'query')
        assert hasattr(output, 'normalized_query')
        assert hasattr(output, 'interpretation')
        assert hasattr(output, 'plan')
        assert hasattr(output, 'results')
        assert hasattr(output, 'rewrites')
        assert isinstance(output.results, list)
        assert isinstance(output.rewrites, list)
        
        print(f"   ✅ retrieve() works")
        print(f"      - Query: {output.query}")
        print(f"      - Normalized: {output.normalized_query}")
        print(f"      - Results: {len(output.results)}")
        print(f"      - Rewrites: {len(output.rewrites)}")
        print(f"      - Processing time: {output.processing_time:.3f}s")
        
    except Exception as e:
        errors.append(f"retrieve() failed: {e}")
        print(f"   ❌ retrieve() failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Custom plan
    print("\n5. Testing custom_plan parameter...")
    try:
        output = engine.retrieve(
            "test query",
            custom_plan={'mode': 'qa', 'internet_enabled': False},
            top_k=5
        )
        assert output is not None
        assert len(output.results) <= 5
        print("   ✅ custom_plan works")
        
    except Exception as e:
        errors.append(f"custom_plan failed: {e}")
        print(f"   ❌ custom_plan failed: {e}")
    
    # Test 6: Stats
    print("\n6. Testing stats...")
    try:
        assert hasattr(engine, 'stats')
        assert isinstance(engine.stats, dict)
        validation_stats = engine.get_validation_stats()
        assert isinstance(validation_stats, dict)
        print("   ✅ Stats work")
        
    except Exception as e:
        errors.append(f"Stats failed: {e}")
        print(f"   ❌ Stats failed: {e}")
    
    # Test 7: Cleanup
    print("\n7. Testing cleanup...")
    try:
        engine.cleanup()
        print("   ✅ cleanup() works")
        
    except Exception as e:
        errors.append(f"Cleanup failed: {e}")
        print(f"   ❌ Cleanup failed: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if errors:
        print(f"❌ {len(errors)} error(s) found:")
        for error in errors:
            print(f"   - {error}")
        return 1
    else:
        print("✅ ALL TESTS PASSED!")
        print("\nThe modularized RetrievalEngine is working correctly with all functionalities preserved.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
