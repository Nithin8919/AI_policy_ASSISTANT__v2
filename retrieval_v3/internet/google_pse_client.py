# Google Programmable Search Engine client

"""
Google PSE Client - Google Programmable Search Engine integration
Searches the web for current information
"""

import os
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class WebResult:
    """Single web search result"""
    title: str
    url: str
    snippet: str
    source: str
    rank: int


class GooglePSEClient:
    """Client for Google Programmable Search Engine API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None
    ):
        """
        Initialize Google PSE client
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            search_engine_id: Search engine ID (or set GOOGLE_SEARCH_ENGINE_ID)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = search_engine_id or os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        site_restrict: Optional[str] = None,
        date_restrict: Optional[str] = None
    ) -> List[WebResult]:
        """
        Search the web using Google PSE
        
        Args:
            query: Search query
            num_results: Number of results (max 10 per request)
            site_restrict: Restrict to specific site (e.g., "gov.in")
            date_restrict: Date restriction (e.g., "d7" for last 7 days)
            
        Returns:
            List of WebResult objects
        """
        if not self.api_key or not self.search_engine_id:
            print("Warning: Google PSE credentials not set, returning empty results")
            return []
        
        try:
            # Build parameters
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'num': min(num_results, 10)  # API limit
            }
            
            if site_restrict:
                params['siteSearch'] = site_restrict
                params['siteSearchFilter'] = 'i'  # Include
            
            if date_restrict:
                params['dateRestrict'] = date_restrict
            
            # Make request
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse results
            data = response.json()
            results = []
            
            for i, item in enumerate(data.get('items', []), 1):
                results.append(WebResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source=self._extract_domain(item.get('link', '')),
                    rank=i
                ))
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Google PSE search failed: {e}")
            return []
        except Exception as e:
            print(f"Error parsing search results: {e}")
            return []
    
    def search_government_sites(
        self,
        query: str,
        num_results: int = 10
    ) -> List[WebResult]:
        """
        Search only government websites
        
        Args:
            query: Search query
            num_results: Number of results
            
        Returns:
            Results from .gov.in domains
        """
        return self.search(
            query=query,
            num_results=num_results,
            site_restrict="gov.in"
        )
    
    def search_recent(
        self,
        query: str,
        days: int = 30,
        num_results: int = 10
    ) -> List[WebResult]:
        """
        Search recent results only
        
        Args:
            query: Search query
            days: Number of days back
            num_results: Number of results
            
        Returns:
            Recent web results
        """
        return self.search(
            query=query,
            num_results=num_results,
            date_restrict=f"d{days}"
        )
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return url


# Convenience function
def google_search(
    query: str,
    num_results: int = 10,
    api_key: Optional[str] = None
) -> List[WebResult]:
    """Quick Google search"""
    client = GooglePSEClient(api_key=api_key)
    return client.search(query, num_results)


if __name__ == "__main__":
    print("Google PSE Client")
    print("=" * 60)
    print("\nSet environment variables:")
    print("  export GOOGLE_API_KEY='your-api-key'")
    print("  export GOOGLE_SEARCH_ENGINE_ID='your-engine-id'")
    print("\nExample usage:")
    print("""
from retrieval_v3.internet import GooglePSEClient

client = GooglePSEClient()

# General search
results = client.search("latest education policies India", num_results=5)

# Government sites only
gov_results = client.search_government_sites("RTE Act amendments")

# Recent results
recent = client.search_recent("education news", days=7)

for result in results:
    print(f"{result.title}")
    print(f"  {result.url}")
    print(f"  {result.snippet}")
""")
