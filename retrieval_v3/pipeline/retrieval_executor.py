# Retrieval Executor

"""
Executes retrieval operations: parallel vector search, BM25, hybrid search, multi-hop
"""

import logging
import time
import concurrent.futures
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .models import RetrievalResult
from retrieval_core.bm25_retriever import BM25Retriever
from retrieval_core.hybrid_search import HybridSearcher
from routing.retrieval_plan import RetrievalPlan

logger = logging.getLogger(__name__)


class RetrievalExecutor:
    """Executes retrieval operations"""
    
    def __init__(
        self,
        qdrant_client,
        embedder,
        executor: ThreadPoolExecutor,
        lock: threading.Lock,
        enable_cache: bool,
        embedding_cache: Dict,
        cache_max_size: int,
        stats: Dict,
        bm25_retriever: Optional[BM25Retriever] = None,
        hybrid_searcher: Optional[HybridSearcher] = None
    ):
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.executor = executor
        self._lock = lock
        self.enable_cache = enable_cache
        self._embedding_cache = embedding_cache
        self._cache_max_size = cache_max_size
        self.stats = stats
        self.bm25_retriever = bm25_retriever
        self.hybrid_searcher = hybrid_searcher or HybridSearcher()
    
    def execute_hybrid_search(
        self,
        search_query: str,
        collection_names: List[str],
        plan: RetrievalPlan,
        hop: int = 1
    ) -> List[RetrievalResult]:
        """
        Execute hybrid search (vector + BM25) for a single query
        
        Returns fused results from both vector and BM25 searches
        """
        vector_res = []
        bm25_res = []
        
        def run_vector_search():
            return self.parallel_retrieve_hop(
                [search_query], 
                collection_names, 
                top_k=plan.top_k_per_vertical, 
                hop_number=hop
            )
        
        def run_bm25_search():
            res = []
            if self.bm25_retriever:
                try:
                    bm25_raw = self.bm25_retriever.search(search_query, top_k=plan.top_k_per_vertical)
                    for r in bm25_raw:
                        res.append(RetrievalResult(
                            chunk_id=r['chunk_id'],
                            doc_id=r['metadata'].get('doc_id', 'unknown'),
                            content=r['content'],
                            score=r['score'],
                            vertical=r['vertical'],
                            metadata=r['metadata'],
                            rewrite_source=f"bm25_{search_query}",
                            hop_number=hop
                        ))
                except Exception as e:
                    logger.warning(f"BM25 search failed: {e}")
            return res

        # Parallelize BM25 and Dense searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_vector = executor.submit(run_vector_search)
            future_bm25 = executor.submit(run_bm25_search)
            
            try:
                # 25s timeout for vector, 10s for BM25 (increased to prevent timeouts)
                vector_res = future_vector.result(timeout=25.0)
                bm25_res = future_bm25.result(timeout=10.0)
            except concurrent.futures.TimeoutError:
                logger.warning("Search timeout - using partial results")
                if future_vector.done():
                    vector_res = future_vector.result()
                if future_bm25.done():
                    bm25_res = future_bm25.result()
            except Exception as e:
                logger.warning(f"Parallel search error: {e}")
                # Fallback to sequential if parallel fails
                if not vector_res:
                    vector_res = run_vector_search()
        
        # Fuse Vector + BM25 for this query
        if not bm25_res:
            return vector_res
            
        # Use RRF to combine
        fused_ids = self.hybrid_searcher.rrf_fusion(
            [r.chunk_id for r in vector_res],
            [r.chunk_id for r in bm25_res]
        )
        
        # Reconstruct results from fused IDs
        fused_results = []
        seen_ids = set()
        
        # Create a lookup map
        all_candidates_map = {r.chunk_id: r for r in vector_res + bm25_res}
        
        for rank, cid in enumerate(fused_ids):
            if cid in all_candidates_map and cid not in seen_ids:
                res = all_candidates_map[cid]
                # Assign a normalized score based on rank
                res.score = 1.0 / (rank + 1)
                fused_results.append(res)
                seen_ids.add(cid)
        
        # Apply section type boost (orders > annexure > preamble)
        try:
            from retrieval_v3.retrieval_core.scoring import section_type_boost
            for result in fused_results:
                section_type = result.metadata.get('section_type')
                if section_type:
                    boost = section_type_boost(section_type)
                    if boost > 1.0:
                        result.score *= boost
                        result.metadata['section_boost'] = boost
        except Exception as e:
            logger.warning(f"Section boost failed: {e}")
        
        return fused_results
    
    def parallel_retrieve_hop(
        self,
        queries: List[str],
        collections: List[str],
        top_k: int,
        hop_number: int = 1
    ) -> List[RetrievalResult]:
        """
        Parallel retrieval across all query-collection combinations
        
        This dramatically speeds up retrieval by running searches concurrently
        OPTIMIZATION P2-3: Batch embedding generation for all queries at once
        """
        if not self.qdrant_client or not self.embedder:
            return self._generate_stub_results(queries, collections, top_k, hop_number)
        
        # OPTIMIZATION P2-3: Batch embedding generation for all queries
        # Generate embeddings for all unique queries at once (more efficient)
        unique_queries = list(set(queries))
        query_to_embedding = {}
        
        # Check cache first
        uncached_queries = []
        with self._lock:
            for query in unique_queries:
                cache_key = f"embed_{query}"
                if self.enable_cache and cache_key in self._embedding_cache:
                    query_to_embedding[query] = self._embedding_cache[cache_key]
                    self.stats['cache_hits'] += 1
                else:
                    uncached_queries.append(query)
        
        # Batch generate embeddings for uncached queries
        if uncached_queries:
            try:
                if hasattr(self.embedder, 'embed_queries'):
                    # Use batch method if available
                    embeddings = self.embedder.embed_queries(uncached_queries)
                    for query, embedding in zip(uncached_queries, embeddings):
                        query_to_embedding[query] = embedding
                elif hasattr(self.embedder, 'embed_texts'):
                    # Batch embed using embed_texts
                    embeddings = self.embedder.embed_texts(uncached_queries)
                    for query, embedding in zip(uncached_queries, embeddings):
                        query_to_embedding[query] = embedding
                else:
                    # Fallback: embed one by one (slower but works)
                    for query in uncached_queries:
                        if hasattr(self.embedder, 'embed_query'):
                            query_to_embedding[query] = self.embedder.embed_query(query)
                        else:
                            query_to_embedding[query] = self.embedder.embed_texts([query])[0]
                
                # Cache the new embeddings
                with self._lock:
                    if self.enable_cache:
                        for query in uncached_queries:
                            if query in query_to_embedding:
                                cache_key = f"embed_{query}"
                                embedding = query_to_embedding[query]
                                if len(self._embedding_cache) >= self._cache_max_size:
                                    oldest_key = next(iter(self._embedding_cache))
                                    del self._embedding_cache[oldest_key]
                                self._embedding_cache[cache_key] = embedding
            except Exception as e:
                logger.warning(f"Batch embedding failed: {e}, falling back to per-query")
                # Fallback: generate one by one
                for query in uncached_queries:
                    if query not in query_to_embedding:
                        try:
                            if hasattr(self.embedder, 'embed_query'):
                                query_to_embedding[query] = self.embedder.embed_query(query)
                            else:
                                query_to_embedding[query] = self.embedder.embed_texts([query])[0]
                        except Exception as e2:
                            logger.warning(f"Embedding failed for '{query}': {e2}")
                            continue
        
        # Create all search tasks (now with pre-computed embeddings)
        search_tasks = []
        for query in queries:
            for collection in collections:
                embedding = query_to_embedding.get(query)
                if embedding is not None:
                    search_tasks.append((query, collection, top_k, hop_number, embedding))
        
        # Execute searches in parallel (embeddings already computed)
        all_results = []
        
        # Submit all tasks to thread pool
        future_to_task = {
            self.executor.submit(self._search_with_embedding, task[0], task[1], task[2], task[3], task[4]): task
            for task in search_tasks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task, timeout=60):  # 60s total timeout
            try:
                results = future.result(timeout=10)  # 10s per individual search
                if results:
                    all_results.extend(results)
            except Exception as e:
                task = future_to_task[future]
                print(f"Parallel search failed for {task[0]} in {task[1]}: {e}")
                continue
        
        return all_results
    
    def _search_with_embedding(
        self,
        query: str,
        collection: str,
        top_k: int,
        hop_number: int,
        embedding
    ) -> List[RetrievalResult]:
        """Search using pre-computed embedding (optimized for batch processing)"""
        try:
            response = self.qdrant_client.query_points(
                collection_name=collection,
                query=embedding,
                limit=top_k,
                score_threshold=0.3,
                with_payload=True,
                with_vectors=False
            )
            search_results = response.points
            
            # Convert to RetrievalResult objects
            results = []
            for hit in search_results:
                try:
                    if isinstance(hit, dict):
                        hit_id = hit.get('id', 'unknown')
                        hit_score = hit.get('score', 0.0)
                        hit_payload = hit.get('payload', {})
                    else:
                        hit_id = hit.id
                        hit_score = hit.score
                        hit_payload = hit.payload
                    
                    results.append(RetrievalResult(
                        chunk_id=str(hit_id),
                        doc_id=hit_payload.get('doc_id', 'unknown'),
                        content=hit_payload.get('text', hit_payload.get('content', '')),
                        score=float(hit_score),
                        vertical=collection.replace('ap_', '').replace('_documents', '').replace('_orders', '').replace('_reports', ''),
                        metadata=hit_payload,
                        rewrite_source=query,
                        hop_number=hop_number
                    ))
                except Exception as e:
                    print(f"Result parsing failed: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Search failed for {collection}: {e}")
            return []
    
    def _search_single_threadsafe(
        self,
        query: str,
        collection: str,
        top_k: int,
        hop_number: int = 1
    ) -> List[RetrievalResult]:
        """Thread-safe version of single search with caching (legacy method for compatibility)"""
        
        # Thread-safe embedding cache access
        embedding = None
        cache_key = f"embed_{query}"
        
        with self._lock:
            if self.enable_cache and cache_key in self._embedding_cache:
                embedding = self._embedding_cache[cache_key]
                self.stats['cache_hits'] += 1
        
        # Generate embedding if not cached
        if embedding is None:
            try:
                if hasattr(self.embedder, 'embed_query'):
                    embedding = self.embedder.embed_query(query)
                else:
                    embedding = self.embedder.embed_texts([query])[0]
                
                # Thread-safe cache update
                with self._lock:
                    if self.enable_cache:
                        if len(self._embedding_cache) >= self._cache_max_size:
                            oldest_key = next(iter(self._embedding_cache))
                            del self._embedding_cache[oldest_key]
                        self._embedding_cache[cache_key] = embedding
                        
            except Exception as e:
                print(f"Embedding failed for '{query}': {e}")
                return []
        
        # Perform search using pre-computed embedding
        return self._search_with_embedding(query, collection, top_k, hop_number, embedding)
        try:
            response = self.qdrant_client.query_points(
                collection_name=collection,
                query=embedding,
                limit=top_k,
                score_threshold=0.3,
                with_payload=True,
                with_vectors=False
            )
            search_results = response.points
            
            # Convert to RetrievalResult objects
            results = []
            for hit in search_results:
                try:
                    if isinstance(hit, dict):
                        hit_id = hit.get('id', 'unknown')
                        hit_score = hit.get('score', 0.0)
                        hit_payload = hit.get('payload', {})
                    else:
                        hit_id = hit.id
                        hit_score = hit.score
                        hit_payload = hit.payload
                    
                    results.append(RetrievalResult(
                        chunk_id=str(hit_id),
                        doc_id=hit_payload.get('doc_id', 'unknown'),
                        content=hit_payload.get('text', hit_payload.get('content', '')),
                        score=float(hit_score),
                        vertical=collection.replace('ap_', '').replace('_documents', '').replace('_orders', '').replace('_reports', ''),
                        metadata=hit_payload,
                        rewrite_source=query,
                        hop_number=hop_number
                    ))
                except Exception as e:
                    print(f"Result parsing failed: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Search failed for {collection}: {e}")
            return []
    
    def generate_hop2_queries(
        self,
        hop1_results: List[RetrievalResult],
        limit: int = 3
    ) -> List[str]:
        """
        Generate queries for second hop based on first hop results
        Extracts key terms from top results
        """
        # Extract top chunks
        top_chunks = sorted(hop1_results, key=lambda x: x.score, reverse=True)[:10]
        
        # Extract key terms (simple heuristic - can be enhanced with LLM)
        key_terms = set()
        
        for chunk in top_chunks:
            # Extract GO refs, sections, etc.
            import re
            go_refs = re.findall(r'GO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*\d+', chunk.content, re.IGNORECASE)
            sections = re.findall(r'Section\s+\d+', chunk.content, re.IGNORECASE)
            
            key_terms.update(go_refs[:2])
            key_terms.update(sections[:2])
        
        # Generate new queries
        hop2_queries = list(key_terms)[:limit]
        
        return hop2_queries if hop2_queries else []
    
    def _generate_stub_results(
        self,
        queries: List[str],
        collections: List[str],
        top_k: int,
        hop_number: int
    ) -> List[RetrievalResult]:
        """Generate stub results for testing without Qdrant"""
        results = []
        
        for i, query in enumerate(queries):
            for j, collection in enumerate(collections):
                for k in range(min(3, top_k)):  # 3 results per query per collection
                    results.append(RetrievalResult(
                        chunk_id=f"stub_{i}_{j}_{k}",
                        doc_id=f"doc_{j}_{k}",
                        content=f"Stub content for query '{query}' from {collection}",
                        score=0.9 - (k * 0.1) - (i * 0.05),
                        vertical=collection.replace('ap_', ''),
                        metadata={'source': 'stub'},
                        rewrite_source=query,
                        hop_number=hop_number
                    ))
        
        return results
