#!/usr/bin/env python3
"""
Comprehensive test for modularized RetrievalEngine
Tests all functionality to ensure nothing broke during modularization
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "retrieval_v3"))

def test_imports():
    """Test 1: Verify all imports work correctly"""
    print("=" * 80)
    print("TEST 1: Import Tests")
    print("=" * 80)
    
    try:
        # Test main imports
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine, RetrievalResult, RetrievalOutput, retrieve
        print("✅ Main imports successful")
        
        # Test module imports
        from retrieval_v3.pipeline import RetrievalEngine as Engine2, RetrievalResult as Result2, RetrievalOutput as Output2
        print("✅ Module imports successful")
        
        # Test direct model imports
        from retrieval_v3.pipeline.models import RetrievalResult as Result3, RetrievalOutput as Output3
        print("✅ Model imports successful")
        
        # Test coordinator imports (internal, but should work)
        from retrieval_v3.pipeline.query_coordinator import QueryUnderstandingCoordinator
        from retrieval_v3.pipeline.retrieval_executor import RetrievalExecutor
        from retrieval_v3.pipeline.result_processor import ResultProcessor
        from retrieval_v3.pipeline.reranking_coordinator import RerankingCoordinator
        from retrieval_v3.pipeline.legal_clause_handler import LegalClauseHandler
        from retrieval_v3.pipeline.internet_handler import InternetSearchHandler
        from retrieval_v3.pipeline.engine_stats import EngineStatsManager
        print("✅ Coordinator imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_engine_initialization():
    """Test 2: Verify engine initializes correctly"""
    print("\n" + "=" * 80)
    print("TEST 2: Engine Initialization")
    print("=" * 80)
    
    try:
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
        
        # Test initialization without Qdrant (stub mode)
        engine = RetrievalEngine(
            qdrant_client=None,
            embedder=None,
            use_llm_rewrites=False,
            use_llm_reranking=False,
            enable_cache=False
        )
        print("✅ Engine initialized in stub mode")
        
        # Verify all coordinators are initialized
        assert hasattr(engine, 'query_coordinator'), "Missing query_coordinator"
        assert hasattr(engine, 'retrieval_executor'), "Missing retrieval_executor"
        assert hasattr(engine, 'result_processor'), "Missing result_processor"
        assert hasattr(engine, 'reranking_coordinator'), "Missing reranking_coordinator"
        assert hasattr(engine, 'legal_clause_handler'), "Missing legal_clause_handler"
        assert hasattr(engine, 'internet_handler'), "Missing internet_handler"
        assert hasattr(engine, 'stats_manager'), "Missing stats_manager"
        print("✅ All coordinators initialized")
        
        # Verify core components
        assert hasattr(engine, 'normalizer'), "Missing normalizer"
        assert hasattr(engine, 'interpreter'), "Missing interpreter"
        assert hasattr(engine, 'router'), "Missing router"
        assert hasattr(engine, 'plan_builder'), "Missing plan_builder"
        print("✅ All core components initialized")
        
        # Verify public methods exist
        assert hasattr(engine, 'retrieve'), "Missing retrieve method"
        assert hasattr(engine, 'retrieve_and_answer'), "Missing retrieve_and_answer method"
        assert hasattr(engine, 'run_diagnostic'), "Missing run_diagnostic method"
        assert hasattr(engine, 'cleanup'), "Missing cleanup method"
        assert hasattr(engine, 'get_validation_stats'), "Missing get_validation_stats method"
        print("✅ All public methods exist")
        
        return engine
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_retrieve_method(engine):
    """Test 3: Verify retrieve() method works"""
    print("\n" + "=" * 80)
    print("TEST 3: retrieve() Method")
    print("=" * 80)
    
    try:
        test_queries = [
            "What is Section 12(1)(c) of RTE Act?",
            "Design a comprehensive FLN framework",
        ]
        
        for query in test_queries:
            print(f"\n📝 Testing query: '{query}'")
            
            # Test basic retrieve
            output = engine.retrieve(query)
            
            # Verify output structure
            assert hasattr(output, 'query'), "Missing query attribute"
            assert hasattr(output, 'normalized_query'), "Missing normalized_query attribute"
            assert hasattr(output, 'interpretation'), "Missing interpretation attribute"
            assert hasattr(output, 'plan'), "Missing plan attribute"
            assert hasattr(output, 'rewrites'), "Missing rewrites attribute"
            assert hasattr(output, 'results'), "Missing results attribute"
            assert hasattr(output, 'processing_time'), "Missing processing_time attribute"
            print(f"   ✅ Output structure valid")
            
            # Verify interpretation
            assert output.interpretation is not None, "Interpretation is None"
            assert hasattr(output.interpretation, 'query_type'), "Missing query_type"
            assert hasattr(output.interpretation, 'scope'), "Missing scope"
            print(f"   ✅ Interpretation: {output.interpretation.query_type.value}")
            
            # Verify plan
            assert output.plan is not None, "Plan is None"
            assert hasattr(output.plan, 'num_rewrites'), "Missing num_rewrites"
            assert hasattr(output.plan, 'top_k_total'), "Missing top_k_total"
            print(f"   ✅ Plan: {output.plan.mode}, top_k={output.plan.top_k_total}")
            
            # Verify results
            assert isinstance(output.results, list), "Results is not a list"
            print(f"   ✅ Found {len(output.results)} results")
            
            # Verify rewrites
            assert isinstance(output.rewrites, list), "Rewrites is not a list"
            assert len(output.rewrites) > 0, "No rewrites generated"
            print(f"   ✅ Generated {len(output.rewrites)} rewrites")
            
            # Test with custom_plan
            output2 = engine.retrieve(query, custom_plan={'mode': 'qa', 'internet_enabled': False})
            assert output2 is not None, "Custom plan retrieve failed"
            print(f"   ✅ Custom plan works")
            
            # Test with top_k
            output3 = engine.retrieve(query, top_k=5)
            assert output3 is not None, "Top_k retrieve failed"
            assert len(output3.results) <= 5, "Top_k limit not respected"
            print(f"   ✅ Top_k limit works")
        
        print("\n✅ retrieve() method test passed")
        return True
    except Exception as e:
        print(f"❌ retrieve() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retrieve_and_answer(engine):
    """Test 4: Verify retrieve_and_answer() method works"""
    print("\n" + "=" * 80)
    print("TEST 4: retrieve_and_answer() Method")
    print("=" * 80)
    
    try:
        query = "What are the key provisions in RTE Act?"
        
        # Test with validation
        output, answer, validation = engine.retrieve_and_answer(
            query=query,
            mode="qa",
            validate_answer=True
        )
        
        assert output is not None, "RetrievalOutput is None"
        assert answer is not None, "Answer is None"
        assert validation is not None, "Validation metadata is None"
        print("✅ retrieve_and_answer() returned all components")
        
        # Verify answer structure
        assert hasattr(answer, 'summary'), "Missing summary"
        assert hasattr(answer, 'sections'), "Missing sections"
        assert hasattr(answer, 'citations'), "Missing citations"
        print("✅ Answer structure valid")
        
        # Test without validation
        output2, answer2, validation2 = engine.retrieve_and_answer(
            query=query,
            mode="qa",
            validate_answer=False
        )
        assert output2 is not None, "RetrievalOutput is None (no validation)"
        assert answer2 is not None, "Answer is None (no validation)"
        print("✅ retrieve_and_answer() works without validation")
        
        print("\n✅ retrieve_and_answer() method test passed")
        return True
    except Exception as e:
        print(f"❌ retrieve_and_answer() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_run_diagnostic(engine):
    """Test 5: Verify run_diagnostic() method works"""
    print("\n" + "=" * 80)
    print("TEST 5: run_diagnostic() Method")
    print("=" * 80)
    
    try:
        query = "What are the rules for RTE reimbursement?"
        
        # Test full diagnostic
        result = engine.run_diagnostic(query, test_type="full")
        assert result is not None, "Diagnostic result is None"
        assert isinstance(result, dict), "Diagnostic result is not a dict"
        print("✅ Full diagnostic works")
        
        # Test individual test types
        test_types = ["sanity", "missing", "structure", "reasoning", "contradiction"]
        for test_type in test_types:
            result = engine.run_diagnostic(query, test_type=test_type)
            assert result is not None, f"{test_type} test result is None"
            print(f"   ✅ {test_type} test works")
        
        print("\n✅ run_diagnostic() method test passed")
        return True
    except Exception as e:
        print(f"❌ run_diagnostic() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stats_and_cleanup(engine):
    """Test 6: Verify stats and cleanup methods"""
    print("\n" + "=" * 80)
    print("TEST 6: Stats and Cleanup Methods")
    print("=" * 80)
    
    try:
        # Test stats access
        assert hasattr(engine, 'stats'), "Missing stats attribute"
        assert isinstance(engine.stats, dict), "Stats is not a dict"
        print("✅ Stats attribute accessible")
        
        # Test get_validation_stats
        validation_stats = engine.get_validation_stats()
        assert isinstance(validation_stats, dict), "Validation stats is not a dict"
        assert 'total_validated' in validation_stats, "Missing total_validated"
        print("✅ get_validation_stats() works")
        
        # Test cleanup
        engine.cleanup()
        print("✅ cleanup() works")
        
        print("\n✅ Stats and cleanup test passed")
        return True
    except Exception as e:
        print(f"❌ Stats/cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_classes():
    """Test 7: Verify data classes work correctly"""
    print("\n" + "=" * 80)
    print("TEST 7: Data Classes")
    print("=" * 80)
    
    try:
        from retrieval_v3.pipeline.models import RetrievalResult, RetrievalOutput
        from retrieval_v3.pipeline.retrieval_engine import RetrievalResult as Result2, RetrievalOutput as Output2
        
        # Test RetrievalResult
        result = RetrievalResult(
            chunk_id="test_123",
            doc_id="doc_456",
            content="Test content",
            score=0.95,
            vertical="test"
        )
        assert result.chunk_id == "test_123", "Chunk ID mismatch"
        assert result.score == 0.95, "Score mismatch"
        print("✅ RetrievalResult works")
        
        # Test that both imports work
        result2 = Result2(
            chunk_id="test_789",
            doc_id="doc_012",
            content="Test content 2",
            score=0.85,
            vertical="test2"
        )
        assert result2.chunk_id == "test_789", "Chunk ID mismatch (import 2)"
        print("✅ RetrievalResult backward compatibility works")
        
        print("\n✅ Data classes test passed")
        return True
    except Exception as e:
        print(f"❌ Data classes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convenience_function():
    """Test 8: Verify convenience function works"""
    print("\n" + "=" * 80)
    print("TEST 8: Convenience Function")
    print("=" * 80)
    
    try:
        from retrieval_v3.pipeline.retrieval_engine import retrieve
        
        # Test convenience function
        output = retrieve("test query", qdrant_client=None, embedder=None)
        assert output is not None, "Convenience function returned None"
        assert hasattr(output, 'query'), "Missing query attribute"
        print("✅ Convenience function works")
        
        print("\n✅ Convenience function test passed")
        return True
    except Exception as e:
        print(f"❌ Convenience function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST SUITE FOR MODULARIZED RETRIEVAL ENGINE")
    print("=" * 80)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Initialization
    engine = test_engine_initialization()
    results.append(("Initialization", engine is not None))
    
    if engine is None:
        print("\n❌ Cannot continue tests - engine initialization failed")
        return
    
    # Test 3: retrieve()
    results.append(("retrieve()", test_retrieve_method(engine)))
    
    # Test 4: retrieve_and_answer()
    results.append(("retrieve_and_answer()", test_retrieve_and_answer(engine)))
    
    # Test 5: run_diagnostic()
    results.append(("run_diagnostic()", test_run_diagnostic(engine)))
    
    # Test 6: Stats and cleanup
    results.append(("Stats & Cleanup", test_stats_and_cleanup(engine)))
    
    # Test 7: Data classes
    results.append(("Data Classes", test_data_classes()))
    
    # Test 8: Convenience function
    results.append(("Convenience Function", test_convenience_function()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The modularized engine works correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
