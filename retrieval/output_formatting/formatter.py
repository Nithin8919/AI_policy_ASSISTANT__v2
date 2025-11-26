# Standardized output for frontend

"""
Output Formatter
================
Standardizes output format for frontend consumption.
Clean, consistent, well-structured.
"""

from typing import Dict, List, Optional
from datetime import datetime


class OutputFormatter:
    """Formats retrieval results for frontend"""
    
    def format_response(
        self,
        results: List[Dict],
        query: str,
        mode: str,
        mode_confidence: float,
        verticals_searched: List[str],
        vertical_coverage: Dict[str, int],
        processing_time: float,
        plan: Dict = None,
        reasoning: Dict = None,
        ideas: Dict = None
    ) -> Dict:
        """
        Format complete response.
        
        Args:
            results: Retrieved and reranked results
            query: Original query
            mode: Detected/explicit mode
            mode_confidence: Confidence in mode detection
            verticals_searched: List of verticals searched
            vertical_coverage: Count of results per vertical
            processing_time: Total processing time
            plan: Optional query plan
            reasoning: Optional reasoning structure (Deep Think)
            ideas: Optional idea structure (Brainstorm)
            
        Returns:
            Formatted response dict
        """
        # Format results
        formatted_results = self.format_results(results)
        
        # Build response
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "query": {
                "original": query,
                "mode": mode,
                "mode_confidence": round(mode_confidence, 3)
            },
            "search": {
                "verticals": verticals_searched,
                "vertical_coverage": vertical_coverage,
                "total_results": len(results)
            },
            "results": formatted_results,
            "performance": {
                "processing_time": round(processing_time, 3),
                "results_per_second": round(len(results) / processing_time, 2) if processing_time > 0 else 0
            }
        }
        
        # Add mode-specific structures
        if reasoning and mode == "deep_think":
            response["reasoning"] = self.format_reasoning(reasoning)
        
        if ideas and mode == "brainstorm":
            response["ideas"] = self.format_ideas(ideas)
        
        # Optionally add plan for debugging
        if plan:
            response["debug"] = {
                "plan": plan
            }
        
        return response
    
    def format_results(self, results: List[Dict]) -> List[Dict]:
        """
        Format individual results.
        
        Args:
            results: Raw results
            
        Returns:
            Formatted results
        """
        formatted = []
        
        for idx, result in enumerate(results):
            payload = result.get("payload", {})
            
            formatted_result = {
                "rank": idx + 1,
                "id": payload.get("chunk_id") or payload.get("id"),
                "text": self._clean_text(
                    payload.get("text") or payload.get("content", "")
                ),
                "vertical": result.get("vertical", "unknown"),
                "score": round(result.get("rerank_score", result.get("score", 0)), 4),
                "metadata": self._format_metadata(payload),
                "highlights": self._extract_highlights(
                    payload.get("text") or payload.get("content", "")
                )
            }
            
            formatted.append(formatted_result)
        
        return formatted
    
    def _format_metadata(self, payload: Dict) -> Dict:
        """Format metadata fields"""
        metadata = {
            "source": payload.get("source"),
            "doc_type": payload.get("doc_type"),
            "year": payload.get("year"),
            "date": payload.get("date"),
            "section": payload.get("section_number"),
            "article": payload.get("article_number"),
            "rule": payload.get("rule_number"),
            "go_number": payload.get("go_number"),
            "case_number": payload.get("case_number"),
            "department": payload.get("department"),
            "court": payload.get("court_name"),
            "act_name": payload.get("act_name")
        }
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def _clean_text(self, text: str) -> str:
        """Clean text for display"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (optional)
        max_length = 2000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def _extract_highlights(self, text: str, max_length: int = 200) -> str:
        """Extract a highlight snippet from text"""
        if not text:
            return ""
        
        # Take first max_length characters
        if len(text) <= max_length:
            return text
        
        # Find a good breaking point
        snippet = text[:max_length]
        last_period = snippet.rfind(".")
        last_space = snippet.rfind(" ")
        
        if last_period > max_length * 0.7:
            return snippet[:last_period + 1]
        elif last_space > max_length * 0.7:
            return snippet[:last_space] + "..."
        else:
            return snippet + "..."
    
    def format_reasoning(self, reasoning: Dict) -> Dict:
        """Format Deep Think reasoning structure"""
        return {
            "policy_chain": {
                "constitutional": reasoning.get("constitutional_foundation", []),
                "statutory": reasoning.get("statutory_framework", []),
                "administrative": reasoning.get("administrative_orders", []),
                "judicial": reasoning.get("judicial_precedents", []),
                "data": reasoning.get("data_evidence", []),
                "schemes": reasoning.get("implementation_schemes", [])
            },
            "coverage": reasoning.get("vertical_coverage", {}),
            "total_sources": reasoning.get("total_sources", 0)
        }
    
    def format_ideas(self, ideas: Dict) -> Dict:
        """Format Brainstorm idea structure"""
        return {
            "global_practices": ideas.get("global_best_practices", []),
            "indian_context": ideas.get("indian_context", []),
            "data_insights": ideas.get("data_insights", []),
            "diversity_score": ideas.get("diversity_score", 0),
            "total_ideas": ideas.get("total_ideas", 0)
        }
    
    def format_error(
        self,
        query: str,
        error: str,
        processing_time: float = 0.0
    ) -> Dict:
        """Format error response"""
        return {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "error": error,
            "processing_time": round(processing_time, 3)
        }


# Global formatter instance
_formatter_instance = None


def get_formatter() -> OutputFormatter:
    """Get global formatter instance"""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = OutputFormatter()
    return _formatter_instance