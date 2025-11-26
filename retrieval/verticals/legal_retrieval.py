# Legal retrieval module

"""
Legal Vertical Retrieval
=========================
Specialized retrieval logic for legal documents.
Handles acts, sections, rules, articles.
"""

from typing import List, Dict, Optional


class LegalRetrieval:
    """Legal-specific retrieval enhancements"""
    
    def __init__(self):
        """Initialize legal retrieval"""
        self.boost_fields = ["act_name", "section_number", "rule_number", "article_number"]
    
    def enhance_filters(self, filters: Dict, entities: Dict) -> Dict:
        """
        Enhance filters with legal-specific logic.
        
        Args:
            filters: Base filters
            entities: Extracted entities
            
        Returns:
            Enhanced filters
        """
        enhanced = filters.copy()
        
        # Add section filters
        if "section" in entities:
            sections = [e.normalized for e in entities["section"]]
            enhanced["section_number"] = sections
        
        # Add article filters
        if "article" in entities:
            articles = [e.normalized for e in entities["article"]]
            enhanced["article_number"] = articles
        
        # Add rule filters
        if "rule" in entities:
            rules = [e.normalized for e in entities["rule"]]
            enhanced["rule_number"] = rules
        
        # Add act name filters
        if "act_name" in entities:
            acts = [e.normalized for e in entities["act_name"]]
            enhanced["act_name"] = acts
        
        return enhanced
    
    def boost_results(self, results: List[Dict]) -> List[Dict]:
        """
        Apply legal-specific boosting to results.
        
        Args:
            results: Search results
            
        Returns:
            Boosted results
        """
        for result in results:
            payload = result.get("payload", {})
            boost = 1.0
            
            # Boost constitutional provisions
            act_name = str(payload.get("act_name", "")).lower()
            if "constitution" in act_name:
                boost *= 1.3
            
            # Boost RTE Act (highly relevant for education)
            elif "right to education" in act_name or "rte" in act_name:
                boost *= 1.2
            
            # Boost if section number is present (more specific)
            if payload.get("section_number"):
                boost *= 1.1
            
            # Apply boost
            result["score"] *= boost
            result["legal_boost"] = boost
        
        return results
    
    def extract_legal_context(self, result: Dict) -> Dict:
        """
        Extract legal-specific context from result.
        
        Args:
            result: Search result
            
        Returns:
            Legal context dict
        """
        payload = result.get("payload", {})
        
        context = {
            "act": payload.get("act_name"),
            "section": payload.get("section_number"),
            "article": payload.get("article_number"),
            "rule": payload.get("rule_number"),
            "chapter": payload.get("chapter_number"),
            "amendment": payload.get("amendment_info"),
            "enforcement_date": payload.get("enforcement_date")
        }
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def suggest_related_sections(self, result: Dict) -> List[str]:
        """
        Suggest related sections to explore.
        
        Args:
            result: Search result
            
        Returns:
            List of suggestions
        """
        payload = result.get("payload", {})
        suggestions = []
        
        section = payload.get("section_number")
        if section:
            try:
                # Suggest adjacent sections
                section_num = int(''.join(filter(str.isdigit, section)))
                suggestions.append(f"Section {section_num - 1}")
                suggestions.append(f"Section {section_num + 1}")
            except ValueError:
                pass
        
        # Suggest related provisions
        act = payload.get("act_name")
        if act:
            suggestions.append(f"Other sections of {act}")
            suggestions.append(f"Rules under {act}")
        
        return suggestions[:3]  # Top 3 suggestions


# Global instance
_legal_retrieval_instance = None


def get_legal_retrieval() -> LegalRetrieval:
    """Get global legal retrieval instance"""
    global _legal_retrieval_instance
    if _legal_retrieval_instance is None:
        _legal_retrieval_instance = LegalRetrieval()
    return _legal_retrieval_instance