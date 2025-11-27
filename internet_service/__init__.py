"""
Internet Service Module
========================
Search and extract content from the internet using Google PSE.

Main entry point:
    from internet_service import search_internet
    
    result = search_internet("latest FLN progress in AP")
    for snippet in result.snippets:
        print(snippet.title, snippet.url)
"""

from .client import InternetServiceClient, get_internet_client, search_internet
from .config import InternetConfig, get_internet_config
from .schemas import InternetSnippet, InternetSearchResult

__all__ = [
    "InternetServiceClient",
    "get_internet_client",
    "search_internet",
    "InternetConfig",
    "get_internet_config",
    "InternetSnippet",
    "InternetSearchResult",
]