# Wide-angle global + domain insights

"""
Brainstorm Mode
===============
Creative idea generation with global perspectives and diversity.
Focuses on schemes, data, and international models.
"""

from typing import Dict, List
from ..query_processing.query_plan import QueryPlan
from ..retrieval_core.vertical_retriever import get_vertical_retriever
from ..retrieval_core.aggregator import get_result_aggregator
from ..retrieval_core.multi_vector_search import compute_mmr
from ..reranking.brainstorm_reranker import get_brainstorm_reranker
from ..embeddings.embedding_router import get_embedding_router


class BrainstormMode:
    """Brainstorm Mode implementation"""
    
    def __init__(self):
        """Initialize Brainstorm mode components"""
        self.embedder = get_embedding_router()
        self.retriever = get_vertical_retriever()
        self.aggregator = get_result_aggregator()
        self.reranker = get_brainstorm_reranker()
    
    def execute(self, plan: QueryPlan) -> Dict:
        """
        Execute Brainstorm mode retrieval.
        
        Strategy:
        - Focus on schemes, data (light on legal/judicial)
        - Use deep embeddings for semantic matching
        - Diversity-focused reranking
        - Return 15 diverse results
        - Boost global/innovative content
        
        Args:
            plan: Query plan
            
        Returns:
            Results dict with diverse ideas
        """
        # Embed query with deep model for better semantic matching
        query_vector, _ = self.embedder.embed_for_mode(
            plan.enhanced_query,
            plan.mode
        )
        
        # Define vertical search strategy for brainstorming
        # Heavy on schemes and data, light on legal/judicial
        vertical_search_config = self._get_search_config(plan.verticals)
        
        # Retrieve with different top_k per vertical
        vertical_results = {}
        for vertical, config in vertical_search_config.items():
            results = self.retriever.retrieve(
                vertical=vertical,
                query_vector=query_vector,
                top_k=config["top_k"],
                filters=plan.filters
            )
            vertical_results[vertical] = results
        
        # Aggregate with vertical weights favoring schemes/data
        vertical_weights = self._compute_brainstorm_weights(vertical_search_config.keys())
        
        aggregated = self.aggregator.merge_and_rank(
            vertical_results,
            vertical_weights=vertical_weights,
            deduplicate=True
        )
        
        # Apply MMR with high diversity
        mmr_results = compute_mmr(
            aggregated,
            lambda_param=0.5,  # 50% relevance, 50% diversity
            top_k=plan.top_k * 2  # Get more for diversity selection
        )
        
        # Diversity-focused reranking
        reranked = self.reranker.rerank(
            results=mmr_results,
            query=plan.normalized_query,
            top_k=plan.rerank_top
        )
        
        # Build idea structure
        idea_structure = self._build_idea_structure(reranked, vertical_results)
        
        return {
            "results": reranked,
            "vertical_results": vertical_results,
            "mode": "brainstorm",
            "strategy": "diversity_innovation",
            "ideas": idea_structure
        }
    
    def _get_search_config(self, planned_verticals: List[str]) -> Dict[str, Dict]:
        """
        Get search configuration for brainstorming.
        
        Args:
            planned_verticals: Verticals from plan
            
        Returns:
            Dict mapping vertical to search config
        """
        # Default config: focus on schemes and data
        default_config = {
            "schemes": {"top_k": 15, "boost": 1.2},
            "data": {"top_k": 15, "boost": 1.1},
            "go": {"top_k": 8, "boost": 0.9},
            "legal": {"top_k": 5, "boost": 0.7},
            "judicial": {"top_k": 5, "boost": 0.7}
        }
        
        # Filter to only planned verticals
        config = {
            v: default_config[v]
            for v in planned_verticals
            if v in default_config
        }
        
        return config
    
    def _compute_brainstorm_weights(self, verticals: List[str]) -> Dict[str, float]:
        """
        Compute weights for brainstorming.
        Boost schemes and data, reduce legal/judicial.
        
        Args:
            verticals: List of verticals
            
        Returns:
            Dict of weights
        """
        weights = {
            "schemes": 1.2,
            "data": 1.1,
            "go": 0.9,
            "legal": 0.7,
            "judicial": 0.7
        }
        
        return {v: weights.get(v, 1.0) for v in verticals}
    
    def _build_idea_structure(
        self,
        final_results: List[Dict],
        vertical_results: Dict[str, List[Dict]]
    ) -> Dict:
        """
        Build idea structure categorizing results.
        
        Args:
            final_results: Final reranked results
            vertical_results: Original vertical results
            
        Returns:
            Idea structure
        """
        # Categorize ideas
        global_models = []
        indian_context = []
        data_insights = []
        
        for result in final_results:
            payload = result.get("payload", {})
            text = (payload.get("text", "") or payload.get("content", "")).lower()
            vertical = result.get("vertical", "")
            
            item = {
                "text": payload.get("text", "")[:300],
                "score": result.get("innovation_score", result.get("score", 0)),
                "source": payload.get("source"),
                "vertical": vertical
            }
            
            # Categorize based on content
            if vertical == "schemes" or any(
                term in text for term in ["finland", "singapore", "international", "global"]
            ):
                global_models.append(item)
            elif vertical == "data":
                data_insights.append(item)
            else:
                indian_context.append(item)
        
        return {
            "global_best_practices": global_models[:5],
            "indian_context": indian_context[:5],
            "data_insights": data_insights[:3],
            "diversity_score": len(set(r.get("vertical") for r in final_results)),
            "total_ideas": len(final_results)
        }


# Global instance
_brainstorm_mode_instance = None


def get_brainstorm_mode() -> BrainstormMode:
    """Get global Brainstorm mode instance"""
    global _brainstorm_mode_instance
    if _brainstorm_mode_instance is None:
        _brainstorm_mode_instance = BrainstormMode()
    return _brainstorm_mode_instance