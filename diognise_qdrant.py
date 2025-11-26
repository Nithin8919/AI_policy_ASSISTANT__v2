#!/usr/bin/env python3
"""
Qdrant Deep Diagnostics
=======================
Find out EXACTLY what's in Qdrant and why searches aren't working.
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from dotenv import load_dotenv
import json

try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

def main():
    print("="*80)
    print("QDRANT DEEP DIAGNOSTICS")
    print("="*80)
    
    # Connect
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    collection = "ap_legal_documents"
    
    print(f"\n📊 Analyzing collection: {collection}")
    
    # 1. Get collection info
    try:
        info = client.get_collection(collection)
        print(f"\n✅ Collection exists")
        print(f"   Points: {getattr(info, 'points_count', 'unknown')}")
        
        vectors_count = getattr(info, "vectors_count", None)
        if vectors_count is not None:
            print(f"   Vectors: {vectors_count}")
        else:
            vector_params = getattr(getattr(info, "config", None), "params", None)
            vector_size = getattr(getattr(vector_params, "vectors", None), "size", None)
            print("   Vectors: not provided by Qdrant client")
            if vector_size:
                print(f"   Vector size (from config): {vector_size}")
        
        # Check indexes
        if hasattr(info.config.params, 'payload_schema'):
            print(f"\n📋 Payload Schema:")
            print(f"   {info.config.params.payload_schema}")
        else:
            print(f"\n⚠️  No payload schema found (indexes may not exist)")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 2. Get sample points to see actual structure
    print(f"\n🔍 Examining actual data structure...")
    
    try:
        # Scroll through some points
        points, _ = client.scroll(
            collection_name=collection,
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if not points:
            print("❌ No points found in collection!")
            return
        
        print(f"\n✅ Found {len(points)} sample points")
        
        # Analyze payload structure
        print("\n📝 ACTUAL PAYLOAD STRUCTURE:")
        print("="*80)
        
        for i, point in enumerate(points[:3], 1):
            print(f"\n[Point {i}] ID: {point.id}")
            print("-"*80)
            payload = point.payload
            
            # Show all keys
            print("Keys in payload:")
            for key in sorted(payload.keys()):
                value = payload[key]
                value_type = type(value).__name__
                
                # Show value preview
                if isinstance(value, (list, dict)):
                    value_preview = json.dumps(value)[:100] + "..."
                else:
                    value_preview = str(value)[:100]
                
                print(f"  • {key}: {value_type} = {value_preview}")
        
        # 3. Look for section-related fields
        print("\n\n🔎 SECTION-RELATED FIELDS:")
        print("="*80)
        
        section_fields = {}
        for point in points:
            for key in point.payload.keys():
                if 'section' in key.lower():
                    if key not in section_fields:
                        section_fields[key] = []
                    section_fields[key].append({
                        'value': point.payload[key],
                        'type': type(point.payload[key]).__name__
                    })
        
        if section_fields:
            for field_name, examples in section_fields.items():
                print(f"\n📌 Field: '{field_name}'")
                print(f"   Type: {examples[0]['type']}")
                print(f"   Sample values:")
                for ex in examples[:3]:
                    print(f"      {ex['value']}")
        else:
            print("❌ NO section-related fields found!")
        
        # 4. Try different filter approaches
        print("\n\n🧪 TESTING DIFFERENT FILTER APPROACHES:")
        print("="*80)
        
        # Try to find any field that might contain "12"
        test_filters = []
        
        # Build test filters based on what we found
        if 'section' in section_fields:
            test_filters.append(("section (exact match)", {
                "must": [
                    FieldCondition(key="section", match=MatchValue(value="12"))
                ]
            }))
            test_filters.append(("section (list match)", {
                "must": [
                    FieldCondition(key="section", match=MatchAny(any=["12"]))
                ]
            }))
        
        if 'sections' in section_fields:
            test_filters.append(("sections (exact match)", {
                "must": [
                    FieldCondition(key="sections", match=MatchValue(value="12"))
                ]
            }))
            test_filters.append(("sections (list match)", {
                "must": [
                    FieldCondition(key="sections", match=MatchAny(any=["12"]))
                ]
            }))
        
        # Test each filter
        for test_name, test_filter in test_filters:
            try:
                results = client.query_points(
                    collection_name=collection,
                    query=[0.0] * 768,  # Dummy vector
                    limit=5,
                    query_filter=Filter(**test_filter),
                    with_payload=True
                )
                
                print(f"\n✅ {test_name}: {len(results.points)} results")
                if results.points:
                    print(f"   First result section field: {results.points[0].payload.get('section') or results.points[0].payload.get('sections')}")
            except Exception as e:
                print(f"\n❌ {test_name}: Error - {e}")
        
        # 5. Try searching without filters
        print("\n\n🔍 TESTING SEARCH WITHOUT FILTERS:")
        print("="*80)
        
        try:
            # Search with dummy vector, no filter
            results = client.query_points(
                collection_name=collection,
                query=[0.0] * 768,
                limit=5,
                with_payload=True
            )
            
            print(f"✅ No-filter search: {len(results.points)} results")
            if results.points:
                print("\nFirst result payload keys:")
                for key in sorted(results.points[0].payload.keys()):
                    print(f"  • {key}")
        except Exception as e:
            print(f"❌ No-filter search failed: {e}")
        
        # 6. Check if we can query by text search
        print("\n\n📝 TESTING TEXT SEARCH:")
        print("="*80)
        
        try:
            # Try to find "Section 12" in text
            results = client.query_points(
                collection_name=collection,
                query=[0.0] * 768,
                limit=10,
                with_payload=True
            )
            
            section_12_chunks = []
            for point in results.points:
                text = point.payload.get('text', '')
                if 'section 12' in text.lower() or 'section-12' in text.lower():
                    section_12_chunks.append(point)
            
            print(f"✅ Found {len(section_12_chunks)} chunks containing 'Section 12' in text")
            
            if section_12_chunks:
                print("\n📄 Sample chunk with 'Section 12':")
                chunk = section_12_chunks[0]
                print(f"   Text preview: {chunk.payload.get('text', '')[:200]}...")
                print(f"\n   Full payload:")
                for key, value in chunk.payload.items():
                    if key != 'text':  # Skip long text
                        print(f"      {key}: {value}")
        except Exception as e:
            print(f"❌ Text search failed: {e}")
    
    except Exception as e:
        print(f"❌ Error examining data: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("DIAGNOSTICS COMPLETE")
    print("="*80)
    print("\n💡 NEXT STEPS:")
    print("1. Check the 'ACTUAL PAYLOAD STRUCTURE' section above")
    print("2. Look for section-related fields (section, sections, mentioned_sections)")
    print("3. Note the field type (list vs string vs int)")
    print("4. Check which filter approach worked in 'TESTING DIFFERENT FILTER APPROACHES'")
    print("5. Update your query_enhancer.py to use the correct field name and type")

if __name__ == "__main__":
    main()