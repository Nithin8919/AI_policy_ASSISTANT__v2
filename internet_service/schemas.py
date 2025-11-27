"""
Internet Service Schemas
=========================
Clean data models for internet search results.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InternetSnippet:
    """Single search result snippet"""
    url: str
    title: str
    snippet: str
    content: str  # Full extracted text
    domain: str
    timestamp: str
    
    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "content": self.content,
            "domain": self.domain,
            "timestamp": self.timestamp
        }


@dataclass
class InternetSearchResult:
    """Complete internet search response"""
    query: str
    snippets: List[InternetSnippet]
    success: bool
    error: Optional[str] = None
    search_time: float = 0.0
    total_results_found: int = 0
    
    def to_dict(self):
        return {
            "query": self.query,
            "snippets": [s.to_dict() for s in self.snippets],
            "success": self.success,
            "error": self.error,
            "search_time": self.search_time,
            "total_results_found": self.total_results_found
        }
    
    @property
    def has_results(self) -> bool:
        return len(self.snippets) > 0