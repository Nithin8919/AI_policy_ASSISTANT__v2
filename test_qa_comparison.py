#!/usr/bin/env python3
"""
QA Mode Comparison Test
=====================
Test whether QA mode gives better answers with V2 features enabled vs disabled.
"""

import os
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables
try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_qa_comparison():
    """Compare QA mode performance with and without V2 features"""
    print("🔬 Testing QA Mode: V2 vs V1 Comparison")
    print("=" * 60)
    
    # Test queries for comparison
    test_queries = [
        "What are the teacher transfer rules in AP?",
        "How is education budget allocated for primary schools?",
        "What is Section 12 admission process?",
        "What are the eligibility criteria for teacher recruitment?",
        "How does the midday meal scheme work?"
    ]
    
    results = {}
    
    for query in test_queries:
        print(f"\n🔍 Testing Query: '{query}'")
        print("-" * 50)
        
        query_results = {
            "query": query,
            "v2_enabled": None,
            "v2_disabled": None
        }
        
        # Test with V2 enabled (current state)
        print("\n📊 V2 Features ENABLED:")
        try:
            v2_result = test_single_query_v2_enabled(query)
            query_results["v2_enabled"] = v2_result
            print(f"✅ V2 Test completed")
            print(f"   Results: {len(v2_result.get('retrieval_results', []))} documents")
            print(f"   Answer length: {len(v2_result.get('answer', ''))}")
            print(f"   Processing time: {v2_result.get('total_time', 0):.2f}s")
        except Exception as e:
            print(f"❌ V2 test failed: {e}")
            query_results["v2_enabled"] = {"error": str(e)}
        
        # Test with V2 disabled
        print("\n📊 V2 Features DISABLED:")
        try:
            v1_result = test_single_query_v2_disabled(query)
            query_results["v2_disabled"] = v1_result
            print(f"✅ V1 Test completed")
            print(f"   Results: {len(v1_result.get('retrieval_results', []))} documents")
            print(f"   Answer length: {len(v1_result.get('answer', ''))}")
            print(f"   Processing time: {v1_result.get('total_time', 0):.2f}s")
        except Exception as e:
            print(f"❌ V1 test failed: {e}")
            query_results["v2_disabled"] = {"error": str(e)}
        
        results[query] = query_results
    
    # Generate comparison report
    print("\n" + "=" * 60)
    print("COMPARISON ANALYSIS")
    print("=" * 60)
    
    generate_comparison_report(results)
    
    # Save detailed results
    save_results(results)
    
    return results

def test_single_query_v2_enabled(query):
    """Test single query with V2 features enabled"""
    from retrieval.router import RetrievalRouter
    from retrieval import get_answer_generator
    
    start_time = time.time()
    
    # Initialize with V2 features (current default)
    router = RetrievalRouter()
    answer_generator = get_answer_generator()
    
    # Get retrieval results
    retrieval_start = time.time()
    response = router.query(query, mode="qa", top_k=20)
    retrieval_time = time.time() - retrieval_start
    
    if not response.get("success"):
        raise Exception(f"Retrieval failed: {response.get('error')}")
    
    results = response.get("results", [])
    
    # Generate answer
    answer_start = time.time()
    answer_response = answer_generator.generate_qa_answer(query, results)
    answer_time = time.time() - answer_start
    
    total_time = time.time() - start_time
    
    return {
        "retrieval_results": results,
        "answer": answer_response.get("answer", ""),
        "citations": answer_response.get("citations", []),
        "sources_used": answer_response.get("sources_used", 0),
        "mode_detected": response.get("mode"),
        "mode_confidence": response.get("mode_confidence", 0),
        "verticals_searched": response.get("verticals_searched", []),
        "retrieval_time": retrieval_time,
        "answer_time": answer_time,
        "total_time": total_time,
        "hybrid_search_used": getattr(router, 'enable_hybrid_search', False),
        "features_used": {
            "hybrid_search": True,
            "dynamic_top_k": True,
            "v2_classifier": True,
            "v2_router": True
        }
    }

