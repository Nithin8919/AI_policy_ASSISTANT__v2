# Retrieval Engine - main orchestrator

"""
Retrieval Engine - Main orchestrator for V3 retrieval pipeline
Coordinates: normalization → interpretation → routing → retrieval → reranking
"""

import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Query understanding imports
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from query_understanding.query_normalizer import QueryNormalizer
from query_understanding.query_interpreter import QueryInterpreter, QueryInterpretation
from query_understanding.query_rewriter import QueryRewriter
from query_understanding.domain_expander import DomainExpander
from query_understanding.category_predictor import CategoryPredictor

from routing.vertical_router import VerticalRouter, Vertical
from routing.retrieval_plan import RetrievalPlanBuilder, RetrievalPlan
from pipeline.diversity_reranker import DiversityReranker

# Import BM25Booster with correct path
import sys
from pathlib import Path
retrieval_v3_dir = Path(__file__).parent.parent
sys.path.insert(0, str(retrieval_v3_dir / "retrieval"))
from bm25_boosting import BM25Booster

# Import production clause indexer  
from production_clause_indexer import ProductionClauseIndexer


@dataclass
class RetrievalResult:
    """Single retrieval result (chunk)"""
    chunk_id: str
    doc_id: str
    content: str
    score: float
    vertical: str
    metadata: Dict = field(default_factory=dict)
    rewrite_source: Optional[str] = None  # Which rewrite retrieved this
    hop_number: int = 1  # Which hop retrieved this


@dataclass
class RetrievalOutput:
    """Complete retrieval output"""
    query: str
    normalized_query: str
    interpretation: QueryInterpretation
    plan: RetrievalPlan
    rewrites: List[str]
    verticals_searched: List[str]
    results: List[RetrievalResult]
    total_candidates: int
    final_count: int
    processing_time: float
    metadata: Dict = field(default_factory=dict)


