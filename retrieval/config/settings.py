# Global config (qdrant, models, modes)

"""
Global Configuration for Retrieval System
==========================================
Single source of truth for all settings.
No BS, just what's needed.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QdrantConfig:
    """Qdrant connection settings"""
    url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
    timeout: int = 30
    prefer_grpc: bool = False


@dataclass
class EmbeddingConfig:
    """Embedding model settings"""
    # Use Google API for lighter resource usage
    provider: str = "google"  # "local" or "google"
    model: str = "models/text-embedding-004"  # Google's model
    dimension: int = 768
    
    # Fallback local models
    fast_model: str = "BAAI/bge-base-en-v1.5"
    fast_dim: int = 768
    deep_model: str = "BAAI/bge-base-en-v1.5"
    deep_dim: int = 768
    
    # Device for local models
    device: str = "cpu"  # Will auto-detect GPU if available
    batch_size: int = 32
    
    # Google API key
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")


@dataclass
class RetrievalConfig:
    """Retrieval settings per mode"""
    # QA Mode - fast and precise
    qa_top_k: int = 10
    qa_rerank_top: int = 5
    qa_timeout: float = 2.0
    
    # Deep Think Mode - comprehensive
    deep_top_k: int = 50
    deep_rerank_top: int = 20
    deep_timeout: float = 10.0
    
    # Brainstorm Mode - diverse
    brainstorm_top_k: int = 40
    brainstorm_rerank_top: int = 15
    brainstorm_timeout: float = 8.0
    
    # Search settings
    score_threshold: float = 0.5
    use_mmr: bool = True
    mmr_lambda: float = 0.7  # Balance between relevance and diversity


@dataclass
class LLMConfig:
    """LLM API settings"""
    provider: str = "anthropic"  # anthropic, openai, or groq
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    
    # API keys from environment
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")


# Global instances
QDRANT_CONFIG = QdrantConfig()
EMBEDDING_CONFIG = EmbeddingConfig()
RETRIEVAL_CONFIG = RetrievalConfig()
LLM_CONFIG = LLMConfig()


def validate_config(allow_missing_llm: bool = False):
    """Validate that all required config is present"""
    errors = []
    
    # Check Qdrant connection
    if not QDRANT_CONFIG.url:
        errors.append("QDRANT_URL not configured")
    
    skip_llm_check = (
        allow_missing_llm or
        os.getenv("ALLOW_MISSING_LLM_CONFIG", "0") == "1"
    )
    
    # Check LLM API key
    if not skip_llm_check:
        if LLM_CONFIG.provider == "anthropic" and not LLM_CONFIG.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not set")
        elif LLM_CONFIG.provider == "openai" and not LLM_CONFIG.openai_api_key:
            errors.append("OPENAI_API_KEY not set")
        elif LLM_CONFIG.provider == "groq" and not LLM_CONFIG.groq_api_key:
            errors.append("GROQ_API_KEY not set")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True


# ===================================================================
# V2 FEATURE FLAGS
# ===================================================================
# Set any flag to False to disable that feature (instant rollback)

FEATURE_FLAGS = {
    # Core improvements (recommended: all True)
    "use_intent_classifier_v2": True,
    "use_query_router_v2": True,
    "use_hybrid_search": True,
    "dynamic_top_k": True,
    
    # Optional enhancements
    "use_internet_verification": True,  # Requires web_search tool
}


# ===================================================================
# HYBRID SEARCH CONFIGURATION
# ===================================================================
HYBRID_SEARCH_CONFIG = {
    "enabled": True,
    "vector_weight": 0.7,      # 70% weight for semantic similarity
    "keyword_weight": 0.3,     # 30% weight for keyword matching
}


# ===================================================================
# INTERNET VERIFICATION CONFIGURATION
# ===================================================================
INTERNET_VERIFICATION_CONFIG = {
    "enabled": True,
    "max_claims_to_verify": 3,           # Limit verification for speed
    "confidence_threshold": 0.7,         # Verify if confidence < 0.7
    "verify_numerical": True,            # Verify numbers
    "verify_recent": True,               # Verify "latest", "current" queries
}


# ===================================================================
# DYNAMIC TOP-K CONFIGURATION
# ===================================================================
DYNAMIC_TOP_K_CONFIG = {
    # Base values (increased from old values)
    "qa_base": 20,              # Was 10
    "deep_think_base": 80,      # Was 50
    "brainstorm_base": 60,      # Was 40
    
    # Multipliers
    "comprehensive_multiplier": 1.5,  # Boost comprehensive queries by 50%
    "min_verticals": 2,               # Minimum verticals for QA
    "max_verticals": 5,               # Maximum verticals
}