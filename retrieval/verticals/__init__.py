"""
Verticals Module
================
Vertical-specific retrieval logic and enhancements.

Each vertical has specialized logic for:
- Filter enhancement
- Result boosting
- Context extraction
- Related suggestions
"""

from .legal_retrieval import LegalRetrieval, get_legal_retrieval
from .go_retrieval import GORetrieval, get_go_retrieval
from .judicial_retrieval import JudicialRetrieval, get_judicial_retrieval
from .data_retrieval import DataRetrieval, get_data_retrieval
from .schemes_retrieval import SchemesRetrieval, get_schemes_retrieval

__all__ = [
    "LegalRetrieval", "get_legal_retrieval",
    "GORetrieval", "get_go_retrieval",
    "JudicialRetrieval", "get_judicial_retrieval",
    "DataRetrieval", "get_data_retrieval",
    "SchemesRetrieval", "get_schemes_retrieval"
]