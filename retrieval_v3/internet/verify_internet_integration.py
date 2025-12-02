import sys
import os
from pathlib import Path
import logging
import traceback

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add retrieval_v3 to path
retrieval_v3_dir = Path(__file__).parent.parent
if str(retrieval_v3_dir) not in sys.path:
    sys.path.insert(0, str(retrieval_v3_dir))

from dotenv import load_dotenv

# Load .env from project root
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    load_dotenv()  # Try current directory
    print(f"⚠️ No .env found at {env_path}, trying current directory")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_env_vars():
    """Check which environment variables are set"""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("="*60)
    
    vars_to_check = [
        "GOOGLE_API_KEY",
        "GOOGLE_CLOUD_API_KEY", 
        "GEMINI_API_KEY",
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION"
    ]
    
    found_vars = {}
    for var in vars_to_check:
        value = os.environ.get(var)
        if value:
            # Show first 10 chars + last 4 chars for security
            masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
            found_vars[var] = masked
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: Not set")
    
    return found_vars


def test_google_search_client():
    """Test GoogleSearchClient directly"""
    print("\n" + "="*60)
    print("TEST 1: GoogleSearchClient Direct Test")
    print("="*60)
    
    try:
        from internet.google_search_client import GoogleSearchClient
        
        print("\n1.1 Initializing GoogleSearchClient...")
        client = GoogleSearchClient()
        
        if not client.client:
            print("❌ FAIL: GoogleSearchClient.client is None")
            print("\nPossible issues:")
            print("  - No API key found (check GOOGLE_API_KEY in .env)")
            print("  - No project ID found (for Vertex AI)")
            print("  - Client initialization failed (check logs above)")
            return False
        
        print("✅ GoogleSearchClient initialized successfully")
        print(f"   Model: {client.model}")
        # Report which auth path is being used
        using_vertex = getattr(client, "use_vertex_ai", False)
        if using_vertex:
            print(f"   Using: Vertex AI (project={getattr(client, 'project_id', 'unknown')})")
        else:
            print("   Using: API Key (AI Studio, vertexai=False)")
        
        print("\n1.2 Testing search functionality...")
        test_query = "AP education policy 2024"
        print(f"   Query: '{test_query}'")
        
        results = client.search(test_query)
        
        if not results:
            print("❌ FAIL: Search returned no results")
            return False
        
        print(f"✅ PASS: Search returned {len(results)} result(s)")
        print("\n1.3 Sample result:")
        for i, result in enumerate(results[:1], 1):
            print(f"   Result {i}:")
            print(f"     Title: {result.get('title', 'N/A')}")
            print(f"     Source: {result.get('source', 'N/A')}")
            print(f"     URL: {result.get('url', 'N/A')}")
            snippet = result.get('snippet', '')
            print(f"     Snippet: {snippet[:150]}..." if len(snippet) > 150 else f"     Snippet: {snippet}")
        
        return True
        
    except ImportError as e:
        print(f"❌ FAIL: Could not import GoogleSearchClient: {e}")
        print("\nMake sure you have installed:")
        print("  pip install google-genai")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error during GoogleSearchClient test: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def test_retrieval_engine_integration():
    """Test integration with RetrievalEngine"""
    print("\n" + "="*60)
    print("TEST 2: RetrievalEngine Integration Test")
    print("="*60)
    
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from retrieval.embeddings.embedder import get_embedder
        from pipeline.retrieval_engine import RetrievalEngine
        
        print("\n2.1 Initializing RetrievalEngine...")

        # Get Qdrant and embedder (may be None, that's okay for this test)
        try:
            qdrant = get_qdrant_client()
            embedder = get_embedder()
            print("✅ Qdrant and embedder initialized")
        except Exception as e:
            print(f"⚠️ Qdrant/embedder init failed (will test without them): {e}")
            qdrant = None
            embedder = None
        
        engine = RetrievalEngine(
            qdrant_client=qdrant,
            embedder=embedder,
            gemini_api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
            use_llm_rewrites=False,  # Disable for faster test
            use_llm_reranking=False,
            enable_cache=False
        )
        print("✅ RetrievalEngine initialized")
        
        print("\n2.2 Testing retrieval with internet search...")
        query = "latest AP education policy updates 2024"
        print(f"   Query: '{query}'")
        
        # Try to enable internet search via custom plan
        output = engine.retrieve(
            query, 
            # Use both keys for clarity; retrieval_engine treats either as enabling internet
            custom_plan={'internet_enabled': True, 'use_internet': True}
        )
        
        web_results = [r for r in output.results if r.vertical == "internet"]
        internal_results = [r for r in output.results if r.vertical != "internet"]
        
        print(f"\n   Found {len(web_results)} web results")
        print(f"   Found {len(internal_results)} internal results")
        
        if web_results:
            print("✅ PASS: Internet search integrated successfully")
            print("\n   Sample web result:")
            print(f"     Title: {web_results[0].metadata.get('title', 'N/A')}")
            print(f"     URL: {web_results[0].metadata.get('url', 'N/A')}")
            print(f"     Content: {web_results[0].content[:100]}...")
            return True
        else:
            print("⚠️ WARNING: No web results found")
            print("   This could mean:")
            print("   - Internet search is not enabled in the retrieval plan")
            print("   - Query didn't trigger internet search")
            print("   - API returned no results")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: RetrievalEngine integration test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def verify_integration():
    """Main verification function"""
    print("="*60)
    print("INTERNET LAYER INTEGRATION VERIFICATION")
    print("="*60)
    
    # Step 1: Check environment variables
    found_vars = check_env_vars()
    
    if not found_vars:
        print("\n❌ CRITICAL: No API keys found!")
        print("\nPlease set one of these in your .env file:")
        print("  GOOGLE_API_KEY=your_key_here")
        print("  (or GOOGLE_CLOUD_API_KEY or GEMINI_API_KEY)")
        return
    
    # Step 2: Test GoogleSearchClient directly
    client_test_passed = test_google_search_client()
    
    # Step 3: Test integration with RetrievalEngine (optional)
    if client_test_passed:
        print("\n" + "="*60)
        print("Proceeding to RetrievalEngine integration test...")
        print("="*60)
        engine_test_passed = test_retrieval_engine_integration()
    else:
        print("\n⚠️ Skipping RetrievalEngine test (GoogleSearchClient test failed)")
        engine_test_passed = False
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"GoogleSearchClient Test: {'✅ PASS' if client_test_passed else '❌ FAIL'}")
    print(f"RetrievalEngine Integration: {'✅ PASS' if engine_test_passed else '⚠️ SKIP/FAIL'}")
    
    if client_test_passed:
        print("\n✅ Internet layer is working!")
    else:
        print("\n❌ Internet layer needs fixing. Check the errors above.")


if __name__ == "__main__":
    verify_integration()
