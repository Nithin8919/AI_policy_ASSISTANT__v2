#!/usr/bin/env python3
"""
FIXED Relevance Test - Using Correct Result Structure
======================================================
Uses the ACTUAL structure returned by RetrievalRouter:
  result['text'] (not result['payload']['text'])
  result['vertical'] (not result['payload']['vertical'])
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retrieval import RetrievalRouter

def test_query_fixed(query: str, expected_keywords: list):
    """Test with CORRECT result structure"""
    
    print("\n" + "="*100)
    print(f"🎙️  QUERY: {query}")
    print("="*100)
    
    router = RetrievalRouter()
    response = router.query(query, mode="qa", top_k=5)
    
    if not response.get("success"):
        print(f"❌ FAILED: {response.get('error')}")
        return False
    
    results = response.get("results", [])
    
    if not results:
        print("❌ NO RESULTS")
        return False
    
    print(f"\n✅ Found {len(results)} results\n")
    
    relevant_count = 0
    
    for i, result in enumerate(results, 1):
        # USE CORRECT STRUCTURE
        text = result.get('text', '')
        vertical = result.get('vertical', 'N/A')
        score = result.get('score', 0)
        chunk_id = result.get('chunk_id', 'N/A')
        metadata = result.get('metadata', {})
        year = metadata.get('year', 'N/A')
        
        print(f"{'─'*100}")
        print(f"[{i}] Score: {score:.3f} | Vertical: {vertical} | Year: {year}")
        print(f"Chunk: {chunk_id}")
        print(f"{'─'*100}")
        
        # Show text
        text_preview = text[:400] if text else "NO TEXT"
        print(f"{text_preview}")
        
        if len(text) > 400:
            print(f"... ({len(text)} total chars)")
        
        # Check relevance
        text_lower = text.lower()
        matches = [kw for kw in expected_keywords if kw.lower() in text_lower]
        
        if matches:
            print(f"\n✅ RELEVANT - Contains: {matches}")
            relevant_count += 1
        else:
            print(f"\n❌ NOT RELEVANT - Missing: {expected_keywords}")
        
        print()
    
    # Summary
    print("="*100)
    relevance_rate = (relevant_count / len(results)) * 100
    print(f"📊 RELEVANCE: {relevant_count}/{len(results)} ({relevance_rate:.0f}%)")
    
    if relevance_rate >= 60:
        print("✅ GOOD - Most results relevant")
        return True
    else:
        print("❌ BAD - Most results NOT relevant")
        return False


def main():
    """Run real tests"""
    
    print("="*100)
    print("🔍 FIXED RELEVANCE TEST - Reading Correct Structure")
    print("="*100)
    
    tests = [
        {
            "query": "What are the rules for SC category teacher transfers?",
            "keywords": ["sc", "category", "teacher", "transfer"],
            "description": "Teacher Transfer FAQs (18 chunks in GOs)"
        },
        {
            "query": "What is the education budget allocation?",
            "keywords": ["budget", "education", "allocation"],
            "description": "Budget Data (635 chunks)"
        },
        {
            "query": "What does Section 12 say?",
            "keywords": ["section", "12", "education", "rte"],
            "description": "RTE Act Section 12 (4 legal chunks)"
        },
        {
            "query": "What schemes exist for minority girls schools?",
            "keywords": ["minority", "girls", "school"],
            "description": "Education Schemes (47 chunks)"
        },
        {
            "query": "Show me teacher salary expenditure data",
            "keywords": ["teacher", "salary", "expenditure"],
            "description": "Salary Data (635 budget chunks)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n{'='*100}")
        print(f"TEST: {test['description']}")
        print(f"{'='*100}")
        
        try:
            if test_query_fixed(test["query"], test["keywords"]):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Final report
    print("\n" + "="*100)
    print("📊 FINAL REPORT")
    print("="*100)
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("\n🎉 EXCELLENT! Retrieval working great!")
    elif success_rate >= 60:
        print("\n✅ GOOD! Most queries work")
    else:
        print("\n❌ BAD! Retrieval needs work")
        print("\nIssues to check:")
        print("1. Are embeddings capturing meaning?")
        print("2. Are filters working correctly?")
        print("3. Is vertical routing correct?")
    
    return success_rate >= 60

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)