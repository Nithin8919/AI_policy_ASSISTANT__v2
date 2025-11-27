"""
Query Orchestrator Module
==========================
Coordinates local RAG, internet, and theory corpus retrieval.

Main entry point:
    from query_orchestrator import get_query_orchestrator
    
    orchestrator = get_query_orchestrator(retrieval_router)
    response = orchestrator.orchestrate(
        query="What is FLN?",
        mode="qa",
        internet_toggle=False
    )
"""

from .router import QueryOrchestrator, get_query_orchestrator
from .config import OrchestratorConfig, get_orchestrator_config
from .triggers import TriggerEngine, get_trigger_engine, TriggerDecision
from .fusion import ContextFusion, get_context_fusion

__all__ = [
    "QueryOrchestrator",
    "get_query_orchestrator",
    "OrchestratorConfig",
    "get_orchestrator_config",
    "TriggerEngine",
    "get_trigger_engine",
    "TriggerDecision",
    "ContextFusion",
    "get_context_fusion",
]