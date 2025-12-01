"""
BM25 Retriever
==============
Implements BM25 search by building an in-memory index from Qdrant data.
Since we cannot re-ingest, we fetch the corpus from Qdrant at startup (or load from cache).
"""

import os
import pickle
import logging
from typing import List, Dict, Optional
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

class BM25Retriever:
    """
    BM25 Retriever using rank_bm25.
    
    Features:
    - Builds/Loads index from Qdrant corpus
    - Caches index to disk for fast startup
    - Tokenization compatible with query processing
    """
    
    def __init__(self, qdrant_client: QdrantClient, cache_dir: str = "cache/bm25"):
        self.client = qdrant_client
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_ids: List[str] = []
        self.corpus_map: Dict[str, Dict] = {} # id -> metadata
        
        # Collections to index
        self.collections = ["go", "legal", "judicial", "scheme", "data"]
        
        # Try to load existing index (don't build in __init__ to avoid blocking)
        self._load_index()
    
    def ensure_bm25_ready(self) -> bool:
        """Ensure BM25 index is loaded and ready. Returns True if ready, False otherwise."""
        if self.bm25 is not None:
            return True
        
        # Try to load from cache first
        if self._load_index():
            return True
        
        # Build index if not cached
        logger.warning("BM25 index not found, building from Qdrant...")
        try:
            self._build_index()
            self._save_index()
            return self.bm25 is not None
        except Exception as e:
            logger.error(f"BM25 build failed: {e}. Continuing without BM25.")
            self.bm25 = None
            return False
    
    def _build_index(self):
        """Fetch all documents from Qdrant and build BM25 index"""
        corpus_tokens = []
        self.corpus_ids = []
        self.corpus_map = {}
        
        total_docs = 0
        
        for collection_name in self.collections:
            try:
                # Scroll through all points
                offset = None
                while True:
                    # Check if we have a wrapper or real client
                    client_instance = self.client.client if hasattr(self.client, 'client') else self.client
                    
                    points, offset = client_instance.scroll(
                        collection_name=collection_name,
                        limit=1000,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    for point in points:
                        content = point.payload.get("content", "") or point.payload.get("text", "")
                        if not content:
                            continue
                            
                        # Simple tokenization
                        tokens = self._tokenize(content)
                        
                        corpus_tokens.append(tokens)
                        self.corpus_ids.append(point.id)
                        self.corpus_map[point.id] = {
                            "vertical": collection_name,
                            "metadata": point.payload
                        }
                        
                    total_docs += len(points)
                    
                    if offset is None:
                        break
                        
                logger.info(f"Indexed {collection_name}: {total_docs} total docs so far")
                
            except Exception as e:
                logger.warning(f"Failed to index collection {collection_name}: {e}")
        
        if not corpus_tokens:
            logger.error("❌ No documents found in Qdrant to index!")
            return
            
        # Build BM25
        logger.info(f"Building BM25 index on {len(corpus_tokens)} documents...")
        self.bm25 = BM25Okapi(corpus_tokens)
        
        # Save to cache
        self._save_index()
        logger.info("✅ BM25 index built and saved.")
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer - should match query tokenization"""
        return text.lower().split()
        
    def _save_index(self):
        """Save index and metadata to cache"""
        try:
            with open(self.cache_dir / "bm25_model.pkl", "wb") as f:
                pickle.dump(self.bm25, f)
            
            with open(self.cache_dir / "corpus_ids.pkl", "wb") as f:
                pickle.dump(self.corpus_ids, f)
                
            with open(self.cache_dir / "corpus_map.pkl", "wb") as f:
                pickle.dump(self.corpus_map, f)
                
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")
            
    def _load_index(self) -> bool:
        """Load index from cache"""
        try:
            if not (self.cache_dir / "bm25_model.pkl").exists():
                return False
                
            with open(self.cache_dir / "bm25_model.pkl", "rb") as f:
                self.bm25 = pickle.load(f)
                
            with open(self.cache_dir / "corpus_ids.pkl", "rb") as f:
                self.corpus_ids = pickle.load(f)
                
            with open(self.cache_dir / "corpus_map.pkl", "rb") as f:
                self.corpus_map = pickle.load(f)
                
            logger.info(f"✅ Loaded BM25 index with {len(self.corpus_ids)} documents")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}")
            return False
            
    def search(self, query: str, top_k: int = 100) -> List[Dict]:
        """Search using BM25"""
        # Ensure index is ready
        if not self.ensure_bm25_ready():
            logger.warning("BM25 index not initialized")
            return []
        
        # Double-check BM25 is not None
        if self.bm25 is None:
            logger.warning("BM25 index is None after ensure_ready")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_n = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_n:
            score = scores[idx]
            if score <= 0:
                continue
                
            doc_id = self.corpus_ids[idx]
            doc_info = self.corpus_map[doc_id]
            
            results.append({
                "chunk_id": doc_id,
                "score": float(score),
                "vertical": doc_info["vertical"],
                "metadata": doc_info["metadata"],
                "content": doc_info["metadata"].get("content", "") or doc_info["metadata"].get("text", "")
            })
            
        return results
