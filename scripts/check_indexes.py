
import os
import sys
from qdrant_client import QdrantClient

# Add project root to path
sys.path.insert(0, os.getcwd())

from retrieval_v3.infra.qdrant_manager import QdrantManager

def check_indexes():
    try:
        # Initialize client
        qm = QdrantManager()
        client = qm.client
        
        collection_name = "ap_government_orders"
        
        print(f"Checking indexes for collection: {collection_name}")
        info = client.get_collection(collection_name)
        
        print(f"Status: {info.status}")
        print(f"Vectors count: {info.vectors_count}")
        print(f"Indexed payload fields:")
        
        # In newer qdrant clients, payload_schema might be dict or object
        schema = info.payload_schema
        if schema:
            for field, field_info in schema.items():
                print(f" - {field}: {field_info.data_type}")
        else:
            print(" - No payload indexes found!")
            
    except Exception as e:
        print(f"Error checking indexes: {e}")

if __name__ == "__main__":
    check_indexes()
