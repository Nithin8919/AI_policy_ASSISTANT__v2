
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Verify retrieval path exists
retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

from retrieval.retrieval_core.qdrant_client import get_qdrant_client

def inspect_payload():
    try:
        print("🔌 Connecting to Qdrant...")
        client = get_qdrant_client().client
        
        # Fetch one point
        res = client.scroll(
            collection_name="ap_government_orders",
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        
        if res[0]:
            point = res[0][0]
            payload = point.payload
            print(f"\n📄 Document ID: {point.id}")
            print("🔍 Payload Metadata Keys:")
            for k in sorted(payload.keys()):
                val_preview = str(payload[k])[:50] + "..." if len(str(payload[k])) > 50 else str(payload[k])
                print(f" - {k}: {val_preview}")
            
            print("\n🔍 Checking 'entities' field structure:")
            if 'entities' in payload:
                ent = payload['entities']
                if isinstance(ent, dict):
                    for k, v in ent.items():
                         print(f"   - entities.{k}: {v}")
                else:
                    print(f"   - entities is type {type(ent)}: {ent}")
            else:
                print("   ⚠️ 'entities' field NOT found in root payload")

            # Check for top-level year vs nested
            if 'year' in payload:
                print(f"\nFound top-level 'year': {payload['year']}")
            
        else:
            print("❌ No documents found in collection!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_payload()
