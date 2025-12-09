"""
Google Cloud Storage service for PDF access.

Handles:
- Generating signed URLs for frontend PDF display
- Fetching PDF bytes for text extraction
- Converting doc_id to GCS PDF filenames
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

from google.cloud import storage
from google.cloud.exceptions import NotFound

from retrieval_v3.utils.pdf_utils import doc_id_to_pdf_filename

logger = logging.getLogger(__name__)


class GCSService:
    """Service for Google Cloud Storage operations."""
    
    def __init__(
        self, 
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize GCS service.
        
        Args:
            bucket_name: GCS bucket name (defaults to env var GCS_BUCKET_NAME)
            credentials_path: Path to service account JSON (defaults to GOOGLE_APPLICATION_CREDENTIALS env var)
        """
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME')
        
        if not self.bucket_name:
            raise ValueError(
                "GCS bucket name must be provided via bucket_name parameter "
                "or GCS_BUCKET_NAME environment variable"
            )
        
        # Initialize storage client
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Uses GOOGLE_APPLICATION_CREDENTIALS env var or Application Default Credentials
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(self.bucket_name)
        
        logger.info(f"GCS Service initialized with bucket: {self.bucket_name}")
    
    def find_pdf_in_bucket(self, pdf_filename: str) -> Optional[str]:
        """
        Recursively search for a PDF file in the bucket with flexible matching.
        
        Tries multiple strategies:
        1. Exact filename match (case-insensitive)
        2. Filename without numeric prefix (e.g., '5294663_file.pdf' → 'file.pdf')
        3. Partial filename match
        
        Args:
            pdf_filename: The PDF filename to search for (e.g., '2025SE_MS26_E.PDF')
            
        Returns:
            Full GCS path if found, None otherwise
        """
        logger.info(f"🔍 Searching for '{pdf_filename}' in bucket recursively...")
        
        # Normalize search filename (case-insensitive)
        search_name_lower = pdf_filename.lower()
        
        # Extract filename without numeric prefix for additional search
        # e.g., '5294663_SALIENT_FEATURES.PDF' → 'SALIENT_FEATURES.PDF'
        filename_without_prefix = None
        if '_' in pdf_filename:
            parts = pdf_filename.split('_', 1)
            if parts[0].isdigit():
                filename_without_prefix = parts[1].lower()
                logger.info(f"   Also searching for variant without numeric prefix: '{filename_without_prefix}'")
        
        # List all blobs in the bucket
        blobs = self.client.list_blobs(self.bucket_name)
        
        matches = []
        for blob in blobs:
            blob_name_lower = blob.name.lower()
            
            # Strategy 1: Exact match (case-insensitive)
            if blob_name_lower.endswith(search_name_lower):
                logger.info(f"✅ Found exact match at: {blob.name}")
                return blob.name
            
            # Strategy 2: Match without numeric prefix
            if filename_without_prefix and blob_name_lower.endswith(filename_without_prefix):
                logger.info(f"✅ Found match (without prefix) at: {blob.name}")
                matches.append(blob.name)
            
            # Strategy 3: Partial match (filename is contained in blob path)
            # This helps with files that might have slightly different naming
            base_search = search_name_lower.replace('.pdf', '').replace('_', '')
            base_blob = blob_name_lower.replace('.pdf', '').replace('_', '').replace('/', '')
            if base_search in base_blob and blob_name_lower.endswith('.pdf'):
                logger.info(f"   Potential partial match: {blob.name}")
                matches.append(blob.name)
        
        # Return first match if any were found
        if matches:
            best_match = matches[0]
            logger.info(f"✅ Returning best match: {best_match}")
            return best_match
        
        logger.warning(f"❌ PDF '{pdf_filename}' not found anywhere in bucket")
        return None
    
    def generate_signed_url(
        self, 
        doc_id: str, 
        expiration_minutes: int = 60,
        source_hint: Optional[str] = None
    ) -> tuple[str, datetime]:
        """
        Generate a v4 signed URL for PDF access.
        
        Args:
            doc_id: Qdrant doc_id (e.g., '2018se_ms70')
            expiration_minutes: URL validity duration in minutes
            source_hint: Optional source/filename hint from metadata
            
        Returns:
            Tuple of (signed_url, expiration_datetime)
            
        Raises:
            NotFound: If PDF doesn't exist in GCS bucket
            Exception: For other GCS errors
        """
        # Convert doc_id to PDF filename
        pdf_filename = doc_id_to_pdf_filename(doc_id)
        
        logger.info(f"Generating signed URL for doc_id='{doc_id}' -> PDF='{pdf_filename}'")
        if source_hint:
            logger.info(f"   Source hint provided: '{source_hint}'")
        
        # Try direct path first
        blob = self.bucket.blob(pdf_filename)
        
        # If not found at root, try multiple strategies
        if not blob.exists():
            logger.warning(f"PDF not found at root, trying alternative strategies...")
            full_path = None
            
            # Strategy 1: Try source hint if it looks like a path
            if source_hint and ('/' in source_hint or source_hint.lower().endswith('.pdf')):
                logger.info(f"   Trying source hint as direct path: {source_hint}")
                test_blob = self.bucket.blob(source_hint)
                if test_blob.exists():
                    logger.info(f"✅ Found PDF using source hint!")
                    full_path = source_hint
            
            # Strategy 2: Search recursively
            if not full_path:
                logger.info(f"   Searching recursively in bucket...")
                full_path = self.find_pdf_in_bucket(pdf_filename)
            
            if full_path:
                logger.info(f"📁 Found PDF at nested path: {full_path}")
                blob = self.bucket.blob(full_path)
            else:
                logger.error(f"PDF not found in GCS: {pdf_filename}")
                raise NotFound(f"PDF '{pdf_filename}' not found in bucket '{self.bucket_name}'")
        
        # Calculate expiration
        expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        
        # Generate signed URL (v4 for better security)
        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=expiration,
            method='GET',
            response_type='application/pdf'
        )
        
        logger.info(f"✅ Generated signed URL for '{pdf_filename}', expires at {expiration.isoformat()}Z")
        
        return signed_url, expiration
    
    def fetch_pdf_bytes(self, doc_id: str) -> bytes:
        """
        Fetch PDF bytes from GCS for text extraction.
        
        Args:
            doc_id: Qdrant doc_id
            
        Returns:
            PDF file bytes
            
        Raises:
            NotFound: If PDF doesn't exist
        """
        pdf_filename = doc_id_to_pdf_filename(doc_id)
        
        logger.info(f"Fetching PDF bytes for '{pdf_filename}'")
        
        blob = self.bucket.blob(pdf_filename)
        
        # If not found at root, search recursively  
        if not blob.exists():
            logger.warning(f"PDF not found at root, searching recursively...")
            full_path = self.find_pdf_in_bucket(pdf_filename)
            
            if full_path:
                logger.info(f"📁 Found PDF at nested path: {full_path}")
                blob = self.bucket.blob(full_path)
            else:
                logger.error(f"PDF not found in GCS: {pdf_filename}")
                raise NotFound(f"PDF '{pdf_filename}' not found in bucket '{self.bucket_name}'")
        
        # Download as bytes
        pdf_bytes = blob.download_as_bytes()
        
        logger.info(f"✅ Fetched {len(pdf_bytes):,} bytes for '{pdf_filename}'")
        
        return pdf_bytes
    
    def pdf_exists(self, doc_id: str) -> bool:
        """
        Check if a PDF exists in GCS.
        
        Args:
            doc_id: Qdrant doc_id
            
        Returns:
            True if PDF exists, False otherwise
        """
        pdf_filename = doc_id_to_pdf_filename(doc_id)
        blob = self.bucket.blob(pdf_filename)
        return blob.exists()


# Global singleton instance (initialized lazily)
_gcs_service: Optional[GCSService] = None


def get_gcs_service() -> GCSService:
    """
    Get or create the global GCS service instance.
    
    Returns:
        GCSService singleton
    """
    global _gcs_service
    
    if _gcs_service is None:
        _gcs_service = GCSService()
    
    return _gcs_service
