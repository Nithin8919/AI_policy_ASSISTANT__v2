#!/usr/bin/env python3
"""
Test Enhanced Legal Queries - Test the complete solution
"""

import requests
import json
import time

def test_legal_queries():
    """Test legal clause queries with enhanced system"""
    
    # Test queries - these should now work reliably
    test_queries = [
        "What is RTE Act Section 12?",
        "RTE Section 12 provisions",  
        "Article 21A Constitution",
        "CCE Rule 7 details",
        "Section 4 RTE Act",
        "Rule 12 AP Education",
        "RTE Act Section 13 admission",
    ]
    
    print("🎯 Testing Enhanced Legal Query System")
    print("=" * 60)
    print("Testing queries that should now work with:")
    print("✅ Legal clause expansion in query rewriter")  
    print("✅ Legal vertical boosting")
    print("✅ BM25 keyword injection")
    print("✅ Clause indexer (388 clauses)")
    print("✅ Fallback exact clause scanner")
    print()
    
    successes = 0
    failures = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        print("-" * 40)
        
        try:
            # Test via API
            response = requests.post(
                "http://localhost:8000/query",
                json={"query": query, "top_k": 5},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and len(data['results']) > 0:
                    successes += 1
                    print(f"✅ SUCCESS - Found {len(data['results'])} results")
                    
                    # Show best result
                    best_result = data['results'][0]
                    print(f"   📄 Best match: {best_result.get('source', 'unknown')}")
                    print(f"   📊 Score: {best_result.get('score', 0):.3f}")
                    print(f"   📝 Preview: {best_result.get('content', '')[:150]}...")
                    
                    # Check for clause indexer usage
                    if any('clause_indexer' in str(r.get('rewrite_source', '')) for r in data['results']):
                        print(f"   🎯 Used clause indexer!")
                    
                else:
                    failures += 1  
                    print(f"❌ FAILURE - No results returned")
                    print(f"   Response: {data}")
            else:
                failures += 1
                print(f"❌ FAILURE - HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            failures += 1
            print(f"❌ FAILURE - Exception: {e}")
        
        # Rate limiting
        time.sleep(1)
    
    # Final results
    print(f"\n🎉 Test Results Summary")
    print("=" * 60)
    print(f"✅ Successes: {successes}/{len(test_queries)} ({successes/len(test_queries)*100:.1f}%)")
    print(f"❌ Failures: {failures}/{len(test_queries)} ({failures/len(test_queries)*100:.1f}%)")
    
    if successes >= len(test_queries) * 0.8:  # 80% success rate
        print(f"\n🚀 EXCELLENT! Legal clause queries now work reliably!")
        print(f"📈 The enhanced system provides consistent results for:")
        print(f"   • RTE Act sections")
        print(f"   • Constitutional articles") 
        print(f"   • CCE rules")
        print(f"   • General legal clauses")
    elif successes >= len(test_queries) * 0.5:  # 50% success rate  
        print(f"\n👍 GOOD IMPROVEMENT! Some queries still need work.")
        print(f"💡 Consider adding more specific clause patterns.")
    else:
        print(f"\n⚠️ Still needs improvement. Check API connectivity and index.")

if __name__ == "__main__":
    test_legal_queries()