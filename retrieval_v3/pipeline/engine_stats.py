# Engine Stats Manager

"""
Manages statistics tracking and caching for the retrieval engine
"""

import statistics
from typing import Dict, List

from .models import RetrievalOutput


class EngineStatsManager:
    """Manages statistics and caching for retrieval engine"""
    
    def __init__(self, enable_cache: bool = True, cache_max_size: int = 100):
        self.enable_cache = enable_cache
        self._cache_max_size = cache_max_size
        
        # Simple caches for speed (always initialize, even if disabled)
        self._embedding_cache = {}
        self._llm_cache = {}
        
        # Stats
        self.stats = {
            'total_queries': 0,
            'avg_processing_time': 0,
            'cache_hits': 0,
            'validation_scores': [],
            'recent_timeouts': 0,  # OPTIMIZATION P4-1: Circuit breaker tracking
        }
        
        # OPTIMIZATION P4-2: Per-stage latency tracking
        self.stage_timings = {
            'query_understanding': [],
            'routing': [],
            'retrieval': [],
            'aggregation': [],
            'reranking': [],
            'total': []
        }
    
    def update_stats(self, output: RetrievalOutput):
        """Update engine statistics"""
        self.stats['total_queries'] += 1
        
        # Update running average
        n = self.stats['total_queries']
        old_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = \
            (old_avg * (n - 1) + output.processing_time) / n
    
    def record_stage_timing(self, stage: str, duration: float):
        """Record timing for a specific stage - OPTIMIZATION P4-2"""
        if stage in self.stage_timings:
            self.stage_timings[stage].append(duration)
            # Keep only last 100 timings per stage to avoid memory bloat
            if len(self.stage_timings[stage]) > 100:
                self.stage_timings[stage] = self.stage_timings[stage][-100:]
    
    def get_stage_stats(self) -> Dict:
        """Get per-stage statistics - OPTIMIZATION P4-2"""
        stage_stats = {}
        for stage, timings in self.stage_timings.items():
            if timings:
                stage_stats[stage] = {
                    'count': len(timings),
                    'avg': statistics.mean(timings),
                    'min': min(timings),
                    'max': max(timings),
                    'p50': statistics.median(timings),
                    'p95': sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 20 else max(timings)
                }
            else:
                stage_stats[stage] = {'count': 0, 'avg': 0, 'min': 0, 'max': 0, 'p50': 0, 'p95': 0}
        return stage_stats
    
    def get_validation_stats(self) -> Dict:
        """Get validation performance statistics"""
        validation_scores = self.stats.get('validation_scores', [])
        
        if not validation_scores:
            return {
                'total_validated': 0,
                'avg_quality_score': 0.0,
                'quality_distribution': {}
            }
        
        avg_score = statistics.mean(validation_scores)
        
        # Quality distribution
        high_quality = len([s for s in validation_scores if s >= 0.8])
        medium_quality = len([s for s in validation_scores if 0.6 <= s < 0.8])
        low_quality = len([s for s in validation_scores if s < 0.6])
        
        return {
            'total_validated': len(validation_scores),
            'avg_quality_score': avg_score,
            'quality_distribution': {
                'high_quality': high_quality,
                'medium_quality': medium_quality, 
                'low_quality': low_quality
            },
            'latest_scores': validation_scores[-5:]  # Last 5 scores
        }
    
    def add_validation_score(self, score: float):
        """Add a validation score"""
        self.stats['validation_scores'].append(score)
    
    def get_cache(self) -> Dict:
        """Get cache dictionaries (returns references for sharing)"""
        return {
            'embedding_cache': self._embedding_cache,
            'llm_cache': self._llm_cache
        }
    
    def get_embedding_cache(self) -> Dict:
        """Get embedding cache reference"""
        return self._embedding_cache
    
    def get_llm_cache(self) -> Dict:
        """Get LLM cache reference"""
        return self._llm_cache
    
    def get_stats(self) -> Dict:
        """Get current stats"""
        return self.stats.copy()
