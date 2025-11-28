# One import to run whole pipeline

"""
Main Router
===========
Single entry point for the entire retrieval system.
Clean, deterministic, battle-tested.

Usage:
    from retrieval import RetrievalRouter
    
    router = RetrievalRouter()
    response = router.query("What is Section 12?")
"""

import time
from typing import Dict, List, Optional

from .config.mode_config import QueryMode
from .config.vertical_map import get_vertical_priority
from .query_processing.query_plan import get_query_planner
from .embeddings.embedding_router import get_embedding_router
from .retrieval_core.vertical_retriever import get_vertical_retriever
from .retrieval_core.aggregator import get_result_aggregator
from .retrieval_core.multi_vector_search import compute_mmr
from .reranking.light_reranker import get_light_reranker
from .reranking.policy_reranker import get_policy_reranker
from .reranking.brainstorm_reranker import get_brainstorm_reranker


class RetrievalRouter:
    """
    Main retrieval router.
    One import, full pipeline.
    """
    
    def __init__(self, enable_hybrid_search: Optional[bool] = None):
        """
        Initialize router (components loaded lazily)
        
        Args:
            enable_hybrid_search: Whether to enable hybrid (vector + BM25) search
                                 If None, uses settings from config
        """
        self.planner = get_query_planner()
        self.embedder = get_embedding_router()
        self.retriever = get_vertical_retriever()
        self.aggregator = get_result_aggregator()
        
        # Use setting from config if not explicitly provided
        if enable_hybrid_search is None:
            from .config.settings import FEATURE_FLAGS
            self.enable_hybrid_search = FEATURE_FLAGS.get("use_hybrid_search", True)
        else:
            self.enable_hybrid_search = enable_hybrid_search
        
        # Rerankers
        self.light_reranker = get_light_reranker()
        self.policy_reranker = get_policy_reranker()
        self.brainstorm_reranker = get_brainstorm_reranker()
    
    def query(
        self,
        query: str,
        mode: Optional[str] = None,
        verticals: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> Dict:
        """
        Execute full retrieval pipeline.
        
        Args:
            query: User query
            mode: Optional explicit mode ("qa", "deep_think", "brainstorm")
            verticals: Optional explicit verticals to search
            top_k: Optional override for number of results
            
        Returns:
            Complete response dict with results and metadata
        """
        start_time = time.time()
        
        try:
            # 1. Build query plan (V2 uses plan method)
            plan = self.planner.plan(
                query,
                mode_override=mode
            )
            
            # Override top_k if provided
            if top_k:
                plan.rerank_top = top_k
            
            # 2. Embed query
            query_vector, embedding_model = self.embedder.embed_for_mode(
                plan.enhanced_query,
                plan.mode
            )
            
            # 3. Retrieve from verticals
            vertical_results = self.retriever.retrieve_multi_vertical(
                verticals=plan.verticals,
                query_vector=query_vector,
                top_k_per_vertical=plan.top_k,
                filters=plan.filters,
                original_query=query,
                use_hybrid_search=self.enable_hybrid_search
            )
            
            # 4. Aggregate results
            vertical_weights = self._compute_vertical_weights(plan.mode, plan.verticals)
            aggregated = self.aggregator.merge_and_rank(
                vertical_results,
                vertical_weights=vertical_weights,
                deduplicate=True
            )
            
            # 5. Apply MMR if configured
            if plan.mode == QueryMode.BRAINSTORM:
                aggregated = compute_mmr(
                    aggregated,
                    lambda_param=0.5,  # More diversity for brainstorming
                    top_k=plan.top_k
                )
            
            # 6. Rerank
            reranked = self._rerank(
                aggregated,
                plan.enhanced_query,
                plan.reranker,
                plan.filters,
                plan.rerank_top
            )
            
            # 7. Format results
            formatted_results = self._format_results(reranked)
            
            # 8. Build response
            response = {
                "success": True,
                "query": query,
                "mode": plan.mode.value,
                "mode_confidence": plan.mode_confidence,
                "verticals_searched": plan.verticals,
                "vertical_coverage": self.aggregator.compute_vertical_coverage(reranked),
                "results_count": len(reranked),
                "results": formatted_results,
                "plan": plan.to_dict(),
                "processing_time": time.time() - start_time
            }
            
            return response
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "processing_time": time.time() - start_time
            }
    
    def _compute_vertical_weights(
        self,
        mode: QueryMode,
        verticals: List[str]
    ) -> Dict[str, float]:
        """
        Compute weights for each vertical based on mode.
        
        Args:
            mode: Query mode
            verticals: Verticals being searched
            
        Returns:
            Dict mapping vertical to weight
        """
        if mode == QueryMode.DEEP_THINK:
            # Legal gets highest weight in deep think
            weights = {}
            for v in verticals:
                priority = get_vertical_priority(v)
                # Invert priority (lower number = higher weight)
                weights[v] = 1.0 / priority
            return weights
        
        elif mode == QueryMode.BRAINSTORM:
            # Equal weights, but boost schemes/data
            weights = {v: 1.0 for v in verticals}
            if "schemes" in weights:
                weights["schemes"] = 1.2
            if "data" in weights:
                weights["data"] = 1.1
            return weights
        
        else:
            # QA mode: equal weights
            return {v: 1.0 for v in verticals}
    
    def _rerank(
        self,
        results: List[Dict],
        query: str,
        reranker_name: str,
        filters: Dict,
        top_k: int
    ) -> List[Dict]:
        """Select and apply appropriate reranker"""
        if not results:
            return []
        
        if reranker_name == "light":
            return self.light_reranker.rerank(results, query, filters, top_k)
        
        elif reranker_name == "policy":
            return self.policy_reranker.rerank(results, query, filters, top_k)
        
        elif reranker_name == "brainstorm":
            return self.brainstorm_reranker.rerank(results, query, top_k)
        
        else:
            # Default to light
            return self.light_reranker.rerank(results, query, filters, top_k)
    
    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """
        Format results for frontend consumption.
        
        Args:
            results: Raw retrieval results
            
        Returns:
            Formatted results
        """
        formatted = []
        
        for idx, result in enumerate(results):
            payload = result.get("payload", {})
            
            formatted_result = {
                "rank": idx + 1,
                "chunk_id": payload.get("chunk_id"),
                "text": payload.get("text") or payload.get("content"),
                "vertical": result.get("vertical"),
                "score": result.get("rerank_score", result.get("score")),
                "metadata": {
                    "source": payload.get("source"),
                    "doc_type": payload.get("doc_type"),
                    "year": payload.get("year"),
                    "section": payload.get("section_number"),
                    "go_number": payload.get("go_number"),
                    "department": payload.get("department")
                }
            }
            
            # Remove None values
            formatted_result["metadata"] = {
                k: v for k, v in formatted_result["metadata"].items()
                if v is not None
            }
            
            formatted.append(formatted_result)
        
        return formatted


# Convenience function
def query(
    query_text: str,
    mode: Optional[str] = None,
    verticals: Optional[List[str]] = None,
    top_k: Optional[int] = None
) -> Dict:
    """
    Convenience function for direct queries.
    
    Args:
        query_text: User query
        mode: Optional mode override
        verticals: Optional verticals override
        top_k: Optional top_k override
        
    Returns:
        Response dict
    """
    router = RetrievalRouter()
    return router.query(query_text, mode, verticals, top_k)