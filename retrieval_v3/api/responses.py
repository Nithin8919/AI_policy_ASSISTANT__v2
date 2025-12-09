"""Pydantic response models for PDF viewer API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class PdfUrlResponse(BaseModel):
    """Response containing a signed GCS URL for PDF access."""
    
    signedUrl: str = Field(
        ..., 
        description="Signed GCS URL for temporary PDF access"
    )
    expiresAt: str = Field(
        ..., 
        description="ISO timestamp when the signed URL expires"
    )
    doc_id: str = Field(
        ...,
        description="Original doc_id from request"
    )
    pdf_filename: str = Field(
        ...,
        description="Actual PDF filename in GCS"
    )


class LocateSnippetResponse(BaseModel):
    """Response containing the page number where a snippet was found."""
    
    page: Optional[int] = Field(
        None, 
        description="Page number where snippet was found (1-indexed), null if not found"
    )
    found: bool = Field(
        ..., 
        description="Whether the snippet was successfully located"
    )
    normalizedSnippet: str = Field(
        ..., 
        description="The normalized version of the snippet used for matching"
    )
    matchConfidence: Optional[str] = Field(
        "exact", 
        description="Confidence level of the match: 'exact', 'fuzzy', or 'none'"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if snippet was not found or processing failed"
    )
    totalPages: Optional[int] = Field(
        None,
        description="Total number of pages in the PDF"
    )
