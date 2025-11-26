# MMR, Hybrid BM25+Embeddings

"""
Multi-Vector Search
===================
Implements MMR (Maximal Marginal Relevance) and hybrid search.
Fast, deterministic, no BS.
"""

import math
from typing import List, Dict, Tuple, Sequence
from collections import Counter
import re


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors"""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot_product / (norm_a * norm_b)


def compute_mmr(
    results: List[Dict],
    lambda_param: float = 0.7,
    top_k: int = 10
) -> List[Dict]:
    """
    Compute Maximal Marginal Relevance to diversify results.
    
    Args:
        results: Search results with scores and vectors
        lambda_param: Balance between relevance (1.0) and diversity (0.0)
        top_k: Number of results to return
        
    Returns:
        Diversified results
    """
    if not results or len(results) <= top_k:
        return results
    
    # Extract vectors (if available)
    vectors = []
    for r in results:
        if "vector" in r and r["vector"] is not None:
            vectors.append(r["vector"])
        else:
            vectors.append(None)
    
    # If no vectors, just return top results by score
    if all(v is None for v in vectors):
        return results[:top_k]
    
    # MMR algorithm
    selected_indices = []
    remaining_indices = list(range(len(results)))
    
    # Start with highest scoring document
    selected_indices.append(0)
    remaining_indices.remove(0)
    
    while len(selected_indices) < top_k and remaining_indices:
        best_score = -float('inf')
        best_idx = None
        
        for idx in remaining_indices:
            if vectors[idx] is None:
                continue
            
            # Relevance score (original score)
            relevance = results[idx]["score"]
            
            # Diversity score (min similarity to already selected)
            max_sim = -1
            for sel_idx in selected_indices:
                if vectors[sel_idx] is not None:
                    sim = cosine_similarity(vectors[idx], vectors[sel_idx])
                    max_sim = max(max_sim, sim)
            
            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        
        if best_idx is not None:
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        else:
            break
    
    # Return selected results
    return [results[i] for i in selected_indices]


def compute_bm25_score(
    query: str,
    document: str,
    k1: float = 1.5,
    b: float = 0.75,
    avg_doc_length: float = 500.0
) -> float:
    """
    Compute BM25 score between query and document.
    
    Args:
        query: Query string
        document: Document string
        k1: BM25 parameter
        b: BM25 parameter
        avg_doc_length: Average document length
        
    Returns:
        BM25 score
    """
    # Tokenize
    query_terms = re.findall(r'\b\w+\b', query.lower())
    doc_terms = re.findall(r'\b\w+\b', document.lower())
    
    if not query_terms or not doc_terms:
        return 0.0
    
    # Term frequencies
    doc_tf = Counter(doc_terms)
    doc_length = len(doc_terms)
    
    # BM25 score
    score = 0.0
    for term in query_terms:
        if term in doc_tf:
            tf = doc_tf[term]
            # Simplified BM25 (without IDF, as we don't have corpus stats)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
            score += numerator / denominator
    
    return score


def hybrid_search(
    vector_results: List[Dict],
    query: str,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[Dict]:
    """
    Combine vector search with keyword matching (BM25).
    
    Args:
        vector_results: Results from vector search
        query: Original query
        vector_weight: Weight for vector scores
        keyword_weight: Weight for keyword scores
        
    Returns:
        Re-scored results
    """
    if not vector_results:
        return []
    
    # Compute keyword scores
    for result in vector_results:
        # Get document text
        payload = result.get("payload", {})
        text = payload.get("text", "") or payload.get("content", "")
        
        # Compute BM25
        keyword_score = compute_bm25_score(query, text)
        
        # Normalize scores to [0, 1]
        vector_score = result["score"]
        
        # Combine scores
        combined_score = (
            vector_weight * vector_score +
            keyword_weight * keyword_score
        )
        
        result["combined_score"] = combined_score
        result["keyword_score"] = keyword_score
    
    # Sort by combined score
    vector_results.sort(key=lambda x: x["combined_score"], reverse=True)
    
    return vector_results


def reciprocal_rank_fusion(
    results_list: List[List[Dict]],
    k: int = 60
) -> List[Dict]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.
    
    Args:
        results_list: List of result lists from different sources
        k: RRF parameter (usually 60)
        
    Returns:
        Fused results
    """
    # Collect all unique documents with their RRF scores
    doc_scores = {}
    
    for results in results_list:
        for rank, result in enumerate(results, start=1):
            doc_id = result.get("id")
            if doc_id is None:
                continue
            
            # RRF score
            rrf_score = 1.0 / (k + rank)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "result": result,
                    "rrf_score": 0.0
                }
            
            doc_scores[doc_id]["rrf_score"] += rrf_score
    
    # Sort by RRF score
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )
    
    # Return results with RRF scores
    fused_results = []
    for doc in sorted_docs:
        result = doc["result"].copy()
        result["rrf_score"] = doc["rrf_score"]
        fused_results.append(result)
    
    return fused_results