"""
Internet Service Client
========================
Main interface for internet search and content extraction.
Clean, simple, reliable.
"""

import time
import logging
from typing import List
from datetime import datetime

from .config import get_internet_config
from .schemas import InternetSnippet, InternetSearchResult
from .search import get_search_engine
from .extract import get_content_extractor
from .filters import get_domain_filter

logger = logging.getLogger(__name__)


class InternetServiceClient:
    """
    Main internet service.
    Combines search, extraction, filtering.
    """
    
    def __init__(self):
        self.config = get_internet_config()
        self.search_engine = get_search_engine()
        self.extractor = get_content_extractor()
        self.filter = get_domain_filter()
    
    def search(
        self,
        query: str,
        max_results: int = None
    ) -> InternetSearchResult:
        """
        Search internet and extract content.
        
        Args:
            query: Search query
            max_results: Max results to return (default from config)
            
        Returns:
            InternetSearchResult with snippets
        """
        
        if max_results is None:
            max_results = self.config.max_results
        
        start_time = time.time()
        
        try:
            logger.info(f"🌐 Internet search: '{query}'")
            
            # 1. Search Google PSE
            raw_results = self.search_engine.search(query, num_results=max_results * 2)
            
            if not raw_results:
                logger.warning("No search results found")
                return InternetSearchResult(
                    query=query,
                    snippets=[],
                    success=True,
                    search_time=time.time() - start_time,
                    total_results_found=0
                )
            
            # 2. Format and filter
            formatted = self.search_engine.format_results(raw_results)
            filtered = self.filter.filter_results(formatted)
            
            # 3. Extract content from each URL
            snippets = []
            
            for result in filtered[:max_results]:
                try:
                    url = result["url"]
                    
                    # Safety check
                    if not self.filter.is_safe_url(url):
                        continue
                    
                    # Extract full content
                    content = self.extractor.extract_with_fallback(
                        url,
                        result["snippet"]
                    )
                    
                    snippet = InternetSnippet(
                        url=url,
                        title=result["title"],
                        snippet=result["snippet"],
                        content=content,
                        domain=result["domain"],
                        timestamp=datetime.now().isoformat()
                    )
                    
                    snippets.append(snippet)
                    
                except Exception as e:
                    logger.warning(f"Error processing result {url}: {e}")
                    continue
            
            search_time = time.time() - start_time
            
            logger.info(f"✅ Internet search completed: {len(snippets)} snippets in {search_time:.2f}s")
            
            return InternetSearchResult(
                query=query,
                snippets=snippets,
                success=True,
                search_time=search_time,
                total_results_found=len(raw_results)
            )
            
        except Exception as e:
            logger.error(f"❌ Internet search failed: {e}")
            return InternetSearchResult(
                query=query,
           """
Internet Service Client
========================
Main interface for internet search and content extraction.
Clean, simple, reliable.
"""

import time
import logging
from typing import List
from datetime import datetime

from .config import get_internet_config
from .schemas import InternetSnippet, InternetSearchResult
from .search import get_search_engine
from .extract import get_content_extractor
from .filters import get_domain_filter

logger = logging.getLogger(__name__)


class InternetServiceClient:
    """
    Main internet service.
    Combines search, extraction, filtering.
    """
    
    def __init__(self):
        self.config = get_internet_config()
        self.search_engine = get_search_engine()
        self.extractor = get_content_extractor()
        self.filter = get_domain_filter()
    
    def search(
        self,
        query: str,
        max_results: int = None
    ) -> InternetSearchResult:
        """
        Search internet using Vertex AI grounding and extract content.
        
        Args:
            query: Search query
            max_results: Max results to return (default from config)
            
        Returns:
            InternetSearchResult with snippets
        """
        
        if max_results is None:
            max_results = self.config.max_results
        
        start_time = time.time()
        
        try:
            logger.info(f"🌐 Internet search (Vertex AI): '{query}'")
            
            # 1. Search using Vertex AI grounding
            raw_results = self.search_engine.search(query, num_results=max_results * 2)
            
            if not raw_results:
                logger.warning("No search results found")
                return InternetSearchResult(
                    query=query,
                    snippets=[],
                    success=True,
                    search_time=time.time() - start_time,
                    total_results_found=0
                )
            
            # 2. Format and filter
            formatted = self.search_engine.format_results(raw_results)
            filtered = self.filter.filter_results(formatted)
            
            # 3. Extract content from each URL
            snippets = []
            
            for result in filtered[:max_results]:
                try:
                    url = result["url"]
                    
                    # Safety check
                    if not self.filter.is_safe_url(url):
                        continue
                    
                    # Extract full content
                    content = self.extractor.extract_with_fallback(
                        url,
                        result["snippet"]
                    )
                    
                    snippet = InternetSnippet(
                        url=url,
                        title=result["title"],
                        snippet=result["snippet"],
                        content=content,
                        domain=result["domain"],
                        timestamp=datetime.now().isoformat()
                    )
                    
                    snippets.append(snippet)
                    
                except Exception as e:
                    logger.warning(f"Error processing result {url}: {e}")
                    continue
            
            search_time = time.time() - start_time
            
            logger.info(f"✅ Internet search completed: {len(snippets)} snippets in {search_time:.2f}s")
            
            return InternetSearchResult(
                query=query,
                snippets=snippets,
                success=True,
                search_time=search_time,
                total_results_found=len(raw_results)
            )
            
        except Exception as e:
            logger.error(f"❌ Internet search failed: {e}")
            return InternetSearchResult(
                query=query,
                snippets=[],
                success=False,
                error=str(e),
                search_time=time.time() - start_time
            )
    
    def health_check(self) -> dict:
        """Check if internet service is healthy"""
        
        has_gcp_config = bool(self.config.gcp_project_id)
        
        vertex_ai_status = "not_configured"
        if has_gcp_config:
            try:
                # Try to access Vertex AI client
                if self.search_engine.client:
                    vertex_ai_status = "healthy"
                else:
                    vertex_ai_status = "initialization_failed"
            except Exception as e:
                vertex_ai_status = f"error: {str(e)}"
        
        return {
            "status": "healthy" if vertex_ai_status == "healthy" else vertex_ai_status,
            "service": "vertex_ai_grounding",
            "gcp_project": self.config.gcp_project_id or "not_configured",
            "gcp_location": self.config.gcp_location,
            "grounding_enabled": self.config.enable_grounding,
            "whitelist_size": len(self.config.whitelisted_domains),
            "max_results": self.config.max_results
        }


# Singleton
_client = None

def get_internet_client() -> InternetServiceClient:
    """Get global internet service client"""
    global _client
    if _client is None:
        _client = InternetServiceClient()
    return _client


# Convenience function
def search_internet(query: str, max_results: int = None) -> InternetSearchResult:
    """
    Quick search function.
    
    Args:
        query: Search query
        max_results: Max results
        
    Returns:
        InternetSearchResult
    """
    client = get_internet_client()
    return client.search(query, max_results)     snippets=[],
                success=False,
                error=str(e),
                search_time=time.time() - start_time
            )
    
    def health_check(self) -> dict:
        """Check if internet service is healthy"""
        
        has_credentials = bool(
            self.config.pse_api_key and 
            self.config.pse_engine_id
        )
        
        return {
            "status": "healthy" if has_credentials else "no_credentials",
            "pse_configured": has_credentials,
            "whitelist_size": len(self.config.whitelisted_domains),
            "max_results": self.config.max_results
        }


# Singleton
_client = None

def get_internet_client() -> InternetServiceClient:
    """Get global internet service client"""
    global _client
    if _client is None:
        _client = InternetServiceClient()
    return _client


# Convenience function
def search_internet(query: str, max_results: int = None) -> InternetSearchResult:
    """
    Quick search function.
    
    Args:
        query: Search query
        max_results: Max results
        
    Returns:
        InternetSearchResult
    """
    client = get_internet_client()
    return client.search(query, max_results)