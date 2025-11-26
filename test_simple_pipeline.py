#!/usr/bin/env python3
"""
Simple Pipeline Test - Direct Testing
=====================================
Direct test of the complete pipeline without complex imports.
Tests the core functionality with uploaded data.
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_qdrant_connection():
    """Test basic Qdrant connectivity"""
    try:
        from qdrant_client import QdrantClient
        
        url = os.getenv('QDRANT_URL')
        api_key = os.getenv('QDRANT_API_KEY')
        
        client = QdrantClient(url=url, api_key=api_key)
        collections = client.get_collections()
        
        print(f"✅ Connected to Qdrant: {len(collections.collections)} collections")
        
        # Check each collection
        total_points = 0
        for collection in collections.collections:
            try:
                count = client.count(collection.name)
                print(f"   📊 {collection.name}: {count.count} chunks")
                total_points += count.count
            except Exception as e:
                print(f"   ❌ {collection.name}: Error - {e}")
        
        print(f"✅ Total chunks in Qdrant: {total_points}")
        return total_points >= 600  # Should have ~689
        
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        return False

def test_embedding_consistency():
    """Test embedding configuration consistency"""
    try:
        import sys
        sys.path.append('ingestion_v2')
        from embedding.google_embedder import get_embedder
        
        embedder = get_embedder()
        
        # Test query embedding
        test_query = "teacher transfer government order"
        query_vector = embedder.embed_texts([test_query])
        
        print(f"✅ Embedding working: {len(query_vector[0])}d vector")
        print(f"   🔧 Using Google API: {embedder.is_using_google}")
        print(f"   📏 Dimension: {embedder.embedding_dimension}")
        
        # Check embedding quality
        import math
        vector = query_vector[0]
        magnitude = math.sqrt(sum(x * x for x in vector))
        is_valid = magnitude > 0.01 and all(math.isfinite(x) for x in vector)
        
        print(f"   ✓ Embedding quality: magnitude={magnitude:.4f}, valid={is_valid}")
        
        return is_valid and len(query_vector[0]) == 768
        
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False

def test_answer_generation():
    """Test Gemini answer generation"""
    try:
        import sys
        sys.path.append('retrieval')
        
        # Import answer generator
        import importlib.util
        spec = importlib.util.spec_from_file_location("answer_generator", "retrieval/answer_generator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        answer_gen = module.get_answer_generator()
        
        # Mock results for testing
        mock_results = [
            {
                "text": "Teacher transfers are governed by GO 123 which states that transfers should be based on merit and administrative requirements.",
                "vertical": "go",
                "metadata": {"go_number": "123", "year": "2023", "department": "Education"}
            },
            {
                "text": "Section 15 of the Education Act provides guidelines for teacher postings and administrative procedures.",
                "vertical": "legal", 
                "metadata": {"section_number": "15", "act_name": "Education Act"}
            }
        ]
        
        # Test QA answer
        query = "What are the rules for teacher transfers?"
        qa_answer = answer_gen.generate_qa_answer(query, mock_results)
        
        print(f"✅ QA Answer Generation:")
        print(f"   📝 Has answer: {bool(qa_answer.get('answer'))}")
        print(f"   🔗 Citations: {len(qa_answer.get('citations', []))}")
        print(f"   🤖 Model: {qa_answer.get('model')}")
        print(f"   📊 Sources used: {qa_answer.get('sources_used')}")
        
        if qa_answer.get('answer'):
            preview = qa_answer['answer'][:150] + "..." if len(qa_answer['answer']) > 150 else qa_answer['answer']
            print(f"   💬 Preview: {preview}")
        
        # Test Deep Think answer
        deep_answer = answer_gen.generate_deep_think_answer(query, mock_results)
        print(f"\n✅ Deep Think Answer Generation:")
        print(f"   📝 Has answer: {bool(deep_answer.get('answer'))}")
        print(f"   🔗 Citations: {len(deep_answer.get('citations', []))}")
        print(f"   🤖 Model: {deep_answer.get('model')}")
        print(f"   📚 Verticals: {deep_answer.get('verticals_covered', [])}")
        
        # Test Brainstorm answer
        brainstorm_answer = answer_gen.generate_brainstorm_answer("How to improve teacher training?", mock_results)
        print(f"\n✅ Brainstorm Answer Generation:")
        print(f"   📝 Has answer: {bool(brainstorm_answer.get('answer'))}")
        print(f"   💡 Creative: {'innovative' in brainstorm_answer.get('answer', '').lower()}")
        print(f"   🤖 Model: {brainstorm_answer.get('model')}")
        
        return (
            bool(qa_answer.get('answer')) and 
            bool(deep_answer.get('answer')) and 
            bool(brainstorm_answer.get('answer'))
        )
        
    except Exception as e:
        print(f"❌ Answer generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_qdrant_search():
    """Test direct search against uploaded data"""
    try:
        from qdrant_client import QdrantClient
        import sys
        sys.path.append('ingestion_v2')
        from embedding.google_embedder import get_embedder
        
        # Connect to Qdrant
        url = os.getenv('QDRANT_URL')
        api_key = os.getenv('QDRANT_API_KEY')
        client = QdrantClient(url=url, api_key=api_key)
        
        # Get embedder
        embedder = get_embedder()
        
        # Test queries
        test_queries = [
            ("teacher transfer rules", "ap_government_orders"),
            ("budget allocation education", "ap_data_reports"), 
            ("education scheme benefits", "ap_schemes")
        ]
        
        all_passed = True
        
        for query, collection in test_queries:
            print(f"\n🔍 Testing: '{query}' in {collection}")
            
            # Embed query
            query_vector = embedder.embed_texts([query])[0]
            
            # Search (correct method name)
            results = client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=3,
                with_payload=True
            ).points
            
            if results:
                print(f"   ✅ Found {len(results)} results")
                for i, result in enumerate(results[:2]):
                    score = result.score
                    text_preview = result.payload.get('text', '')[:100] + "..."
                    print(f"   📄 Result {i+1}: Score={score:.3f}")
                    print(f"      {text_preview}")
                    
                    # Check metadata
                    metadata = result.payload
                    entities = metadata.get('entities', [])
                    relations = metadata.get('relations', [])
                    print(f"      📊 Entities: {len(entities)}, Relations: {len(relations)}")
            else:
                print(f"   ❌ No results found")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Direct search test failed: {e}")
        return False

def test_end_to_end_simple():
    """Simple end-to-end test of key query"""
    try:
        # This would be the full pipeline test but simplified
        print("\n🚀 End-to-End Test: Teacher Transfer Query")
        
        # 1. Test we can embed the query
        import sys
        sys.path.append('ingestion_v2')
        from embedding.google_embedder import get_embedder
        
        embedder = get_embedder()
        query = "What are the government rules for teacher transfers in AP?"
        query_vector = embedder.embed_texts([query])[0]
        print(f"   ✅ Query embedded: {len(query_vector)}d")
        
        # 2. Test we can search Qdrant
        from qdrant_client import QdrantClient
        url = os.getenv('QDRANT_URL')
        api_key = os.getenv('QDRANT_API_KEY')
        client = QdrantClient(url=url, api_key=api_key)
        
        results = client.query_points(
            collection_name="ap_government_orders",
            query=query_vector,
            limit=5,
            with_payload=True
        ).points
        
        print(f"   ✅ Search completed: {len(results)} results")
        
        # 3. Test answer generation
        if results:
            mock_results = []
            for result in results:
                mock_results.append({
                    "text": result.payload.get('text', ''),
                    "vertical": "go",
                    "metadata": result.payload
                })
            
            # Generate answer
            import importlib.util
            spec = importlib.util.spec_from_file_location("answer_generator", "retrieval/answer_generator.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            answer_gen = module.get_answer_generator()
            answer_response = answer_gen.generate_qa_answer(query, mock_results)
            
            print(f"   ✅ Answer generated: {bool(answer_response.get('answer'))}")
            if answer_response.get('answer'):
                preview = answer_response['answer'][:200] + "..."
                print(f"   📝 Answer preview: {preview}")
                print(f"   📚 Model used: {answer_response.get('model')}")
                print(f"   🔗 Citations: {len(answer_response.get('citations', []))}")
                
            return bool(answer_response.get('answer'))
        else:
            print("   ❌ No search results to generate answer from")
            return False
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run comprehensive but simple tests"""
    print("🧪 SIMPLE PIPELINE TEST SUITE")
    print("="*50)
    
    start_time = time.time()
    tests = []
    
    print("\n1. Testing Qdrant Connection...")
    tests.append(("Qdrant Connection", test_qdrant_connection()))
    
    print("\n2. Testing Embedding Consistency...")
    tests.append(("Embedding Consistency", test_embedding_consistency()))
    
    print("\n3. Testing Answer Generation...")
    tests.append(("Answer Generation", test_answer_generation()))
    
    print("\n4. Testing Direct Search...")
    tests.append(("Direct Search", test_direct_qdrant_search()))
    
    print("\n5. Testing End-to-End...")
    tests.append(("End-to-End", test_end_to_end_simple()))
    
    # Summary
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    duration = time.time() - start_time
    
    print(f"\n{'='*50}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*50}")
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"⏱️ Duration: {duration:.2f}s")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED! System is working correctly.")
    elif passed >= total * 0.8:
        print(f"\n✅ MOSTLY WORKING! {total-passed} test(s) need attention.")
    else:
        print(f"\n⚠️ NEEDS WORK! {total-passed} test(s) failing.")
    
    # Save simple report
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": {name: result for name, result in tests},
        "summary": {
            "passed": passed,
            "total": total,
            "success_rate": passed / total,
            "duration": duration
        }
    }
    
    with open(f"simple_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

if __name__ == "__main__":
    main()