import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

from retrieval.retrieval_core.qdrant_client import get_qdrant_client

def check_collections():
    print("🔍 Checking Collection Data...\n")
    
    try:
        client = get_qdrant_client().client
        
        collections_to_check = ['go', 'ap_government_orders']
        
        for coll_name in collections_to_check:
            try:
                info = client.get_collection(coll_name)
                print(f"📊 Collection: {coll_name}")
                print(f"   Points: {info.points_count}")
                print(f"   Vectors: {info.vectors_count}")
                
                # Sample a document
                points, _ = client.scroll(
                    collection_name=coll_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )
                
                if points:
                    payload = points[0].payload
                    print(f"   Sample keys: {list(payload.keys())[:10]}")
                    
                    # Check for relations
                    relations = payload.get('relations', [])
                    if relations:
                        print(f"   Has relations: YES ({len(relations)} relations)")
                        if relations:
                            rel_types = set(r.get('relation_type') or r.get('type') for r in relations)
                            print(f"   Relation types: {rel_types}")
                    else:
                        print(f"   Has relations: NO")
                print()
                
            except Exception as e:
                print(f"❌ Collection {coll_name}: {e}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_collections()
