# Simple & fast

"""
QA Mode
=======
Simple and fast question-answering mode.
Optimized for speed and precision.
"""

from typing import Dict, List, Optional
from ..query_processing.query_plan import QueryPlan
from ..retrieval_core.vertical_retriever import get_vertical_retriever
from ..retrieval_core.aggregator import get_result_aggregator
from ..reranking.light_reranker import get_light_reranker
from ..embeddings.embedding_router import get_embedding_router


class QAMode:
    """QA Mode implementation"""
    
    def __init__(self):
        """Initialize QA mode components"""
        self.embedder = get_embedding_router()
        self.retriever = get_vertical_retriever()
        self.aggregator = get_result_aggregator()
        self.reranker = get_light_reranker()
    
    def execute(self, plan: QueryPlan) -> Dict:
        """
        Execute QA mode retrieval.
        
        Strategy:
        - Search only relevant verticals (1-2)
        - Use fast embeddings
        - Light reranking
        - Return top 5 results
        
        Args:
            plan: Query plan
            
        Returns:
            Results dict
        """
        # Embed query with fast model
        query_vector, _ = self.embedder.embed_for_mode(
            plan.enhanced_query,
            plan.mode
        )
        
        # Retrieve from verticals
        vertical_results = self.retriever.retrieve_multi_vertical(
            verticals=plan.verticals,
            query_vector=query_vector,
            top_k_per_vertical=plan.top_k,
            filters=plan.filters
        )
        
        # Quick aggregation (no heavy processing)
        aggregated = self.aggregator.merge_and_rank(
            vertical_results,
            vertical_weights={v: 1.0 for v in plan.verticals},  # Equal weights
            deduplicate=True
        )
        
        # Light reranking
        reranked = self.reranker.rerank(
            results=aggregated,
            query=plan.normalized_query,
            filters=plan.filters,
            top_k=plan.rerank_top
        )
        
        return {
            "results": reranked,
            "vertical_results": vertical_results,
            "mode": "qa",
            "strategy": "fast_precision"
        }


# Global instance
_qa_mode_instance = None


def get_qa_mode() -> QAMode:
    """Get global QA mode instance"""
    global _qa_mode_instance
    if _qa_mode_instance is None:
        _qa_mode_instance = QAMode()
    return _qa_mode_instance