# Merges, dedupes, global ranks

"""
Aggregator
==========
Merges, dedupes, and globally ranks results from multiple verticals.
Clean, deterministic.
"""

from typing import List, Dict
from collections import defaultdict


class ResultAggregator:
    """Aggregates results from multiple verticals"""
    
    def aggregate(
        self,
        vertical_results: Dict[str, List[Dict]],
        vertical_weights: Dict[str, float] = None
    ) -> List[Dict]:
        """
        Aggregate results from multiple verticals.
        
        Args:
            vertical_results: Dict mapping vertical to results
            vertical_weights: Optional weights per vertical
            
        Returns:
            Merged and globally ranked results
        """
        if not vertical_results:
            return []
        
        # Default weights (equal)
        if vertical_weights is None:
            vertical_weights = {v: 1.0 for v in vertical_results.keys()}
        
        # Collect all results with adjusted scores
        all_results = []
        
        for vertical, results in vertical_results.items():
            weight = vertical_weights.get(vertical, 1.0)
            
            for result in results:
                # Adjust score by vertical weight
                adjusted_result = result.copy()
                adjusted_result["original_score"] = result["score"]
                adjusted_result["adjusted_score"] = result["score"] * weight
                adjusted_result["vertical_weight"] = weight
                
                all_results.append(adjusted_result)
        
        # Sort by adjusted score
        all_results.sort(key=lambda x: x["adjusted_score"], reverse=True)
        
        return all_results
    
    def deduplicate(
        self,
        results: List[Dict],
        similarity_threshold: float = 0.95
    ) -> List[Dict]:
        """
        Remove duplicate or near-duplicate results.
        
        Args:
            results: Search results
            similarity_threshold: Text similarity threshold for deduplication
            
        Returns:
            Deduplicated results
        """
        if not results:
            return []
        
        # Group by chunk_id first (exact duplicates)
        seen_ids = set()
        deduped = []
        
        for result in results:
            payload = result.get("payload", {})
            chunk_id = payload.get("chunk_id") or payload.get("id")
            
            if chunk_id and chunk_id in seen_ids:
                continue
            
            if chunk_id:
                seen_ids.add(chunk_id)
            
            deduped.append(result)
        
        # TODO: Could add fuzzy text deduplication here if needed
        # For now, exact ID deduplication is sufficient
        
        return deduped
    
    def merge_and_rank(
        self,
        vertical_results: Dict[str, List[Dict]],
        vertical_weights: Dict[str, float] = None,
        deduplicate: bool = True
    ) -> List[Dict]:
        """
        Complete aggregation pipeline.
        
        Args:
            vertical_results: Results per vertical
            vertical_weights: Weights per vertical
            deduplicate: Whether to deduplicate
            
        Returns:
            Final ranked results
        """
        # Aggregate
        merged = self.aggregate(vertical_results, vertical_weights)
        
        # Deduplicate if requested
        if deduplicate:
            merged = self.deduplicate(merged)
        
        return merged
    
    def get_top_k(
        self,
        results: List[Dict],
        k: int,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        Get top K results above minimum score.
        
        Args:
            results: Search results
            k: Number to return
            min_score: Minimum score threshold
            
        Returns:
            Top K results
        """
        # Filter by minimum score
        filtered = [r for r in results if r.get("adjusted_score", r["score"]) >= min_score]
        
        # Return top K
        return filtered[:k]
    
    def group_by_vertical(
        self,
        results: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Group results by vertical.
        
        Args:
            results: Search results
            
        Returns:
            Dict mapping vertical to results
        """
        grouped = defaultdict(list)
        
        for result in results:
            vertical = result.get("vertical", "unknown")
            grouped[vertical].append(result)
        
        return dict(grouped)
    
    def compute_vertical_coverage(
        self,
        results: List[Dict]
    ) -> Dict[str, int]:
        """
        Compute how many results came from each vertical.
        
        Args:
            results: Search results
            
        Returns:
            Dict mapping vertical to count
        """
        counts = defaultdict(int)
        
        for result in results:
            vertical = result.get("vertical", "unknown")
            counts[vertical] += 1
        
        return dict(counts)


# Global aggregator instance
_aggregator_instance = None


def get_result_aggregator() -> ResultAggregator:
    """Get global result aggregator instance"""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = ResultAggregator()
    return _aggregator_instance