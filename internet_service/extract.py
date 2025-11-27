"""
Content Extraction
==================
Extract clean text from web pages using trafilatura.
Fast, reliable, handles most cases.
"""

import time
import logging
from typing import Optional

import requests
from trafilatura import extract
from trafilatura.settings import use_config

from .config import get_internet_config

logger = logging.getLogger(__name__)


class ContentExtractor:
    """
    Extract clean text from URLs.
    Uses trafilatura for quality extraction.
    """
    
    def __init__(self):
        self.config = get_internet_config()
        
        # Configure trafilatura for fast extraction
        self.trafilatura_config = use_config()
        self.trafilatura_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "100")
        self.trafilatura_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "50")
    
    def extract(self, url: str) -> Optional[str]:
        """
        Extract text content from URL.
        
        Args:
            url: URL to extract from
            
        Returns:
            Extracted text or None if failed
        """
        
        try:
            # Fetch HTML
            start_time = time.time()
            
            response = requests.get(
                url,
                timeout=self.config.extract_timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PolicyBot/1.0)"
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {response.status_code}")
                return None
            
            html = response.text
            
            # Extract text
            text = extract(
                html,
                config=self.trafilatura_config,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            
            extract_time = time.time() - start_time
            
            if not text:
                logger.warning(f"No content extracted from {url}")
                return None
            
            # Truncate if too long
            if len(text) > self.config.max_content_length:
                text = text[:self.config.max_content_length] + "..."
            
            logger.debug(f"Extracted {len(text)} chars from {url} in {extract_time:.2f}s")
            
            return text
            
        except requests.Timeout:
            logger.warning(f"Timeout extracting from {url}")
            return None
        except Exception as e:
            logger.warning(f"Error extracting from {url}: {e}")
            return None
    
    def extract_with_fallback(self, url: str, snippet: str) -> str:
        """
        Extract text with fallback to snippet.
        
        Args:
            url: URL to extract from
            snippet: Fallback snippet from search
            
        Returns:
            Extracted text or snippet
        """
        
        text = self.extract(url)
        
        if text and len(text) > len(snippet):
            return text
        
        # Fallback to snippet
        logger.debug(f"Using snippet for {url}")
        return snippet


# Singleton
_extractor = None

def get_content_extractor() -> ContentExtractor:
    """Get global content extractor"""
    global _extractor
    if _extractor is None:
        _extractor = ContentExtractor()
    return _extractor