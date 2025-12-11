import os
import sys
from dotenv import load_dotenv

load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

from retrieval.retrieval_core.qdrant_client import get_qdrant_client

def search_go_24():
    print("🔍 Searching for GO MS No.24 in Qdrant...\n")
    
    try:
        client = get_qdrant_client().client
        
        # Strategy 1: Search by go_number field
        print("1️⃣ Searching by go_number=24...")
        points, _ = client.scroll(
            collection_name="ap_government_orders",
            scroll_filter={
                "must": [
                    {"key": "go_number", "match": {"value": 24}}
                ]
            },
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if points:
            print(f"   ✅ Found {len(points)} documents with go_number=24")
            for p in points[:3]:
                print(f"      - doc_id: {p.payload.get('doc_id')}")
                print(f"        vertical: {p.payload.get('vertical')}")
                print(f"        year: {p.payload.get('year')}")
                print(f"        department: {p.payload.get('department')}")
                print()
        else:
            print("   ❌ No documents found with go_number=24")
        
        # Strategy 2: Search by doc_id pattern
        print("\n2️⃣ Searching by doc_id containing '24'...")
        points, _ = client.scroll(
            collection_name="ap_government_orders",
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        matching_docs = [p for p in points if 'ms24' in p.payload.get('doc_id', '').lower() or '_24' in p.payload.get('doc_id', '')]
        
        if matching_docs:
            print(f"   ✅ Found {len(matching_docs)} documents with 'ms24' or '_24' in doc_id")
            for p in matching_docs[:5]:
                go_num = p.payload.get('go_number')
                print(f"      - doc_id: {p.payload.get('doc_id')}")
                print(f"        go_number: {go_num} (Type: {type(go_num)})")
                print(f"        year: {p.payload.get('year')}")
                print(f"        All keys: {list(p.payload.keys())}")
        else:
            print("   ❌ No documents found with 'ms24' or '_24' in doc_id")
        
        # Strategy 3: Full text search
        print("\n3️⃣ Searching full text for 'GO MS No.24' or 'G.O.Ms.No.24'...")
        # This would require a text search - let's check a few docs
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    search_go_24()