def test_single_query_v2_disabled(query):
    """Test single query with V2 features disabled"""
    from retrieval.router import RetrievalRouter
    from retrieval import get_answer_generator
    
    start_time = time.time()
    
    # Initialize with V2 features disabled
    router = RetrievalRouter(enable_hybrid_search=False)
    answer_generator = get_answer_generator()
    
    # Temporarily disable V2 features by modifying settings
    try:
        from retrieval.config import settings
        original_flags = settings.FEATURE_FLAGS.copy()
        
        # Disable V2 features
        settings.FEATURE_FLAGS['use_hybrid_search'] = False
        settings.FEATURE_FLAGS['dynamic_top_k'] = False
        settings.FEATURE_FLAGS['use_intent_classifier_v2'] = False
        settings.FEATURE_FLAGS['use_query_router_v2'] = False
        
        # Get retrieval results with V1 approach
        retrieval_start = time.time()
        response = router.query(query, mode="qa", top_k=5)  # Use smaller top_k like V1
        retrieval_time = time.time() - retrieval_start
        
        if not response.get("success"):
            raise Exception(f"Retrieval failed: {response.get('error')}")
        
        results = response.get("results", [])
        
        # Generate answer
        answer_start = time.time()
        answer_response = answer_generator.generate_qa_answer(query, results)
        answer_time = time.time() - answer_start
        
        total_time = time.time() - start_time
        
        return {
            "retrieval_results": results,
            "answer": answer_response.get("answer", ""),
            "citations": answer_response.get("citations", []),
            "sources_used": answer_response.get("sources_used", 0),
            "mode_detected": response.get("mode"),
            "mode_confidence": response.get("mode_confidence", 0),
            "verticals_searched": response.get("verticals_searched", []),
            "retrieval_time": retrieval_time,
            "answer_time": answer_time,
            "total_time": total_time,
            "hybrid_search_used": False,
            "features_used": {
                "hybrid_search": False,
                "dynamic_top_k": False,
                "v2_classifier": False,
                "v2_router": False
            }
        }
    
    finally:
        # Restore original flags
        if 'original_flags' in locals():
            settings.FEATURE_FLAGS.update(original_flags)

def generate_comparison_report(results):
    """Generate detailed comparison report"""
    v2_wins = 0
    v1_wins = 0
    ties = 0
    
    print("\n📊 DETAILED COMPARISON:")
    print("-" * 40)
    
    for query, data in results.items():
        v2_data = data.get("v2_enabled", {})
        v1_data = data.get("v2_disabled", {})
        
        if "error" in v2_data or "error" in v1_data:
            continue
        
        print(f"\nQuery: {query}")
        print(f"{'Metric':<20} {'V2':<15} {'V1':<15} {'Winner'}")
        print("-" * 65)
        
        # Compare metrics
        metrics = [
            ("Results Count", len(v2_data.get('retrieval_results', [])), len(v1_data.get('retrieval_results', []))),
            ("Answer Length", len(v2_data.get('answer', '')), len(v1_data.get('answer', ''))),
            ("Sources Used", v2_data.get('sources_used', 0), v1_data.get('sources_used', 0)),
            ("Citations", len(v2_data.get('citations', [])), len(v1_data.get('citations', []))),
            ("Mode Confidence", f"{v2_data.get('mode_confidence', 0):.2f}", f"{v1_data.get('mode_confidence', 0):.2f}"),
            ("Total Time (s)", f"{v2_data.get('total_time', 0):.2f}", f"{v1_data.get('total_time', 0):.2f}")
        ]
        
        query_v2_wins = 0
        query_v1_wins = 0
        
        for metric_name, v2_val, v1_val in metrics:
            if isinstance(v2_val, (int, float)) and isinstance(v1_val, (int, float)):
                if metric_name == "Total Time (s)":  # Lower is better for time
                    winner = "V1" if v1_val < v2_val else "V2" if v2_val < v1_val else "Tie"
                    if winner == "V1": query_v1_wins += 1
                    elif winner == "V2": query_v2_wins += 1
                else:  # Higher is better for other metrics
                    winner = "V2" if v2_val > v1_val else "V1" if v1_val > v2_val else "Tie"
                    if winner == "V2": query_v2_wins += 1
                    elif winner == "V1": query_v1_wins += 1
            else:
                winner = "N/A"
            
            print(f"{metric_name:<20} {str(v2_val):<15} {str(v1_val):<15} {winner}")
        
        # Determine query winner
        if query_v2_wins > query_v1_wins:
            v2_wins += 1
            query_winner = "V2"
        elif query_v1_wins > query_v2_wins:
            v1_wins += 1
            query_winner = "V1"
        else:
            ties += 1
            query_winner = "Tie"
        
        print(f"\n🏆 Query Winner: {query_winner}")
        
        # Show answer quality comparison
        if v2_data.get('answer') and v1_data.get('answer'):
            print(f"\n📝 Answer Preview Comparison:")
            print(f"V2: {v2_data.get('answer', '')[:150]}...")
            print(f"V1: {v1_data.get('answer', '')[:150]}...")
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"V2 Wins: {v2_wins}")
    print(f"V1 Wins: {v1_wins}")
    print(f"Ties: {ties}")
    print(f"Total Queries: {len(results)}")
    
    if v2_wins > v1_wins:
        print("\n🎉 V2 Features show BETTER performance!")
        print("   ✅ Enhanced retrieval and answer quality")
    elif v1_wins > v2_wins:
        print("\n⚠️ V1 Features show better performance")
        print("   ❌ V2 features may need adjustment")
    else:
        print("\n🤝 Performance is similar between V1 and V2")

def save_results(results):
    """Save detailed results to file"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"qa_comparison_results_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Detailed results saved: {filename}")
    except Exception as e:
        print(f"\n⚠️ Could not save results: {e}")

if __name__ == "__main__":
    test_qa_comparison()