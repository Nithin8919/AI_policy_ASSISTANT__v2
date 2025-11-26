#!/usr/bin/env python3
"""
Cleanup Test Data from Qdrant
==============================
Removes test data uploaded during testing.
"""

import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

sys.path.append('retrieval')
from config.vertical_map import get_collection_name, get_all_collections

def cleanup_test_data():
    """Remove test data from Qdrant"""
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY'),
        check_compatibility=False
    )
    
    print("=" * 70)
    print("CLEANING UP TEST DATA")
    print("=" * 70)
    
    collections = get_all_collections()
    total_deleted = 0
    
    for collection_name in collections:
        try:
            count_before = client.count(collection_name).count
            print(f"\n📊 {collection_name}: {count_before} points")
            
            if count_before > 0:
                print(f"   🗑️ Dropping collection {collection_name}...")
                client.delete_collection(collection_name)
                total_deleted += count_before
                print(f"   ✅ Collection {collection_name} deleted")
            else:
                print(f"   ℹ️ Collection already empty")
        
        except Exception as e:
            print(f"   ⚠️ Error cleaning {collection_name}: {e}")
    
    print("\n" + "=" * 70)
    print(f"✅ Cleanup complete! Removed all data from {len(collections)} collections (deleted {total_deleted} points total)")
    print("=" * 70)

if __name__ == "__main__":
    cleanup_test_data()

