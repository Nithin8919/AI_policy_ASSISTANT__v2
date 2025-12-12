# Reranking Coordinator

"""
Coordinates reranking operations: LLM, cross-encoder, diversity, relation-entity
"""

import logging
import concurrent.futures
from typing import List, Dict, Optional

from .models import RetrievalResult
from query_understanding.category_predictor import CategoryPredictor
from pipeline.diversity_reranker import DiversityReranker
from reranking.cross_encoder_reranker import CrossEncoderReranker
from routing.retrieval_plan import RetrievalPlan

logger = logging.getLogger(__name__)


class RerankingCoordinator:
    """Coordinates all reranking operations"""
    
    def __init__(
        self,
        category_predictor: CategoryPredictor,
        diversity_reranker: DiversityReranker,
        cross_encoder: Optional[CrossEncoderReranker] = None,
        relation_entity_processor = None,
        use_cross_encoder: bool = True,
        use_relation_entity: bool = True,
        gemini_api_key: Optional[str] = None,
        enable_cache: bool = True,
        llm_cache: Optional[Dict] = None,
        cache_max_size: int = 100,
        stats: Optional[Dict] = None
    ):
        self.category_predictor = category_predictor
        self.diversity_reranker = diversity_reranker
        self.cross_encoder = cross_encoder
        self.relation_entity_processor = relation_entity_processor
        self.use_cross_encoder = use_cross_encoder
        self.use_relation_entity = use_relation_entity
        self.gemini_api_key = gemini_api_key
        self.enable_cache = enable_cache
        self._llm_cache = llm_cache or {}
        self._cache_max_size = cache_max_size
        self.stats = stats or {}
    
    def rerank(
        self,
        query: str,
        normalized_query: str,
        results: List[RetrievalResult],
        interpretation,
        plan: RetrievalPlan,
        trace_steps: List[str],
        bm25_booster = None
    ) -> List[RetrievalResult]:
        """
        Coordinate complete reranking pipeline
        
        OPTIMIZATION P3-1: Query-specific reranking strategies
        - QA: Fast cross-encoder only (skip relation-entity)
        - Policy: Full pipeline
        - Legal: Already handled by clause indexer
        
        Returns:
            Reranked results
        """
        query_type = interpretation.query_type.value
        mode = getattr(plan, 'mode', 'qa')
        
        # OPTIMIZATION P3-1: Query-specific reranking strategies
        is_qa_mode = query_type == 'qa' or mode == 'qa'
        is_legal_query = 'legal' in normalized_query.lower() or any(
            keyword in normalized_query.lower() 
            for keyword in ['section', 'clause', 'article', 'rule', 'act']
        )
        
        # 5.1: Predict categories (cache for reuse in metadata)
        predicted_categories = self.category_predictor.predict_categories(
            normalized_query, 
            query_type=query_type
        )
        # Cache for reuse in retrieval_engine metadata generation
        self._last_predicted_categories = predicted_categories
        
        # OPTIMIZATION P1-4 & P3-1: Parallelize BM25 boost and relation-entity when both needed
        # OPTIMIZATION P3-1: Skip relation-entity for QA mode (fast path)
        needs_bm25_boost = bm25_booster is not None
        needs_relation_entity = (
            self.use_relation_entity and 
            self.relation_entity_processor and
            not is_qa_mode and  # OPTIMIZATION P3-1: Skip for QA
            not (interpretation.query_type.value == 'qa' and interpretation.confidence > 0.8 and len(normalized_query.split()) < 8)
        )
        
        # Check result quality for early skip
        # CRITICAL: Use raw_score from metadata (not normalized score) for consistency with weak retrieval detection
        top_scores = [r.metadata.get('raw_score', r.score) for r in results[:3]] if results else []
        has_high_quality_results = (
            len(top_scores) >= 3 and 
            max(top_scores) > 0.7 and
            sum(top_scores) / len(top_scores) > 0.65
        )
        
        # OPTIMIZATION P1-1 & P4-1: Skip relation-entity for simple queries or high-quality results
        # OPTIMIZATION P4-1: Circuit breaker - check if recent operations timed out
        if has_high_quality_results:
            needs_relation_entity = False
            logger.info(f"⚡ Skipping relation-entity processing (high-quality results already)")
        
        # OPTIMIZATION P4-1: Circuit breaker - check system load
        # Skip expensive operations if we've had recent timeouts
        if needs_relation_entity and hasattr(self, 'stats') and self.stats:
            # Check if we've had recent failures (simple circuit breaker)
            recent_failures = self.stats.get('recent_timeouts', 0)
            if recent_failures > 3:  # If 3+ recent timeouts, skip expensive operations
                needs_relation_entity = False
                logger.warning(f"⚠️ Circuit breaker: Skipping relation-entity (recent_timeouts={recent_failures})")
        
        # Run BM25 boost and relation-entity in parallel if both needed
        if needs_bm25_boost and needs_relation_entity:
            # Parallel execution
            def run_bm25_boost():
                return bm25_booster.boost_results(
                    normalized_query,
                    results,
                    boost_threshold=0.0
                )
            
            def run_relation_entity():
                timeout_limit = 8.0 if interpretation.needs_deep_mode else 5.0
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.relation_entity_processor.process_complete,
                        query=normalized_query,
                        results=results,  # Use original results for relation-entity
                        phases_enabled={
                            'relation_scoring': True, 
                            'entity_matching': True, 
                            'entity_expansion': True,
                            'bidirectional_search': False
                        }
                    )
                    try:
                        result = future.result(timeout=timeout_limit)
                        # Reset failure counter on success
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = max(0, self.stats.get('recent_timeouts', 0) - 1)
                        return result
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"⏱️ Relation-entity timeout ({timeout_limit}s), using original results")
                        # OPTIMIZATION P4-1: Track timeout for circuit breaker
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = self.stats.get('recent_timeouts', 0) + 1
                        return results
                    except Exception as e:
                        logger.error(f"❌ Relation-entity processing failed: {e}, using original results")
                        # Track failure for circuit breaker
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = self.stats.get('recent_timeouts', 0) + 1
                        return results
            
            # Execute in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_bm25 = executor.submit(run_bm25_boost)
                future_relation = executor.submit(run_relation_entity)
                
                try:
                    bm25_boosted = future_bm25.result(timeout=3.0)
                    relation_enhanced = future_relation.result(timeout=8.0)
                    logger.info(f"✅ Parallel BM25 boost + relation-entity completed")
                except concurrent.futures.TimeoutError:
                    logger.warning("⏱️ Parallel reranking timeout, using partial results")
                    bm25_boosted = future_bm25.result() if future_bm25.done() else results
                    relation_enhanced = future_relation.result() if future_relation.done() else bm25_boosted
        else:
            # Sequential execution (one or both skipped)
            if needs_bm25_boost:
                bm25_boosted = bm25_booster.boost_results(
                    normalized_query,
                    results,
                    boost_threshold=0.0
                )
            else:
                bm25_boosted = results
            
            # 5.3: RELATION-ENTITY PROCESSING (if needed)
            if needs_relation_entity:
                trace_steps.append("Checking superseded policies and relations...")
                print(f"🔗 Starting relation-entity processing...")
                
                # Add timeout protection (8s for deep think, 5s for regular)
                timeout_limit = 8.0 if interpretation.needs_deep_mode else 5.0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.relation_entity_processor.process_complete,
                        query=normalized_query,
                        results=bm25_boosted,
                        phases_enabled={
                            'relation_scoring': True, 
                            'entity_matching': True, 
                            'entity_expansion': True,
                            'bidirectional_search': False  # DISABLED - was taking 38.78s and finding 0 results
                        }
                    )
                    
                    try:
                        relation_enhanced = future.result(timeout=timeout_limit)
                        logger.info(f"✅ Relation-entity processing completed within {timeout_limit}s")
                        # Reset failure counter on success
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = max(0, self.stats.get('recent_timeouts', 0) - 1)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"⏱️ Relation-entity timeout ({timeout_limit}s), using BM25 results")
                        # OPTIMIZATION P4-1: Track timeout for circuit breaker
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = self.stats.get('recent_timeouts', 0) + 1
                        relation_enhanced = bm25_boosted
                    except Exception as e:
                        logger.error(f"❌ Relation-entity processing failed: {e}, using BM25 results")
                        # Track failure for circuit breaker
                        if hasattr(self, 'stats') and self.stats:
                            self.stats['recent_timeouts'] = self.stats.get('recent_timeouts', 0) + 1
                        relation_enhanced = bm25_boosted
            else:
                relation_enhanced = bm25_boosted
            
        # OPTIMIZATION P2-2: Parallelize cross-encoder and diversity preparation
        # 5.4: Cross-Encoder Reranking (High Precision)
        # OPTIMIZATION P3-1: QA mode uses fast cross-encoder, Policy uses full pipeline
        if self.use_cross_encoder and self.cross_encoder:
            trace_steps.append("Applying rerankers and diversity checks...")
            # Convert to dicts for reranker
            res_dicts = [{'content': r.content, 'score': r.score, 'obj': r} for r in relation_enhanced]
            # Pass mode to cross-encoder for adaptive candidate selection
            reranked_dicts = self.cross_encoder.rerank(
                normalized_query, 
                res_dicts, 
                top_k=plan.rerank_top_k,
                mode=mode  # Use mode from plan
            )
            
            # Update scores in objects
            reranked = []
            for rd in reranked_dicts:
                r_obj = rd['obj']
                r_obj.score = rd['score']
                reranked.append(r_obj)
        else:
            reranked = sorted(relation_enhanced, key=lambda x: x.score, reverse=True)[:plan.rerank_top_k]
            
        # 5.5: Diversity Reranking (MMR)
        # OPTIMIZATION P3-3: Only run diversity if results are too similar
        # Check similarity before running expensive diversity reranking
        should_run_diversity = True
        if len(reranked) > 1 and plan.diversity_weight > 0:
            # Quick similarity check: compare top-3 results
            top_3 = reranked[:3]
            if len(top_3) >= 2:
                # Simple heuristic: check if top results are from same vertical
                verticals = [r.vertical for r in top_3]
                unique_verticals = len(set(verticals))
                # If all top-3 are from same vertical, diversity is needed
                # If already diverse (2+ verticals), skip diversity reranking
                if unique_verticals >= 2:
                    should_run_diversity = False
                    logger.info(f"⚡ Skipping diversity reranking (already diverse: {unique_verticals} verticals)")
        
        if should_run_diversity:
            final_results = self.diversity_reranker.rerank_with_diversity(
                normalized_query,
                reranked,
                predicted_categories,
                top_k=plan.top_k_total,
                diversity_weight=plan.diversity_weight
            )
        else:
            # Just take top-k without diversity reranking
            final_results = reranked[:plan.top_k_total]
        
        return final_results
