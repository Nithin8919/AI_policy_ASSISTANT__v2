"""
PDF utility functions for filename conversion and text normalization.
"""

import re
from typing import Optional


def doc_id_to_pdf_filename(doc_id: str) -> str:
    """
    Convert Qdrant doc_id to GCS PDF filename.
    
    Handles two cases:
    1. Simple doc_id (e.g., "2018se_ms70") → Convert to uppercase + add .PDF
    2. Full GCS path (e.g., "Documents/file.pdf") → Return as-is
    
    Examples:
        "2018se_ms70" → "2018SE_MS70.PDF"
        "go_123_2023" → "GO_123_2023.PDF"
        "Documents/Data Reports/file.pdf" → "Documents/Data Reports/file.pdf"
        "path/to/document.PDF" → "path/to/document.PDF"
    
    Args:
        doc_id: Qdrant document ID (can be simple ID or full GCS path)
        
    Returns:
        PDF filename or path
    """
    if not doc_id:
        raise ValueError("doc_id cannot be empty")
    
    # If doc_id already looks like a path (contains /) or already has .pdf/.PDF extension,
    # return it as-is
    if '/' in doc_id or doc_id.lower().endswith('.pdf'):
        return doc_id
    
    # Otherwise, convert simple doc_id to uppercase and add .PDF extension
    pdf_filename = doc_id.upper() + ".PDF"
    
    return pdf_filename


def pdf_filename_to_doc_id(pdf_filename: str) -> str:
    """
    Convert GCS PDF filename back to Qdrant doc_id.
    
    Converts uppercase PDF filename to lowercase doc_id.
    
    Examples:
        "2018SE_MS70.PDF" -> "2018se_ms70"
        "GO_123_2023.PDF" -> "go_123_2023"
        "POLICY_BRIEF.PDF" -> "policy_brief"
    
    Args:
        pdf_filename: PDF filename (uppercase with .PDF extension)
        
    Returns:
        Lowercase doc_id (without extension)
    """
    if not pdf_filename:
        raise ValueError("pdf_filename cannot be empty")
    
    # Remove .PDF extension (case-insensitive) and convert to lowercase
    doc_id = pdf_filename.rsplit('.', 1)[0].lower()
    
    return doc_id


def normalize_text(text: str) -> str:
    """
    Normalize text for robust matching.
    
    Performs:
    - Convert to lowercase
    - Remove line breaks (including hyphenated line breaks)
    - Collapse multiple spaces to single space
    - Strip leading/trailing whitespace
    
    Examples:
        "Section 12 of the RTE Act" -> "section 12 of the rte act"
        "Multi-\nple   spaces" -> "multiple spaces"
        "UPPERCASE text" -> "uppercase text"
        "Line-\nbreak hyphen" -> "linebreak hyphen"
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Handle hyphenated line breaks (e.g., "word-\nbreak" -> "wordbreak")
    # Remove newline followed by hyphen, or hyphen followed by newline
    normalized = re.sub(r'-\s*\n\s*', '', normalized)  # hyphen-newline
    normalized = re.sub(r'\s*\n\s*-', '', normalized)   # newline-hyphen
    
    # Replace all whitespace (including newlines, tabs) with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


if __name__ == "__main__":
    # Test functions
    print("Testing PDF Utils")
    print("=" * 60)
    
    # Test doc_id conversion
    test_cases = [
        ("2018se_ms70", "2018SE_MS70.PDF"),
        ("go_123_2023", "GO_123_2023.PDF"),
        ("policy_brief", "POLICY_BRIEF.PDF"),
    ]
    
    print("\ndoc_id → PDF filename:")
    for doc_id, expected_pdf in test_cases:
        result = doc_id_to_pdf_filename(doc_id)
        status = "✅" if result == expected_pdf else "❌"
        print(f"{status} {doc_id} → {result} (expected: {expected_pdf})")
    
    print("\nPDF filename → doc_id:")
    for expected_doc_id, pdf_filename in test_cases:
        result = pdf_filename_to_doc_id(pdf_filename)
        status = "✅" if result == expected_doc_id else "❌"
        print(f"{status} {pdf_filename} → {result} (expected: {expected_doc_id})")
    
    # Test normalization
    print("\nText normalization:")
    norm_tests = [
        ("Section 12 of the RTE Act", "section 12 of the rte act"),
        ("Multi-\nple   spaces", "multiple spaces"),
        ("UPPERCASE text", "uppercase text"),
        ("Line-\nbreak hyphen", "linebreak hyphen"),
    ]
    
    for input_text, expected in norm_tests:
        result = normalize_text(input_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} {repr(input_text)} → {repr(result)} (expected: {repr(expected)})")











