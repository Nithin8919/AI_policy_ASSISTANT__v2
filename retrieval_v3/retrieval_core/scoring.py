"""
Scoring Utilities - Time-based and Relation-based Scoring
==========================================================
Provides recency scoring, operational validity checks, and relation boost calculation.
"""

import math
import time
from typing import Dict, List, Optional, Set


# Relation weights (capped, deduped)
RELATION_WEIGHTS = {
    "amends": 0.7,
    "implements": 0.4,
    "cites": 0.2,
    "supersedes": -1.0,  # Negative for superseding docs (the old one)
    "governed_by": 0.3,
}


def time_score(payload: Dict, now_ts: Optional[int] = None) -> float:
    """
    Calculate time-based recency score with operational validity
    
    Args:
        payload: Document payload with date_issued_ts, is_superseded, effective_to_ts
        now_ts: Current timestamp (defaults to now)
        
    Returns:
        Score between -1.0 and 1.0
        - Fresh, active docs: ~0.7-0.9
        - Old but active: ~0.2-0.4
        - Superseded: -0.5 to -0.9
    """
    if now_ts is None:
        now_ts = int(time.time())
    
    issued_ts = payload.get("date_issued_ts")
    if not issued_ts:
        return 0.0  # No date info, neutral score
    
    # Calculate days since issuance
    days_old = max(1, (now_ts - issued_ts) / 86400)
    
    # Recency component: ~0.9 for fresh, ~0.3 for old
    recency = 1.0 / (1.0 + math.log10(days_old))
    
    # Apply operational validity penalties
    if payload.get("is_superseded"):
        recency -= 0.9  # Heavy penalty for superseded docs
    
    effective_to = payload.get("effective_to_ts")
    if effective_to and effective_to < now_ts:
        recency -= 0.7  # Penalty for expired docs
    
    return max(-1.0, min(1.0, recency))


def relation_bonus(relation_types: List[str]) -> float:
    """
    Calculate relation-based score boost (capped, deduped)
    
    Args:
        relation_types: List of relation types for this document
        
    Returns:
        Bonus score between -1.0 and 0.9
    """
    seen = set()
    bonus = 0.0
    
    for rel_type in relation_types:
        if rel_type in seen:
            continue  # Skip duplicates
        seen.add(rel_type)
        bonus += RELATION_WEIGHTS.get(rel_type, 0.0)
    
    # Cap total bonus
    return max(-1.0, min(0.9, bonus))


def section_type_boost(section_type: Optional[str]) -> float:
    """
    Boost based on section type (orders > content > annexure > preamble)
    UPDATED: Strengthened to prioritize actual policy content
    
    Args:
        section_type: Type of section (orders, annexure, preamble, content)
        
    Returns:
        Boost multiplier (0.85-1.3)
    """
    boosts = {
        "orders": 1.3,       # STRONGEST boost - actual policy orders
        "order": 1.3,        # Singular form
        "content": 1.2,      # General content - increased from 1.0
        "annexure": 1.0,     # Appendices - neutral
        "preamble": 0.85,    # Decreased from 1.05 - administrative fluff
        "table": 0.95,       # Tables - slightly less relevant
    }
    return boosts.get(section_type.lower() if section_type else "", 1.0)


def deduplicate_by_doc_id(results: List[Dict]) -> List[Dict]:
    """
    Deduplicate results by doc_id, keeping highest score
    
    Args:
        results: List of result dicts with 'doc_id' and 'score'
        
    Returns:
        Deduplicated list
    """
    seen = {}
    
    for result in results:
        doc_id = result.get('doc_id')
        if not doc_id:
            continue
        
        score = result.get('score', 0.0)
        
        if doc_id not in seen or score > seen[doc_id]['score']:
            seen[doc_id] = result
    
    return list(seen.values())


def rrf_fusion(rankings: Dict[str, List[int]], k: int = 60) -> Dict[str, float]:
    """
    Reciprocal Rank Fusion for combining multiple rankings
    
    Args:
        rankings: Dict of doc_id -> [rank1, rank2, ...] (1-indexed)
        k: RRF constant (default 60)
        
    Returns:
        Dict of doc_id -> fused_score
    """
    scores = {}
    
    for doc_id, ranks in rankings.items():
        score = sum(1.0 / (k + rank) for rank in ranks)
        scores[doc_id] = score
    
    return scores


def mmr_diversify(
    candidates: Dict[str, float],
    embeddings: Dict[str, List[float]],
    k: int = 10,
    lambda_param: float = 0.7
) -> List[str]:
    """
    Maximal Marginal Relevance for diversification
    
    Args:
        candidates: Dict of doc_id -> base_score
        embeddings: Dict of doc_id -> embedding vector
        k: Number of results to return
        lambda_param: Trade-off between relevance and diversity (0.7 = 70% relevance)
        
    Returns:
        List of doc_ids in MMR order
    """
    selected = set()
    result = []
    
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Simple cosine similarity"""
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        return dot / (mag1 * mag2) if mag1 and mag2 else 0.0
    
    remaining = dict(candidates)
    
    while len(result) < k and remaining:
        best_doc = None
        best_score = -1e9
        
        for doc_id, base_score in remaining.items():
            # Calculate max similarity to already selected docs
            if selected and doc_id in embeddings:
                max_sim = max(
                    cosine_similarity(embeddings[doc_id], embeddings[sel_id])
                    for sel_id in selected
                    if sel_id in embeddings
                )
            else:
                max_sim = 0.0
            
            # MMR score: λ * relevance - (1-λ) * similarity
            mmr_score = lambda_param * base_score - (1 - lambda_param) * max_sim
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_doc = doc_id
        
        if best_doc:
            result.append(best_doc)
            selected.add(best_doc)
            remaining.pop(best_doc)
        else:
            break
    
    return result


# Example usage
if __name__ == "__main__":
    print("Scoring Utilities")
    print("=" * 60)
    
    # Test time scoring
    now = int(time.time())
    
    # Recent, active doc
    recent_doc = {"date_issued_ts": now - (30 * 86400)}  # 30 days ago
    print(f"Recent doc score: {time_score(recent_doc, now):.3f}")
    
    # Old, active doc
    old_doc = {"date_issued_ts": now - (365 * 5 * 86400)}  # 5 years ago
    print(f"Old doc score: {time_score(old_doc, now):.3f}")
    
    # Superseded doc
    superseded_doc = {
        "date_issued_ts": now - (365 * 2 * 86400),
        "is_superseded": True
    }
    print(f"Superseded doc score: {time_score(superseded_doc, now):.3f}")
    
    # Test relation bonus
    relations = ["amends", "implements", "amends"]  # Duplicate should be ignored
    print(f"\nRelation bonus: {relation_bonus(relations):.3f}")
