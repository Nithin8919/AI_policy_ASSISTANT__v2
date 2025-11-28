# Per-mode behaviours + routing rules

"""
Mode Configuration
==================
Defines behavior for QA, Deep Think, and Brainstorm modes.
Clean, deterministic, no overlap.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
from .settings import DYNAMIC_TOP_K_CONFIG


class QueryMode(Enum):
    """Three modes of operation"""
    QA = "qa"
    DEEP_THINK = "deep_think"
    BRAINSTORM = "brainstorm"


@dataclass
class ModeConfig:
    """Configuration for a specific mode"""
    mode: QueryMode
    
    # Which verticals to search
    verticals: List[str]
    
    # Retrieval settings
    top_k: int
    rerank_top: int
    
    # Embedding model to use
    embedding_model: str  # "fast" or "deep"
    
    # Reranking strategy
    reranker: str  # "light", "policy", or "brainstorm"
    
    # Query enhancement
    enhance_query: bool
    expand_synonyms: bool
    extract_entities: bool
    
    # LLM synthesis
    synthesis_style: str
    include_citations: bool
    max_context_chunks: int
    
    # Timeout
    timeout: float


# QA Mode - Increased from 10 to 20
QA_MODE_CONFIG = ModeConfig(
    mode=QueryMode.QA,
    
    # Search only relevant verticals (determined by query router)
    verticals=[],  # Will be set dynamically
    
    # Fast and precise
    top_k=DYNAMIC_TOP_K_CONFIG.get("qa_base", 20),  # V2: Increased
    rerank_top=10,  # V2: Increased from 5
    
    # Use fast embeddings
    embedding_model="fast",
    
    # Light reranking
    reranker="light",
    
    # Minimal query enhancement
    enhance_query=True,
    expand_synonyms=False,
    extract_entities=True,
    
    # Concise synthesis
    synthesis_style="concise",
    include_citations=True,
    max_context_chunks=5,
    
    # Fast timeout
    timeout=2.0
)


# Deep Think Mode - Increased from 50 to 80
DEEP_THINK_MODE_CONFIG = ModeConfig(
    mode=QueryMode.DEEP_THINK,
    
    # Search ALL verticals
    verticals=["legal", "go", "judicial", "data", "schemes"],
    
    # Comprehensive retrieval
    top_k=DYNAMIC_TOP_K_CONFIG.get("deep_think_base", 80),  # V2: Increased
    rerank_top=30,  # V2: Increased from 20
    
    # Use deep embeddings
    embedding_model="deep",
    
    # Policy-aware reranking
    reranker="policy",
    
    # Full query enhancement
    enhance_query=True,
    expand_synonyms=True,
    extract_entities=True,
    
    # Deep synthesis with chain-of-thought
    synthesis_style="deep_policy",
    include_citations=True,
    max_context_chunks=20,
    
    # Longer timeout for comprehensive search
    timeout=10.0
)


# Brainstorm Mode - Increased from 40 to 60
BRAINSTORM_MODE_CONFIG = ModeConfig(
    mode=QueryMode.BRAINSTORM,
    
    # Focus on external, data, and schemes
    verticals=["schemes", "data"],  # Light touch on legal/judicial
    
    # Diverse retrieval
    top_k=DYNAMIC_TOP_K_CONFIG.get("brainstorm_base", 60),  # V2: Increased
    rerank_top=20,  # V2: Increased from 15
    
    # Use deep embeddings for better semantic matching
    embedding_model="deep",
    
    # Diversity-focused reranking
    reranker="brainstorm",
    
    # Creative query enhancement
    enhance_query=True,
    expand_synonyms=True,
    extract_entities=False,  # Less structured
    
    # Exploratory synthesis
    synthesis_style="exploratory",
    include_citations=False,  # More free-form
    max_context_chunks=15,
    
    # Medium timeout
    timeout=8.0
)


# Mode lookup
MODE_CONFIGS = {
    QueryMode.QA: QA_MODE_CONFIG,
    QueryMode.DEEP_THINK: DEEP_THINK_MODE_CONFIG,
    QueryMode.BRAINSTORM: BRAINSTORM_MODE_CONFIG
}


def get_mode_config(mode: QueryMode) -> ModeConfig:
    """Get configuration for a mode"""
    return MODE_CONFIGS[mode]


# Synthesis prompt templates
SYNTHESIS_PROMPTS = {
    "concise": """Answer the question directly and concisely using the provided context.

Question: {query}

Context:
{context}

Provide a clear, factual answer with inline citations [1], [2], etc.""",

    "deep_policy": """Provide a comprehensive policy analysis using the chain-of-thought approach:

1. Constitutional Foundation
2. Relevant Acts & Rules
3. Government Orders (implementation)
4. Judicial Precedents
5. Data Evidence
6. Practical Recommendations

Question: {query}

Context from all verticals:
{context}

Synthesize a deep, integrated policy perspective with citations.""",

    "exploratory": """Generate creative ideas and insights based on the context provided.

Topic: {query}

Context (global models, data, schemes):
{context}

Provide:
- Novel ideas
- Global best practices
- Ground realities in AP
- Innovative approaches
- Feasibility considerations"""
}


def get_synthesis_prompt(style: str) -> str:
    """Get synthesis prompt template for a style"""
    return SYNTHESIS_PROMPTS.get(style, SYNTHESIS_PROMPTS["concise"])