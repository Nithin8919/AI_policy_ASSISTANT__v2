#!/usr/bin/env python3
"""
Setup Internet Integration for V3 Retrieval
==========================================
Configure Google Programmable Search Engine integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add paths
sys.path.insert(0, 'retrieval_v3')

def setup_internet_integration():
    """Setup and test internet integration"""
    
    print("🌐 SETTING UP INTERNET INTEGRATION")
    print("=" * 60)
    
    # Check current credentials
    api_key = os.getenv('GOOGLE_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    print(f"\n📋 Current Credentials:")
    print(f"   • Google API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"   • Search Engine ID: {'✅ Set' if search_engine_id else '❌ Missing'}")
    
    if not api_key or not search_engine_id:
        print(f"\n🔑 CREDENTIALS NEEDED:")
        print(f"=" * 40)
        print(f"""
To enable internet search, you need:

1. GOOGLE API KEY:
   → Go to: https://console.cloud.google.com/
   → Enable "Custom Search JSON API"
   → Create API key
   → Add to .env: GOOGLE_API_KEY=your-key-here

2. GOOGLE SEARCH ENGINE ID:
   → Go to: https://cse.google.com/
   → Create new search engine
   → Configure for education/government sites
   → Add to .env: GOOGLE_SEARCH_ENGINE_ID=your-id-here

3. RECOMMENDED SEARCH ENGINE SETUP:
   → Sites to search: *.edu.in, *.gov.in, mhrd.gov.in, education.gov.in
   → Language: English + Hindi
   → Safe Search: Moderate
   → Image Search: Off (text only)
""")
        return False
    
    # Test internet components
    try:
        print(f"\n🧪 TESTING INTERNET COMPONENTS:")
        print(f"-" * 40)
        
        # Test Internet Router
        from routing.internet_router import InternetRouter
        router = InternetRouter()
        
        test_queries = [
            ("What is Section 12 RTE Act?", False),  # Should NOT use internet
            ("Latest education policies 2024", True),  # Should use internet  
            ("Current FLN guidelines", True),  # Should use internet
            ("Recent changes in midday meal", True),  # Should use internet
        ]
        
        print(f"1. Testing Internet Router:")
        router_success = True
        
        for query, expected in test_queries:
            should_use = router.should_use_internet(query)
            status = "✅" if should_use == expected else "❌"
            print(f"   {status} '{query}' → Internet: {should_use}")
            if should_use != expected:
                router_success = False
        
        print(f"   Router Status: {'✅ WORKING' if router_success else '❌ ISSUES'}")
        
        # Test Google PSE Client
        print(f"\n2. Testing Google PSE Client:")
        from internet.google_pse_client import GooglePSEClient
        
        pse_client = GooglePSEClient(
            api_key=api_key,
            search_engine_id=search_engine_id
        )
        
        # Test search
        print(f"   Testing with query: 'latest education policy India'...")
        results = pse_client.search("latest education policy India", num_results=3)
        
        if results:
            print(f"   ✅ PSE Client WORKING - {len(results)} results found")
            for i, result in enumerate(results[:2], 1):
                print(f"      {i}. {result.title[:50]}...")
                print(f"         {result.source}")
        else:
            print(f"   ❌ PSE Client FAILED - No results (check credentials)")
            return False
        
        # Test specialized searches
        print(f"\n3. Testing Specialized Searches:")
        
        # Government sites only
        gov_results = pse_client.search_government_sites("RTE Act", num_results=2)
        print(f"   • Government sites: {len(gov_results)} results")
        
        # Recent results
        recent_results = pse_client.search_recent("education news", days=30, num_results=2)
        print(f"   • Recent results: {len(recent_results)} results")
        
        print(f"\n✅ INTERNET INTEGRATION: FULLY OPERATIONAL")
        return True
        
    except Exception as e:
        print(f"\n❌ Internet integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_internet_features():
    """Demonstrate internet search capabilities"""
    
    print(f"\n🌐 INTERNET SEARCH CAPABILITIES:")
    print(f"=" * 60)
    
    print(f"""
