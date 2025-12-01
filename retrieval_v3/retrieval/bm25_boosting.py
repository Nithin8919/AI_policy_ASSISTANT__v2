# BM25 Boosting for Infrastructure and Scheme Documents

"""
BM25 Boosting for V3 Retrieval
==============================
Boosts infrastructure and scheme-heavy documents that are keyword-heavy but embedding-light.
These documents often don't match "education policies" semantically but are crucial for comprehensive answers.
"""

import re
import math
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class BM25Score:
    """BM25 score for a document"""
    doc_id: str
    score: float
    matched_terms: List[str]
    category: str


class BM25Booster:
    """
    BM25-based boosting for keyword-heavy documents that semantic search misses.
    
    Focuses on:
    - Infrastructure documents (Nadu-Nedu, facilities, safety)
    - Scheme documents (Amma Vodi, welfare programs) 
    - Technical documents with specific terminology
    """
    
    # Keywords that indicate infrastructure/scheme content but low embedding similarity
    BOOST_CATEGORIES = {
        'government_orders': {
            'keywords': [
                # GO number patterns
                'go ms no', 'go rt no', 'go no', 'government order',
                'ms no 1', 'ms no 2', 'ms no 3', 'ms no 4', 'ms no 5',
                'rt no 1', 'rt no 2', 'rt no 3', 'rt no 4', 'rt no 5',
                
                # GO content patterns
                'orders issued', 'hereby ordered', 'notification', 'circular',
                'policy guidelines', 'implementation instructions', 'directions',
                'subject approval', 'sanctioned', 'authorized', 'constituted',
                
                # Administrative terms
                'commissioner', 'secretary', 'director', 'principal secretary',
                'government of andhra pradesh', 'school education department',
                'higher education department', 'finance department',
                
                # Policy actions
                'establishment', 'appointment', 'transfer', 'posting',
                'budget allocation', 'fund release', 'scheme implementation',
                'monitoring committee', 'review meeting'
            ],
            'boost_factor': 1.8,  # 80% boost for GO-specific content
            'pattern_type': 'go_specific'  # Special handling for GO patterns
        },
        
        'legal_clauses': {
            'keywords': [
                'section 12', 'section 13', 'section 14', 'section 15', 'section 16',
                'article 21a', 'article 45', 'right to education', 'rte act',
                'cce rules', 'assessment rules', 'examination rules',
                'admission criteria', 'age criteria', 'reservation quota',
                'free and compulsory education', 'neighbourhood school',
                'special category', 'economically weaker section',
                'private school', 'government school', 'aided school'
            ],
            'boost_factor': 2.0,  # 100% boost for exact legal clause matches
            'pattern_type': 'exact_phrase'  # Require exact phrase matching
        },
        
        'infrastructure': {
            'keywords': [
                'nadu nedu', 'infrastructure', 'building', 'classroom', 'toilet',
                'drinking water', 'electricity', 'boundary wall', 'compound wall',
                'furniture', 'bench', 'desk', 'blackboard', 'laboratory', 'library',
                'playground', 'sports facility', 'kitchen', 'ramp', 'accessibility',
                'construction', 'renovation', 'maintenance', 'repair', 'TMF',
                'CCTV', 'security', 'fire safety', 'emergency exit', 'sanitation',
                'hygiene', 'medical room', 'first aid', 'compound', 'fencing'
            ],
            'boost_factor': 1.5,  # 50% boost for infrastructure matches
            'pattern_type': 'flexible'  # Allow word boundary matching
        },
        
        'welfare_schemes': {
            'keywords': [
                'amma vodi', 'vidya kanuka', 'vidya deevena', 'gorumudda',
                'mid day meal', 'midday meal', 'school kit', 'uniform',
                'scholarship', 'financial assistance', 'transport scheme',
                'hostel', 'residential school', 'welfare scheme', 'benefit',
                'incentive', 'allowance', 'stipend', 'nutrition program',
                'health checkup', 'medical assistance', 'free textbook',
                'bicycle scheme', 'student welfare', 'social security'
            ],
            'boost_factor': 1.4,  # 40% boost for welfare scheme matches
            'pattern_type': 'phrase_priority'  # Prioritize multi-word phrases
        },
        
        'safety_compliance': {
            'keywords': [
                'fire safety', 'emergency procedure', 'evacuation plan', 'safety drill',
                'accident prevention', 'child protection', 'safety audit',
                'compliance check', 'safety standard', 'security protocol',
                'CCTV monitoring', 'visitor management', 'gate security',
                'boundary security', 'staff verification', 'background check',
                'child safety policy', 'harassment prevention', 'grievance'
            ],
            'boost_factor': 1.3,  # 30% boost for safety matches
            'pattern_type': 'phrase_priority'
        },
        
        'technical_specifications': {
            'keywords': [
                'specification', 'technical requirement', 'standard', 'norm',
                'measurement', 'dimension', 'capacity', 'quantity', 'quality',
                'procurement', 'tender', 'supplier', 'vendor', 'contract',
                'rate analysis', 'cost estimation', 'budget allocation',
                'financial provision', 'expenditure', 'utilization certificate'
            ],
            'boost_factor': 1.2,  # 20% boost for technical terms
            'pattern_type': 'flexible'
        }
    }
    
    # BM25 parameters
    K1 = 1.2  # Term frequency saturation parameter
    B = 0.75  # Length normalization parameter
    
    def __init__(self):
        """Initialize BM25 booster"""
        self._compile_patterns()
        self.avg_doc_length = None
        self.doc_frequencies = None
        self.total_docs = 0
    
    def _compile_patterns(self):
        """Pre-compile keyword patterns for efficiency with improved specificity"""
        self.category_patterns = {}
        
        for category, config in self.BOOST_CATEGORIES.items():
            patterns = []
            pattern_type = config.get('pattern_type', 'flexible')
            
            for keyword in config['keywords']:
                keyword_lower = keyword.lower()
                
                if pattern_type == 'exact_phrase':
                    # Exact phrase matching for legal clauses
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    
                elif pattern_type == 'go_specific':
                    # Special handling for GO patterns
                    if 'ms no' in keyword_lower or 'rt no' in keyword_lower or 'go no' in keyword_lower:
                        # Match GO number patterns more flexibly
                        pattern = keyword_lower.replace(' ', r'\s*').replace('no', r'(?:no\.?|number)')
                        pattern = r'\b' + pattern + r'\s*\d*'
                    else:
                        # Standard word boundary matching for other GO terms
                        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    
                elif pattern_type == 'phrase_priority':
                    # Multi-word phrases get higher priority
                    if ' ' in keyword_lower:
                        # For phrases, allow slight variations
                        words = keyword_lower.split()
                        pattern = r'\b' + r'\s+'.join(re.escape(word) for word in words) + r'\b'
                    else:
                        # Single words with word boundaries
                        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                
                else:  # flexible (default)
                    # Standard word boundary matching
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                
                patterns.append(re.compile(pattern, re.IGNORECASE))
                
            self.category_patterns[category] = {
                'patterns': patterns,
                'boost_factor': config['boost_factor'],
                'pattern_type': pattern_type
            }
    
    def should_boost_query(self, query: str) -> bool:
        """Check if query should trigger BM25 boosting"""
        boost_triggers = [
            # Legal and GO triggers
            'government order', 'go no', 'ms no', 'rt no', 'notification',
            'section', 'article', 'rule', 'act', 'policy', 'guidelines',
            'commissioner', 'secretary', 'director', 'department',
            
            # Infrastructure triggers  
            'infrastructure', 'facility', 'building', 'construction',
            'nadu nedu', 'classroom', 'toilet', 'laboratory',
            
            # Scheme triggers
            'scheme', 'welfare', 'benefit', 'assistance', 'amma vodi',
            'scholarship', 'hostel', 'transport', 'nutrition',
            
            # Safety and compliance
            'safety', 'security', 'compliance', 'standard', 'audit',
            
            # Technical and procurement
            'technical', 'specification', 'procurement', 'tender'
        ]
        
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in boost_triggers)
    
    def extract_boost_terms(self, query: str) -> Dict[str, List[str]]:
        """Extract terms from query that should be boosted"""
        boost_terms = defaultdict(list)
        query_lower = query.lower()
        
        for category, config in self.category_patterns.items():
            for pattern in config['patterns']:
                matches = pattern.findall(query_lower)
                if matches:
                    boost_terms[category].extend(matches)
        
        return dict(boost_terms)
    
    def calculate_bm25_score(
        self,
        query_terms: List[str],
        document_text: str,
        doc_length: Optional[int] = None
    ) -> float:
        """Calculate BM25 score for document given query terms"""
        if not query_terms or not document_text:
            return 0.0
        
        doc_text_lower = document_text.lower()
        doc_tokens = re.findall(r'\w+', doc_text_lower)
        doc_length = doc_length or len(doc_tokens)
        
        if doc_length == 0:
            return 0.0
        
        # Use default average document length if not set
        avg_dl = self.avg_doc_length or 100
        
        score = 0.0
        for term in query_terms:
            term_lower = term.lower()
            
            # Term frequency in document
            tf = doc_tokens.count(term_lower)
            if tf == 0:
                continue
            
            # Document frequency (assume moderate frequency if not known)
            df = 1  # Will be improved when we have corpus statistics
            total_docs = self.total_docs or 1000
            
            # IDF calculation
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            # BM25 formula
            term_score = idf * (tf * (self.K1 + 1)) / (
                tf + self.K1 * (1 - self.B + self.B * doc_length / avg_dl)
            )
            
            score += term_score
        
        return score
    
    def boost_results(
        self,
        query: str,
        results: List,  # List[RetrievalResult]
        boost_threshold: float = 0.5
    ) -> List:
        """
        Apply BM25 boosting to results
        
        Args:
            query: Original query
            results: List of RetrievalResult objects
            boost_threshold: Minimum original score to apply boosting
            
        Returns:
            Results with boosted scores for infrastructure/scheme documents
        """
        if not self.should_boost_query(query):
            return results
        
        boost_terms = self.extract_boost_terms(query)
        if not boost_terms:
            return results
        
        boosted_results = []
        
        for result in results:
            boosted_result = result  # Start with original
            original_score = result.score
            
            # Only boost results above threshold (avoid boosting poor matches)
            if original_score < boost_threshold:
                boosted_results.append(boosted_result)
                continue
            
            # Calculate category-specific boosts
            total_boost = 0.0
            matched_categories = []
            
            for category, terms in boost_terms.items():
                if category not in self.category_patterns:
                    continue
                
                # Calculate BM25 score for these terms in this document
                bm25_score = self.calculate_bm25_score(terms, result.content)
                
                if bm25_score > 0:
                    boost_factor = self.category_patterns[category]['boost_factor']
                    category_boost = bm25_score * boost_factor * 0.1  # Scale factor
                    total_boost += category_boost
                    matched_categories.append(category)
            
            # Apply boost to original score
            if total_boost > 0:
                # Create boosted result
                boosted_result = result
                boosted_result.score = min(original_score + total_boost, 1.0)  # Cap at 1.0
                
                # Add boost metadata
                if not hasattr(boosted_result, 'metadata'):
                    boosted_result.metadata = {}
                
                boosted_result.metadata.update({
                    'bm25_boost_applied': True,
                    'original_score': original_score,
                    'boost_amount': total_boost,
                    'boosted_categories': matched_categories
                })
            
            boosted_results.append(boosted_result)
        
        # Re-sort by boosted scores
        boosted_results.sort(key=lambda x: x.score, reverse=True)
        
        return boosted_results
    
    def explain_boosting(self, query: str, results: List) -> Dict:
        """Explain which results were boosted and why"""
        boost_terms = self.extract_boost_terms(query)
        
        explanation = {
            'query': query,
            'should_boost': self.should_boost_query(query),
            'boost_terms_by_category': boost_terms,
            'boosted_results': [],
            'boost_summary': {
                'total_results': len(results),
                'boosted_count': 0,
                'categories_triggered': list(boost_terms.keys())
            }
        }
        
        for i, result in enumerate(results):
            if hasattr(result, 'metadata') and result.metadata.get('bm25_boost_applied'):
                explanation['boosted_results'].append({
                    'rank': i + 1,
                    'doc_id': result.chunk_id,
                    'original_score': result.metadata.get('original_score', 0),
                    'boosted_score': result.score,
                    'boost_amount': result.metadata.get('boost_amount', 0),
                    'categories': result.metadata.get('boosted_categories', []),
                    'content_preview': result.content[:100] + '...'
                })
                explanation['boost_summary']['boosted_count'] += 1
        
        return explanation


