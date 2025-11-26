# Vertical → Collections mapping

"""
Vertical to Collection Mapping
================================
Maps logical verticals to actual Qdrant collection names.
Clean, no confusion.
"""

from typing import Dict, List
from enum import Enum


class Vertical(Enum):
    """Logical verticals in the system"""
    LEGAL = "legal"
    GO = "go"
    JUDICIAL = "judicial"
    DATA = "data"
    SCHEMES = "schemes"


# Vertical to Qdrant collection mapping
# This is the ONLY place where collection names are defined
VERTICAL_TO_COLLECTION: Dict[str, str] = {
    "legal": "ap_legal_documents",
    "go": "ap_government_orders",
    "judicial": "ap_judicial_documents",
    "data": "ap_data_reports",
    "schemes": "ap_schemes"
}


# Reverse mapping
COLLECTION_TO_VERTICAL: Dict[str, str] = {
    v: k for k, v in VERTICAL_TO_COLLECTION.items()
}


def get_collection_name(vertical: str) -> str:
    """Get Qdrant collection name for a vertical"""
    if vertical not in VERTICAL_TO_COLLECTION:
        raise ValueError(f"Unknown vertical: {vertical}")
    return VERTICAL_TO_COLLECTION[vertical]


def get_vertical_name(collection: str) -> str:
    """Get vertical name from collection name"""
    if collection not in COLLECTION_TO_VERTICAL:
        raise ValueError(f"Unknown collection: {collection}")
    return COLLECTION_TO_VERTICAL[collection]


def get_all_verticals() -> List[str]:
    """Get list of all verticals"""
    return list(VERTICAL_TO_COLLECTION.keys())


def get_all_collections() -> List[str]:
    """Get list of all collection names"""
    return list(VERTICAL_TO_COLLECTION.values())


# Vertical metadata
VERTICAL_METADATA: Dict[str, Dict] = {
    "legal": {
        "description": "Acts, Rules, Sections, Legal Provisions",
        "priority": 1,  # Highest priority in policy reasoning
        "boost_fields": ["act_name", "section_number", "rule_number"],
        "entity_types": ["act", "section", "rule", "article"]
    },
    "go": {
        "description": "Government Orders, Notifications, Circulars",
        "priority": 2,
        "boost_fields": ["go_number", "department", "year"],
        "entity_types": ["go_number", "department", "scheme_name"]
    },
    "judicial": {
        "description": "Court Judgments, Precedents, Legal Interpretations",
        "priority": 3,
        "boost_fields": ["case_name", "court_name", "judgment_date"],
        "entity_types": ["case_number", "court", "petitioner", "respondent"]
    },
    "data": {
        "description": "UDISE, ASER, Statistical Reports, Surveys",
        "priority": 4,
        "boost_fields": ["report_name", "year", "metric_name"],
        "entity_types": ["year", "district", "metric"]
    },
    "schemes": {
        "description": "Schemes, Programs, Guidelines, International Models",
        "priority": 5,
        "boost_fields": ["scheme_name", "year", "country"],
        "entity_types": ["scheme", "country", "organization"]
    }
}


def get_vertical_metadata(vertical: str) -> Dict:
    """Get metadata for a vertical"""
    if vertical not in VERTICAL_METADATA:
        raise ValueError(f"Unknown vertical: {vertical}")
    return VERTICAL_METADATA[vertical]


def get_vertical_priority(vertical: str) -> int:
    """Get priority for a vertical (lower = higher priority)"""
    return VERTICAL_METADATA[vertical]["priority"]