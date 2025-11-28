#!/usr/bin/env python3
"""
Test AI Curriculum Query
=======================
Test the specific query "I want to change school syllabus integrating AI" 
to see what's happening with query expansion and retrieval.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_ai_curriculum_query():
    """Test the specific AI curriculum integration query"""
    print("🔬 Testing AI Curriculum Query Pipeline")
    print("=" * 60)
    
    query = "I want to change school syllabus integrating AI"
    print(f"🎯 Query: '{query}'")
    print("-" * 60)
    
    # Test 1: Check query enhancement
    print("\n📋 STEP 1: Testing Query Enhancement")
    try:
        from retrieval.query_processing.query_enhancer import get_query_enhancer
        from retrieval.query_processing.entity_extractor import get_entity_extractor
        
        enhancer = get_query_enhancer()
        entity_extractor = get_entity_extractor()
        
        # Extract entities first
        entities = entity_extractor.extract(query)
        print(f"   Entities found: {entities}")
        
        # Enhance query
        enhanced_query = enhancer.enhance(query, entities, mode="deep_think")
        print(f"   Enhanced query: {enhanced_query}")
        print(f"   Length: {len(enhanced_query)} characters")
        
    except Exception as e:
        print(f"❌ Query enhancement failed: {e}")
        return
    
    # Test 2: Check router response with enhanced query
    print("\n📋 STEP 2: Testing Router with Enhanced Query")
    try:
        from retrieval.router import RetrievalRouter
        
        router = RetrievalRouter()
        response = router.query(enhanced_query, mode="deep_think", top_k=20)
        
        if response.get("success"):
            results = response.get("results", [])
            print(f"   ✅ Retrieved {len(results)} results")
            
            # Check what collections were searched
            verticals = response.get("verticals_searched", [])
            print(f"   Collections searched: {verticals}")
            
            # Check sources and content
            if results:
                print("\n   📄 Top 5 Results:")
                for i, result in enumerate(results[:5], 1):
                    source = result.get("source", "Unknown")
                    vertical = result.get("vertical", "Unknown")
                    text_preview = result.get("text", "")[:100] + "..."
                    score = result.get("score", 0)
                    
                    print(f"   {i}. {source} ({vertical}) - Score: {score:.3f}")
                    print(f"      Text: {text_preview}")
                    print()
        else:
            print(f"   ❌ Router failed: {response.get('error')}")
            return
            
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return
    
    # Test 3: Search specifically for our known initiatives
    print("\n📋 STEP 3: Testing Specific Initiative Searches")
    
    specific_queries = [
        "Atal Tinkering Lab curriculum",
        "NEP 2020 AI integration", 
        "Samagra Shiksha ICT component",
        "artificial intelligence education policy",
        "technology integration schools"
    ]
    
    for test_query in specific_queries:
        print(f"\n   🔍 Testing: '{test_query}'")
        try:
            response = router.query(test_query, mode="qa", top_k=10)
            if response.get("success"):
                results = response.get("results", [])
                print(f"      Found {len(results)} results")
                
                # Look for relevant content
                relevant_count = 0
                for result in results:
                    text = result.get("text", "").lower()
                    source = result.get("source", "")
                    if any(term in text for term in ["atal", "nep", "samagra", "technology", "digital", "ict"]):
                        relevant_count += 1
                        print(f"      ✅ Relevant: {source[:50]}...")
                
                print(f"      Relevant results: {relevant_count}/{len(results)}")
            else:
                print(f"      ❌ Failed: {response.get('error')}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 4: Check what's actually in the database
    print("\n📋 STEP 4: Checking Database Content")
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from retrieval.config.vertical_map import get_all_collections
        
        qdrant = get_qdrant_client()
        collections = get_all_collections()
        
        for collection in collections:
            try:
                count = qdrant.count(collection)
                print(f"   📚 {collection}: {count.count} documents")
                
                # Try to sample some documents
                try:
                    sample = qdrant.scroll(
                        collection_name=collection,
                        limit=3,
                        with_payload=True
                    )
                    
                    if sample[0]:  # Check if there are results
                        print(f"      Sample documents:")
                        for i, doc in enumerate(sample[0][:2], 1):
                            payload = doc.payload
                            text = payload.get("text", "")[:80]
                            source = payload.get("source", "Unknown")
                            print(f"        {i}. {source}: {text}...")
                except Exception as e:
                    print(f"      Could not sample: {e}")
                    
            except Exception as e:
                print(f"   ❌ Error checking {collection}: {e}")
    
    except Exception as e:
        print(f"❌ Database check failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_ai_curriculum_query()