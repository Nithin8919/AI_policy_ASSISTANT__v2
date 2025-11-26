"""
Retrieval Module
================
Main retrieval system for AP Policy Assistant.

Main entry point:
    from retrieval import RetrievalRouter
    router = RetrievalRouter()
    response = router.query("What is Section 12?")
"""

__all__ = [
    "RetrievalRouter",
    "query",
    "AnswerGenerator",
    "get_answer_generator",
]


def __getattr__(name):
    """Lazily import heavy modules to avoid pulling torch/numpy on package import."""
    if name == "RetrievalRouter" or name == "query":
        from . import router
        if name == "RetrievalRouter":
            return router.RetrievalRouter
        return router.query
    if name == "AnswerGenerator" or name == "get_answer_generator":
        from . import answer_generator
        if name == "AnswerGenerator":
            return answer_generator.AnswerGenerator
        return answer_generator.get_answer_generator
    raise AttributeError(f"module 'retrieval' has no attribute '{name}'")