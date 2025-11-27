"""
Context Fusion
==============
Merge results from multiple sources intelligently.
No duplication, proper prioritization.
"""

import logging
from typing import List, Dict, Tuple

from .config import get_orchestrator_config

logger = logging.getLogger(__name__)


class ContextFusion:
    """
    Merge contexts from multiple sources.
    Priority: Local > Internet > Theory
    """
    
    def __init__(self):
        self.config = get_orchestrator_config()
    
    def merge(
        self,
        local_results: List[Dict],
        internet_results: List[Dict] = None,
        theory_results: List[Dict] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Merge results from all sources.
        
        Args:
            local_results: Results from local RAG
            internet_results: Results from internet
            theory_results: Results from theory corpus
            
        Returns:
            (merged_results, metadata)
        """
        
        merged = []
        metadata = {
            "local_count": 0,
            "internet_count": 0,
            "theory_count": 0,
            "total_count": 0,
            "sources": []
        }
        
        # 1. Add local results (HIGHEST PRIORITY)
        if local_results:
            for result in local_results:
                result["source_type"] = "local"
                result["priority"] = 1.0
                merged.append(result)
            
            metadata["local_count"] = len(local_results)
            metadata["sources"].append("local")
            logger.info(f"Added {len(local_results)} local results")
        
        # 2. Add internet results
        if internet_results:
            for result in internet_results:
                result["source_type"] = "internet"
                result["priority"] = self.config.internet_weight
                merged.append(result)
            
            metadata["internet_count"] = len(internet_results)
            metadata["sources"].append("internet")
            logger.info(f"Added {len(internet_results)} internet results")
        
        # 3. Add theory results
        if theory_results:
            for result in theory_results:
                result["source_type"] = "theory"
                result["priority"] = self.config.theory_weight
                merged.append(result)
            
            metadata["theory_count"] = len(theory_results)
            metadata["sources"].append("theory")
            logger.info(f"Added {len(theory_results)} theory results")
        
        metadata["total_count"] = len(merged)
        
        # 4. Sort by priority (local first, then internet, then theory)
        merged.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return merged, metadata
    
    def format_for_llm(
        self,
        local_results: List[Dict],
        internet_results: List[Dict] = None,
        theory_results: List[Dict] = None
    ) -> Dict:
        """
        Format results for LLM consumption.
        Separate contexts clearly.
        
        Args:
            local_results: Local RAG results
            internet_results: Internet results
            theory_results: Theory results
            
        Returns:
            Structured context dict
        """
        
        return {
            "local": self._format_local(local_results),
            "internet": self._format_internet(internet_results) if internet_results else None,
            "theory": self._format_theory(theory_results) if theory_results else None
        }
    
    def _format_local(self, results: List[Dict]) -> List[Dict]:
        """Format local results"""
        
        formatted = []
        
        for i, result in enumerate(results, 1):
            formatted.append({
                "index": i,
                "text": result.get("text", ""),
                "source": result.get("metadata", {}).get("document_name", "Unknown"),
                "vertical": result.get("metadata", {}).get("vertical", "policy"),
                "score": result.get("score", 0.0)
            })
        
        return formatted
    
    def _format_internet(self, results: List[Dict]) -> List[Dict]:
        """Format internet results"""
        
        if not results:
            return []
        
        formatted = []
        start_idx = 101  # Internet sources start at [101]
        
        for i, result in enumerate(results, start_idx):
            formatted.append({
                "index": i,
                "text": result.get("content", ""),
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "domain": result.get("domain", ""),
                "snippet": result.get("snippet", "")
            })
        
        return formatted
    
    def _format_theory(self, results: List[Dict]) -> List[Dict]:
        """Format theory results"""
        
        if not results:
            return []
        
        formatted = []
        start_idx = 201  # Theory sources start at [201]
        
        for i, result in enumerate(results, start_idx):
            formatted.append({
                "index": i,
                "text": result.get("text", ""),
                "title": result.get("metadata", {}).get("title", "Theory"),
                "author": result.get("metadata", {}).get("author", ""),
                "score": result.get("score", 0.0)
            })
        
        return formatted


# Singleton
_fusion = None

def get_context_fusion() -> ContextFusion:
    """Get global context fusion instance"""
    global _fusion
    if _fusion is None:
        _fusion = ContextFusion()
    return _fusion