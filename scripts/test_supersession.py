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
from retrieval_v3.retrieval_core.supersession_manager import SupersessionManager

def test_supersession():
    print("🧪 Testing Supersession Manager...\n")
    
    try:
        client = get_qdrant_client()
        
        print("📊 Initializing SupersessionManager...")
        manager = SupersessionManager(client)
        
        print(f"\n✅ Supersession Manager Loaded:")
        print(f"   - Superseded documents: {len(manager.superseded_ids)}")
        print(f"   - Supersession mappings: {len(manager.supersession_map)}")
        
        if manager.supersession_map:
            print(f"\n📋 Sample Supersessions:")
            for i, (old_id, new_id) in enumerate(list(manager.supersession_map.items())[:5], 1):
                print(f"   {i}. {old_id} → {new_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_supersession()
