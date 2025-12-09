"""Pydantic request models for PDF viewer API endpoints."""

from pydantic import BaseModel, Field


class LocateSnippetRequest(BaseModel):
    """Request to locate a text snippet within a PDF."""
    
    doc_id: str = Field(
        ..., 
        description="Document ID from Qdrant (e.g., '2018se_ms70')",
        example="2018se_ms70"
    )
    snippet: str = Field(
        ..., 
        description="Text snippet to locate in the PDF",
        min_length=10,
        example="Section 12 of the RTE Act establishes..."
    )
