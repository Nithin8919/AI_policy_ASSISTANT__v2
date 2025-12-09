"""
API endpoint for generating signed PDF URLs.

GET /api/pdf-url?doc_id=<doc_id>
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from google.cloud.exceptions import NotFound

from retrieval_v3.services.gcs_service import get_gcs_service
from .responses import PdfUrlResponse
from retrieval_v3.utils.pdf_utils import doc_id_to_pdf_filename

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pdf-url", response_model=PdfUrlResponse)
async def get_pdf_url(
    doc_id: str = Query(
        ..., 
        description="Document ID from Qdrant (e.g., '2018se_ms70')",
        example="2018se_ms70"
    ),
    expiration_minutes: int = Query(
        60,
        description="URL expiration time in minutes",
        ge=5,
        le=1440  # Max 24 hours
    ),
    source_hint: str = Query(
        None,
        description="Optional source/filename hint from citation metadata"
    )
):
    """
    Generate a signed GCS URL for PDF access.
    
    This endpoint:
    1. Converts the doc_id to the actual PDF filename (e.g., 2018se_ms70 → 2018SE_MS70.PDF)
    2. Tries source_hint if provided (may contain actual GCS path)
    3. Verifies the PDF exists in GCS
    4. Generates a v4 signed URL with configurable expiration
    
    Args:
        doc_id: Normalized document ID from Qdrant
        expiration_minutes: How long the URL should remain valid
        source_hint: Optional source/filename from citation metadata
        
    Returns:
        PdfUrlResponse with signedUrl and expiration timestamp
        
    Raises:
        404: PDF not found in GCS bucket
        500: GCS service error
    """
    try:
        logger.info(f"📄 PDF URL request for doc_id='{doc_id}'")
        if source_hint:
            logger.info(f"   Source hint: '{source_hint}'")
        
        # Get GCS service
        gcs_service = get_gcs_service()
        
        # Generate signed URL with source hint
        signed_url, expiration = gcs_service.generate_signed_url(
            doc_id=doc_id,
            expiration_minutes=expiration_minutes,
            source_hint=source_hint
        )
        
        # Get the PDF filename for response
        pdf_filename = doc_id_to_pdf_filename(doc_id)
        
        response = PdfUrlResponse(
            signedUrl=signed_url,
            expiresAt=expiration.isoformat() + 'Z',  # ISO format with Z suffix
            doc_id=doc_id,
            pdf_filename=pdf_filename
        )
        
        logger.info(f"✅ Generated PDF URL for '{pdf_filename}'")
        return response
    
    except NotFound as e:
        logger.error(f"PDF not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"PDF not found for doc_id '{doc_id}'. Expected filename: {doc_id_to_pdf_filename(doc_id)}"
        )
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="GCS service not properly configured. Please check GCS_BUCKET_NAME environment variable."
        )
    
    except Exception as e:
        logger.error(f"Error generating PDF URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF URL: {str(e)}"
        )
