# Diversity Reranker - ensure category coverage

"""
Diversity Reranker - Ensure category coverage
"""

from typing import List, Dict
from collections import defaultdict


class DiversityReranker:
    """Ensure diverse category coverage"""
    
    def __init__(self):
        """Initialize reranker"""
        pass
    
    def rerank(
        self,
        results: List[Dict],
        diversity_weight: float = 0.3,
        top_k: int = 20
    ) -> List[Dict]:
        """
        MMR-style diversity reranking
        
        Args:
            results: Input results
            diversity_weight: Balance relevance vs diversity
            top_k: Final count
            
        Returns:
            Diversified results
        """
        selected = []
        remaining = results.copy()
        category_counts = defaultdict(int)
        
        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -1
            
            for i, result in enumerate(remaining):
                # Relevance
                rel_score = result.get('score', 0)
                
                # Diversity penalty
                categories = result.get('categories', ['unknown'])
                cat = categories[0] if categories else 'unknown'
                div_penalty = category_counts[cat] * diversity_weight
                
                combined = rel_score - div_penalty
                
                if combined > best_score:
                    best_score = combined
                    best_idx = i
            
            # Select
            selected_result = remaining.pop(best_idx)
            selected.append(selected_result)
            
            # Update counts
            cats = selected_result.get('categories', ['unknown'])
            for cat in cats:
                category_counts[cat] += 1
        
        return selected





