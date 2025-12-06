# Internet / External Search Layer
# Google PSE client, crawler, merger, page cleaner

"""
Internet Layer - Web search and content fetching
Google PSE integration, crawling, merging
"""

from .google_pse_client import GooglePSEClient, WebResult, google_search
from .internet_crawler import InternetCrawler, fetch_url
from .page_cleaner import PageCleaner, clean_html
from .internet_merger import InternetMerger, MergedResult, merge_results

__all__ = [
    # Google PSE
    'GooglePSEClient',
    'WebResult',
    'google_search',
    
    # Crawler
    'InternetCrawler',
    'fetch_url',
    
    # Cleaner
    'PageCleaner',
    'clean_html',
    
    # Merger
    'InternetMerger',
    'MergedResult',
    'merge_results',
]













