# Signals - detect recency, authority

"""
Signals - Authority and recency scoring
"""

import re
from datetime import datetime


class SignalScorer:
    """Score documents based on authority and recency"""
    
    def authority_score(self, source: str) -> float:
        """Score based on source authority"""
        authority_map = {
            'act': 1.0,
            'rule': 0.9,
            'go': 0.85,
            'circular': 0.7,
            'guideline': 0.6,
        }
        
        source_lower = source.lower()
        for key, score in authority_map.items():
            if key in source_lower:
                return score
        
        return 0.5  # Default
    
    def recency_score(self, text: str) -> float:
        """Score based on recency (extract year)"""
        current_year = datetime.now().year
        
        # Extract years
        years = re.findall(r'(20\d{2})', text)
        
        if not years:
            return 0.5  # Unknown
        
        # Get most recent year
        max_year = max(int(y) for y in years)
        
        # Score: 1.0 for current year, decay for older
        age = current_year - max_year
        score = max(0.0, 1.0 - (age * 0.1))
        
        return score