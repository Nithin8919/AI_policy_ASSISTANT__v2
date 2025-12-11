"""
Vertex AI Grounding Integration
================================
Uses Vertex AI's built-in grounding feature to search the web via Google Search.
Clean, GCP-native, production-ready.
"""

import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse

from .config import get_internet_config

logger = logging.getLogger(__name__)


class VertexAISearchEngine:
    """
    Vertex AI search with Google Search grounding.
    GCP native, uses Gemini with grounding enabled.
    """
    
    def __init__(self):
        self.config = get_internet_config()
        self._client = None
        self._model = None
    
    @property
    def client(self):
        """Lazy load Vertex AI client"""
        if self._client is None:
            try:
                import vertexai
                from vertexai.preview.generative_models import GenerativeModel
                
                # Initialize Vertex AI
                vertexai.init(
                    project=self.config.gcp_project_id,
                    location=self.config.gcp_location
                )
                
                self._client = vertexai
                logger.info(f"✅ Vertex AI initialized: {self.config.gcp_project_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vertex AI: {e}")
                self._client = None
        
        return self._client
    
    @property
    def model(self):
        """Lazy load Gemini model with grounding"""
        if self._model is None and self.client:
            try:
                from vertexai.preview.generative_models import GenerativeModel, Tool
                from vertexai.preview import grounding
                
                # Create grounding tool
                grounding_tool = Tool.from_google_search_retrieval(
                    grounding.GoogleSearchRetrieval()
                )
                
                # Initialize model with grounding
                self._model = GenerativeModel(
                    "gemini-2.5-flash",  # Fast model for search
                    tools=[grounding_tool]
                )
                
                logger.info("✅ Gemini model initialized with grounding")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini model: {e}")
                self._model = None
        
        return self._model
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search using Vertex AI grounding.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of formatted search results
        """
        
        if not self.config.gcp_project_id:
            logger.warning("❌ GCP project ID not configured")
            return []
        
        try:
            start_time = time.time()
            
            # Build search prompt
            search_prompt = f"""Search the web for: {query}

Provide {num_results} relevant, recent results about this topic.
Focus on:
- Government and official sources
- Educational institutions
- International organizations
- Recent news from reputable outlets

For each result, include the source URL and a brief summary."""
            
            # Generate with grounding
            response = self.model.generate_content(
                search_prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for factual search
                    "max_output_tokens": 2048,
                }
            )
            
            search_time = time.time() - start_time
            
            # Extract grounding metadata
            results = self._extract_grounding_citations(response)
            
            logger.info(f"✅ Vertex AI grounding returned {len(results)} results in {search_time:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vertex AI search error: {e}")
            return []
    
    def _extract_grounding_citations(self, response) -> List[Dict]:
        """
        Extract citations from grounding metadata.
        
        Args:
            response: Vertex AI response object
            
        Returns:
            List of formatted citations
        """
        
        results = []
        
        try:
            # Check if grounding metadata exists
            if not hasattr(response, 'candidates') or not response.candidates:
                logger.warning("No candidates in response")
                return results
            
            candidate = response.candidates[0]
            
            # Extract grounding metadata
            if hasattr(candidate, 'grounding_metadata'):
                grounding_metadata = candidate.grounding_metadata
                
                # Get grounding supports (citations)
                if hasattr(grounding_metadata, 'grounding_supports'):
                    for support in grounding_metadata.grounding_supports:
                        try:
                            # Extract citation info
                            if hasattr(support, 'segment'):
                                segment = support.segment
                                
                                # Get grounding chunk indices
                                if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                                    text_snippet = response.text[segment.start_index:segment.end_index]
                                else:
                                    text_snippet = ""
                                
                                # Get source URIs
                                if hasattr(support, 'grounding_chunk_indices'):
                                    for chunk_idx in support.grounding_chunk_indices:
                                        # Get the actual chunk
                                        if hasattr(grounding_metadata, 'grounding_chunks'):
                                            chunks = grounding_metadata.grounding_chunks
                                            if chunk_idx < len(chunks):
                                                chunk = chunks[chunk_idx]
                                                
                                                # Extract web info
                                                if hasattr(chunk, 'web'):
                                                    web = chunk.web
                                                    url = getattr(web, 'uri', '')
                                                    title = getattr(web, 'title', 'Untitled')
                                                    
                                                    # Filter by whitelist
                                                    if not self.config.is_domain_allowed(url):
                                                        continue
                                                    
                                                    domain = urlparse(url).netloc
                                                    
                                                    results.append({
                                                        "url": url,
                                                        "title": title,
                                                        "snippet": text_snippet[:200] if text_snippet else "",
                                                        "domain": domain
                                                    })
                        
                        except Exception as e:
                            logger.debug(f"Error extracting support: {e}")
                            continue
                
                # Alternative: extract from web retrieval chunks directly
                if hasattr(grounding_metadata, 'web_search_queries'):
                    logger.debug(f"Web search queries used: {grounding_metadata.web_search_queries}")
            
            # If no grounding metadata, try to extract URLs from text
            if not results:
                logger.warning("No grounding metadata found, attempting to extract URLs from text")
                results = self._extract_urls_from_text(response.text)
            
        except Exception as e:
            logger.error(f"Error extracting grounding citations: {e}")
        
        return results[:self.config.max_results]
    
    def _extract_urls_from_text(self, text: str) -> List[Dict]:
        """
        Fallback: Extract URLs mentioned in generated text.
        
        Args:
            text: Generated response text
            
        Returns:
            List of extracted URLs
        """
        import re
        
        results = []
        
        # Find URLs in text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            if self.config.is_domain_allowed(url):
                domain = urlparse(url).netloc
                results.append({
                    "url": url,
                    "title": f"Source from {domain}",
                    "snippet": "",
                    "domain": domain
                })
        
        return results
    
    def format_results(self, raw_results: List[Dict]) -> List[Dict]:
        """
        Format raw results to our schema.
        
        Args:
            raw_results: Raw results from Vertex AI
            
        Returns:
            List of formatted result dicts
        """
        formatted = []
        
        for item in raw_results:
            try:
                url = item.get("url", "")
                
                # Filter by whitelist
                if not self.config.is_domain_allowed(url):
                    continue
                
                formatted.append({
                    "url": url,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "domain": item.get("domain", "")
                })
                
            except Exception as e:
                logger.warning(f"Error formatting result: {e}")
                continue
        
        return formatted


# Singleton
_search_engine = None

def get_search_engine() -> VertexAISearchEngine:
    """Get global search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = VertexAISearchEngine()
    return _search_engine