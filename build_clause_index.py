#!/usr/bin/env python3
"""
Build Clause Index - One-time script to build clause index from existing data
Run this once to create the clause index for instant clause lookups
"""

import sys
from pathlib import Path

# Add retrieval_v3 to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "retrieval_v3"))

from qdrant_client import QdrantClient
from retrieval_v3.utils.clause_indexer import ClauseIndexer


def main():
    """Build clause index from existing Qdrant collections"""
    
    print("🚀 Building Clause Index for Legal Clause Queries")
    print("=" * 60)
    print("This will scan your existing data to create instant clause lookups")
    print("No data will be modified - only reading existing chunks")
    print()
    
    # Connect to Qdrant
    try:
        qdrant = QdrantClient(host='localhost', port=6333)
        print("✅ Connected to Qdrant")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        print("Make sure Qdrant is running on localhost:6333")
        return
    
    # Initialize indexer
    indexer = ClauseIndexer(qdrant, index_file='clause_index.json')
    
    # Collections to scan
    collections_to_scan = [
        'ap_legal_documents',
        'ap_government_orders',
        # Add more collections as needed
    ]
    
    # Build index
    print(f"📄 Scanning {len(collections_to_scan)} collections:")
    for collection in collections_to_scan:
        print(f"  - {collection}")
    print()
    
    try:
        clause_index = indexer.build_index(collections_to_scan)
        
        # Show results
        stats = indexer.get_stats()
        print(f"✅ Successfully built clause index!")
        print(f"📊 Statistics:")
        print(f"  Total clauses indexed: {stats['total_clauses']}")
        print(f"  Average confidence: {stats['avg_confidence']:.2f}")
        print(f"  By clause type: {stats['by_type']}")
        print(f"  By vertical: {stats['by_vertical']}")
        
        # Test some lookups
        print(f"\n🔍 Testing clause lookups:")
        test_queries = [
            "RTE Act Section 12",
            "Article 21A",
            "CCE Rule 7",
            "Section 4"
        ]
        
        for query in test_queries:
            matches = indexer.lookup_clause(query)
            print(f"  '{query}' -> {len(matches)} matches")
            
            if matches:
                best_match = matches[0]
                print(f"    Best: {best_match.clause_text} (confidence: {best_match.confidence:.2f})")
                print(f"    Content: {best_match.content[:80]}...")
        
        print(f"\n🎯 Clause index saved to 'clause_index.json'")
        print(f"🚀 Your system now has instant clause lookup capability!")
        
    except Exception as e:
        print(f"❌ Failed to build clause index: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()