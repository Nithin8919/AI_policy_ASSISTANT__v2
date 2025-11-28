# Page Cleaner - cleans HTML → text

"""
Page Cleaner - Extract clean text from HTML
Removes scripts, styles, navigation, ads
"""

import re
from typing import Optional


class PageCleaner:
    """Clean HTML and extract readable text"""
    
    def __init__(self):
        """Initialize cleaner"""
        pass
    
    def clean_html(self, html: str) -> str:
        """
        Extract clean text from HTML
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned text
        """
        # Try BeautifulSoup if available
        try:
            from bs4 import BeautifulSoup
            return self._clean_with_bs4(html)
        except ImportError:
            # Fallback to regex
            return self._clean_with_regex(html)
    
    def _clean_with_bs4(self, html: str) -> str:
        """Clean using BeautifulSoup"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _clean_with_regex(self, html: str) -> str:
        """Fallback regex-based cleaning"""
        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = self._decode_html_entities(text)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _decode_html_entities(self, text: str) -> str:
        """Decode common HTML entities"""
        entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&rsquo;': "'",
            '&lsquo;': "'",
            '&rdquo;': '"',
            '&ldquo;': '"',
        }
        
        for entity, char in entities.items():
            text = text.replace(entity, char)
        
        return text
    
    def extract_main_content(self, html: str) -> str:
        """
        Try to extract main content area
        
        Args:
            html: Raw HTML
            
        Returns:
            Main content text
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for main content tags
            main_content = None
            
            # Try common content containers
            for tag_name in ['main', 'article']:
                main_content = soup.find(tag_name)
                if main_content:
                    break
            
            # Try common class names
            if not main_content:
                for class_name in ['content', 'main-content', 'article-content', 'post-content']:
                    main_content = soup.find(class_=class_name)
                    if main_content:
                        break
            
            # If found, clean that section
            if main_content:
                return self._clean_with_bs4(str(main_content))
            else:
                # Fall back to full page
                return self.clean_html(html)
                
        except ImportError:
            # No BeautifulSoup, use full page
            return self.clean_html(html)


# Convenience function
def clean_html(html: str) -> str:
    """Quick HTML cleaning"""
    cleaner = PageCleaner()
    return cleaner.clean_html(html)


if __name__ == "__main__":
    print("Page Cleaner")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.internet import PageCleaner

cleaner = PageCleaner()

# Clean HTML
html = "<html><body><p>Hello world</p></body></html>"
text = cleaner.clean_html(html)
print(text)  # "Hello world"

# Extract main content
text = cleaner.extract_main_content(html)
""")
    
    # Demo
    sample_html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <nav>Navigation here</nav>
        <main>
            <h1>Education Policy Update</h1>
            <p>This is the main content about education policy.</p>
        </main>
        <footer>Footer content</footer>
    </body>
    </html>
    """
    
    cleaner = PageCleaner()
    cleaned = cleaner.clean_html(sample_html)
    print(f"\nCleaned text: {cleaned}")