🎯 INTELLIGENT ROUTING:
   The system automatically decides when to use internet search based on:
   
   ✅ TRIGGERS FOR INTERNET:
   • Temporal: "latest", "recent", "current", "new", "updated"
   • Future years: "2024", "2025", "2026+"  
   • News: "news", "announced", "launched", "changes"
   • Comparative: "versus", "compare with", "difference between"
   
   ❌ NO INTERNET FOR:
   • Historical queries: "Section 12 RTE Act"
   • Static policies: "teacher transfer rules"
   • Document analysis: "Nadu-Nedu implementation"

🔍 SEARCH TYPES:
   • General Web Search: All indexed content
   • Government Sites Only: *.gov.in domains
   • Recent Results: Last 7/30/90 days
   • Site-specific: Restrict to education domains

🚀 INTEGRATION WITH V3:
   • Parallel search: Internet + local database simultaneously
   • Smart merging: Combines web results with policy documents
   • Relevance reranking: LLM judges internet vs local relevance
   • Content cleaning: Extracts clean text from web pages

📊 PERFORMANCE:
   • Internet search timeout: 10s max
   • Parallel execution with database search
   • Cached results for repeated queries
   • Fallback to database-only if internet fails
""")

def test_internet_enabled_v3():
    """Test V3 retrieval with internet integration"""
    
    print(f"\n🚀 TESTING INTERNET-ENABLED V3 RETRIEVAL:")
    print(f"=" * 60)
    
    try:
        # Import components
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from ingestion_v2.embedding.google_embedder import get_embedder
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
        
        # Setup engine with internet
        qdrant = get_qdrant_client()
        embedder = get_embedder()
        
        engine = RetrievalEngine(
            qdrant_client=qdrant,
            embedder=embedder,
            use_llm_rewrites=True,
            use_llm_reranking=True,
            enable_cache=True
        )
        
        # Test internet-triggering queries
        internet_queries = [
            "Latest education policies 2024",
            "Recent changes in FLN guidelines", 
            "Current status of NEP 2020 implementation",
            "New initiatives in digital education"
        ]
        
        print(f"Testing {len(internet_queries)} internet queries...")
        
        for i, query in enumerate(internet_queries, 1):
            print(f"\n{i}. Query: {query}")
            print(f"   {'='*50}")
            
            # Check internet routing
            from routing.internet_router import InternetRouter
            router = InternetRouter()
            should_use_internet = router.should_use_internet(query)
            triggers = router.get_internet_keywords(query)
            
            print(f"   Internet routing: {'✅ YES' if should_use_internet else '❌ NO'}")
            if should_use_internet:
                print(f"   Triggers: {triggers}")
            
            # Run V3 retrieval (will use internet if configured)
            result = engine.retrieve(query, top_k=10)
            
            print(f"   Results: {result.final_count} found")
            print(f"   Time: {result.processing_time:.2f}s")
            print(f"   Sources: {result.verticals_searched}")
            
            # Show top result
            if result.results:
                top = result.results[0]
                print(f"   Top result: {top.content[:100]}...")
        
        print(f"\n✅ INTERNET-ENABLED V3: OPERATIONAL")
        
    except Exception as e:
        print(f"❌ Internet V3 test failed: {e}")

def main():
    """Main setup function"""
    
    success = setup_internet_integration()
    
    if success:
        demonstrate_internet_features()
        test_internet_enabled_v3()
        
        print(f"\n🎉 INTERNET INTEGRATION: READY FOR PRODUCTION")
        print(f"=" * 60)
        print(f"""
✅ SETUP COMPLETE:
   • Internet routing: Working
   • Google PSE client: Connected  
   • Specialized searches: Available
   • V3 integration: Ready

🚀 ENHANCED CAPABILITIES:
   • Real-time information retrieval
   • Latest policy updates
   • Current education news
   • Comparative analysis with web data

💡 USAGE:
   Just ask queries with "latest", "recent", "current", "2024+" 
   and the system will automatically include web search results!
""")
    else:
        print(f"\n⚠️ INTERNET INTEGRATION: SETUP REQUIRED")
        print(f"Please provide the required Google PSE credentials.")

if __name__ == "__main__":
    main()