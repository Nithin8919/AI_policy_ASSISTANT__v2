# Embedding Utils

"""
Embedding Utilities
Helper functions for working with embeddings and vector operations
"""

import numpy as np
from typing import List, Optional


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        # Convert to numpy
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure [0, 1] range
        return max(0.0, min(1.0, similarity))
        
    except Exception as e:
        print(f"Error calculating cosine similarity: {e}")
        return 0.0


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate Euclidean distance between two vectors
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Distance (lower = more similar)
    """
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        return float(np.linalg.norm(v1 - v2))
        
    except Exception as e:
        print(f"Error calculating Euclidean distance: {e}")
        return float('inf')


def normalize_vector(vector: List[float]) -> List[float]:
    """
    Normalize a vector to unit length
    
    Args:
        vector: Input vector
        
    Returns:
        Normalized vector
    """
    try:
        v = np.array(vector)
        norm = np.linalg.norm(v)
        
        if norm == 0:
            return vector
        
        normalized = v / norm
        return normalized.tolist()
        
    except Exception as e:
        print(f"Error normalizing vector: {e}")
        return vector


def batch_cosine_similarity(
    query_vector: List[float],
    vectors: List[List[float]]
) -> List[float]:
    """
    Calculate cosine similarity between query and multiple vectors
    
    Args:
        query_vector: Query embedding
        vectors: List of document embeddings
        
    Returns:
        List of similarity scores
    """
    try:
        q = np.array(query_vector)
        docs = np.array(vectors)
        
        # Compute dot products
        dot_products = np.dot(docs, q)
        
        # Compute norms
        query_norm = np.linalg.norm(q)
        doc_norms = np.linalg.norm(docs, axis=1)
        
        # Avoid division by zero
        if query_norm == 0:
            return [0.0] * len(vectors)
        
        doc_norms[doc_norms == 0] = 1.0
        
        # Calculate similarities
        similarities = dot_products / (doc_norms * query_norm)
        
        # Ensure [0, 1] range
        similarities = np.clip(similarities, 0.0, 1.0)
        
        return similarities.tolist()
        
    except Exception as e:
        print(f"Error in batch cosine similarity: {e}")
        return [0.0] * len(vectors)


def average_vectors(vectors: List[List[float]]) -> Optional[List[float]]:
    """
    Calculate average of multiple vectors
    
    Args:
        vectors: List of vectors
        
    Returns:
        Average vector or None if empty
    """
    if not vectors:
        return None
    
    try:
        v = np.array(vectors)
        avg = np.mean(v, axis=0)
        return avg.tolist()
        
    except Exception as e:
        print(f"Error averaging vectors: {e}")
        return None


def weighted_average_vectors(
    vectors: List[List[float]],
    weights: List[float]
) -> Optional[List[float]]:
    """
    Calculate weighted average of vectors
    
    Args:
        vectors: List of vectors
        weights: List of weights (should sum to 1.0)
        
    Returns:
        Weighted average vector
    """
    if not vectors or not weights or len(vectors) != len(weights):
        return None
    
    try:
        v = np.array(vectors)
        w = np.array(weights).reshape(-1, 1)
        
        weighted_avg = np.sum(v * w, axis=0)
        return weighted_avg.tolist()
        
    except Exception as e:
        print(f"Error in weighted average: {e}")
        return None


def vector_dimension(vector: List[float]) -> int:
    """Get vector dimension"""
    return len(vector)


def is_valid_embedding(vector: List[float], expected_dim: int = None) -> bool:
    """
    Check if vector is a valid embedding
    
    Args:
        vector: Vector to check
        expected_dim: Expected dimension (optional)
        
    Returns:
        True if valid
    """
    if not vector or not isinstance(vector, (list, np.ndarray)):
        return False
    
    if expected_dim and len(vector) != expected_dim:
        return False
    
    # Check for NaN or Inf
    try:
        v = np.array(vector)
        if np.any(np.isnan(v)) or np.any(np.isinf(v)):
            return False
    except:
        return False
    
    return True


if __name__ == "__main__":
    print("Embedding Utilities")
    print("=" * 60)
    
    # Demo
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [2.0, 4.0, 6.0]
    vec3 = [0.5, 1.0, 1.5]
    
    print("\nDemo vectors:")
    print(f"vec1: {vec1}")
    print(f"vec2: {vec2}")
    print(f"vec3: {vec3}")
    
    print("\nCosine similarity:")
    print(f"vec1 vs vec2: {cosine_similarity(vec1, vec2):.3f}")
    print(f"vec1 vs vec3: {cosine_similarity(vec1, vec3):.3f}")
    
    print("\nEuclidean distance:")
    print(f"vec1 vs vec2: {euclidean_distance(vec1, vec2):.3f}")
    
    print("\nNormalized vec1:")
    print(f"{normalize_vector(vec1)}")
    
    print("\nBatch similarity (vec1 vs [vec2, vec3]):")
    print(batch_cosine_similarity(vec1, [vec2, vec3]))
    
    print("\nAverage of [vec1, vec2, vec3]:")
    print(average_vectors([vec1, vec2, vec3]))
    
    print("\nWeighted average (weights: [0.5, 0.3, 0.2]):")
    print(weighted_average_vectors([vec1, vec2, vec3], [0.5, 0.3, 0.2]))
    
    print("\nValidation:")
    print(f"vec1 is valid: {is_valid_embedding(vec1)}")
    print(f"vec1 has expected dim 3: {is_valid_embedding(vec1, expected_dim=3)}")
    print(f"vec1 has expected dim 5: {is_valid_embedding(vec1, expected_dim=5)}")
