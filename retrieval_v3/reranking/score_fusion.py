# Score Fusion - combine vector, BM25, LLM, internet relevance

"""
Score Fusion - Combine multiple scoring signals
"""

from typing import List, Dict


class ScoreFusion:
    """Fuse multiple scores into final ranking"""
    
    def __init__(
        self,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.2,
        llm_weight: float = 0.2,
        recency_weight: float = 0.1
    ):
        """
        Args:
            vector_weight: Vector similarity weight
            bm25_weight: BM25 keyword weight
            llm_weight: LLM reranking weight
            recency_weight: Recency signal weight
        """
        self.weights = {
            'vector': vector_weight,
            'bm25': bm25_weight,
            'llm': llm_weight,
            'recency': recency_weight
        }
        
        # Normalize
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
    
    def fuse_scores(self, results: List[Dict]) -> List[Dict]:
        """
        Fuse all scores
        
        Args:
            results: Results with multiple scores
            
        Returns:
            Results with final_score
        """
        for result in results:
            final = 0.0
            
            final += self.weights['vector'] * result.get('vector_score', 0)
            final += self.weights['bm25'] * result.get('bm25_score', 0)
            final += self.weights['llm'] * result.get('llm_score', 0)
            final += self.weights['recency'] * result.get('recency_score', 0)
            
            result['final_score'] = final
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return results
