import os
import sys
from dotenv import load_dotenv
import json

load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

sys.path.insert(0, os.path.join(project_root, 'retrieval'))
sys.path.insert(0, os.path.join(project_root, 'retrieval_v3'))

from pipeline.retrieval_engine import RetrievalEngine
from retrieval.retrieval_core.qdrant_client import get_qdrant_client

def test_go_24_query():
    print("🧪 Testing GO 24 Retrieval...\n")
    
    try:
        qdrant_client = get_qdrant_client()
        v3_engine = RetrievalEngine(qdrant_client=qdrant_client)
        
        query = "What are the key provisions in GO MS No.24 related to teacher eligibility?"
        
        print(f"Query: {query}\n")
        
        # Run retrieval (no max_results param)
        output = v3_engine.retrieve(query)
        
        print(f"📊 Results: {output.final_count} documents found")
        print(f"⏱️  Time: {output.processing_time:.2f}s\n")
        
        # Check interpretation
        print(f"🔍 Query Interpretation:")
        print(f"   Type: {output.interpretation.query_type.value}")
        print(f"   Entities: {output.interpretation.detected_entities}")
        print(f"   Keywords: {output.interpretation.keywords[:5]}")
        print()
        
        # Show top results
        print("📄 Top Results:")
        for i, result in enumerate(output.results[:5], 1):
            print(f"\n{i}. {result.doc_id} (score: {result.score:.3f})")
            print(f"   Vertical: {result.vertical}")
            print(f"   Year: {result.metadata.get('year', 'N/A')}")
            print(f"   GO Number: {result.metadata.get('go_number', 'N/A')}")
            print(f"   Content: {result.content[:100]}...")
        
        # Check if any GO 24 was found
        go_24_results = [r for r in output.results if r.metadata.get('go_number') == 24]
        print(f"\n✅ Found {len(go_24_results)} results with go_number=24")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_go_24_query()
