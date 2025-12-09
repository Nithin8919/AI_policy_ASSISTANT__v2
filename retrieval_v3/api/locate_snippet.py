"""
API endpoint for temporarily returning the raw PDF instead of locating a snippet.

POST /api/locate-snippet
"""

import io
import logging
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud.exceptions import NotFound

from retrieval_v3.services.gcs_service import get_gcs_service
from .requests import LocateSnippetRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/locate-snippet")
async def locate_snippet(request: LocateSnippetRequest):
    """
    Temporarily return the raw PDF instead of locating a snippet.

    This flow only fetches the PDF from GCS and streams it back so we can
    verify PDF delivery before enabling snippet search.

    Raises:
        404: PDF not found in GCS
        500: Configuration errors
    """
    start_time = time.time()

    try:
        logger.info(
            f"📄 PDF fetch request for doc_id='{request.doc_id}' "
            f"(snippet length: {len(request.snippet)} chars)"
        )

        # Get GCS service and fetch PDF bytes
        gcs_service = get_gcs_service()
        logger.info("📥 Fetching PDF from GCS...")
        fetch_start = time.time()
        pdf_bytes = gcs_service.fetch_pdf_bytes(request.doc_id)
        fetch_time = time.time() - fetch_start

        logger.info(
            f"✅ Fetched PDF in {fetch_time:.2f}s ({len(pdf_bytes):,} bytes). "
            f"Total time: {time.time() - start_time:.2f}s"
        )

        # Stream the PDF back to the client
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={request.doc_id}.pdf",
            },
        )

    except NotFound as e:
        logger.error(f"PDF not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"PDF not found for doc_id '{request.doc_id}'"
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="GCS service not properly configured"
        )

    except Exception as e:
        logger.error(f"Error fetching PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch PDF: {str(e)}"
        )
