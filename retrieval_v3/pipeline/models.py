# Pipeline Models - Core Data Structures

"""
Core data structures for the retrieval pipeline
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from query_understanding.query_interpreter import QueryInterpretation
from routing.retrieval_plan import RetrievalPlan


@dataclass
class RetrievalResult:
    """Single retrieval result (chunk)"""
    chunk_id: str
    doc_id: str
    content: str
    score: float
    vertical: str
    metadata: Dict = field(default_factory=dict)
    rewrite_source: Optional[str] = None  # Which rewrite retrieved this
    hop_number: int = 1  # Which hop retrieved this


@dataclass
class RetrievalOutput:
    """Complete retrieval output"""
    query: str
    normalized_query: str
    interpretation: QueryInterpretation
    plan: RetrievalPlan
    rewrites: List[str]
    verticals_searched: List[str]
    results: List[RetrievalResult]
    total_candidates: int
    final_count: int
    processing_time: float
    metadata: Dict = field(default_factory=dict)
    trace_steps: List[str] = field(default_factory=list)
