# Aggregator - merges chunks from all sources

"""
Result Aggregator - Merge and deduplicate results
"""

from typing import List, Dict, Set
from collections import defaultdict


class ResultAggregator:
    """Aggregate results from multiple sources"""
    
    def __init__(self):
        """Initialize aggregator"""
        pass
    
    def aggregate(
        self,
        results_list: List[List[Dict]],
        deduplicate: bool = True,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Aggregate results from multiple retrievals
        
        Args:
            results_list: List of result lists
            deduplicate: Remove duplicates by chunk_id
            max_results: Maximum final results
            
        Returns:
            Merged and sorted results
        """
        all_results = []
        
        # Flatten
        for results in results_list:
            all_results.extend(results)
        
        # Deduplicate if requested
        if deduplicate:
            all_results = self.deduplicate_by_id(all_results)
        
        # Sort by score
        all_results.sort(
            key=lambda x: x.get('score', x.get('final_score', 0)),
            reverse=True
        )
        
        return all_results[:max_results]
    
    def deduplicate_by_id(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicates, keeping highest score"""
        seen = {}
        
        for result in results:
            chunk_id = result.get('chunk_id', result.get('id'))
            
            if chunk_id not in seen:
                seen[chunk_id] = result
            else:
                # Keep higher score
                old_score = seen[chunk_id].get('score', 0)
                new_score = result.get('score', 0)
                
                if new_score > old_score:
                    seen[chunk_id] = result
        
        return list(seen.values())
    
    def merge_by_vertical(
        self,
        results: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Group results by vertical"""
        by_vertical = defaultdict(list)
        
        for result in results:
            vertical = result.get('vertical', 'unknown')
            by_vertical[vertical].append(result)
        
        return dict(by_vertical)


if __name__ == "__main__":
    print("Result Aggregator")











