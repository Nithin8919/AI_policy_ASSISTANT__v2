#!/usr/bin/env python3
"""
Test Production Clause Indexer - Verify Qdrant storage works
"""

import sys
sys.path.append('.')
sys.path.append('retrieval_v3')

from production_clause_indexer import ProductionClauseIndexer

def test_production_indexer():
    """Test the production clause indexer"""
    
    print("🧪 Testing Production Clause Indexer")
    print("=" * 50)
    
    # Initialize indexer
    indexer = ProductionClauseIndexer()
    
    # Test queries
    test_queries = [
        "RTE Section 12",
        "rte section 12", 
        "Article 21A",
        "CCE Rule 7",
        "Section 4 RTE"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 30)
        
        try:
            matches = indexer.lookup_clause(query)
            
            if matches:
                print(f"✅ Found {len(matches)} matches:")
                for i, match in enumerate(matches[:2], 1):
                    print(f"  {i}. {match.clause_text}")
                    print(f"     Confidence: {match.confidence}")
                    print(f"     Chunk ID: {match.chunk_id[:8]}...")
                    print(f"     Vertical: {match.vertical}")
            else:
                print(f"❌ No matches found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎯 Production clause indexer test complete!")


if __name__ == "__main__":
    test_production_indexer()