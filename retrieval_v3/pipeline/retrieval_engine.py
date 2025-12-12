# Retrieval Engine - main orchestrator

"""
Retrieval Engine - Main orchestrator for V3 retrieval pipeline
Coordinates: normalization → interpretation → routing → retrieval → reranking
"""

import time
from typing import List, Dict, Optional, Any
import os
from concurrent.futures import ThreadPoolExecutor
import threading
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
retrieval_v3_dir = Path(__file__).parent.parent
sys.path.insert(0, str(retrieval_v3_dir / "retrieval"))
from bm25_boosting import BM25Booster

# Import production clause indexer  
from production_clause_indexer import ProductionClauseIndexer

# Import answer generation components
from answer_generation.answer_builder import AnswerBuilder, Answer
from answer_generation.answer_validator import AnswerValidator

# Import relation-entity system
from relation_reranker import RelationEntityProcessor

# NEW IMPORTS
from retrieval_core.bm25_retriever import BM25Retriever
from retrieval_core.supersession_manager import SupersessionManager
from reranking.cross_encoder_reranker import CrossEncoderReranker
from retrieval_core.hybrid_search import HybridSearcher
from cache.query_cache import QueryCache
from internet.google_search_client import GoogleSearchClient

# Import modularized components
from .models import RetrievalResult, RetrievalOutput
from .query_coordinator import QueryUnderstandingCoordinator
from .retrieval_executor import RetrievalExecutor
from .result_processor import ResultProcessor
from .reranking_coordinator import RerankingCoordinator
from .legal_clause_handler import LegalClauseHandler
from .internet_handler import InternetSearchHandler
from .engine_stats import EngineStatsManager

