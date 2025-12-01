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

# Add V3 modules to path (simulating main_v3.py)
sys.path.insert(0, 'retrieval_v3')
sys.path.insert(0, 'retrieval')

try:
    # Import V3 components
    from retrieval.retrieval_core.qdrant_client import get_qdrant_client
    from retrieval.embeddings.embedder import get_embedder
    from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
    
    logger.info("🚀 STARTING V3 CONNECTION TEST")
    
    # Initialize V3 retrieval engine (EXACTLY like main_v3.py)
    logger.info("📡 Connecting to Qdrant...")
    qdrant = get_qdrant_client()
    
    logger.info("🧠 Loading Google embedder...")
    embedder = get_embedder()
    
    logger.info("⚡ Creating V3 retrieval engine...")
    v3_engine = RetrievalEngine(
        qdrant_client=qdrant,
        embedder=embedder,
        use_llm_rewrites=True,
        use_llm_reranking=True,
        enable_cache=True
    )
    
    logger.info("✅ Engine initialized successfully!")
    
    # Run a test query
    query = "What are the recent GOs related to school education in AP?"
    logger.info(f"🔍 Running test query: '{query}'")
    
    start_time = time.time()
    results = v3_engine.retrieve(query)
    elapsed = time.time() - start_time
    
    logger.info(f"✅ Query completed in {elapsed:.2f}s")
    logger.info(f"📊 Retrieved {len(results.results)} results")
    
    if results.results:
        top_doc = results.results[0]
        logger.info(f"🏆 Top Result: {top_doc.doc_id} (Score: {top_doc.score:.3f})")
        logger.info(f"   Section Boost: {top_doc.metadata.get('section_boost', 'None')}")
        
    # Check for auto-filter
    if '🎯' in str(results) or 'Auto-pinned' in str(results): 
        logger.info('✅ Auto-filter applied')
        
except Exception as e:
    logger.error(f"❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
