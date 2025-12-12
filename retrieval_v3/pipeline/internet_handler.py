# Internet Search Handler

"""
Handles internet search integration
"""

import logging
import time
from typing import List, Optional

from .models import RetrievalResult
from internet.google_search_client import GoogleSearchClient

logger = logging.getLogger(__name__)


class InternetSearchHandler:
    """Handles internet search integration"""
    
    def __init__(self, google_search_client: Optional[GoogleSearchClient] = None):
        self.google_search_client = google_search_client
    
    def should_enable_internet(
        self,
        plan,
        custom_plan: Optional[dict] = None
    ) -> bool:
        """
        Determine if internet search should be enabled
        
        Priority:
        1. Explicit custom_plan override (user preference)
        2. Plan automatic detection
        """
        internet_enabled = False
        
        # Priority 1: Check custom_plan for explicit override (user preference takes precedence)
        if custom_plan:
            if custom_plan.get('internet_enabled') is not None:
                internet_enabled = custom_plan.get('internet_enabled')
                logger.info(f"🌐 Internet {'enabled' if internet_enabled else 'disabled'} via custom_plan override")
            elif custom_plan.get('use_internet') is not None:
                internet_enabled = custom_plan.get('use_internet')
                logger.info(f"🌐 Internet {'enabled' if internet_enabled else 'disabled'} via custom_plan (legacy)")
        
        # Priority 2: Check if plan says internet is needed (automatic detection) - only if not explicitly set
        if internet_enabled is False and plan.use_internet:
            internet_enabled = True
            logger.info(f"🌐 Internet enabled via automatic detection (query interpretation)")
        
        return internet_enabled
    
    def search(
        self,
        query: str,
        trace_steps: List[str]
    ) -> List[RetrievalResult]:
        """
        Perform internet search and convert to RetrievalResult objects
        
        Returns:
            List of RetrievalResult objects from internet search
        """
        internet_results = []
        
        if not self.google_search_client:
            return internet_results
        
        trace_steps.append("Searching internet for latest policies...")
        logger.info(f"🌐 Internet search enabled for: {query}")
        
        try:
            # Optimized timeout: reduced from 20s to 10s for faster failure detection
            web_raw_results = self.google_search_client.search(query, timeout=10.0)
            
            # Convert to RetrievalResult objects
            for i, res in enumerate(web_raw_results):
                internet_results.append(RetrievalResult(
                    chunk_id=f"web_{i}_{int(time.time())}",
                    doc_id=f"web_{i}",
                    content=f"{res['title']}\n{res['snippet']}",
                    score=0.85 - (i * 0.05), # Decay score for web results
                    vertical="internet",
                    metadata={
                        'title': res['title'],
                        'url': res['url'],
                        'source': 'Google Search',
                        'is_web': True
                    },
                    rewrite_source="original_query",
                    hop_number=1
                ))
            logger.info(f"🌐 Found {len(internet_results)} web results")
        except Exception as e:
            logger.error(f"Internet search failed: {e}")
        
        return internet_results
