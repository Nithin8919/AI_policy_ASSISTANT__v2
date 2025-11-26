# Data retrieval module

"""
Data Vertical Retrieval
========================
Specialized retrieval logic for data reports.
Handles UDISE, ASER, statistics, metrics.
"""

from typing import List, Dict, Optional
import re


class DataRetrieval:
    """Data-specific retrieval enhancements"""
    
    def __init__(self):
        """Initialize data retrieval"""
        self.boost_fields = ["report_name", "year", "metric_name", "district"]
        self.key_reports = [
            "udise", "aser", "district information", "state education",
            "unified district", "annual report"
        ]
    
    def enhance_filters(self, filters: Dict, entities: Dict) -> Dict:
        """
        Enhance filters with data-specific logic.
        
        Args:
            filters: Base filters
            entities: Extracted entities
            
        Returns:
            Enhanced filters
        """
        enhanced = filters.copy()
        
        # Year filters already added by general enhancement
        # Can add data-specific filters here if needed
        
        return enhanced
    
    def boost_results(self, results: List[Dict]) -> List[Dict]:
        """
        Apply data-specific boosting to results.
        
        Args:
            results: Search results
            
        Returns:
            Boosted results
        """
        for result in results:
            payload = result.get("payload", {})
            boost = 1.0
            
            # Boost key reports
            source = str(payload.get("source", "")).lower()
            for key_report in self.key_reports:
                if key_report in source:
                    boost *= 1.2
                    break
            
            # Boost if contains quantitative data
            text = str(payload.get("text", "")).lower()
            if self._contains_metrics(text):
                boost *= 1.15
            
            # Boost recent data
            year = payload.get("year")
            if year:
                try:
                    year_int = int(year) if isinstance(year, str) else year
                    if year_int >= 2020:
                        boost *= 1.2
                    elif year_int >= 2018:
                        boost *= 1.1
                except (ValueError, TypeError):
                    pass
            
            # Apply boost
            result["score"] *= boost
            result["data_boost"] = boost
        
        return results
    
    def _contains_metrics(self, text: str) -> bool:
        """Check if text contains quantitative metrics"""
        # Look for percentages, numbers with units
        patterns = [
            r'\d+\.?\d*%',  # Percentages
            r'\d+\.?\d*\s*(lakh|crore|thousand|million)',  # Large numbers
            r'(enrollment|dropout|attendance|score).*\d+',  # Metrics with numbers
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_data_context(self, result: Dict) -> Dict:
        """
        Extract data-specific context from result.
        
        Args:
            result: Search result
            
        Returns:
            Data context dict
        """
        payload = result.get("payload", {})
        
        context = {
            "report": payload.get("report_name") or payload.get("source"),
            "year": payload.get("year"),
            "academic_year": payload.get("academic_year"),
            "district": payload.get("district"),
            "metric_type": payload.get("metric_type"),
            "data_source": payload.get("data_source"),
            "survey_period": payload.get("survey_period")
        }
        
        # Extract metrics from text
        metrics = self._extract_metrics(payload.get("text", ""))
        if metrics:
            context["key_metrics"] = metrics
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def _extract_metrics(self, text: str, max_metrics: int = 3) -> List[str]:
        """Extract key metrics from text"""
        metrics = []
        
        # Find sentences with percentages
        sentences = text.split('.')
        for sentence in sentences:
            if '%' in sentence or 'percent' in sentence.lower():
                metrics.append(sentence.strip())
                if len(metrics) >= max_metrics:
                    break
        
        return metrics
    
    def suggest_related_data(self, result: Dict) -> List[str]:
        """
        Suggest related data sources to explore.
        
        Args:
            result: Search result
            
        Returns:
            List of suggestions
        """
        payload = result.get("payload", {})
        suggestions = []
        
        # Suggest year-over-year comparison
        year = payload.get("year")
        if year:
            try:
                year_int = int(year) if isinstance(year, str) else year
                suggestions.append(f"Data from {year_int - 1} for comparison")
                suggestions.append(f"Trend analysis {year_int - 3} to {year_int}")
            except (ValueError, TypeError):
                pass
        
        # Suggest district-wise breakdown
        suggestions.append("District-wise breakdown")
        
        # Suggest related metrics
        suggestions.append("Related performance indicators")
        
        return suggestions[:3]


# Global instance
_data_retrieval_instance = None


def get_data_retrieval() -> DataRetrieval:
    """Get global data retrieval instance"""
    global _data_retrieval_instance
    if _data_retrieval_instance is None:
        _data_retrieval_instance = DataRetrieval()
    return _data_retrieval_instance