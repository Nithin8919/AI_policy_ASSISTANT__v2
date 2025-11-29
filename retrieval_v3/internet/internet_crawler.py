# Internet Crawler - fallback scraper (gov sites only)

"""
Internet Crawler - Fetch and extract content from web pages
Fallback HTML fetcher for government domains
"""

import requests
from typing import Optional
from urllib.parse import urlparse


class InternetCrawler:
    """Fetch and extract web page content"""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize crawler
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.allowed_domains = [
            'gov.in', 'nic.in', 'ac.in',  # Indian government/education
            'unesco.org', 'oecd.org',      # International education
            'ncert.nic.in', 'ncte.gov.in'  # Education bodies
        ]
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL
        
        Args:
            url: Web page URL
            
        Returns:
            HTML content or None if failed
        """
        # Check if allowed domain
        if not self._is_allowed_domain(url):
            print(f"Domain not in allowed list: {url}")
            return None
        
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Education Policy Assistant Bot)'
                }
            )
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch {url}: {e}")
            return None
    
    def fetch_and_clean(self, url: str) -> Optional[str]:
        """
        Fetch page and extract clean text
        
        Args:
            url: Web page URL
            
        Returns:
            Cleaned text content
        """
        html = self.fetch_page(url)
        if not html:
            return None
        
        # Use page cleaner
        from .page_cleaner import PageCleaner
        cleaner = PageCleaner()
        return cleaner.clean_html(html)
    
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL is from allowed domain"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check if any allowed domain is in the URL domain
            return any(allowed in domain for allowed in self.allowed_domains)
            
        except:
            return False
    
    def add_allowed_domain(self, domain: str):
        """Add a domain to allowed list"""
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)


# Convenience function
def fetch_url(url: str) -> Optional[str]:
    """Quick URL fetch"""
    crawler = InternetCrawler()
    return crawler.fetch_and_clean(url)


if __name__ == "__main__":
    print("Internet Crawler")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.internet import InternetCrawler

crawler = InternetCrawler()

# Fetch a government page
content = crawler.fetch_and_clean("https://www.education.gov.in/...")

# Add custom allowed domain
crawler.add_allowed_domain("myedu.org")

if content:
    print(content[:500])
""")
