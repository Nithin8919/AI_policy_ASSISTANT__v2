# Result Processor

"""
Processes retrieval results: deduplication, score normalization, fusion
"""

import statistics
from typing import List

from .models import RetrievalResult


class ResultProcessor:
    """Processes and transforms retrieval results"""
    
    @staticmethod
    def deduplicate_results(results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Deduplicate results by chunk_id, keeping highest score"""
        seen = {}
        
        for result in results:
            if result.chunk_id not in seen:
                seen[result.chunk_id] = result
            else:
                # Keep higher score
                if result.score > seen[result.chunk_id].score:
                    seen[result.chunk_id] = result
        
        # Return sorted by score
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)
    
    @staticmethod
    def normalize_scores(
        results: List[RetrievalResult], 
        method: str = 'min-max'
    ) -> List[RetrievalResult]:
        """
        Normalize scores to 0-1 range for better multi-hop/multi-rewrite fusion
        PRESERVES raw scores in metadata for weak-retrieval detection
        
        OPTIMIZATION P3-2: Use z-score only when score distribution is wide
        Prefer min-max for most cases (simpler, preserves relative ordering better)
        
        Args:
            results: List of retrieval results
            method: 'min-max' (default, faster) or 'z-score' (only when needed)
            
        Returns:
            Results with normalized scores (raw_score preserved in metadata)
        """
        if not results:
            return results
        
        scores = [r.score for r in results]
        
        # OPTIMIZATION P3-2: Auto-select method based on score distribution
        if method == 'auto':
            # Use z-score only if score range is very wide (suggests different scales)
            score_range = max(scores) - min(scores)
            score_mean = statistics.mean(scores)
            # If range is > 2x mean, use z-score; otherwise min-max
            if score_range > 2 * score_mean and len(scores) > 5:
                method = 'z-score'
                logger.debug(f"Using z-score normalization (wide range: {score_range:.2f})")
            else:
                method = 'min-max'
                logger.debug(f"Using min-max normalization (range: {score_range:.2f})")
        
        if method == 'min-max':
            min_score = min(scores)
            max_score = max(scores)
            
            # Handle edge case where all scores are the same
            if max_score == min_score:
                for r in results:
                    # Preserve raw score before normalization
                    if 'raw_score' not in r.metadata:
                        r.metadata['raw_score'] = r.score
                    r.score = 1.0
                return results
            
            # Min-max normalization to [0, 1]
            # CRITICAL: Preserve raw score in metadata for weak-retrieval detection
            for r in results:
                if 'raw_score' not in r.metadata:
                    r.metadata['raw_score'] = r.score
                r.score = (r.score - min_score) / (max_score - min_score)
        
        elif method == 'z-score':
            mean_score = statistics.mean(scores)
            stdev_score = statistics.stdev(scores) if len(scores) > 1 else 1.0
            
            if stdev_score == 0:
                stdev_score = 1.0
            
            # Z-score normalization, then shift to [0, 1]
            # CRITICAL: Preserve raw score in metadata for weak-retrieval detection
            for r in results:
                if 'raw_score' not in r.metadata:
                    r.metadata['raw_score'] = r.score
                z_score = (r.score - mean_score) / stdev_score
                r.score = max(0.0, min(1.0, (z_score + 3) / 6))  # Assuming 3-sigma range
        
        return results
    
    @staticmethod
    def reciprocal_rank_fusion(
        result_lists: List[List[RetrievalResult]],
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion - combine multiple ranked lists
        
        RRF works better than score averaging because:
        - Results appearing in multiple sources get boosted (strong consensus signal)
        - Handles different score scales naturally 
        - Position-based relevance (rank matters more than raw score)
        
        Formula: RRF_score(chunk) = Σ 1/(k + rank_in_list_i) for all lists containing chunk
        
        Args:
            result_lists: List of ranked result lists (from different sources)
            k: RRF parameter (typically 60, controls rank smoothing)
            
        Returns:
            Fused results sorted by RRF score
        """
        if not result_lists:
            return []
        
        chunk_scores = {}
        chunk_to_result = {}
        
        # Calculate RRF scores
        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                chunk_id = result.chunk_id
                
                # Add RRF score contribution
                rrf_contribution = 1.0 / (k + rank)
                chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf_contribution
                
                # Store the result object (keep highest-scored version)
                if chunk_id not in chunk_to_result or result.score > chunk_to_result[chunk_id].score:
                    chunk_to_result[chunk_id] = result
        
        # Sort by RRF score (descending)
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build final result list with RRF scores
        fused_results = []
        for chunk_id, rrf_score in sorted_chunks:
            result = chunk_to_result[chunk_id]
            # Update metadata with RRF info
            result.metadata['rrf_score'] = rrf_score
            result.metadata['fusion_method'] = 'rrf'
            result.metadata['original_score'] = result.score
            # Update main score to RRF score for consistency
            result.score = rrf_score
            fused_results.append(result)
        
        return fused_results
