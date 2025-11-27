"""
Internet Service Configuration
================================
Settings for Vertex AI Grounding and content extraction.
"""

import os
from typing import Set
from dataclasses import dataclass


@dataclass
class InternetConfig:
    """Internet service configuration"""
    
    # Vertex AI settings (GCP Native)
    gcp_project_id: str = None
    gcp_location: str = "us-central1"
    gcp_credentials_path: str = None  # Optional: path to service account JSON
    
    # Vertex AI Search settings
    enable_grounding: bool = True
    grounding_source: str = "google_search"  # or "vertex_ai_search"
    
    # Search settings
    max_results: int = 5
    search_timeout: float = 5.0  # Vertex AI can be slower
    
    # Extraction settings
    extract_timeout: float = 2.0
    max_content_length: int = 3000  # chars per snippet
    
    # Domain whitelist (trusted sources only)
    whitelisted_domains: Set[str] = None
    
    # Retry settings
    max_retries: int = 2
    retry_delay: float = 0.5
    
    def __post_init__(self):
        # Load from environment
        if self.gcp_project_id is None:
            self.gcp_project_id = os.getenv("GCP_PROJECT_ID", "")
        
        if self.gcp_credentials_path is None:
            self.gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        
        # Default whitelist (trusted education/policy sources)
        if self.whitelisted_domains is None:
            self.whitelisted_domains = {
                # Indian Government
                "gov.in",
                "nic.in",
                "india.gov.in",
                "education.gov.in",
                "mhrd.gov.in",
                "apgovern.in",
                
                # International Organizations
                "unesco.org",
                "worldbank.org",
                "oecd.org",
                "unicef.org",
                "who.int",
                
                # Research/Academia
                "edu",
                "ac.in",
                "ac.uk",
                "nih.gov",
                "ncbi.nlm.nih.gov",
                
                # News (reputable)
                "thehindu.com",
                "indianexpress.com",
                "economist.com",
                "reuters.com",
                
                # Education-specific
                "edudel.nic.in",
                "ncert.nic.in",
                "nios.ac.in",
                "ugc.ac.in",
                "aicte-india.org",
            }
    
    def is_domain_allowed(self, url: str) -> bool:
        """Check if domain is whitelisted"""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc.lower()
            
            # Check exact match
            if domain in self.whitelisted_domains:
                return True
            
            # Check if any whitelisted domain is a suffix
            for allowed in self.whitelisted_domains:
                if domain.endswith(f".{allowed}") or domain == allowed:
                    return True
            
            return False
        except:
            return False


# Default instance
DEFAULT_CONFIG = InternetConfig()


def get_internet_config() -> InternetConfig:
    """Get internet service configuration"""
    return DEFAULT_CONFIG
        
        # Default whitelist (trusted education/policy sources)
        if self.whitelisted_domains is None:
            self.whitelisted_domains = {
                # Indian Government
                "gov.in",
                "nic.in",
                "india.gov.in",
                "education.gov.in",
                "mhrd.gov.in",
                "apgovern.in",
                
                # International Organizations
                "unesco.org",
                "worldbank.org",
                "oecd.org",
                "unicef.org",
                "who.int",
                
                # Research/Academia
                "edu",
                "ac.in",
                "ac.uk",
                "nih.gov",
                "ncbi.nlm.nih.gov",
                
                # News (reputable)
                "thehindu.com",
                "indianexpress.com",
                "economist.com",
                "reuters.com",
                
                # Education-specific
                "edudel.nic.in",
                "ncert.nic.in",
                "nios.ac.in",
                "ugc.ac.in",
                "aicte-india.org",
            }
    
    def is_domain_allowed(self, url: str) -> bool:
        """Check if domain is whitelisted"""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc.lower()
            
            # Check exact match
            if domain in self.whitelisted_domains:
                return True
            
            # Check if any whitelisted domain is a suffix
            for allowed in self.whitelisted_domains:
                if domain.endswith(f".{allowed}") or domain == allowed:
                    return True
            
            return False
        except:
            return False


# Default instance
DEFAULT_CONFIG = InternetConfig()


def get_internet_config() -> InternetConfig:
    """Get internet service configuration"""
    return DEFAULT_CONFIG