"""
Hybrid Search - Combine vector search with BM25 keyword search
Uses Reciprocal Rank Fusion (RRF) for score combination
"""

from typing import List, Dict, Set
from dataclasses import dataclass
import math
import re


@dataclass
class HybridResult:
    """Result from hybrid search"""
    chunk_id: str
    content: str
    vector_score: float
    bm25_score: float
    final_score: float
    metadata: Dict


class BM25:
    """Enhanced BM25 implementation with legal keyword injection"""
    
    # Legal keyword mappings for BM25 boosting
    LEGAL_KEYWORD_MAPPINGS = {
        'rte section 12': [
            '25% admission', 'weaker section', 'disadvantaged group', 
            'free and compulsory education', 'admission quota', 'section 12'
        ],
        'rte section 13': [
            'no capitation fee', 'admission procedures', 'no screening',
            'age appropriate admission', 'section 13'
        ],
        'article 21a': [
            'fundamental right', 'free education', 'compulsory education',
            'article 21a', 'constitutional provision'
        ],
        'cce rules': [
            'continuous comprehensive evaluation', 'assessment', 'grading',
            'evaluation methods', 'scholastic areas'
        ],
        'section 4 rte': [
            'age appropriate admission', 'special training', 'elementary education',
            'special provisions', 'section 4'
        ],
        'section 17': [
            'no capitation fee', 'selection procedure', 'admission',
            'section 17', 'prohibition'
        ]
    }
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        self.idf_cache = {}
    
    def compute_idf(self, term: str, doc_freq: int, total_docs: int) -> float:
        """Compute IDF score for a term"""
        if term in self.idf_cache:
            return self.idf_cache[term]
        
        idf = math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
        self.idf_cache[term] = idf
        return idf
    
    def score(
        self,
        query_terms: List[str],
        doc_terms: List[str],
        avg_doc_length: float,
        total_docs: int,
        term_doc_freqs: Dict[str, int]
    ) -> float:
        """
        Compute BM25 score for a document
        
        Args:
            query_terms: Query term list
            doc_terms: Document term list
            avg_doc_length: Average document length in corpus
            total_docs: Total number of documents
            term_doc_freqs: Dict mapping term -> doc frequency
            
        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = len(doc_terms)
        
        # Term frequency in doc
        term_freqs = {}
        for term in doc_terms:
            term_freqs[term] = term_freqs.get(term, 0) + 1
        
        for query_term in query_terms:
            if query_term not in term_freqs:
                continue
            
            # Term frequency
            tf = term_freqs[query_term]
            
            # IDF
            doc_freq = term_doc_freqs.get(query_term, 1)
            idf = self.compute_idf(query_term, doc_freq, total_docs)
            
            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (doc_length / avg_doc_length)
            )
            
            score += idf * (numerator / denominator)
        
        return score
    
    def score_with_legal_boost(
        self,
        query: str,
        query_terms: List[str],
        doc_terms: List[str],
        avg_doc_length: float,
        total_docs: int,
        term_doc_freqs: Dict[str, int],
        boost_factor: float = 2.0
    ) -> float:
        """
        Enhanced BM25 scoring with legal keyword injection
        
        Args:
            query: Original query string
            query_terms: Query term list
            doc_terms: Document term list  
            avg_doc_length: Average document length in corpus
            total_docs: Total number of documents
            term_doc_freqs: Dict mapping term -> doc frequency
            boost_factor: Boost multiplier for legal keywords
            
        Returns:
            Enhanced BM25 score with legal boosting
        """
        # Get base BM25 score
        base_score = self.score(query_terms, doc_terms, avg_doc_length, total_docs, term_doc_freqs)
        
        # Check if this is a legal clause query
        if not self._is_legal_clause_query(query):
            return base_score
        
        # Get legal keywords for this query
        legal_keywords = self._get_legal_keywords(query)
        if not legal_keywords:
            return base_score
        
        # Calculate bonus score for legal keyword matches
        doc_text = ' '.join(doc_terms).lower()
        legal_bonus = 0.0
        
        for keyword in legal_keywords:
            if keyword.lower() in doc_text:
                # Higher bonus for exact keyword matches
                keyword_count = doc_text.count(keyword.lower())
                legal_bonus += keyword_count * 0.5  # Bonus per keyword match
        
        # Apply boost if legal keywords found
        if legal_bonus > 0:
            return base_score * boost_factor + legal_bonus
        
        return base_score
    
    def _is_legal_clause_query(self, query: str) -> bool:
        """Check if query is asking for specific legal clause/section/rule"""
        query_lower = query.lower()
        patterns = [
            r'\b(?:section|clause|article|rule|sub-rule|amendment)\s+\d+',
            r'\b(?:rte|cce|apsermc|education)\s+act\b',
            r'\b\d+\(\d+\)\(\w+\)\b',  # 12(1)(c) pattern
            r'\b(?:act|rule|regulation)\s+\d+',
            r'\bsection\s+\d+\b',
            r'\brule\s+\d+\b',
            r'\barticle\s+\d+\w*\b'
        ]
        return any(re.search(pattern, query_lower) for pattern in patterns)
    
    def _get_legal_keywords(self, query: str) -> List[str]:
        """Get relevant legal keywords for query"""
        query_lower = query.lower()
        
        # Check for direct mappings
        for key, keywords in self.LEGAL_KEYWORD_MAPPINGS.items():
            if key in query_lower:
                return keywords
        
        # Check for partial matches
        if 'rte' in query_lower and 'section' in query_lower:
            # Extract section number
            section_match = re.search(r'section\s+(\d+)', query_lower)
            if section_match:
                section_num = section_match.group(1)
                if f'rte section {section_num}' in self.LEGAL_KEYWORD_MAPPINGS:
                    return self.LEGAL_KEYWORD_MAPPINGS[f'rte section {section_num}']
        
        # Default legal keywords for any clause query
        if self._is_legal_clause_query(query):
            return ['legal provision', 'act', 'section', 'clause', 'rule']
        
        return []


class HybridSearcher:
    """Combine vector and keyword search with RRF fusion"""
    
    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        rrf_k: int = 60
    ):
        """
        Args:
            vector_weight: Weight for vector scores (0-1)
            keyword_weight: Weight for keyword scores (0-1)
            rrf_k: RRF constant (default 60)
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.rrf_k = rrf_k
        self.bm25 = BM25()
    
    def hybrid_search(
        self,
        query: str,
        vector_results: List[Dict],
        corpus_documents: List[str] = None,
        top_k: int = 20
    ) -> List[HybridResult]:
        """
        Perform hybrid search combining vector and BM25
        
        Args:
            query: Query string
            vector_results: Results from vector search
            corpus_documents: Full corpus for BM25 (optional)
            top_k: Final result count
            
        Returns:
            List of HybridResult objects with fused scores
        """
        # Prepare query terms
        query_terms = query.lower().split()
        
        # If no corpus provided, use simple term matching
        if corpus_documents is None:
            return self._simple_hybrid(query_terms, vector_results, top_k)
        
        # Full BM25 scoring
        return self._full_hybrid(
            query_terms,
            vector_results,
            corpus_documents,
            top_k
        )
    
    def _simple_hybrid(
        self,
        query_terms: List[str],
        vector_results: List[Dict],
        top_k: int
    ) -> List[HybridResult]:
        """Simple hybrid using term overlap"""
        results = []
        
        for result in vector_results:
            content = result.get('content', '').lower()
            doc_terms = content.split()
            
            # Count term overlaps
            overlap = sum(1 for term in query_terms if term in doc_terms)
            bm25_score = overlap / max(len(query_terms), 1)
            
            # Combine scores
            vector_score = result.get('score', 0.0)
            final_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * bm25_score
            )
            
            results.append(HybridResult(
                chunk_id=result.get('chunk_id', result.get('id', 'unknown')),
                content=result.get('content', ''),
                vector_score=vector_score,
                bm25_score=bm25_score,
                final_score=final_score,
                metadata=result.get('metadata', {})
            ))
        
        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results[:top_k]
    
    def _full_hybrid(
        self,
        query_terms: List[str],
        vector_results: List[Dict],
        corpus_documents: List[str],
        top_k: int
    ) -> List[HybridResult]:
        """Full hybrid with proper BM25"""
        # Compute corpus statistics
        total_docs = len(corpus_documents)
        avg_length = sum(len(doc.split()) for doc in corpus_documents) / total_docs
        
        # Compute document frequencies
        term_doc_freqs = {}
        for doc in corpus_documents:
            unique_terms = set(doc.lower().split())
            for term in unique_terms:
                term_doc_freqs[term] = term_doc_freqs.get(term, 0) + 1
        
        # Score each result
        results = []
        
        for result in vector_results:
            content = result.get('content', '')
            doc_terms = content.lower().split()
            
            # BM25 score
            bm25_score = self.bm25.score(
                query_terms,
                doc_terms,
                avg_length,
                total_docs,
                term_doc_freqs
            )
            
            # Normalize BM25 (rough normalization)
            bm25_score = min(bm25_score / 10.0, 1.0)
            
            # Vector score
            vector_score = result.get('score', 0.0)
            
            # Combine
            final_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * bm25_score
            )
            
            results.append(HybridResult(
                chunk_id=result.get('chunk_id', result.get('id', 'unknown')),
                content=content,
                vector_score=vector_score,
                bm25_score=bm25_score,
                final_score=final_score,
                metadata=result.get('metadata', {})
            ))
        
        # Sort and return
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results[:top_k]
    
    def rrf_fusion(
        self,
        vector_rankings: List[str],
        keyword_rankings: List[str],
        k: int = None
    ) -> List[str]:
        """
        Reciprocal Rank Fusion
        
        Args:
            vector_rankings: Ranked list of IDs from vector search
            keyword_rankings: Ranked list of IDs from keyword search
            k: RRF constant
            
        Returns:
            Fused ranking list
        """
        if k is None:
            k = self.rrf_k
        
        scores = {}
        
        # Score from vector rankings
        for rank, doc_id in enumerate(vector_rankings, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        
        # Score from keyword rankings
        for rank, doc_id in enumerate(keyword_rankings, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        
        # Sort by RRF score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return [doc_id for doc_id, score in sorted_docs]


if __name__ == "__main__":
    # Example usage
    print("Hybrid Search - Vector + BM25 Fusion")
    print("=" * 60)
    
    # Mock vector results
    vector_results = [
        {'chunk_id': '1', 'content': 'Teacher transfer rules', 'score': 0.9},
        {'chunk_id': '2', 'content': 'School infrastructure', 'score': 0.8},
        {'chunk_id': '3', 'content': 'Teacher training program', 'score': 0.75},
    ]
    
    searcher = HybridSearcher(vector_weight=0.7, keyword_weight=0.3)
    
    query = "teacher transfer"
    results = searcher.hybrid_search(query, vector_results, top_k=3)
    
    print(f"Query: {query}\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.content}")
        print(f"   Vector: {result.vector_score:.3f}, BM25: {result.bm25_score:.3f}")
        print(f"   Final: {result.final_score:.3f}")
        print()
