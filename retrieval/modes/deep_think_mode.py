# 360° reasoning across verticals

"""
Deep Think Mode
===============
Comprehensive 360° policy reasoning across all verticals.
Legal → GO → Judicial → Data → Schemes hierarchy.
"""

from typing import Dict, List
from ..query_processing.query_plan import QueryPlan
from ..retrieval_core.vertical_retriever import get_vertical_retriever
from ..retrieval_core.aggregator import get_result_aggregator
from ..retrieval_core.multi_vector_search import compute_mmr
from ..reranking.policy_reranker import get_policy_reranker
from ..embeddings.embedding_router import get_embedding_router
from ..config.vertical_map import get_vertical_priority


class DeepThinkMode:
    """Deep Think Mode implementation"""
    
    def __init__(self):
        """Initialize Deep Think mode components"""
        self.embedder = get_embedding_router()
        self.retriever = get_vertical_retriever()
        self.aggregator = get_result_aggregator()
        self.reranker = get_policy_reranker()
    
    def execute(self, plan: QueryPlan) -> Dict:
        """
        Execute Deep Think mode retrieval.
        
        Strategy:
        - Search ALL verticals
        - Use deep embeddings
        - Policy-aware reranking (legal-first)
        - Return top 20 results
        - Ensure vertical diversity
        
        Args:
            plan: Query plan
            
        Returns:
            Results dict with policy reasoning
        """
        # Embed query with deep model
        query_vector, _ = self.embedder.embed_for_mode(
            plan.enhanced_query,
            plan.mode
        )
        
        # Retrieve from ALL verticals
        vertical_results = self.retriever.retrieve_multi_vertical(
            verticals=plan.verticals,
            query_vector=query_vector,
            top_k_per_vertical=plan.top_k,
            filters=plan.filters
        )
        
        # Compute vertical weights based on policy hierarchy
        vertical_weights = self._compute_policy_weights(plan.verticals)
        
        # Aggregate with policy weights
        aggregated = self.aggregator.merge_and_rank(
            vertical_results,
            vertical_weights=vertical_weights,
            deduplicate=True
        )
        
        # Apply MMR for some diversity while maintaining relevance
        mmr_results = compute_mmr(
            aggregated,
            lambda_param=0.7,  # 70% relevance, 30% diversity
            top_k=plan.top_k
        )
        
        # Policy-aware reranking
        reranked = self.reranker.rerank(
            results=mmr_results,
            query=plan.normalized_query,
            filters=plan.filters,
            top_k=plan.rerank_top
        )
        
        # Build policy reasoning structure
        reasoning = self._build_policy_reasoning(reranked, vertical_results)
        
        return {
            "results": reranked,
            "vertical_results": vertical_results,
            "mode": "deep_think",
            "strategy": "policy_hierarchy",
            "reasoning": reasoning
        }
    
    def _compute_policy_weights(self, verticals: List[str]) -> Dict[str, float]:
        """
        Compute weights based on policy hierarchy.
        Legal > GO > Judicial > Data > Schemes
        
        Args:
            verticals: List of verticals
            
        Returns:
            Dict of weights
        """
        weights = {}
        for vertical in verticals:
            priority = get_vertical_priority(vertical)
            # Convert priority to weight (lower priority = higher weight)
            # Priority 1 → weight 1.0
            # Priority 2 → weight 0.9
            # Priority 3 → weight 0.8
            # Priority 4 → weight 0.7
            # Priority 5 → weight 0.6
            weights[vertical] = 1.1 - (priority * 0.1)
        
        return weights
    
    def _build_policy_reasoning(
        self,
        final_results: List[Dict],
        vertical_results: Dict[str, List[Dict]]
    ) -> Dict:
        """
        Build policy reasoning structure showing coverage.
        
        Args:
            final_results: Final reranked results
            vertical_results: Original vertical results
            
        Returns:
            Reasoning structure
        """
        # Count results by vertical in final output
        vertical_coverage = {}
        for result in final_results:
            vertical = result.get("vertical", "unknown")
            vertical_coverage[vertical] = vertical_coverage.get(vertical, 0) + 1
        
        # Build reasoning chain
        reasoning = {
            "constitutional_foundation": self._extract_by_vertical(
                final_results, "legal", max_items=3
            ),
            "statutory_framework": self._extract_by_vertical(
                final_results, "legal", max_items=3
            ),
            "administrative_orders": self._extract_by_vertical(
                final_results, "go", max_items=3
            ),
            "judicial_precedents": self._extract_by_vertical(
                final_results, "judicial", max_items=2
            ),
            "data_evidence": self._extract_by_vertical(
                final_results, "data", max_items=2
            ),
            "implementation_schemes": self._extract_by_vertical(
                final_results, "schemes", max_items=2
            ),
            "vertical_coverage": vertical_coverage,
            "total_sources": len(final_results)
        }
        
        return reasoning
    
    def _extract_by_vertical(
        self,
        results: List[Dict],
        vertical: str,
        max_items: int = 3
    ) -> List[Dict]:
        """Extract results from a specific vertical"""
        vertical_results = [
            {
                "text": r.get("payload", {}).get("text", "")[:200],
                "score": r.get("rerank_score", r.get("score", 0)),
                "source": r.get("payload", {}).get("source")
            }
            for r in results
            if r.get("vertical") == vertical
        ]
        return vertical_results[:max_items]


# Global instance
_deep_think_mode_instance = None


def get_deep_think_mode() -> DeepThinkMode:
    """Get global Deep Think mode instance"""
    global _deep_think_mode_instance
    if _deep_think_mode_instance is None:
        _deep_think_mode_instance = DeepThinkMode()
    return _deep_think_mode_instance