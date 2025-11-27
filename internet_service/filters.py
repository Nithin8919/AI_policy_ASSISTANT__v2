"""
Domain Filters
==============
Security and quality filtering for internet results.
"""

import logging
from typing import List, Dict
from urllib.parse import urlparse

from .config import get_internet_config

logger = logging.getLogger(__name__)


class DomainFilter:
    """
    Filter results by domain whitelist.
    Ensures only trusted sources.
    """
    
    def __init__(self):
        self.config = get_internet_config()
    
    def filter_results(self, results: List[Dict]) -> List[Dict]:
        """
        Filter results to only whitelisted domains.
        
        Args:
            results: List of search results
            
        Returns:
            Filtered list
        """
        
        filtered = []
        blocked_count = 0
        
        for result in results:
            url = result.get("url", "")
            
            if self.config.is_domain_allowed(url):
                filtered.append(result)
            else:
                blocked_count += 1
                domain = urlparse(url).netloc
                logger.debug(f"Blocked non-whitelisted domain: {domain}")
        
        if blocked_count > 0:
            logger.info(f"Filtered out {blocked_count} non-whitelisted results")
        
        return filtered
    
    def is_safe_url(self, url: str) -> bool:
        """
        Check if URL is safe to fetch.
        
        Args:
            url: URL to check
            
        Returns:
            True if safe
        """
        
        # Basic checks
        if not url.startswith(("http://", "https://")):
            return False
        
        # Check whitelist
        if not self.config.is_domain_allowed(url):
            return False
        
        # Block suspicious patterns
        suspicious = [
            ".onion",
            "bit.ly",
            "tinyurl",
            ".tk",
            ".ml",
            "data:",
            "javascript:"
        ]
        
        url_lower = url.lower()
        for pattern in suspicious:
            if pattern in url_lower:
                logger.warning(f"Blocked suspicious URL pattern: {pattern}")
                return False
        
        return True


# Singleton
_filter = None

def get_domain_filter() -> DomainFilter:
    """Get global domain filter"""
    global _filter
    if _filter is None:
        _filter = DomainFilter()
    return _filter