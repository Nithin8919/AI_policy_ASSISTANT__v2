# Legal Clause Handler

"""
Handles legal clause queries: detection, fast path lookup, fallback scanning
"""

import logging
import re
from typing import List, Optional

from .models import RetrievalResult
from query_understanding.query_interpreter import QueryType, QueryScope, QueryInterpretation
from routing.retrieval_plan import RetrievalPlan

logger = logging.getLogger(__name__)


class LegalClauseHandler:
    """Handles legal clause queries with fast path optimization"""
    
    def __init__(self, clause_indexer=None, qdrant_client=None):
        self.clause_indexer = clause_indexer
        self.qdrant_client = qdrant_client
    
    def is_legal_clause_query(self, query: str) -> bool:
        """Check if query is asking for specific legal clause/section/rule"""
        query_lower = query.lower()
        
        # Enhanced patterns for better legal clause detection
        patterns = [
            # Basic section/article/rule patterns
            r'\b(?:section|clause|article|rule|sub-rule|amendment)\s+\d+',
            r'\bsection\s+\d+\b',
            r'\brule\s+\d+\b', 
            r'\barticle\s+\d+\w*\b',
            
            # Act + section combinations
            r'\b(?:rte|cce|apsermc|education)\s+(?:act\s+)?section\s+\d+',
            r'\b(?:rte|cce|apsermc)\s+(?:act|rule)\b',
            r'\bsection\s+\d+\s+(?:of\s+)?(?:rte|cce|apsermc|education)\s+act',
            
            # Complex legal patterns
            r'\b\d+\(\d+\)\(\w+\)\b',  # 12(1)(c) pattern
            r'\b(?:act|rule|regulation)\s+\d+',
            r'\b(?:go|government\s+order)\s+(?:no\.?\s*)?\d+',
            
            # Preserved token patterns (handle normalization artifacts)
            r'__preserved_\d+__',  # Catches normalized numbers
            r'\b(?:section|article|rule)\s+__preserved_\d+__',
        ]
        
        # Check all patterns
        for pattern in patterns:
            if re.search(pattern, query_lower):
                print(f"🔍 Legal clause pattern matched: '{pattern}' in '{query_lower}'")
                return True
        
        # Additional heuristic: check for legal keywords + numbers
        has_legal_keyword = any(keyword in query_lower for keyword in [
            'section', 'article', 'rule', 'clause', 'act', 'rte', 'cce', 'apsermc'
        ])
        has_number = re.search(r'\d+', query_lower)
        
        if has_legal_keyword and has_number:
            print(f"🔍 Legal heuristic matched: legal_keyword + number in '{query_lower}'")
            return True
            
        return False
    
    def clause_indexer_lookup(self, query: str) -> List[RetrievalResult]:
        """
        Use clause indexer for instant clause lookup
        """
        if not self.clause_indexer:
            return []
        
        try:
            clause_matches = self.clause_indexer.lookup_clause(query)
            results = []
            
            for match in clause_matches:
                results.append(RetrievalResult(
                    chunk_id=match.chunk_id,
                    doc_id=match.doc_id,
                    content=match.content,
                    score=match.confidence,
                    vertical=match.vertical,
                    metadata={'source': 'clause_indexer'},
                    rewrite_source='clause_indexer'
                ))
            
            return results
            
        except Exception as e:
            print(f"Clause indexer lookup failed: {e}")
            return []
    
    def fallback_clause_scan(
        self, 
        query: str, 
        collection_names: List[str]
    ) -> List[RetrievalResult]:
        """
        Fallback exact clause scanner for legal queries
        When regular search fails, scan for exact clause matches
        """
        query_lower = query.lower()
        
        # Extract clause/section patterns
        clause_patterns = []
        
        # Section X
        section_match = re.search(r'section\s+(\d+)', query_lower)
        if section_match:
            section_num = section_match.group(1)
            clause_patterns.extend([
                f'section {section_num}',
                f'section {section_num}.',
                f'({section_num})',
                f'{section_num})'
            ])
        
        # Rule X
        rule_match = re.search(r'rule\s+(\d+)', query_lower)
        if rule_match:
            rule_num = rule_match.group(1)
            clause_patterns.extend([
                f'rule {rule_num}',
                f'rule {rule_num}.',
                f'({rule_num})'
            ])
        
        # Article X
        article_match = re.search(r'article\s+(\d+\w*)', query_lower)
        if article_match:
            article_num = article_match.group(1)
            clause_patterns.extend([
                f'article {article_num}',
                f'article {article_num}.'
            ])
        
        if not clause_patterns:
            return []
        
        # Search for exact matches in legal collection
        legal_collections = [c for c in collection_names if 'legal' in c.lower()]
        if not legal_collections:
            return []
        
        try:
            results = []
            
            for collection in legal_collections:
                # Use simple text search since Filter might be complex
                for pattern in clause_patterns[:2]:  # Limit patterns to avoid timeout
                    try:
                        search_results = self.qdrant_client.client.scroll if hasattr(self.qdrant_client, "client") else self.qdrant_client.scroll(
                            collection_name=collection,
                            limit=10,
                            with_payload=True
                        )
                        
                        if search_results[0]:
                            for point in search_results[0]:
                                content = point.payload.get('content', '').lower()
                                if pattern in content:
                                    results.append(RetrievalResult(
                                        chunk_id=str(point.id),
                                        doc_id=point.payload.get('doc_id', 'unknown'),
                                        content=point.payload.get('content', ''),
                                        score=1.0,  # High score for exact matches
                                        vertical='legal',
                                        metadata=point.payload,
                                        rewrite_source='fallback_clause_scanner'
                                    ))
                    except Exception as e:
                        print(f"Pattern search failed for {pattern}: {e}")
                        continue
            
            # Remove duplicates and return top 3
            unique_results = {}
            for result in results:
                if result.chunk_id not in unique_results:
                    unique_results[result.chunk_id] = result
            
            return list(unique_results.values())[:3]
            
        except Exception as e:
            print(f"Fallback clause scanner failed: {e}")
            return []
    
    def try_fast_path(
        self,
        query: str,
        normalized_query: str,
        top_k: Optional[int] = None
    ) -> Optional[tuple]:
        """
        Try fast path for legal clause queries
        
        Returns:
            (RetrievalOutput, None) if fast path successful, None otherwise
        """
        if not self.is_legal_clause_query(normalized_query) or not self.clause_indexer:
            return None
        
        print(f"🔍 Legal clause query detected - trying fast path: {normalized_query}")
        
        # Use original query for clause lookup (avoids normalized tokens)
        clause_results = self.clause_indexer_lookup(query)  # Original query, not normalized
        
        # If we found good clause matches, use fast path
        if clause_results and len(clause_results) >= 2:
            print(f"⚡ Fast path successful - found {len(clause_results)} clause matches")
            
            # Create minimal interpretation for legal queries
            fast_interpretation = QueryInterpretation(
                query_type=QueryType.QA,  # Legal clause queries are QA type
                scope=QueryScope.NARROW,  # Specific legal clause
                needs_internet=False,
                needs_deep_mode=False,
                confidence=0.95,
                detected_entities={"legal_clauses": [normalized_query]},
                keywords=[normalized_query.lower()],
                temporal_references=[],
                reasoning="legal_clause_fast_path_detected"
            )
            
            # Create simple plan for fast path
            final_top_k = min(top_k or 10, len(clause_results))
            fast_plan = RetrievalPlan(
                num_rewrites=1,
                num_hops=1,
                top_k_per_vertical=final_top_k,
                top_k_total=final_top_k,
                use_internet=False,
                use_hybrid=False,
                rerank_top_k=final_top_k,
                diversity_weight=0.0,  # No diversity needed for clause lookup
                mode="fast_clause_lookup"
            )
            
            return fast_interpretation, fast_plan, clause_results[:final_top_k]
        
        return None