# Convenience functions
def boost_infrastructure_results(query: str, results: List) -> List:
    """Quick BM25 boosting for infrastructure/scheme documents"""
    booster = BM25Booster()
    return booster.boost_results(query, results)


def should_use_bm25_boosting(query: str) -> bool:
    """Check if query should use BM25 boosting"""
    booster = BM25Booster()
    return booster.should_boost_query(query)


if __name__ == "__main__":
    # Test BM25 boosting
    booster = BM25Booster()
    
    test_queries = [
        "Nadu-Nedu infrastructure development guidelines",
        "Amma Vodi welfare scheme implementation", 
        "School building safety and security measures",
        "What is Section 12 RTE Act?",  # Should not trigger boosting
        "Teacher training programs"  # Should not trigger boosting
    ]
    
    print("BM25 Booster Test Results")
    print("=" * 80)
    
    for query in test_queries:
        should_boost = booster.should_boost_query(query)
        boost_terms = booster.extract_boost_terms(query)
        
        print(f"\nQuery: {query}")
        print(f"Should boost: {should_boost}")
        if boost_terms:
            print("Boost terms by category:")
            for category, terms in boost_terms.items():
                boost_factor = booster.category_patterns[category]['boost_factor']
                print(f"  • {category} ({boost_factor}x): {terms}")
        print("-" * 80)
    
    print(f"\nBM25 Boosting targets:")
    print("• Infrastructure documents (Nadu-Nedu, facilities)")
    print("• Welfare scheme documents (Amma Vodi, benefits)")  
    print("• Safety/compliance documents")
    print("• Technical specification documents")
    print("\nThis rescues keyword-heavy documents that semantic search misses!")