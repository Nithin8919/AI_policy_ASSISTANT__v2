# GO retrieval module

"""
GO Vertical Retrieval
=====================
Specialized retrieval logic for Government Orders.
Handles GO numbers, departments, notifications.
"""

from typing import List, Dict, Optional
from datetime import datetime


class GORetrieval:
    """GO-specific retrieval enhancements"""
    
    def __init__(self):
        """Initialize GO retrieval"""
        self.boost_fields = ["go_number", "department", "notification_number"]
    
    def enhance_filters(self, filters: Dict, entities: Dict) -> Dict:
        """
        Enhance filters with GO-specific logic.
        
        Args:
            filters: Base filters
            entities: Extracted entities
            
        Returns:
            Enhanced filters
        """
        enhanced = filters.copy()
        
        # Add GO number filters
        if "go_number" in entities:
            go_numbers = [e.normalized for e in entities["go_number"]]
            enhanced["go_number"] = go_numbers
        
        return enhanced
    
    def boost_results(self, results: List[Dict]) -> List[Dict]:
        """
        Apply GO-specific boosting to results.
        
        Args:
            results: Search results
            
        Returns:
            Boosted results
        """
        current_year = datetime.now().year
        
        for result in results:
            payload = result.get("payload", {})
            boost = 1.0
            
            # Boost recent GOs (last 3 years)
            year = payload.get("year")
            if year:
                try:
                    year_int = int(year) if isinstance(year, str) else year
                    if year_int >= current_year - 3:
                        boost *= 1.2
                    elif year_int >= current_year - 5:
                        boost *= 1.1
                except (ValueError, TypeError):
                    pass
            
            # Boost education department GOs
            dept = str(payload.get("department", "")).lower()
            if any(term in dept for term in ["education", "school", "teacher"]):
                boost *= 1.15
            
            # Boost if GO number is exact match
            if payload.get("go_number"):
                boost *= 1.1
            
            # Apply boost
            result["score"] *= boost
            result["go_boost"] = boost
        
        return results
    
    def extract_go_context(self, result: Dict) -> Dict:
        """
        Extract GO-specific context from result.
        
        Args:
            result: Search result
            
        Returns:
            GO context dict
        """
        payload = result.get("payload", {})
        
        context = {
            "go_number": payload.get("go_number"),
            "department": payload.get("department"),
            "notification_type": payload.get("notification_type"),
            "subject": payload.get("subject"),
            "issuing_authority": payload.get("issuing_authority"),
            "date": payload.get("date"),
            "status": self._determine_status(payload)
        }
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def _determine_status(self, payload: Dict) -> str:
        """Determine GO status (active, superseded, etc.)"""
        # Simple heuristic based on year
        year = payload.get("year")
        if not year:
            return "unknown"
        
        try:
            year_int = int(year) if isinstance(year, str) else year
            current_year = datetime.now().year
            
            if year_int >= current_year - 2:
                return "likely_active"
            elif year_int >= current_year - 5:
                return "possibly_active"
            else:
                return "historical"
        except (ValueError, TypeError):
            return "unknown"
    
    def suggest_related_gos(self, result: Dict) -> List[str]:
        """
        Suggest related GOs to explore.
        
        Args:
            result: Search result
            
        Returns:
            List of suggestions
        """
        payload = result.get("payload", {})
        suggestions = []
        
        # Suggest GOs from same department
        dept = payload.get("department")
        if dept:
            suggestions.append(f"Other GOs from {dept}")
        
        # Suggest GOs from same year
        year = payload.get("year")
        if year:
            suggestions.append(f"Related GOs from {year}")
        
        # Suggest implementation circulars
        suggestions.append("Implementation circulars")
        
        return suggestions[:3]


# Global instance
_go_retrieval_instance = None


def get_go_retrieval() -> GORetrieval:
    """Get global GO retrieval instance"""
    global _go_retrieval_instance
    if _go_retrieval_instance is None:
        _go_retrieval_instance = GORetrieval()
    return _go_retrieval_instance