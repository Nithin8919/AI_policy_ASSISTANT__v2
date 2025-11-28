# Builds final retrieval plan

"""
Query Plan
==========
Builds complete retrieval plan from query processing results.
This is the blueprint that the retrieval engine executes.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from ..config.mode_config import QueryMode, get_mode_config
import logging

logger = logging.getLogger(__name__)


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
    
    # V2: Intent signals for advanced processing
    intent_signals: Optional[Any] = None
    
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
    """Builds query plans with V2 support"""
    
    def __init__(self):
        """Initialize query planner with V2 support"""
        from .normalizer import get_normalizer
        from .entity_extractor import get_entity_extractor  
        from .query_enhancer import get_query_enhancer
        from ..config.settings import FEATURE_FLAGS, DYNAMIC_TOP_K_CONFIG
        
        self.normalizer = get_normalizer()
        self.entity_extractor = get_entity_extractor()
        self.query_enhancer = get_query_enhancer()
        
        # V2: Smart component selection based on feature flags
        if FEATURE_FLAGS.get("use_intent_classifier_v2", False):
            try:
                from .intent_classifier import get_intent_classifier_v2
                self.intent_classifier = get_intent_classifier_v2()
                self.using_v2_classifier = True
                logger.info("✅ Using Intent Classifier V2")
            except (ImportError, AttributeError):
                from .intent_classifier import get_intent_classifier
                self.intent_classifier = get_intent_classifier()
                self.using_v2_classifier = False
                logger.warning("⚠️  Intent Classifier V2 not found, using V1")
        else:
            from .intent_classifier import get_intent_classifier
            self.intent_classifier = get_intent_classifier()
            self.using_v2_classifier = False
            logger.info("ℹ️  Using Intent Classifier V1 (legacy)")
        
        if FEATURE_FLAGS.get("use_query_router_v2", False):
            try:
                from .query_router_v2 import get_query_router_v2
                self.query_router = get_query_router_v2()
                self.using_v2_router = True
                logger.info("✅ Using Query Router V2")
            except ImportError:
                from .query_router import get_query_router
                self.query_router = get_query_router()
                self.using_v2_router = False
                logger.warning("⚠️  Query Router V2 not found, using V1")
        else:
            from .query_router import get_query_router
            self.query_router = get_query_router()
            self.using_v2_router = False
            logger.info("ℹ️  Using Query Router V1 (legacy)")
    
    def plan(
        self,
        query: str,
        mode_override: Optional[str] = None
    ) -> QueryPlan:
        """
        Build query execution plan with V2 enhancements.
        
        Args:
            query: User query
            explicit_mode: Optional mode override
            explicit_verticals: Optional vertical override
            
        Returns:
            QueryPlan with all parameters
        """
        # 1. Normalize query
        normalized = self.normalizer.normalize(query)
        
        # 2. Extract entities
        entities = self.entity_extractor.extract(normalized)
        
        # 3. Classify intent (V2 returns extra signals)
        intent_signals = None
        
        if self.using_v2_classifier:
            # V2 returns: (mode, confidence, intent_signals)
            mode, mode_confidence, intent_signals = self.intent_classifier.classify(
                normalized, entities
            )
        else:
            # V1 returns: (mode, confidence)
            mode, mode_confidence = self.intent_classifier.classify(normalized)
        
        # Handle mode override
        if mode_override:
            mode = QueryMode(mode_override)
            mode_confidence = 1.0
            logger.info(f"⚠️  Mode overridden to: {mode.value}")
        
        # 4. Get mode configuration (moved earlier)
        mode_config = get_mode_config(mode)
        
        # 5. Enhance query BEFORE routing (CRITICAL FIX)
        enhanced = self.query_enhancer.enhance(normalized, entities, mode.value)
        
        # 6. Route to verticals using ENHANCED query (V2 needs intent_signals)
        if self.using_v2_router and intent_signals:
            # V2 signature: route(query, entities, mode, intent_signals)
            # FIXED: Use enhanced query for routing, not normalized
            verticals = self.query_router.route(
                enhanced, entities, mode, intent_signals
            )
            vertical_confidences = {v: 1.0 for v in verticals}
        else:
            # V1 signature: route(query, entities)
            # FIXED: Use enhanced query for routing, not normalized
            routed = self.query_router.route(enhanced, entities)
            verticals = [v for v, _ in routed[:3]]  # Top 3
            vertical_confidences = {v: conf for v, conf in routed}
        
        # Log the routing decision
        logger.info(f"🎯 Routing enhanced query to: {verticals}")
        
        # 7. Dynamic Top-K (V2 feature)
        from ..config.settings import FEATURE_FLAGS, DYNAMIC_TOP_K_CONFIG
        if FEATURE_FLAGS.get("dynamic_top_k", False) and intent_signals:
            top_k = self._calculate_dynamic_top_k(
                mode_config.top_k,
                enhanced,  # Use enhanced query for dynamic top-k too
                intent_signals,
                len(verticals)
            )
        else:
            top_k = mode_config.top_k
        
        # 8. Build filters
        filters = self.query_enhancer.build_filter_dict(entities)
        
        # 9. Create plan
        plan = QueryPlan(
            original_query=query,
            normalized_query=normalized,
            enhanced_query=enhanced,
            mode=mode,
            mode_confidence=mode_confidence,
            verticals=verticals,
            vertical_confidences=vertical_confidences,
            entities=entities,
            top_k=top_k,
            rerank_top=mode_config.rerank_top,
            embedding_model=mode_config.embedding_model,
            reranker=mode_config.reranker,
            filters=filters,
            synthesis_style=mode_config.synthesis_style,
            max_context_chunks=mode_config.max_context_chunks,
            include_citations=mode_config.include_citations,
            timeout=mode_config.timeout,
            intent_signals=intent_signals,  # NEW: Include signals in plan
        )
        
        logger.info(f"📋 Query Plan: mode={mode.value}, verticals={len(verticals)}, top_k={top_k}")
        
        return plan

    def build_plan(
        self,
        query: str,
        explicit_mode: Optional[str] = None,
        explicit_verticals: Optional[List[str]] = None
    ) -> QueryPlan:
        """
        Backward compatibility method - delegates to plan()
        
        Args:
            query: User query
            explicit_mode: Optional mode override
            explicit_verticals: Optional verticals (ignored in V2)
            
        Returns:
            QueryPlan object
        """
        return self.plan(query, explicit_mode)
    
    def _calculate_dynamic_top_k(
        self,
        base_k: int,
        query: str,
        intent_signals: Any,
        num_verticals: int
    ) -> int:
        """
        Calculate dynamic top-k based on query characteristics.
        
        V2 FEATURE: Boosts top-k for comprehensive queries.
        """
        from ..config.settings import DYNAMIC_TOP_K_CONFIG
        
        top_k = base_k
        
        # Boost for comprehensive queries
        if intent_signals and hasattr(intent_signals, 'comprehensive_score') and intent_signals.comprehensive_score > 0.5:
            multiplier = DYNAMIC_TOP_K_CONFIG.get("comprehensive_multiplier", 1.5)
            top_k = int(base_k * multiplier)
            logger.info(f"🔼 Boosting top-k for comprehensive query: {base_k} → {top_k}")
        
        # Scale by number of verticals (more verticals = more results needed)
        if num_verticals > 3:
            top_k = int(top_k * 1.2)
            logger.info(f"🔼 Boosting top-k for multi-vertical search: → {top_k}")
        
        return top_k


# Factory function
def create_query_planner() -> QueryPlanner:
    """Create query planner with V2 support"""
    return QueryPlanner()


# Global planner instance
_planner_instance = None


def get_query_planner() -> QueryPlanner:
    """Get global query planner instance"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = create_query_planner()
    return _planner_instance