# Re-export models for backward compatibility
__all__ = ['RetrievalEngine', 'RetrievalResult', 'RetrievalOutput', 'retrieve']


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
        gemini_api_key: Optional[str] = None, # Deprecated, kept for backward compatibility
        use_llm_rewrites: bool = False,
        use_llm_reranking: bool = True,
        use_cross_encoder: bool = True, # Default to True now
        enable_cache: bool = True,
        use_relation_entity: bool = True,
    ):
        """
        Initialize retrieval engine
        
        Args:
            qdrant_client: Qdrant client for vector search
            embedder: Embedding model for query encoding
            gemini_api_key: Deprecated/Ignored (We strictly use OAuth/Vertex AI now)
            use_llm_rewrites: Use Gemini for query rewrites
            use_llm_reranking: Use Gemini for reranking
            use_cross_encoder: Use cross-encoder model for reranking
            use_relation_entity: Use relation and entity aware processing
        """
        # Core components
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        
        # REMOVED API Key logic - STRICTLY OAUTH
        # Leave None so any legacy API-key code paths short-circuit.
        self.gemini_api_key = None
        
        # Flags
        self.use_llm_rewrites = use_llm_rewrites
        self.use_llm_reranking = use_llm_reranking
        self.use_cross_encoder = use_cross_encoder
        self.enable_cache = enable_cache
        self.use_relation_entity = use_relation_entity
        
        # Thread pool for parallel operations
        # OPTIMIZATION P2-4: Adaptive sizing will be applied per-query (executor shared)
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
        
        # NEW: Initialize BM25 Retriever
        self.bm25_retriever = BM25Retriever(qdrant_client) if qdrant_client else None
        
        # NEW: Initialize Hybrid Searcher
        self.hybrid_searcher = HybridSearcher()
        
        # Supersession tracking - DISABLED: Relation reranker already uses 'is_superseded' from payload
        # This manager would scan 5495 docs at startup to find only 13 supersessions (slow + redundant)
        self.supersession_manager = None  # SupersessionManager(qdrant_client) if qdrant_client else None
        
        # Initialize production clause indexer for instant clause lookup
        self.clause_indexer = ProductionClauseIndexer(qdrant_client) if qdrant_client else None
        
        # Initialize answer generation and validation components
        # Removed API key passing - AnswerBuilder uses OAuth internally now
        self.answer_builder = AnswerBuilder(use_llm=True)
        self.answer_validator = AnswerValidator()
        
        # Initialize cross-encoder model (lazy loading)
        self.cross_encoder = None
        if self.use_cross_encoder:
            self.cross_encoder = CrossEncoderReranker()
        
        # Initialize relation-entity processor
        self.relation_entity_processor = None
        if self.use_relation_entity:
            self.relation_entity_processor = RelationEntityProcessor(qdrant_client)
        
        # Initialize query cache (10 minute TTL)
        self.query_cache = QueryCache(ttl_seconds=600)
        
        # Initialize Diagnostic Runner
        from diagnostics.diagnostic_runner import DiagnosticRunner
        # Removed API key passing
        self.diagnostic_runner = DiagnosticRunner()
        
        # NEW: Initialize Google Search Client
        # Removed API key passing
        self.google_search_client = GoogleSearchClient()
        
        # Initialize stats manager
        self.stats_manager = EngineStatsManager(enable_cache=enable_cache)
        # Share stats dict reference for backward compatibility
        self.stats = self.stats_manager.stats
        
        # Initialize coordinators
        self.query_coordinator = QueryUnderstandingCoordinator(
            normalizer=self.normalizer,
            interpreter=self.interpreter,
            rewriter=self.rewriter,
            expander=self.expander,
            executor=self.executor,
            use_llm_rewrites=use_llm_rewrites
        )
        
        # Get cache references from stats manager (shared caches)
        embedding_cache = self.stats_manager.get_embedding_cache()
        llm_cache = self.stats_manager.get_llm_cache()
        
        self.retrieval_executor = RetrievalExecutor(
            qdrant_client=qdrant_client,
            embedder=embedder,
            executor=self.executor,
            lock=self._lock,
            enable_cache=enable_cache,
            embedding_cache=embedding_cache,
            cache_max_size=self.stats_manager._cache_max_size,
            stats=self.stats,
            bm25_retriever=self.bm25_retriever,
            hybrid_searcher=self.hybrid_searcher
        )
        
        self.result_processor = ResultProcessor()
        
        self.reranking_coordinator = RerankingCoordinator(
            category_predictor=self.category_predictor,
            diversity_reranker=self.diversity_reranker,
            cross_encoder=self.cross_encoder,
            relation_entity_processor=self.relation_entity_processor,
            use_cross_encoder=use_cross_encoder,
            use_relation_entity=use_relation_entity,
            gemini_api_key=self.gemini_api_key,
            enable_cache=enable_cache,
            llm_cache=llm_cache,
            cache_max_size=self.stats_manager._cache_max_size,
            stats=self.stats
        )
        
        self.legal_clause_handler = LegalClauseHandler(
            clause_indexer=self.clause_indexer,
            qdrant_client=qdrant_client
        )
        
        self.internet_handler = InternetSearchHandler(
            google_search_client=self.google_search_client
        )
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        custom_plan: Optional[Dict] = None,
        force_verticals: Optional[List[str]] = None,
        external_context: Optional[str] = None
    ) -> RetrievalOutput:
        """
        Main retrieval function - orchestrates entire pipeline
        
        Args:
            query: Raw user query
            top_k: Override final result count
            custom_plan: Override retrieval plan parameters
            force_verticals: Force specific verticals (bypass routing)
            external_context: Additional context (e.g. from uploaded files)
            
        Returns:
            RetrievalOutput with results and metadata
        """
        start_time = time.time()
        trace_steps = []
        trace_steps.append("Understanding your query...")
        
        # OPTIMIZATION P4-2: Track per-stage timings
        stage_start = time.time()
        
        # STEP 1: QUERY UNDERSTANDING (PARALLEL PROCESSING)
        # ====================================================================
        
        # 1.1: Normalize query
        normalized_query = self.normalizer.normalize_query(query)
        logger.info(f"📝 Normalized query: {normalized_query}")
        
        # P1 Quick Win #3: Auto-pin filters for "recent GOs" queries
        force_filter = None
        if "recent" in normalized_query.lower() and ("go" in normalized_query.lower() or "government order" in normalized_query.lower()):
            import time as time_module
            # Round to start of day for cache stability
            now_ts = int(time_module.time())
            start_of_day = (now_ts // 86400) * 86400
            eighteen_months_ago = start_of_day - (18 * 30 * 86400)
            
            force_filter = {
                "must": [
                    {"key": "vertical", "match": {"value": "go"}},
                    {"key": "date_issued_ts", "range": {"gte": eighteen_months_ago}}
                ]
            }
            
            # Extract department if mentioned
            if "school education" in normalized_query.lower():
                force_filter["must"].append({
                    "key": "department",
                    "match": {"value": "School Education"}
                })
            
            logger.info(f"🎯 Auto-pinned filters for recent GOs query (last 18 months)")
        
        # CHECK CACHE FIRST (after normalization and filter determination)
        # OPTIMIZATION P2-5: Include mode in cache lookup
        logger.info(f"DEBUG: enable_cache={self.enable_cache}")
        if self.enable_cache:
            mode = custom_plan.get('mode') if custom_plan else None
            cached_result = self.query_cache.get(normalized_query, force_filter, mode=mode)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # 1.2: CLAUSE INDEXER FAST PATH - Handle legal clause queries instantly
        # ====================================================================
        is_qa_mode = custom_plan and custom_plan.get('mode') == 'qa'
        fast_path_result = self.legal_clause_handler.try_fast_path(query, normalized_query, top_k)
        if fast_path_result:
            fast_interpretation, fast_plan, clause_results = fast_path_result
            processing_time = time.time() - start_time
            
            output = RetrievalOutput(
                query=query,
                normalized_query=normalized_query,
                interpretation=fast_interpretation,
                plan=fast_plan,
                rewrites=[normalized_query],  # Single rewrite
                verticals_searched=['legal'],
                results=clause_results,
                total_candidates=len(clause_results),
                final_count=len(clause_results),
                processing_time=processing_time,
                metadata={
                    'fast_path': True,
                    'clause_indexer_hits': len(clause_results),
                    'bypass_full_pipeline': True,
                    'fast_path_confidence': 0.95
                }
            )
            
            self.stats_manager.update_stats(output)
            return output
        
        # Add trace step for understanding phase
        trace_steps.append("Expanding and rewriting query...")
        
        # 1.3: Query Understanding via Coordinator
        # Pass already-normalized query to avoid double normalization
        interpretation, rewrites, expanded_rewrites = self.query_coordinator.understand_query(
            query=query,
            normalized_query=normalized_query,
            external_context=external_context,
            is_qa_mode=is_qa_mode
        )
        
        # OPTIMIZATION P2-4: Adaptive thread pool sizing based on query complexity
        # Note: Executor is shared, but we log the optimal size for monitoring
        if is_qa_mode:
            optimal_workers = 4
        elif interpretation.query_type.value in ['policy', 'framework', 'brainstorm']:
            optimal_workers = 10
        else:
            optimal_workers = 6
        logger.debug(f"🔧 Optimal thread pool size for this query: {optimal_workers} workers")
        
        # Add context entities trace if external context provided
        if external_context:
            context_entities = self.query_coordinator.extract_entities_from_text(external_context)
            if context_entities:
                trace_steps.append("Analyzing uploaded file content...")
                logger.info(f"📄 Extracted entities from file: {context_entities}")
                trace_steps.append(f"Found relevant entities in file: {', '.join(context_entities[:3])}...")
        
        # OPTIMIZATION P4-2: Record query understanding timing
        query_understanding_time = time.time() - stage_start
        self.stats_manager.record_stage_timing('query_understanding', query_understanding_time)
        stage_start = time.time()
        
        # STEP 2: ROUTING & PLANNING
        # ====================================================================
        
        trace_steps.append("Searching verticals...")
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
        
        # OPTIMIZATION: Make QA mode lightweight (faster retrieval)
        if is_qa_mode:
            # Reduce rewrites, disable LLM rewrites, reduce expansion, single hop
            plan.num_rewrites = 1  # Only use original query + minimal rewrites
            plan.num_hops = 1  # Single hop only
            logger.info("⚡ QA mode: Using lightweight retrieval (1 rewrite, 1 hop)")
        
        # OPTIMIZATION P4-2: Record routing timing
        routing_time = time.time() - stage_start
        self.stats_manager.record_stage_timing('routing', routing_time)
        stage_start = time.time()
        
        # STEP 3: RETRIEVAL (HYBRID)
        # ====================================================================
        
        all_results = []
        trace_steps.append("Running hybrid retrieval (vector + BM25)...")
        
        # Execute for all rewrites
        # Run hybrid for original query
        all_results.extend(self.retrieval_executor.execute_hybrid_search(
            normalized_query, collection_names, plan, hop=1
        ))
        
        # OPTIMIZATION P1-5: Early exit check after first retrieval
        # Check if we have high-quality results that don't need multi-hop or expensive reranking
        early_exit_triggered = False
        if all_results:
            # Get top results and check their scores (use raw_score if available)
            top_results = sorted(all_results, key=lambda x: x.metadata.get('raw_score', x.score), reverse=True)[:3]
            top_scores = [r.metadata.get('raw_score', r.score) for r in top_results]
            
            # Early exit conditions:
            # 1. Top-3 results have high scores (> 0.8)
            # 2. Query is simple QA (not complex policy/framework)
            # 3. We have at least 3 good results
            has_excellent_results = (
                len(top_scores) >= 3 and
                max(top_scores) > 0.8 and
                sum(top_scores) / len(top_scores) > 0.75
            )
            is_simple_query = (
                interpretation.query_type.value == 'qa' and
                interpretation.scope.value == 'narrow' and
                len(normalized_query.split()) < 10
            )
            
            if has_excellent_results and is_simple_query:
                early_exit_triggered = True
                logger.info(f"⚡ Early exit triggered: excellent results found (top score: {max(top_scores):.2f})")
                # Skip rewrites, multi-hop, and use lightweight reranking
                all_results = top_results + all_results[3:plan.top_k_total * 2]  # Keep top + some more for diversity
        
        # Run vector-only for rewrites (to keep it fast) - SKIP if early exit
        if not early_exit_triggered and len(expanded_rewrites) > 1:
            rewrite_results = self.retrieval_executor.parallel_retrieve_hop(
                expanded_rewrites[1:], # Skip original
                collection_names,
                top_k=plan.top_k_per_vertical,
                hop_number=1
            )
            all_results.extend(self.result_processor.normalize_scores(rewrite_results, method='min-max'))
            
        # 3.2: Multi-hop retrieval (if enabled) - SKIP if early exit
        # OPTIMIZATION P2-1: Conditional multi-hop - only run if needed
        if not early_exit_triggered and plan.num_hops > 1 and all_results:
            # Check if first hop results are good enough
            top_scores_hop1 = [r.metadata.get('raw_score', r.score) for r in all_results[:5]]
            max_score_hop1 = max(top_scores_hop1) if top_scores_hop1 else 0.0
            avg_score_hop1 = sum(top_scores_hop1) / len(top_scores_hop1) if top_scores_hop1 else 0.0
            
            # Only run multi-hop if:
            # 1. First hop results are poor (max < 0.6) OR
            # 2. Query type requires deep search (POLICY/FRAMEWORK) OR
            # 3. User explicitly requested deep search (custom_plan)
            should_run_multihop = (
                max_score_hop1 < 0.6 or  # Poor results
                interpretation.query_type.value in ['policy', 'framework', 'brainstorm'] or  # Complex query
                (custom_plan and custom_plan.get('deep_search', False))  # Explicit request
            )
            
            if should_run_multihop:
                logger.info(f"🔄 Running multi-hop retrieval (max_score={max_score_hop1:.2f}, query_type={interpretation.query_type.value})")
                hop2_queries = self.retrieval_executor.generate_hop2_queries(all_results, limit=3)
                hop2_results = self.retrieval_executor.parallel_retrieve_hop(
                    hop2_queries,
                    collection_names,
                    top_k=plan.top_k_per_vertical // 2,
                    hop_number=2
                )
                all_results.extend(self.result_processor.normalize_scores(hop2_results, method='min-max'))
            else:
                logger.info(f"⚡ Skipping multi-hop (good results from first hop: max_score={max_score_hop1:.2f})")
        
        # 3.3: Internet Retrieval (Optional Layer)
        # ====================================================================
        internet_enabled = self.internet_handler.should_enable_internet(plan, custom_plan)
        if internet_enabled:
            internet_results = self.internet_handler.search(query, trace_steps)
            all_results.extend(internet_results)
        
        # OPTIMIZATION P4-2: Record retrieval timing
        retrieval_time = time.time() - stage_start
        self.stats_manager.record_stage_timing('retrieval', retrieval_time)
        stage_start = time.time()
        
        # STEP 4: AGGREGATION & FILTERING
        # ====================================================================
        
        # 4.1: Deduplicate
        unique_results = self.result_processor.deduplicate_results(all_results)
        
        # 4.2: Supersession Filtering
        if self.supersession_manager:
            active_results = []
            superseded_results = []
            
            for res in unique_results:
                if self.supersession_manager.is_superseded(res.doc_id):
                    # Mark as superseded in metadata
                    res.metadata['is_superseded'] = True
                    res.metadata['superseded_by'] = self.supersession_manager.get_superseding_doc_id(res.doc_id)
                    superseded_results.append(res)
                else:
                    active_results.append(res)
            
            # Prioritize active results, but keep superseded ones at the bottom if relevant
            unique_results = active_results + superseded_results
        
        # 4.3: Limit to total budget
        unique_results = unique_results[:plan.top_k_total * 2] # Keep more for reranking
        
        # OPTIMIZATION P4-2: Record aggregation timing
        aggregation_time = time.time() - stage_start
        self.stats_manager.record_stage_timing('aggregation', aggregation_time)
        stage_start = time.time()
        
        # STEP 5: ENHANCED RERANKING
        # ====================================================================
        # OPTIMIZATION P1-5: Use lightweight reranking for early exit cases
        if early_exit_triggered:
            # Lightweight reranking: just sort by score and apply diversity
            trace_steps.append("Applying lightweight reranking (early exit)...")
            sorted_results = sorted(unique_results, key=lambda x: x.metadata.get('raw_score', x.score), reverse=True)
            # Simple diversity: take top result from each vertical if multiple verticals
            final_results = []
            seen_verticals = set()
            for r in sorted_results:
                if r.vertical not in seen_verticals or len(final_results) < plan.top_k_total:
                    final_results.append(r)
                    seen_verticals.add(r.vertical)
                if len(final_results) >= plan.top_k_total:
                    break
            logger.info(f"⚡ Early exit: Using lightweight reranking ({len(final_results)} results)")
        else:
            # Full reranking pipeline
            final_results = self.reranking_coordinator.rerank(
                query=query,
                normalized_query=normalized_query,
                results=unique_results,
                interpretation=interpretation,
                plan=plan,
                trace_steps=trace_steps,
                bm25_booster=self.bm25_booster
            )
        
        # 5.6: Clause indexer lookup for legal queries with poor results
        if self.legal_clause_handler.is_legal_clause_query(normalized_query) and len(final_results) < 3:
            clause_results = self.legal_clause_handler.clause_indexer_lookup(normalized_query)
            if clause_results:
                print(f"🎯 Clause indexer found {len(clause_results)} results for '{normalized_query}'")
                # Merge with existing results, prioritizing clause indexer results
                final_results = clause_results + [r for r in final_results if r.chunk_id not in {c.chunk_id for c in clause_results}]
                final_results = final_results[:plan.top_k_total]
            else:
                # Fallback to original clause scanner
                clause_results = self.legal_clause_handler.fallback_clause_scan(normalized_query, collection_names)
                if clause_results:
                    final_results = clause_results + [r for r in final_results if r.chunk_id not in {c.chunk_id for c in clause_results}]
                    final_results = final_results[:plan.top_k_total]
        
        # STEP 6: PACKAGE OUTPUT
        # ====================================================================
        
        trace_steps.append("Building final results...")
        processing_time = time.time() - start_time
        
        # OPTIMIZATION P4-2: Record reranking timing
        reranking_time = time.time() - stage_start
        self.stats_manager.record_stage_timing('reranking', reranking_time)
        self.stats_manager.record_stage_timing('total', processing_time)
        
        # OPTIMIZATION: Reuse predicted categories from reranking (already computed)
        # Check if categories were already predicted in reranking coordinator
        if hasattr(self.reranking_coordinator, '_last_predicted_categories'):
            predicted_categories = self.reranking_coordinator._last_predicted_categories
        else:
            # Fallback: predict if not cached
            predicted_categories = self.category_predictor.predict_categories(
                normalized_query, 
                query_type=interpretation.query_type.value
            )
        
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
            },
            trace_steps=trace_steps
        )
        
        # Update stats
        self.stats_manager.update_stats(output)
        
        # CACHE THE RESULT before returning
        # OPTIMIZATION P2-5: Include mode in cache key
        mode = custom_plan.get('mode') if custom_plan else getattr(plan, 'mode', None)
        self.query_cache.set(normalized_query, output, force_filter, mode=mode)
        
        return output
    
    def retrieve_and_answer(
        self,
        query: str,
        mode: str = "qa",
        top_k: Optional[int] = None,
        validate_answer: bool = True
    ) -> tuple[RetrievalOutput, Answer, Dict]:
        """
        Complete pipeline: retrieve + build answer + validate
        
        Args:
            query: User query
            mode: Answer mode (qa, policy, framework, etc.)
            top_k: Override final result count
            validate_answer: Whether to validate the generated answer
            
        Returns:
            (RetrievalOutput, Answer, validation_metadata)
        """
        # Step 1: Retrieve results
        retrieval_output = self.retrieve(query, top_k=top_k)
        
        # Step 2: Convert RetrievalResult to dict format for answer builder
        results_for_builder = []
        for result in retrieval_output.results:
            results_for_builder.append({
                'content': result.content,
                'chunk_id': result.chunk_id,
                'doc_id': result.doc_id,
                'score': result.score,
                'vertical': result.vertical,
                'metadata': result.metadata,
                'url': result.metadata.get('url') if 'url' in result.metadata else None
            })
        
        # Step 3: Build answer
        answer = self.answer_builder.build_answer(
            query=query,
            results=results_for_builder,
            mode=mode
        )
        
        # Step 4: Validate answer (if enabled)
        validation_metadata = {}
        if validate_answer:
            # Convert Answer object to dict for validator
            answer_dict = {
                'summary': answer.summary,
                'sections': answer.sections,
                'citations': answer.citations,
                'confidence': answer.confidence,
                'metadata': answer.metadata
            }
            
            # Validate
            is_valid, issues = self.answer_validator.validate_answer(
                answer_dict, results_for_builder, query
            )
            
            # Get quality score
            quality_score = self.answer_validator.get_quality_score(
                answer_dict, results_for_builder, query
            )
            
            # Get suggestions
            suggestions = self.answer_validator.suggest_improvements(
                answer_dict, results_for_builder, query
            )
            
            # Update answer metadata with validation info
            answer.metadata.update({
                'validation': {
                    'is_valid': is_valid,
                    'issues': issues,
                    'quality_score': quality_score,
                    'suggestions': suggestions
                }
            })
            
            validation_metadata = {
                'is_valid': is_valid,
                'issues': issues,
                'quality_score': quality_score,
                'suggestions': suggestions
            }
            
            # Track validation scores for stats
            self.stats_manager.add_validation_score(quality_score)
            
            # Log validation issues if any
            if not is_valid:
                print(f"⚠️ Answer validation issues for query '{query}':")
                for issue in issues[:3]:  # Show top 3 issues
                    print(f"   - {issue}")
                if suggestions:
                    print(f"   Suggestions: {suggestions[0]}")
        
        return retrieval_output, answer, validation_metadata
    
    def run_diagnostic(self, query: str, test_type: str = "full") -> Dict[str, Any]:
        """
        Run diagnostic tests on a query
        
        Args:
            query: User query
            test_type: 'full' for master prompt, 'all' for all tests, or specific test name
            
        Returns:
            Diagnostic results
        """
        # Perform retrieval first
        retrieval_output = self.retrieve(query)
        results = retrieval_output.results
        
        if test_type == "full":
            return self.diagnostic_runner.run_full_diagnostic(query, results)
        elif test_type == "all":
            return self.diagnostic_runner.run_all_tests(query, results)
        elif test_type == "sanity":
            return self.diagnostic_runner.run_retrieval_sanity_test(query, results)
        elif test_type == "missing":
            return self.diagnostic_runner.run_missing_info_test(query, results)
        elif test_type == "structure":
            return self.diagnostic_runner.run_policy_structure_test(query, results)
        elif test_type == "reasoning":
            return self.diagnostic_runner.run_reasoning_test(query, results)
        elif test_type == "contradiction":
            return self.diagnostic_runner.run_contradiction_test(query, results)
        else:
            return {"error": f"Unknown test type: {test_type}"}
    
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
    
    def get_validation_stats(self) -> Dict:
        """Get validation performance statistics"""
        return self.stats_manager.get_validation_stats()
    
    def get_performance_stats(self) -> Dict:
        """Get per-stage performance statistics - OPTIMIZATION P4-2"""
        return {
            'stage_timings': self.stats_manager.get_stage_stats(),
            'overall': self.stats_manager.get_stats()
        }


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
