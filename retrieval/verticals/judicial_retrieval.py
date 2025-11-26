# Judicial retrieval module

"""
Judicial Vertical Retrieval
============================
Specialized retrieval logic for court judgments.
Handles cases, courts, precedents.
"""

from typing import List, Dict, Optional


class JudicialRetrieval:
    """Judicial-specific retrieval enhancements"""
    
    def __init__(self):
        """Initialize judicial retrieval"""
        self.boost_fields = ["case_number", "court_name", "judgment_date"]
        self.court_hierarchy = {
            "supreme court": 1.0,
            "high court": 0.9,
            "district court": 0.7,
            "tribunal": 0.6
        }
    
    def enhance_filters(self, filters: Dict, entities: Dict) -> Dict:
        """
        Enhance filters with judicial-specific logic.
        
        Args:
            filters: Base filters
            entities: Extracted entities
            
        Returns:
            Enhanced filters
        """
        enhanced = filters.copy()
        
        # Add case number filters
        if "case_number" in entities:
            cases = [e.normalized for e in entities["case_number"]]
            enhanced["case_number"] = cases
        
        return enhanced
    
    def boost_results(self, results: List[Dict]) -> List[Dict]:
        """
        Apply judicial-specific boosting to results.
        
        Args:
            results: Search results
            
        Returns:
            Boosted results
        """
        for result in results:
            payload = result.get("payload", {})
            boost = 1.0
            
            # Boost by court authority
            court = str(payload.get("court_name", "")).lower()
            for court_type, authority in self.court_hierarchy.items():
                if court_type in court:
                    boost *= authority
                    break
            
            # Boost if case is cited frequently (if available)
            citation_count = payload.get("citation_count", 0)
            if citation_count > 10:
                boost *= 1.2
            elif citation_count > 5:
                boost *= 1.1
            
            # Boost landmark judgments
            text = str(payload.get("text", "")).lower()
            if any(term in text for term in ["landmark", "precedent", "overruled", "binding"]):
                boost *= 1.15
            
            # Apply boost
            result["score"] *= boost
            result["judicial_boost"] = boost
        
        return results
    
    def extract_judicial_context(self, result: Dict) -> Dict:
        """
        Extract judicial-specific context from result.
        
        Args:
            result: Search result
            
        Returns:
            Judicial context dict
        """
        payload = result.get("payload", {})
        
        context = {
            "case_number": payload.get("case_number"),
            "court": payload.get("court_name"),
            "bench": payload.get("bench"),
            "judge": payload.get("judge_name"),
            "petitioner": payload.get("petitioner"),
            "respondent": payload.get("respondent"),
            "judgment_date": payload.get("judgment_date"),
            "citation": payload.get("citation"),
            "case_type": payload.get("case_type"),
            "verdict": payload.get("verdict")
        }
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def determine_precedent_value(self, result: Dict) -> str:
        """
        Determine precedent value of judgment.
        
        Args:
            result: Search result
            
        Returns:
            Precedent value (binding, persuasive, informative)
        """
        payload = result.get("payload", {})
        court = str(payload.get("court_name", "")).lower()
        
        if "supreme court" in court:
            return "binding"
        elif "high court" in court:
            return "persuasive"
        else:
            return "informative"
    
    def suggest_related_cases(self, result: Dict) -> List[str]:
        """
        Suggest related cases to explore.
        
        Args:
            result: Search result
            
        Returns:
            List of suggestions
        """
        payload = result.get("payload", {})
        suggestions = []
        
        # Suggest cited cases
        if payload.get("cited_cases"):
            suggestions.append("Cases cited in this judgment")
        
        # Suggest later citations
        suggestions.append("Later cases citing this judgment")
        
        # Suggest similar cases
        case_type = payload.get("case_type")
        if case_type:
            suggestions.append(f"Other {case_type} cases")
        
        return suggestions[:3]


# Global instance
_judicial_retrieval_instance = None


def get_judicial_retrieval() -> JudicialRetrieval:
    """Get global judicial retrieval instance"""
    global _judicial_retrieval_instance
    if _judicial_retrieval_instance is None:
        _judicial_retrieval_instance = JudicialRetrieval()
    return _judicial_retrieval_instance