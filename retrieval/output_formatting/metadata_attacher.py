# Add metadata blocks

"""
Metadata Attacher
=================
Attaches rich metadata blocks to results.
Makes results more informative and actionable.
"""

from typing import Dict, List, Optional
from datetime import datetime


class MetadataAttacher:
    """Attaches metadata to results"""
    
    def attach_metadata(
        self,
        results: List[Dict],
        include_provenance: bool = True,
        include_quality: bool = True,
        include_related: bool = False
    ) -> List[Dict]:
        """
        Attach metadata blocks to results.
        
        Args:
            results: Search results
            include_provenance: Include source provenance
            include_quality: Include quality indicators
            include_related: Include related document hints
            
        Returns:
            Results with attached metadata
        """
        for result in results:
            metadata_block = {}
            
            if include_provenance:
                metadata_block["provenance"] = self._build_provenance(result)
            
            if include_quality:
                metadata_block["quality"] = self._build_quality_indicators(result)
            
            if include_related:
                metadata_block["related"] = self._build_related_hints(result)
            
            result["metadata_block"] = metadata_block
        
        return results
    
    def _build_provenance(self, result: Dict) -> Dict:
        """Build source provenance information"""
        payload = result.get("payload", {})
        
        provenance = {
            "vertical": result.get("vertical"),
            "collection": result.get("collection"),
            "source_document": payload.get("source"),
            "document_type": payload.get("doc_type"),
            "chunk_id": payload.get("chunk_id"),
            "document_id": payload.get("document_id"),
            "page_number": payload.get("page_number"),
            "position_in_doc": payload.get("position_in_doc")
        }
        
        # Add temporal info
        if payload.get("year"):
            provenance["year"] = payload.get("year")
        if payload.get("date"):
            provenance["date"] = payload.get("date")
        
        # Add authority info
        if payload.get("issuing_authority"):
            provenance["issuing_authority"] = payload.get("issuing_authority")
        if payload.get("court_name"):
            provenance["court"] = payload.get("court_name")
        
        # Remove None values
        return {k: v for k, v in provenance.items() if v is not None}
    
    def _build_quality_indicators(self, result: Dict) -> Dict:
        """Build quality indicator information"""
        payload = result.get("payload", {})
        
        quality = {
            "relevance_score": round(result.get("rerank_score", result.get("score", 0)), 4),
            "vector_score": round(result.get("score", 0), 4)
        }
        
        # Add reranking signals if available
        if "term_overlap" in result:
            quality["term_match"] = round(result.get("term_overlap", 0), 3)
        
        if "recency_score" in result:
            quality["recency"] = round(result.get("recency_score", 0), 3)
        
        if "authority_score" in result:
            quality["authority"] = round(result.get("authority_score", 0), 3)
        
        if "innovation_score" in result:
            quality["innovation"] = round(result.get("innovation_score", 0), 3)
        
        # Determine confidence level
        score = quality["relevance_score"]
        if score >= 0.8:
            quality["confidence"] = "high"
        elif score >= 0.6:
            quality["confidence"] = "medium"
        else:
            quality["confidence"] = "low"
        
        return quality
    
    def _build_related_hints(self, result: Dict) -> Dict:
        """Build hints about related documents"""
        payload = result.get("payload", {})
        
        related = {}
        
        # Same document hints
        if payload.get("document_id"):
            related["same_document"] = {
                "available": True,
                "document_id": payload.get("document_id")
            }
        
        # Cross-references
        if payload.get("cross_references"):
            related["cross_references"] = payload.get("cross_references")
        
        # Related sections
        if payload.get("section_number"):
            related["nearby_sections"] = {
                "current": payload.get("section_number"),
                "hint": "Check adjacent sections for context"
            }
        
        # Related GOs
        if payload.get("go_number"):
            related["same_series"] = {
                "go_number": payload.get("go_number"),
                "hint": "Check related GOs from same department"
            }
        
        return related if related else None
    
    def add_action_hints(
        self,
        results: List[Dict],
        vertical: str
    ) -> List[Dict]:
        """
        Add action hints based on vertical.
        
        Args:
            results: Search results
            vertical: Vertical name
            
        Returns:
            Results with action hints
        """
        for result in results:
            hints = []
            
            if vertical == "legal":
                hints = [
                    "Check related sections",
                    "Review amendments",
                    "See judicial interpretations"
                ]
            elif vertical == "go":
                hints = [
                    "Check implementation status",
                    "Review related GOs",
                    "See department circulars"
                ]
            elif vertical == "judicial":
                hints = [
                    "Read full judgment",
                    "Check if appealed",
                    "See cited precedents"
                ]
            elif vertical == "data":
                hints = [
                    "Download full report",
                    "Compare year-over-year",
                    "Check district-wise data"
                ]
            elif vertical == "schemes":
                hints = [
                    "Check eligibility criteria",
                    "Review implementation guidelines",
                    "See similar schemes"
                ]
            
            result["action_hints"] = hints
        
        return results
    
    def build_summary_metadata(
        self,
        results: List[Dict]
    ) -> Dict:
        """
        Build summary metadata for all results.
        
        Args:
            results: All search results
            
        Returns:
            Summary metadata dict
        """
        if not results:
            return {}
        
        # Collect statistics
        verticals = [r.get("vertical") for r in results]
        scores = [r.get("rerank_score", r.get("score", 0)) for r in results]
        years = [r.get("payload", {}).get("year") for r in results if r.get("payload", {}).get("year")]
        
        summary = {
            "total_results": len(results),
            "verticals_represented": list(set(verticals)),
            "vertical_distribution": {v: verticals.count(v) for v in set(verticals)},
            "score_range": {
                "min": round(min(scores), 4) if scores else 0,
                "max": round(max(scores), 4) if scores else 0,
                "mean": round(sum(scores) / len(scores), 4) if scores else 0
            },
            "temporal_range": {
                "earliest": min(years) if years else None,
                "latest": max(years) if years else None
            },
            "confidence_distribution": self._get_confidence_distribution(results)
        }
        
        return summary
    
    def _get_confidence_distribution(self, results: List[Dict]) -> Dict:
        """Get distribution of confidence levels"""
        high = sum(1 for r in results if r.get("rerank_score", r.get("score", 0)) >= 0.8)
        medium = sum(1 for r in results if 0.6 <= r.get("rerank_score", r.get("score", 0)) < 0.8)
        low = sum(1 for r in results if r.get("rerank_score", r.get("score", 0)) < 0.6)
        
        return {
            "high": high,
            "medium": medium,
            "low": low
        }


# Global metadata attacher instance
_metadata_attacher_instance = None


def get_metadata_attacher() -> MetadataAttacher:
    """Get global metadata attacher instance"""
    global _metadata_attacher_instance
    if _metadata_attacher_instance is None:
        _metadata_attacher_instance = MetadataAttacher()
    return _metadata_attacher_instance