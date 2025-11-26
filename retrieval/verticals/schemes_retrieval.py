# Schemes retrieval module

"""
Schemes Vertical Retrieval
===========================
Specialized retrieval logic for schemes and programs.
Handles government schemes, international models.
"""

from typing import List, Dict, Optional


class SchemesRetrieval:
    """Schemes-specific retrieval enhancements"""
    
    def __init__(self):
        """Initialize schemes retrieval"""
        self.boost_fields = ["scheme_name", "country", "organization", "status"]
        self.international_indicators = [
            "finland", "singapore", "south korea", "japan", "oecd",
            "unesco", "world bank", "unicef", "global", "international"
        ]
    
    def enhance_filters(self, filters: Dict, entities: Dict) -> Dict:
        """
        Enhance filters with schemes-specific logic.
        
        Args:
            filters: Base filters
            entities: Extracted entities
            
        Returns:
            Enhanced filters
        """
        enhanced = filters.copy()
        
        # Can add scheme-specific filters if needed
        
        return enhanced
    
    def boost_results(self, results: List[Dict]) -> List[Dict]:
        """
        Apply schemes-specific boosting to results.
        
        Args:
            results: Search results
            
        Returns:
            Boosted results
        """
        for result in results:
            payload = result.get("payload", {})
            boost = 1.0
            
            # Boost international models (valuable for brainstorming)
            text = str(payload.get("text", "")).lower()
            source = str(payload.get("source", "")).lower()
            
            for indicator in self.international_indicators:
                if indicator in text or indicator in source:
                    boost *= 1.25
                    break
            
            # Boost active schemes
            status = str(payload.get("status", "")).lower()
            if "active" in status or "ongoing" in status:
                boost *= 1.15
            
            # Boost successful implementations
            if any(term in text for term in ["success", "effective", "impact", "outcome"]):
                boost *= 1.1
            
            # Apply boost
            result["score"] *= boost
            result["schemes_boost"] = boost
        
        return results
    
    def extract_schemes_context(self, result: Dict) -> Dict:
        """
        Extract schemes-specific context from result.
        
        Args:
            result: Search result
            
        Returns:
            Schemes context dict
        """
        payload = result.get("payload", {})
        
        context = {
            "scheme_name": payload.get("scheme_name"),
            "country": payload.get("country"),
            "organization": payload.get("organization"),
            "status": payload.get("status"),
            "launch_year": payload.get("launch_year"),
            "target_group": payload.get("target_group"),
            "budget": payload.get("budget"),
            "outcomes": payload.get("outcomes"),
            "type": self._determine_type(payload)
        }
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def _determine_type(self, payload: Dict) -> str:
        """Determine scheme type (indian, international, pilot, etc.)"""
        text = str(payload.get("text", "")).lower()
        source = str(payload.get("source", "")).lower()
        
        # Check for international
        for indicator in self.international_indicators:
            if indicator in text or indicator in source:
                return "international"
        
        # Check for pilot/experimental
        if any(term in text for term in ["pilot", "experimental", "trial"]):
            return "pilot"
        
        # Check for central scheme
        if any(term in text for term in ["central", "national", "india"]):
            return "central"
        
        # Check for state scheme
        if any(term in text for term in ["state", "andhra pradesh", "ap"]):
            return "state"
        
        return "unknown"
    
    def extract_learnings(self, result: Dict) -> List[str]:
        """
        Extract key learnings from scheme.
        
        Args:
            result: Search result
            
        Returns:
            List of learnings
        """
        payload = result.get("payload", {})
        text = str(payload.get("text", "")).lower()
        
        learnings = []
        
        # Look for success factors
        if "success" in text:
            # Extract sentence containing success
            sentences = text.split('.')
            for sent in sentences:
                if "success" in sent:
                    learnings.append(sent.strip()[:150])
                    break
        
        # Look for challenges
        if any(term in text for term in ["challenge", "difficulty", "obstacle"]):
            sentences = text.split('.')
            for sent in sentences:
                if any(term in sent for term in ["challenge", "difficulty", "obstacle"]):
                    learnings.append(sent.strip()[:150])
                    break
        
        return learnings[:2]  # Top 2 learnings
    
    def suggest_related_schemes(self, result: Dict) -> List[str]:
        """
        Suggest related schemes to explore.
        
        Args:
            result: Search result
            
        Returns:
            List of suggestions
        """
        payload = result.get("payload", {})
        suggestions = []
        
        # Suggest similar schemes from same country
        country = payload.get("country")
        if country:
            suggestions.append(f"Other schemes from {country}")
        
        # Suggest schemes with similar objectives
        suggestions.append("Schemes with similar objectives")
        
        # Suggest implementation guidelines
        suggestions.append("Implementation guidelines and best practices")
        
        return suggestions[:3]


# Global instance
_schemes_retrieval_instance = None


def get_schemes_retrieval() -> SchemesRetrieval:
    """Get global schemes retrieval instance"""
    global _schemes_retrieval_instance
    if _schemes_retrieval_instance is None:
        _schemes_retrieval_instance = SchemesRetrieval()
    return _schemes_retrieval_instance