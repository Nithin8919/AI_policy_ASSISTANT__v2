"""
Script to fix backend issues:
1. Create missing 'go' collection
2. Rebuild BM25 index
3. Verify index size
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add project root to path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'retrieval_v3'))

from qdrant_client import QdrantClient
from qdrant_client.http import models
from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval_v3.retrieval_core.bm25_retriever import BM25Retriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_backend_issues():
    logger.info("🔧 Starting backend fix...")
    
    # 1. Initialize Qdrant Client
    try:
        client = get_qdrant_client()
        logger.info("✅ Qdrant client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Qdrant client: {e}")
        return

    # 2. Check and create 'go' collection
    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        logger.info(f"📚 Available collections: {collection_names}")
        
        if 'go' not in collection_names:
            logger.warning("⚠️ Collection 'go' missing. Creating it...")
            # Access underlying client for create_collection
            client.client.create_collection(
                collection_name='go',
                vectors_config=models.VectorParams(
                    size=768,  # Assuming standard embedding size
                    distance=models.Distance.COSINE
                )
            )
            logger.info("✅ Collection 'go' created")
        else:
            logger.info("✅ Collection 'go' exists")
            
    except Exception as e:
        logger.error(f"❌ Failed to check/create 'go' collection: {e}")

    # 3. Rebuild BM25 Index
    try:
        logger.info("🔄 Rebuilding BM25 index...")
        
        # Delete existing cache to force rebuild
        cache_dir = Path("cache/bm25")
        if cache_dir.exists():
            for f in cache_dir.glob("*.pkl"):
                f.unlink()
            logger.info("🗑️ Cleared existing BM25 cache")
            
        # Initialize retriever (will auto-build)
        retriever = BM25Retriever(client)
        
        # Verify index size
        if retriever.ensure_bm25_ready():
            doc_count = len(retriever.corpus_ids)
            if doc_count > 0:
                logger.info(f"✅ BM25 index successfully built with {doc_count} documents")
            else:
                logger.error("❌ BM25 index built but has 0 documents! Check Qdrant data.")
        else:
            logger.error("❌ Failed to build BM25 index")
            
    except Exception as e:
        logger.error(f"❌ Error rebuilding BM25 index: {e}")

if __name__ == "__main__":
    fix_backend_issues()
