
import os
import sys
import time
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Add project root to path
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Get absolute path to project root (2 levels up from scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Verify retrieval path exists
retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

print(f"📂 Added project root to path: {project_root}")

try:
    # Try importing using the pattern from main_v3.py
    # "from retrieval.retrieval_core.qdrant_client import get_qdrant_client"
    # Make sure we can find 'retrieval' module
    from retrieval.retrieval_core.qdrant_client import get_qdrant_client
    print("✅ Imported get_qdrant_client successfully")
except ImportError:
    # Fallback or deeper search if needed
    print("⚠️ Direct import failed, trying explicit sys.path hack for 'retrieval'")
    sys.path.append(os.path.join(project_root, 'retrieval'))
    from retrieval_core.qdrant_client import get_qdrant_client

def fix_indexes():
    try:
        print("🔌 Connecting to Qdrant...")
        client = get_qdrant_client()
        
        # Get the actual QdrantClient from the wrapper
        qdrant_client = client.client
        
        collection_name = "ap_government_orders"
        
        # Verify collection exists (using wrapper's method or client's)
        if not client.collection_exists(collection_name):
            print(f"❌ Collection {collection_name} does not exist!")
            return

        print(f"✅ Collection {collection_name} found.")
        
        # Define indexes to create
        # We use 'keyword' for string fields to ensure exact matching
        indexes_to_create = [
            ("entities.years", "keyword"),
            ("entities.go_numbers", "keyword"),
            ("entities.sections", "keyword"),
            ("entities.acts", "keyword"),
            ("entities.departments", "keyword"),
            ("entities.schemes", "keyword"),
            ("entities.go_refs", "keyword"),
            ("date_issued_ts", "integer"),
            ("is_superseded", "keyword"),
            ("vertical", "keyword"),
            ("go_number", "integer"),  # Keep integer index
            ("go_number", "keyword"),  # CRITICAL: Add keyword index for string matching
            ("year", "integer"),  # Already exists, but ensure it's there
        ]
        
        for field_name, field_type in indexes_to_create:
            print(f"🛠️ Creating index for '{field_name}' ({field_type})...")
            try:
                # Use the underlying client for index creation
                qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"   ✅ Index creation initiated for {field_name}")
            except Exception as e:
                # Often returns error if index already exists, which is fine
                print(f"   ⚠️ result: {e}")
                
        print("\n⏳ Waiting 5 seconds for indexes to stabilize...")
        time.sleep(5)
        
        print("\n🔍 Verifying indexes...")
        info = qdrant_client.get_collection(collection_name)
        schema = info.payload_schema
        
        if schema:
            print(f"✅ Current Payload Indexes:")
            for field, field_info in schema.items():
                print(f" - {field}: {field_info.data_type}")
        else:
            print("❌ No payload indexes found reported by server (might take time).")
            
        print("\n✅ Schema update complete!")
            
    except Exception as e:
        print(f"❌ Error fixing indexes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_indexes()
