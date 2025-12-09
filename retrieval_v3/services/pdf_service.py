"""
PDF text extraction and snippet location service.

Handles:
- On-demand PDF text extraction using pdfplumber
- Page-by-page snippet location with early termination
- Text normalization for robust matching
"""

import io
import logging
from typing import Optional, Dict
from functools import lru_cache

import pdfplumber

from retrieval_v3.utils.pdf_utils import normalize_text

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF text extraction and snippet location."""
    
    def __init__(self):
        """Initialize PDF service."""
        logger.info("PDF Service initialized")
    
    def locate_snippet_in_pdf(
        self, 
        pdf_bytes: bytes, 
        snippet: str,
        doc_id: Optional[str] = None
    ) -> Dict:
        """
        Locate a text snippet within a PDF document.
        
        Uses page-by-page extraction with early termination for performance.
        
        Args:
            pdf_bytes: PDF file bytes
            snippet: Text snippet to locate
            doc_id: Optional doc_id for logging
            
        Returns:
            Dict with keys:
                - page: int (1-indexed page number where found, or None)
                - found: bool
                - normalized_snippet: str
                - total_pages: int
                - match_confidence: str ('exact' or 'none')
        """
        doc_label = doc_id or "PDF"
        logger.info(f"Locating snippet in {doc_label} (snippet length: {len(snippet)} chars)")
        
        # Normalize the snippet for matching
        normalized_snippet = normalize_text(snippet)
        
        if not normalized_snippet:
            logger.warning("Empty snippet after normalization")
            return {
                'page': None,
                'found': False,
                'normalized_snippet': '',
                'total_pages': 0,
                'match_confidence': 'none',
                'error': 'Empty snippet provided'
            }
        
        try:
            # Open PDF from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"📄 PDF has {total_pages} pages")
                
                # Search page by page (early termination)
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text from page
                    page_text = page.extract_text()
                    
                    if not page_text:
                        logger.debug(f"Page {page_num}: No text extracted (might be scanned)")
                        continue
                    
                    # Normalize page text
                    normalized_page_text = normalize_text(page_text)
                    
                    # Strategy 1: Exact Normalized Match
                    if normalized_snippet in normalized_page_text:
                        logger.info(f"✅ Snippet found on page {page_num}/{total_pages} (Exact Match)")
                        return {
                            'page': page_num,
                            'found': True,
                            'normalized_snippet': normalized_snippet,
                            'total_pages': total_pages,
                            'match_confidence': 'exact'
                        }
                    
                    # Strategy 2: Partial Match (First 50 chars)
                    # Often the beginning of a citation is consistent even if the end is cut off or different
                    snippet_start = normalized_snippet[:50]
                    if len(snippet_start) > 20 and snippet_start in normalized_page_text:
                        logger.info(f"✅ Snippet found on page {page_num}/{total_pages} (Partial Start Match)")
                        return {
                            'page': page_num,
                            'found': True,
                            'normalized_snippet': snippet_start, # Return what was found
                            'total_pages': total_pages,
                            'match_confidence': 'medium'
                        }

                    # Strategy 3: Token Overlap (Bag of Words)
                    # If > 70% of unique significant words in snippet are present in page
                    snippet_tokens = set(word for word in normalized_snippet.split() if len(word) > 3)
                    if len(snippet_tokens) > 5:
                        page_tokens = set(normalized_page_text.split())
                        common_tokens = snippet_tokens.intersection(page_tokens)
                        overlap_ratio = len(common_tokens) / len(snippet_tokens)
                        
                        if overlap_ratio > 0.7:
                            logger.info(f"✅ Snippet found on page {page_num}/{total_pages} (Token Overlap: {overlap_ratio:.2f})")
                            return {
                                'page': page_num,
                                'found': True,
                                'normalized_snippet': normalized_snippet,
                                'total_pages': total_pages,
                                'match_confidence': 'low'
                            }
                    
                    # Log progress every 10 pages
                    if page_num % 10 == 0:
                        logger.debug(f"Searched {page_num}/{total_pages} pages...")
                
                # If not found, return page 1 but indicate not found
                # This ensures the viewer opens even if snippet isn't located
                logger.warning(f"❌ Snippet NOT found in {total_pages} pages. Defaulting to page 1.")
                return {
                    'page': 1,
                    'found': False, 
                    'normalized_snippet': normalized_snippet,
                    'total_pages': total_pages,
                    'match_confidence': 'none',
                    'error': 'Snippet not found, defaulted to page 1'
                }
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
            return {
                'page': None,
                'found': False,
                'normalized_snippet': normalized_snippet,
                'total_pages': 0,
                'match_confidence': 'none',
                'error': f'PDF processing error: {str(e)}'
            }
    
    def extract_page_text(self, pdf_bytes: bytes, page_num: int) -> Optional[str]:
        """
        Extract text from a specific page.
        
        Args:
            pdf_bytes: PDF file bytes
            page_num: Page number (1-indexed)
            
        Returns:
            Extracted text or None if error
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            
            with pdfplumber.open(pdf_file) as pdf:
                if page_num < 1 or page_num > len(pdf.pages):
                    logger.error(f"Invalid page number: {page_num} (total pages: {len(pdf.pages)})")
                    return None
                
                page = pdf.pages[page_num - 1]  # Convert to 0-indexed
                text = page.extract_text()
                
                return text
        
        except Exception as e:
            logger.error(f"Error extracting page {page_num}: {e}")
            return None
    
    def get_page_count(self, pdf_bytes: bytes) -> int:
        """
        Get the total number of pages in a PDF.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            Number of pages
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            
            with pdfplumber.open(pdf_file) as pdf:
                return len(pdf.pages)
        
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return 0


# Global singleton instance
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    """
    Get or create the global PDF service instance.
    
    Returns:
        PDFService singleton
    """
    global _pdf_service
    
    if _pdf_service is None:
        _pdf_service = PDFService()
    
    return _pdf_service
