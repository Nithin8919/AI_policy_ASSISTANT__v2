#!/usr/bin/env python3
"""
Create Qdrant Payload Indexes
==============================
Creates indexes on nested fields for entity expansion and relation search.
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def create_indexes():
    """Create payload indexes for all collections"""
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    collections = ["ap_government_orders", "ap_legal_documents", "ap_judicial_documents"]
    
    # Indexes to create
    indexes = [
        # Entity indexes
        ("entities.go_numbers", PayloadSchemaType.KEYWORD),
        ("entities.sections", PayloadSchemaType.KEYWORD),
        ("entities.go_refs", PayloadSchemaType.KEYWORD),
        ("entities.departments", PayloadSchemaType.KEYWORD),  # NEW: Fix 400 error
        ("entities.acts", PayloadSchemaType.KEYWORD),
        ("entities.schemes", PayloadSchemaType.KEYWORD),  # NEW: Fix 400 error

        
        # Relation indexes
        ("relations[].type", PayloadSchemaType.KEYWORD),
        ("relations[].relation_type", PayloadSchemaType.KEYWORD),
        ("relations[].target", PayloadSchemaType.KEYWORD),
        
        # Core metadata indexes
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("vertical", PayloadSchemaType.KEYWORD),
        ("go_number", PayloadSchemaType.KEYWORD),
        ("department", PayloadSchemaType.KEYWORD),
        ("section_type", PayloadSchemaType.KEYWORD),
        
        # Date/time indexes (INTEGER for timestamps)
        ("year", PayloadSchemaType.INTEGER),
        ("date_issued_ts", PayloadSchemaType.INTEGER),  # NEW: Unix epoch
        
        # Operational validity
        ("is_superseded", PayloadSchemaType.KEYWORD),  # NEW: Boolean as keyword
    ]
    
    for collection in collections:
        print(f"\n📦 Processing collection: {collection}")
        
        try:
            # Check if collection exists
            collections_list = client.get_collections()
            if collection not in [c.name for c in collections_list.collections]:
                print(f"   ⚠️  Collection {collection} not found, skipping")
                continue
            
            for field_name, schema_type in indexes:
                try:
                    print(f"   Creating index: {field_name} ({schema_type})")
                    client.create_payload_index(
                        collection_name=collection,
                        field_name=field_name,
                        field_schema=schema_type
                    )
                    print(f"   ✅ Created index: {field_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ℹ️  Index already exists: {field_name}")
                    else:
                        print(f"   ⚠️  Failed to create index {field_name}: {e}")
        
        except Exception as e:
            print(f"   ❌ Error processing collection {collection}: {e}")
    
    print("\n✅ Index creation complete!")

if __name__ == "__main__":
    create_indexes()
