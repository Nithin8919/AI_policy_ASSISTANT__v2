# Light normalization (punctuation, casing)

"""
Query Normalizer
================
Light normalization - just what's needed, nothing more.
"""

import re
from typing import Optional


class QueryNormalizer:
    """Lightweight query normalization"""
    
    # Useless filler words to remove
    STOPWORDS = {
        "tell", "me", "about", "what", "is", "are", "the", "a", "an",
        "please", "can", "you", "could", "would", "how", "why", "when",
        "where", "which", "who", "whom", "whose", "explain", "describe"
    }
    
    def normalize(self, query: str) -> str:
        """
        Normalize query text.
        
        Steps:
        1. Lowercase
        2. Remove extra whitespace
        3. Basic punctuation cleanup
        
        Does NOT remove stopwords by default (they help with context).
        """
        # Lowercase
        query = query.lower()
        
        # Remove multiple spaces
        query = re.sub(r'\s+', ' ', query)
        
        # Remove leading/trailing whitespace
        query = query.strip()
        
        # Fix common punctuation issues
        query = re.sub(r'\s+([.,!?;:])', r'\1', query)  # Remove space before punctuation
        query = re.sub(r'([.,!?;:])\s*$', '', query)  # Remove trailing punctuation
        
        return query
    
    def remove_filler(self, query: str) -> str:
        """
        Remove filler words while preserving meaning.
        Use sparingly - only for very conversational queries.
        """
        words = query.lower().split()
        
        # Remove stopwords from start
        while words and words[0] in self.STOPWORDS:
            words.pop(0)
        
        # Remove stopwords from end
        while words and words[-1] in self.STOPWORDS:
            words.pop()
        
        return ' '.join(words)
    
    def clean_for_bm25(self, query: str) -> str:
        """
        Clean query for BM25 keyword matching.
        More aggressive than regular normalization.
        """
        # Normalize first
        query = self.normalize(query)
        
        # Remove filler
        query = self.remove_filler(query)
        
        # Remove punctuation for keyword matching
        query = re.sub(r'[^\w\s-]', ' ', query)
        
        # Remove extra spaces again
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query


# Global normalizer instance
_normalizer_instance = None


def get_normalizer() -> QueryNormalizer:
    """Get global normalizer instance"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = QueryNormalizer()
    return _normalizer_instance