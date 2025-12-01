import sys
import os
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add V3 modules to path
sys.path.insert(0, 'retrieval_v3')
sys.path.insert(0, 'retrieval')

try:
    from retrieval.retrieval_core.qdrant_client import get_qdrant_client
    from retrieval.embeddings.embedder import get_embedder
    from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
    
    logger.info("🚀 STARTING P1 QUICK WINS ANALYSIS")
    
    # Initialize Engine
    logger.info("⚡ Initializing V3 Engine...")
    v3_engine = RetrievalEngine(
        qdrant_client=get_qdrant_client(),
        embedder=get_embedder(),
        use_llm_rewrites=True,
        use_llm_reranking=True,
        enable_cache=True
    )
    
    # Test Cases
    politician_queries = [
        {
            "name": "Auto-Filter & Recency Test",
            "query": "What have you done for the teachers recently? Show me the latest orders!",
            "check": lambda r, l: "🎯" in l or "Auto-pinned" in l,
            "desc": "Verifies 'recent' keyword triggers 18-month date filter"
        },
        {
            "name": "Section Boost Test",
            "query": "I want the specific orders regarding school restructuring, not just the preamble!",
            "check": lambda r, l: any(doc.metadata.get('section_boost', 0) > 1.0 for doc in r.results[:3]),
            "desc": "Verifies 'orders' section gets 1.3x boost"
        },
        {
            "name": "Surgical Expansion Test",
            "query": "Tell me about the amendments to the comprehensive education act.",
            "check": lambda r, l: "Surgical expansion" in l,
            "desc": "Verifies neighbor expansion is limited to top-20 and amends/supersedes"
        }
    ]
    
    print("\n" + "="*60)
    print("🎤 RUNNING POLITICIAN QUERY ANALYSIS")
    print("="*60 + "\n")
    
    for test in politician_queries:
        print(f"🧐 TEST: {test['name']}")
        print(f"❓ Query: \"{test['query']}\"")
        print(f"🎯 Goal: {test['desc']}")
        
        # Capture logs to check for internal logic triggers
        import io
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger.addHandler(handler)
        
        start = time.time()
        results = v3_engine.retrieve(test['query'])
        elapsed = time.time() - start
        
        logs = log_capture.getvalue()
        logger.removeHandler(handler)
        
        print(f"⏱️  Latency: {elapsed:.2f}s")
        print(f"📊 Results: {len(results.results)}")
        
        # Run Verification
        passed = False
        try:
            # Check logs for specific markers we added in P1
            if "recent" in test['name'].lower():
                # For auto-filter, we check the logs for the specific emoji or message
                if "🎯" in logs or "Auto-pinned" in logs:
                    passed = True
            elif "Section" in test['name']:
                # For section boost, check metadata of top results
                for doc in results.results[:5]:
                    boost = doc.metadata.get('section_boost')
                    section = doc.metadata.get('section_type')
                    print(f"   - Doc {doc.doc_id}: Section='{section}', Boost={boost}")
                    if boost and boost > 1.0:
                        passed = True
            elif "Surgical" in test['name']:
                # Check logs for surgical expansion message
                if "Surgical expansion" in logs:
                    passed = True
                    
        except Exception as e:
            print(f"   ⚠️ Check failed: {e}")
            
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"Status: {status}\n")
        print("-" * 60 + "\n")

except Exception as e:
    logger.error(f"❌ ANALYSIS FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
