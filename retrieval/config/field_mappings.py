"""
Field Mappings Configuration
============================
Maps query filter fields to actual Qdrant payload fields across verticals.

This solves the mismatch between:
- What the query processor generates (e.g., "sections")
- What's actually in Qdrant (e.g., "section", "sections", "mentioned_sections")

CRITICAL: This configuration MUST match the ingestion metadata schema.
"""

from typing import List, Dict
from qdrant_client import models


# Field mappings by vertical
# Format: filter_field -> {vertical -> [list of payload fields to check]}
FIELD_MAPPINGS = {
    # Section filters
    "sections": {
        "legal": ["section", "sections", "mentioned_sections"],  # Check all 3 fields
        "go": ["mentioned_sections"],  # GOs only have mentioned sections
        "judicial": ["mentioned_sections"],  # Judicial docs reference sections
        "data": [],  # Data docs don't have sections
        "schemes": []  # Scheme docs don't have sections
    },
    
    # GO number filters
    "go_number": {
        "go": ["go_number"],  # Primary field for GO docs
        "legal": ["mentioned_gos"],  # Legal docs reference GOs
        "judicial": ["mentioned_gos"],  # Judicial docs reference GOs
        "data": [],
        "schemes": []
    },
    
    # Year filters (universal)
    "year": {
        "legal": ["year"],
        "go": ["year"],
        "judicial": ["year"],
        "data": ["year"],
        "schemes": ["year"]
    },
    
    # Department filters
    "department": {
        "go": ["department", "departments"],  # Can be singular or plural
        "legal": [],
        "judicial": [],
        "data": ["departments"],
        "schemes": ["departments"]
    },
    
    # Case number filters
    "case_number": {
        "judicial": ["case_number"],
        "legal": [],
        "go": [],
        "data": [],
        "schemes": []
    },
    
    # Scheme name filters
    "scheme_name": {
        "schemes": ["scheme_name"],
        "go": ["schemes", "mentioned_schemes"],
        "legal": [],
        "judicial": [],
        "data": []
    }
}


def get_mapped_fields(filter_field: str, vertical: str) -> List[str]:
    """
    Get all possible payload fields for a filter field in a vertical.
    
    Args:
        filter_field: The filter field name (e.g., "sections", "go_number")
        vertical: The vertical name (e.g., "legal", "go")
        
    Returns:
        List of payload field names to check in Qdrant.
        Empty list if field not applicable to vertical.
        
    Example:
        >>> get_mapped_fields("sections", "legal")
        ["section", "sections", "mentioned_sections"]
        
        >>> get_mapped_fields("sections", "data")
        []
    """
    if filter_field not in FIELD_MAPPINGS:
        # If not in mappings, assume direct mapping
        return [filter_field]
    
    vertical_map = FIELD_MAPPINGS[filter_field]
    mapped_fields = vertical_map.get(vertical, [])
    
    # If no mapping for this vertical, return empty (means field not applicable)
    return mapped_fields


def build_multi_field_condition(
    filter_field: str,
    values: List[str],
    vertical: str
) -> List[models.FieldCondition]:
    """
    Build Qdrant field conditions that check multiple possible payload fields.
    
    This creates OR logic - the value can be in ANY of the mapped fields.
    
    Args:
        filter_field: Filter field name
        values: Values to match
        vertical: Vertical name
        
    Returns:
        List of Qdrant FieldCondition objects (connected by OR)
        
    Example:
        For filter_field="sections", values=["12"], vertical="legal":
        Creates conditions:
        - section = "12" OR
        - sections contains "12" OR  
        - mentioned_sections contains "12"
    """
    mapped_fields = get_mapped_fields(filter_field, vertical)
    
    if not mapped_fields:
        # Field not applicable to this vertical
        return []
    
    conditions = []
    
    for payload_field in mapped_fields:
        # Single value - exact match
        if len(values) == 1:
            conditions.append(
                models.FieldCondition(
                    key=payload_field,
                    match=models.MatchValue(value=values[0])
                )
            )
        # Multiple values - match any
        else:
            conditions.append(
                models.FieldCondition(
                    key=payload_field,
                    match=models.MatchAny(any=values)
                )
            )
    
    return conditions


def validate_filter(filter_field: str, vertical: str) -> bool:
    """
    Validate if a filter field is applicable to a vertical.
    
    Args:
        filter_field: Filter field name
        vertical: Vertical name
        
    Returns:
        True if filter is valid for this vertical
        
    Example:
        >>> validate_filter("sections", "legal")
        True
        
        >>> validate_filter("sections", "data")
        False
    """
    mapped_fields = get_mapped_fields(filter_field, vertical)
    return len(mapped_fields) > 0


def get_all_filter_fields() -> List[str]:
    """Get list of all supported filter fields"""
    return list(FIELD_MAPPINGS.keys())


def get_vertical_filters(vertical: str) -> List[str]:
    """
    Get all applicable filter fields for a vertical.
    
    Args:
        vertical: Vertical name
        
    Returns:
        List of filter field names applicable to this vertical
        
    Example:
        >>> get_vertical_filters("legal")
        ["sections", "year", "go_number"]
    """
    applicable = []
    
    for filter_field in FIELD_MAPPINGS:
        if validate_filter(filter_field, vertical):
            applicable.append(filter_field)
    
    return applicable


# Export all
__all__ = [
    "FIELD_MAPPINGS",
    "get_mapped_fields",
    "build_multi_field_condition",
    "validate_filter",
    "get_all_filter_fields",
    "get_vertical_filters"
]