class RetrievalEngine:
    """
    Main V3 Retrieval Engine
    
    Orchestrates the complete retrieval pipeline:
    1. Query Understanding (normalize, interpret, rewrite, expand)
    2. Routing (select verticals, build plan)
    3. Retrieval (vector search across rewrites and verticals)
    4. Aggregation (merge and deduplicate)
    5. Reranking (LLM + diversity)
    """
    
    def __init__(
        self,
        qdrant_client=None,
        embedder=None,
        gemini_api_key: Optional[str] = None,
        use_llm_rewrites: bool = False,
        use_llm_reranking: bool = True,
        enable_cache: bool = True,
    ):
        """
        Initialize retrieval engine
        
        Args:
            qdrant_client: Qdrant client for vector search
            embedder: Embedding model for query encoding
            gemini_api_key: API key for Gemini Flash
            use_llm_rewrites: Use Gemini for query rewrites
            use_llm_reranking: Use Gemini for reranking
        """
        # Core components
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        # Flags
        self.use_llm_rewrites = use_llm_rewrites
        self.use_llm_reranking = use_llm_reranking
        self.enable_cache = enable_cache
        
        # Simple caches for speed
        if self.enable_cache:
            self._embedding_cache = {}
            self._llm_cache = {}
            self._cache_max_size = 100
            
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="v3_retrieval")
        self._lock = threading.Lock()  # For thread-safe cache access
        
        # Initialize pipeline components
        self.normalizer = QueryNormalizer()
        self.interpreter = QueryInterpreter()
        self.rewriter = QueryRewriter()
        self.expander = DomainExpander()
        self.category_predictor = CategoryPredictor()
        self.router = VerticalRouter()
        self.plan_builder = RetrievalPlanBuilder()
        self.diversity_reranker = DiversityReranker(self.category_predictor)
        self.bm25_booster = BM25Booster()
        
        # Initialize production clause indexer for instant clause lookup
        self.clause_indexer = ProductionClauseIndexer(qdrant_client) if qdrant_client else None
        
        # Stats
        self.stats = {
            'total_queries': 0,
            'avg_processing_time': 0,
            'cache_hits': 0,
        }
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        custom_plan: Optional[Dict] = None,
        force_verticals: Optional[List[str]] = None,
    ) -> RetrievalOutput:
        """
        Main retrieval function - orchestrates entire pipeline
        
        Args:
            query: Raw user query
            top_k: Override final result count
            custom_plan: Override retrieval plan parameters
            force_verticals: Force specific verticals (bypass routing)
            
        Returns:
            RetrievalOutput with results and metadata
        """
        start_time = time.time()
        
        # STEP 1: QUERY UNDERSTANDING (PARALLEL PROCESSING)
        # ====================================================================
        
        # 1.1: Normalize query (fast, no parallelization needed)
        normalized_query = self.normalizer.normalize_query(query)
        
        # 1.2: Submit parallel tasks for query understanding
        understanding_futures = {}
        
        # Interpretation task
        understanding_futures['interpretation'] = self.executor.submit(
            self.interpreter.interpret_query, normalized_query
        )
        
        # Rewrites task
        if self.use_llm_rewrites and self.gemini_api_key:
            understanding_futures['rewrites'] = self.executor.submit(
                self.rewriter.generate_rewrites_with_gemini,
                normalized_query, 3, self.gemini_api_key
            )
        else:
            understanding_futures['rewrites'] = self.executor.submit(
                self.rewriter.generate_rewrites,
                normalized_query, 3
            )
        
        # Wait for parallel tasks to complete
        try:
            interpretation = understanding_futures['interpretation'].result(timeout=2)
            rewrites_obj = understanding_futures['rewrites'].result(timeout=5)
            rewrites = [normalized_query] + [r.text for r in rewrites_obj]
        except Exception as e:
            print(f"Parallel query understanding failed: {e}")
            # Fallback to sequential
            interpretation = self.interpreter.interpret_query(normalized_query)
            rewrites = [normalized_query]
        
        # 1.4: Expand with domain keywords (parallel)
        expansion_futures = {
            self.executor.submit(self.expander.expand_query, r, 8): r 
            for r in rewrites
        }
        
        expanded_rewrites = []
        for future in as_completed(expansion_futures, timeout=3):
            try:
                expanded = future.result()
                expanded_rewrites.append(expanded)
            except Exception as e:
                original_query = expansion_futures[future]
                print(f"Expansion failed for '{original_query}': {e}")
                expanded_rewrites.append(original_query)  # Use original as fallback
        
        # STEP 2: ROUTING & PLANNING
        # ====================================================================
        
        # 2.1: Route to verticals
        if force_verticals:
            verticals = [Vertical(v) for v in force_verticals]
        else:
            verticals = self.router.route_query(
                normalized_query,
                interpretation.query_type.value,
                interpretation.detected_entities
            )
        
        collection_names = self.router.get_collection_names(verticals)
        
        # 2.2: Build retrieval plan
        plan = self.plan_builder.build_plan(
            query_type=interpretation.query_type.value,
            scope=interpretation.scope.value,
            needs_internet=interpretation.needs_internet,
            num_verticals=len(verticals),
            custom_params=custom_plan
        )
        
        # Override top_k if provided
        if top_k:
            plan.top_k_total = top_k
        
        # STEP 3: RETRIEVAL
        # ====================================================================
        
        all_results = []
        
        # 3.1: First hop - parallel retrieval with all rewrites
        hop1_results = self._parallel_retrieve_hop(
            expanded_rewrites,
            collection_names,
            top_k=plan.top_k_per_vertical,
            hop_number=1
        )
        all_results.extend(hop1_results)
        
        # 3.2: Multi-hop retrieval (if enabled)
        if plan.num_hops > 1 and hop1_results:
            hop2_queries = self._generate_hop2_queries(hop1_results, limit=3)
            hop2_results = self._parallel_retrieve_hop(
                hop2_queries,
                collection_names,
                top_k=plan.top_k_per_vertical // 2,
                hop_number=2
            )
            all_results.extend(hop2_results)
        
        # STEP 4: AGGREGATION
        # ====================================================================
        
        # 4.1: Deduplicate by chunk_id
        unique_results = self._deduplicate_results(all_results)
        
        # 4.2: Limit to total budget
        unique_results = unique_results[:plan.top_k_total]
        
        # STEP 5: ENHANCED RERANKING WITH CATEGORY COVERAGE
        # ====================================================================
        
        # 5.1: Predict required policy categories for comprehensive coverage
        predicted_categories = self.category_predictor.predict_categories(
            normalized_query, 
            query_type=interpretation.query_type.value
        )
        
        # 5.2: BM25 boosting for infrastructure/scheme documents
        bm25_boosted = self.bm25_booster.boost_results(
            normalized_query,
            unique_results,
            boost_threshold=0.3
        )
        
        # 5.3: LLM-based reranking (if enabled)
        if self.use_llm_reranking and self.gemini_api_key:
            reranked = self._llm_rerank(
                normalized_query,
                bm25_boosted,
                top_k=plan.rerank_top_k
            )
        else:
            # Simple score-based ranking
            reranked = sorted(
                bm25_boosted,
                key=lambda x: x.score,
                reverse=True
            )[:plan.rerank_top_k]
        
        # 5.4: Diversity reranking with mandatory category coverage
        final_results = self.diversity_reranker.rerank_with_diversity(
            normalized_query,
            reranked,
            predicted_categories,
            top_k=plan.top_k_total,
            diversity_weight=plan.diversity_weight
        )
        
        # 5.5: Clause indexer lookup for legal queries with poor results
        if self._is_legal_clause_query(normalized_query) and len(final_results) < 3:
            clause_results = self._clause_indexer_lookup(normalized_query)
            if clause_results:
                print(f"🎯 Clause indexer found {len(clause_results)} results for '{normalized_query}'")
                # Merge with existing results, prioritizing clause indexer results
                final_results = clause_results + [r for r in final_results if r.chunk_id not in {c.chunk_id for c in clause_results}]
                final_results = final_results[:plan.top_k_total]
            else:
                # Fallback to original clause scanner
                clause_results = self._fallback_clause_scan(normalized_query, collection_names)
                if clause_results:
                    final_results = clause_results + [r for r in final_results if r.chunk_id not in {c.chunk_id for c in clause_results}]
                    final_results = final_results[:plan.top_k_total]
        
        # STEP 6: PACKAGE OUTPUT
        # ====================================================================
        
        processing_time = time.time() - start_time
        
        output = RetrievalOutput(
            query=query,
            normalized_query=normalized_query,
            interpretation=interpretation,
            plan=plan,
            rewrites=rewrites,
            verticals_searched=[v.value for v in verticals],
            results=final_results,
            total_candidates=len(all_results),
            final_count=len(final_results),
            processing_time=processing_time,
            metadata={
                'num_rewrites': len(rewrites),
                'num_verticals': len(verticals),
                'num_hops': plan.num_hops,
                'dedup_reduction': len(all_results) - len(unique_results),
                'predicted_categories': [cat.value for cat in predicted_categories],
                'category_coverage_report': self.diversity_reranker.get_category_coverage_report(
                    normalized_query, final_results, predicted_categories
                ) if final_results else {}
            }
        )
        
        # Update stats
        self._update_stats(output)
        
        return output
    
    def _is_legal_clause_query(self, query: str) -> bool:
        """Check if query is asking for specific legal clause/section/rule"""
        import re
        query_lower = query.lower()
        patterns = [
            r'\b(?:section|clause|article|rule|sub-rule|amendment)\s+\d+',
            r'\b(?:rte|cce|apsermc|education)\s+act\b',
            r'\b\d+\(\d+\)\(\w+\)\b',  # 12(1)(c) pattern
            r'\b(?:act|rule|regulation)\s+\d+',
            r'\bsection\s+\d+\b',
            r'\brule\s+\d+\b',
            r'\barticle\s+\d+\w*\b'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _clause_indexer_lookup(self, query: str) -> List[RetrievalResult]:
        """
        Use clause indexer for instant clause lookup
        """
        if not self.clause_indexer:
            return []
        
        try:
            clause_matches = self.clause_indexer.lookup_clause(query)
            results = []
            
            for match in clause_matches:
                results.append(RetrievalResult(
                    chunk_id=match.chunk_id,
                    doc_id=match.doc_id,
                    content=match.content,
                    score=match.confidence,
                    vertical=match.vertical,
                    metadata={'source': 'clause_indexer'},
                    rewrite_source='clause_indexer'
                ))
            
            return results
            
        except Exception as e:
            print(f"Clause indexer lookup failed: {e}")
            return []
    
    def _fallback_clause_scan(
        self, 
        query: str, 
        collection_names: List[str]
    ) -> List[RetrievalResult]:
        """
        Fallback exact clause scanner for legal queries
        When regular search fails, scan for exact clause matches
        """
        import re
        
        query_lower = query.lower()
        
        # Extract clause/section patterns
        clause_patterns = []
        
        # Section X
        section_match = re.search(r'section\s+(\d+)', query_lower)
        if section_match:
            section_num = section_match.group(1)
            clause_patterns.extend([
                f'section {section_num}',
                f'section {section_num}.',
                f'({section_num})',
                f'{section_num})'
            ])
        
        # Rule X
        rule_match = re.search(r'rule\s+(\d+)', query_lower)
        if rule_match:
            rule_num = rule_match.group(1)
            clause_patterns.extend([
                f'rule {rule_num}',
                f'rule {rule_num}.',
                f'({rule_num})'
            ])
        
        # Article X
        article_match = re.search(r'article\s+(\d+\w*)', query_lower)
        if article_match:
            article_num = article_match.group(1)
            clause_patterns.extend([
                f'article {article_num}',
                f'article {article_num}.'
            ])
        
        if not clause_patterns:
            return []
        
        # Search for exact matches in legal collection
        legal_collections = [c for c in collection_names if 'legal' in c.lower()]
        if not legal_collections:
            return []
        
        try:
            results = []
            
            for collection in legal_collections:
                # Use simple text search since Filter might be complex
                for pattern in clause_patterns[:2]:  # Limit patterns to avoid timeout
                    try:
                        search_results = self.qdrant_client.scroll(
                            collection_name=collection,
                            limit=10,
                            with_payload=True
                        )
                        
                        if search_results[0]:
                            for point in search_results[0]:
                                content = point.payload.get('content', '').lower()
                                if pattern in content:
                                    results.append(RetrievalResult(
                                        chunk_id=str(point.id),
                                        doc_id=point.payload.get('doc_id', 'unknown'),
                                        content=point.payload.get('content', ''),
                                        score=1.0,  # High score for exact matches
                                        vertical='legal',
                                        metadata=point.payload,
                                        rewrite_source='fallback_clause_scanner'
                                    ))
                    except Exception as e:
                        print(f"Pattern search failed for {pattern}: {e}")
                        continue
            
            # Remove duplicates and return top 3
            unique_results = {}
            for result in results:
                if result.chunk_id not in unique_results:
                    unique_results[result.chunk_id] = result
            
            return list(unique_results.values())[:3]
            
        except Exception as e:
            print(f"Fallback clause scanner failed: {e}")
            return []

    def cleanup(self):
        """Clean up resources (thread pool, etc.)"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup()
        except:
            pass
    
    def _parallel_retrieve_hop(
        self,
        queries: List[str],
        collections: List[str],
        top_k: int,
        hop_number: int = 1
    ) -> List[RetrievalResult]:
        """
        Parallel retrieval across all query-collection combinations
        
        This dramatically speeds up retrieval by running searches concurrently
        """
        if not self.qdrant_client or not self.embedder:
            return self._generate_stub_results(queries, collections, top_k, hop_number)
        
        # Create all search tasks
        search_tasks = []
        for query in queries:
            for collection in collections:
                search_tasks.append((query, collection, top_k, hop_number))
        
        # Execute searches in parallel
        all_results = []
        
        # Submit all tasks to thread pool
        future_to_task = {
            self.executor.submit(self._search_single_threadsafe, task[0], task[1], task[2], task[3]): task
            for task in search_tasks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task, timeout=30):  # 30s total timeout
            try:
                results = future.result(timeout=5)  # 5s per individual search
                if results:
                    all_results.extend(results)
            except Exception as e:
                task = future_to_task[future]
                print(f"Parallel search failed for {task[0]} in {task[1]}: {e}")
                continue
        
        return all_results
    
    def _search_single_threadsafe(
        self,
        query: str,
        collection: str,
        top_k: int,
        hop_number: int = 1
    ) -> List[RetrievalResult]:
        """Thread-safe version of single search with caching"""
        
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
        
        # Perform search
        try:
            search_results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=embedding,
                limit=top_k,
                score_threshold=0.3
            )
            
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
    
    def _retrieve_hop(
        self,
        queries: List[str],
        collections: List[str],
        top_k: int,
        hop_number: int = 1
    ) -> List[RetrievalResult]:
        """
        Retrieve documents for a single hop
        
        Args:
            queries: List of query variations
            collections: Qdrant collections to search
            top_k: Results per query per collection
            hop_number: Which hop this is (for tracking)
            
        Returns:
            List of RetrievalResult objects
        """
        results = []
        
        if not self.qdrant_client or not self.embedder:
            # Stub results for testing without Qdrant
            return self._generate_stub_results(queries, collections, top_k, hop_number)
        
        for query in queries:
            # Check embedding cache first
            query_vector = None
            if self.enable_cache and query in self._embedding_cache:
                query_vector = self._embedding_cache[query]
                self.stats['cache_hits'] += 1
            else:
                # Embed query
                if hasattr(self.embedder, 'embed_single'):
                    query_vector = self.embedder.embed_single(query)
                elif hasattr(self.embedder, 'embed_query'):
                    query_vector = self.embedder.embed_query(query)
                else:
                    query_vector = self.embedder.embed_texts([query])[0]
                
                # Cache the embedding
                if self.enable_cache:
                    if len(self._embedding_cache) >= self._cache_max_size:
                        # Simple cache eviction - remove oldest
                        oldest_key = next(iter(self._embedding_cache))
                        del self._embedding_cache[oldest_key]
                    self._embedding_cache[query] = query_vector
            
            for collection in collections:
                try:
                    # Vector search
                    search_results = self.qdrant_client.search(
                        collection_name=collection,
                        query_vector=query_vector,
                        limit=top_k
                    )
                    
                    # Convert to RetrievalResult objects
                    for hit in search_results:
                        # Handle both dict and object formats
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
                            score=hit_score,
                            vertical=collection.replace('ap_', '').replace('_documents', '').replace('_orders', '').replace('_reports', ''),
                            metadata=hit_payload,
                            rewrite_source=query,
                            hop_number=hop_number
                        ))
                
                except Exception as e:
                    print(f"Error searching {collection}: {e}")
                    continue
        
        return results
    
    def _generate_hop2_queries(
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
    
    def _deduplicate_results(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Deduplicate results by chunk_id, keeping highest score"""
        seen = {}
        
        for result in results:
            if result.chunk_id not in seen:
                seen[result.chunk_id] = result
            else:
                # Keep higher score
                if result.score > seen[result.chunk_id].score:
                    seen[result.chunk_id] = result
        
        # Return sorted by score
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)
    
    def _llm_rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 20
    ) -> List[RetrievalResult]:
        """
        Rerank using Gemini Flash for semantic relevance
        
        Fast and cheap reranking with Gemini 1.5 Flash 8B
        """
        if not self.gemini_api_key or not results:
            return results[:top_k]
        
        # Check cache for LLM reranking
        cache_key = f"{query}_{len(results)}"
        if self.enable_cache and cache_key in self._llm_cache:
            cached_ranking = self._llm_cache[cache_key]
            self.stats['cache_hits'] += 1
            # Apply cached ranking
            reranked = []
            for idx in cached_ranking:
                if idx < len(results):
                    reranked.append(results[idx])
            return reranked[:top_k]
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-8b')
            
            # Prepare candidates (top results only to save tokens)
            candidates = results[:min(30, len(results))]
            
            # Build prompt
            candidates_text = "\n\n".join([
                f"ID: {i}\nContent: {r.content[:300]}..."  # First 300 chars
                for i, r in enumerate(candidates)
            ])
            
            prompt = f"""You are a relevance judge for education policy documents.

Query: {query}

Rank these document chunks by relevance to the query. Return ONLY a comma-separated list of IDs in order of relevance (most relevant first).

Candidates:
{candidates_text}

Output format: 0,5,2,8,1,... (just the IDs, comma-separated)"""

            # Generate ranking
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,  # Low temperature for consistency
                    'max_output_tokens': 100,
                }
            )
            
            # Parse response
            ranked_ids = [int(x.strip()) for x in response.text.strip().split(',') if x.strip().isdigit()]
            
            # Cache the ranking
            if self.enable_cache:
                if len(self._llm_cache) >= self._cache_max_size:
                    oldest_key = next(iter(self._llm_cache))
                    del self._llm_cache[oldest_key]
                self._llm_cache[cache_key] = ranked_ids
            
            # Reorder results
            reranked = []
            for rank_id in ranked_ids:
                if rank_id < len(candidates):
                    # Update score based on LLM rank
                    result = candidates[rank_id]
                    result.score = 1.0 - (rank_id / len(ranked_ids))  # Normalize score
                    reranked.append(result)
            
            # Add remaining results
            remaining = [r for i, r in enumerate(candidates) if i not in ranked_ids]
            reranked.extend(remaining)
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"LLM reranking failed: {e}, using score-based ranking")
            return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
    
    def _diversity_rerank(
        self,
        results: List[RetrievalResult],
        diversity_weight: float = 0.3,
        top_k: int = 20
    ) -> List[RetrievalResult]:
        """
        Ensure diversity across verticals/categories
        
        MMR-style reranking balancing relevance and diversity
        """
        if diversity_weight == 0:
            return results[:top_k]
        
        selected = []
        remaining = results.copy()
        
        # Track coverage
        vertical_counts = {}
        
        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -1
            
            for i, result in enumerate(remaining):
                # Relevance score
                rel_score = result.score
                
                # Diversity penalty (how many from this vertical already selected)
                vertical = result.vertical
                vertical_count = vertical_counts.get(vertical, 0)
                div_penalty = vertical_count * diversity_weight
                
                # Combined score
                combined = rel_score - div_penalty
                
                if combined > best_score:
                    best_score = combined
                    best_idx = i
            
            # Select best
            selected_result = remaining.pop(best_idx)
            selected.append(selected_result)
            
            # Update vertical count
            vertical_counts[selected_result.vertical] = \
                vertical_counts.get(selected_result.vertical, 0) + 1
        
        return selected
    
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
    
    def _update_stats(self, output: RetrievalOutput):
        """Update engine statistics"""
        self.stats['total_queries'] += 1
        
        # Update running average
        n = self.stats['total_queries']
        old_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = \
            (old_avg * (n - 1) + output.processing_time) / n


