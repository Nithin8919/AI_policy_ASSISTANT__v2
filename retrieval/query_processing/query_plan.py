# Builds final retrieval plan

"""
Query Plan
==========
Builds complete retrieval plan from query processing results.
This is the blueprint that the retrieval engine executes.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from ..config.mode_config import QueryMode, get_mode_config


@dataclass
class QueryPlan:
    """
    Complete retrieval plan.
    Deterministic blueprint for execution.
    """
    # Original query
    original_query: str
    
    # Normalized query
    normalized_query: str
    
    # Enhanced query (with synonyms, entities)
    enhanced_query: str
    
    # Detected mode
    mode: QueryMode
    mode_confidence: float
    
    # Verticals to search
    verticals: List[str]
    vertical_confidences: Dict[str, float]
    
    # Extracted entities
    entities: Dict
    
    # Retrieval parameters (from mode config)
    top_k: int
    rerank_top: int
    embedding_model: str
    reranker: str
    
    # Filters to apply
    filters: Dict[str, List[str]]
    
    # Synthesis parameters
    synthesis_style: str
    max_context_chunks: int
    include_citations: bool
    
    # Timeout
    timeout: float
    
    def to_dict(self) -> Dict:
        """Convert plan to dictionary"""
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "enhanced_query": self.enhanced_query,
            "mode": self.mode.value,
            "mode_confidence": self.mode_confidence,
            "verticals": self.verticals,
            "vertical_confidences": self.vertical_confidences,
            "entities": {k: [e.value for e in v] for k, v in self.entities.items()},
            "top_k": self.top_k,
            "rerank_top": self.rerank_top,
            "embedding_model": self.embedding_model,
            "reranker": self.reranker,
            "filters": self.filters,
            "synthesis_style": self.synthesis_style,
            "max_context_chunks": self.max_context_chunks,
            "include_citations": self.include_citations,
            "timeout": self.timeout
        }


class QueryPlanner:
    """Builds query plans"""
    
    def __init__(
        self,
        normalizer,
        intent_classifier,
        entity_extractor,
        query_enhancer,
        query_router
    ):
        """Initialize planner with all query processing components"""
        self.normalizer = normalizer
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.query_enhancer = query_enhancer
        self.query_router = query_router
    
    def build_plan(
        self,
        query: str,
        explicit_mode: Optional[str] = None,
        explicit_verticals: Optional[List[str]] = None
    ) -> QueryPlan:
        """
        Build complete query plan.
        
        Args:
            query: User query
            explicit_mode: Override mode detection (optional)
            explicit_verticals: Override vertical routing (optional)
            
        Returns:
            QueryPlan object
        """
        # 1. Normalize query
        normalized = self.normalizer.normalize(query)
        
        # 2. Detect mode
        if explicit_mode:
            mode = self.intent_classifier.classify_explicit(explicit_mode)
            mode_confidence = 1.0
        else:
            mode, mode_confidence = self.intent_classifier.classify(normalized)
        
        # 3. Get mode config
        mode_config = get_mode_config(mode)
        
        # 4. Extract entities
        entities = self.entity_extractor.extract(normalized)
        
        # 5. Enhance query (if configured for mode)
        if mode_config.enhance_query:
            enhanced = self.query_enhancer.enhance(
                normalized,
                entities,  # Pass entities as second parameter
                mode.value  # Pass mode as string value
            )
        else:
            enhanced = normalized
        
        # 6. Route to verticals
        if explicit_verticals:
            verticals = explicit_verticals
            vertical_confidences = {v: 1.0 for v in verticals}
        elif mode_config.verticals:
            # Mode specifies verticals (e.g., Deep Think = all)
            verticals = mode_config.verticals
            vertical_confidences = {v: 1.0 for v in verticals}
        else:
            # Route based on query content (e.g., QA mode)
            routed = self.query_router.route(normalized, entities)
            verticals = [v for v, _ in routed[:3]]  # Top 3
            vertical_confidences = {v: conf for v, conf in routed}
        
        # 7. Build filters from entities
        filters = self.query_enhancer.build_filter_dict(entities)
        
        # 8. Create plan
        plan = QueryPlan(
            original_query=query,
            normalized_query=normalized,
            enhanced_query=enhanced,
            mode=mode,
            mode_confidence=mode_confidence,
            verticals=verticals,
            vertical_confidences=vertical_confidences,
            entities=entities,
            top_k=mode_config.top_k,
            rerank_top=mode_config.rerank_top,
            embedding_model=mode_config.embedding_model,
            reranker=mode_config.reranker,
            filters=filters,
            synthesis_style=mode_config.synthesis_style,
            max_context_chunks=mode_config.max_context_chunks,
            include_citations=mode_config.include_citations,
            timeout=mode_config.timeout
        )
        
        return plan


# Factory function
def create_query_planner() -> QueryPlanner:
    """Create query planner with all dependencies"""
    from .normalizer import get_normalizer
    from .intent_classifier import get_intent_classifier
    from .entity_extractor import get_entity_extractor
    from .query_enhancer import get_query_enhancer
    from .query_router import get_query_router
    
    return QueryPlanner(
        normalizer=get_normalizer(),
        intent_classifier=get_intent_classifier(),
        entity_extractor=get_entity_extractor(),
        query_enhancer=get_query_enhancer(),
        query_router=get_query_router()
    )


# Global planner instance
_planner_instance = None


def get_query_planner() -> QueryPlanner:
    """Get global query planner instance"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = create_query_planner()
    return _planner_instance