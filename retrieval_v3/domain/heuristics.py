# Heuristics - detect categories using keywords

"""
Heuristics - Detect chunk categories using keywords
"""

from typing import List
import re


class CategoryDetector:
    """Detect document/chunk category"""
    
    def __init__(self):
        from .categories import CATEGORIES
        self.categories = CATEGORIES
    
    def detect_category(self, text: str) -> List[str]:
        """
        Detect categories in text
        
        Returns:
            List of matching categories
        """
        text_lower = text.lower()
        matches = []
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append(category)
                    break
        
        return matches