# Convenience function
def retrieve(query: str, qdrant_client=None, embedder=None) -> RetrievalOutput:
    """Quick retrieval function"""
    engine = RetrievalEngine(qdrant_client=qdrant_client, embedder=embedder)
    return engine.retrieve(query)


# Example usage and tests
if __name__ == "__main__":
    print("Retrieval Engine V3 - Testing")
    print("=" * 80)
    
    # Test without Qdrant (stub mode)
    engine = RetrievalEngine(
        qdrant_client=None,
        embedder=None,
        use_llm_rewrites=False,
        use_llm_reranking=False
    )
    
    test_queries = [
        "What is Section 12(1)(c) of RTE Act?",
        "Design a comprehensive FLN framework",
        "Compare Nadu-Nedu and Samagra Shiksha schemes",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 80)
        
        output = engine.retrieve(query)
        
        print(f"Normalized: {output.normalized_query}")
        print(f"Type: {output.interpretation.query_type.value}")
        print(f"Scope: {output.interpretation.scope.value}")
        print(f"Mode: {output.plan.mode}")
        print(f"Verticals: {output.verticals_searched}")
        print(f"Rewrites: {len(output.rewrites)}")
        print(f"Results: {output.final_count} (from {output.total_candidates} candidates)")
        print(f"Processing time: {output.processing_time:.3f}s")
        
        print("\nTop 3 Results:")
        for i, result in enumerate(output.results[:3], 1):
            print(f"  {i}. [{result.vertical}] Score: {result.score:.3f}")
            print(f"     {result.content[:100]}...")
        
        print("=" * 80)
    
    print(f"\nEngine Stats:")
    print(f"  Total queries: {engine.stats['total_queries']}")
    print(f"  Avg processing time: {engine.stats['avg_processing_time']:.3f}s")
