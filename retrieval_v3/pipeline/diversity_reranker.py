# Diversity Reranker - Enforce category coverage and domain diversity

"""
Diversity Reranker for V3 Pipeline
==================================
Ensures comprehensive coverage across all predicted policy categories.
Prevents clustering in 1-2 domains by enforcing mandatory diversity.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

# Import V3 components
import sys
from pathlib import Path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from query_understanding.category_predictor import CategoryPredictor, PolicyCategory


@dataclass
class CategoryResult:
    """Result with category assignment"""
    result: 'RetrievalResult'  # Will be imported from retrieval_engine
    categories: List[PolicyCategory]
    category_confidence: float
    content_keywords: List[str]


class DiversityReranker:
    """
    Enforce diversity across policy categories to ensure comprehensive coverage.
    
    Key Features:
    - Mandatory coverage: Ensure at least one result per predicted category
    - Domain diversity: Prevent clustering in similar topics
    - Quality preservation: Maintain relevance while enforcing diversity
    - Category detection: Classify results into policy categories
    """
    
    # Keywords that strongly indicate each category in result content
    CATEGORY_INDICATORS = {
        PolicyCategory.ACCESS: [
            'admission', 'enrollment', 'dropout', 'out-of-school', 'inclusion',
            'girl child education', 'SC ST', 'minority', 'disabled', 'CWSN',
            'school mapping', 'catchment', 'distance norm', 'equity', 'access'
        ],
        
        PolicyCategory.INFRASTRUCTURE: [
            'nadu nedu', 'infrastructure', 'building', 'classroom', 'toilet',
            'drinking water', 'electricity', 'playground', 'library', 'laboratory',
            'kitchen', 'boundary wall', 'ramp', 'CCTV', 'fire safety', 'TMF',
            'maintenance', 'construction', 'facility', 'sanitation'
        ],
        
        PolicyCategory.GOVERNANCE: [
            'administration', 'governance', 'management', 'inspection', 'monitoring',
            'supervision', 'compliance', 'regulation', 'DEO', 'MEO', 'DIET',
            'SCERT', 'RJD', 'CCE coordinator', 'headmaster', 'principal',
            'district collector', 'authority', 'responsibility', 'oversight'
        ],
        
        PolicyCategory.WELFARE: [
            'amma vodi', 'vidya kanuka', 'vidya deevena', 'gorumudda',
            'mid day meal', 'midday meal', 'school kit', 'uniform', 'scholarship',
            'financial assistance', 'transport', 'hostel', 'residential school',
            'welfare scheme', 'benefit', 'incentive', 'nutrition'
        ],
        
        PolicyCategory.CURRICULUM: [
            'curriculum', 'syllabus', 'textbook', 'subject', 'course', 'content',
            'learning material', 'digital content', 'e-content', 'pedagogy',
            'teaching method', 'learning outcome', 'competency', 'FLN',
            'foundational literacy', 'lesson plan', 'activity'
        ],
        
        PolicyCategory.ASSESSMENT: [
            'assessment', 'evaluation', 'examination', 'test', 'CCE',
            'continuous comprehensive evaluation', 'grading', 'marking',
            'progress tracking', 'learning assessment', 'achievement',
            'performance', 'result', 'pass', 'fail', 'promotion', 'scoring'
        ],
        
        PolicyCategory.TEACHER: [
            'teacher', 'teaching', 'faculty', 'staff', 'recruitment', 'appointment',
            'transfer', 'posting', 'training', 'capacity building',
            'professional development', 'in-service', 'pre-service',
            'teacher education', 'B.Ed', 'TET', 'DSC', 'educator'
        ]
    }
    
    def __init__(self, category_predictor: Optional[CategoryPredictor] = None):
        """Initialize diversity reranker"""
        self.category_predictor = category_predictor or CategoryPredictor()
        self._compile_keyword_patterns()
    
    def _compile_keyword_patterns(self):
        """Pre-compile keyword patterns for efficiency"""
        self.category_patterns = {}
        
        for category, keywords in self.CATEGORY_INDICATORS.items():
            patterns = []
            for keyword in keywords:
                # Create flexible pattern that matches variations
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                patterns.append(re.compile(pattern, re.IGNORECASE))
            self.category_patterns[category] = patterns
    
    def rerank_with_diversity(
        self,
        query: str,
        results: List,  # List[RetrievalResult] 
        predicted_categories: List[PolicyCategory],
        top_k: int = 20,
        min_per_category: int = 1,
        diversity_weight: float = 0.4
    ) -> List:
        """
        Rerank results to ensure category diversity and comprehensive coverage
        
        Args:
            query: Original query
            results: List of RetrievalResult objects
            predicted_categories: Categories that should be covered
            top_k: Final number of results
            min_per_category: Minimum results per predicted category
            diversity_weight: Weight for diversity vs relevance (0.0 to 1.0)
            
        Returns:
            Reranked list with enforced category diversity
        """
        if not results or not predicted_categories:
            return results[:top_k]
        
        # Step 1: Classify all results into categories
        categorized_results = self._classify_results(results, predicted_categories)
        
        # Step 2: Group results by category
        category_groups = self._group_by_categories(categorized_results)
        
        # Step 3: Ensure mandatory coverage
        selected_results = []
        used_result_ids = set()
        
        # First pass: Ensure at least min_per_category for each predicted category
        for category in predicted_categories:
            category_results = category_groups.get(category, [])
            
            # Sort by relevance score within category
            category_results.sort(key=lambda x: x.result.score, reverse=True)
            
            # Select top results from this category
            selected_from_category = 0
            for cat_result in category_results:
                if (selected_from_category < min_per_category and 
                    cat_result.result.chunk_id not in used_result_ids and
                    len(selected_results) < top_k):
                    
                    selected_results.append(cat_result.result)
                    used_result_ids.add(cat_result.result.chunk_id)
                    selected_from_category += 1
        
        # Step 4: Fill remaining slots with best remaining results
        remaining_results = [
            cat_result for cat_result in categorized_results 
            if cat_result.result.chunk_id not in used_result_ids
        ]
        
        # Sort remaining by combined score (relevance + diversity)
        remaining_results.sort(
            key=lambda x: self._calculate_combined_score(
                x, selected_results, diversity_weight
            ),
            reverse=True
        )
        
        # Add remaining results up to top_k
        for cat_result in remaining_results:
            if len(selected_results) >= top_k:
                break
            selected_results.append(cat_result.result)
            used_result_ids.add(cat_result.result.chunk_id)
        
        return selected_results
    
    def _classify_results(
        self, 
        results: List, 
        predicted_categories: List[PolicyCategory]
    ) -> List[CategoryResult]:
        """Classify each result into policy categories"""
        categorized_results = []
        
        for result in results:
            # Analyze content to determine categories
            categories, confidence, keywords = self._analyze_content_categories(
                result.content, predicted_categories
            )
            
            categorized_results.append(CategoryResult(
                result=result,
                categories=categories,
                category_confidence=confidence,
                content_keywords=keywords
            ))
        
        return categorized_results
    
    def _analyze_content_categories(
        self, 
        content: str, 
        predicted_categories: List[PolicyCategory]
    ) -> Tuple[List[PolicyCategory], float, List[str]]:
        """Analyze content and assign to policy categories"""
        category_scores = {}
        found_keywords = []
        
        # Score each predicted category based on keyword matches
        for category in predicted_categories:
            score = 0.0
            category_keywords = []
            
            if category in self.category_patterns:
                for pattern in self.category_patterns[category]:
                    matches = pattern.findall(content)
                    if matches:
                        score += len(matches)
                        category_keywords.extend(matches)
            
            if score > 0:
                category_scores[category] = score
                found_keywords.extend(category_keywords)
        
        # Assign to categories with score > 0
        assigned_categories = [
            cat for cat, score in category_scores.items() if score > 0
        ]
        
        # If no categories matched, assign to most likely category based on content
        if not assigned_categories and predicted_categories:
            assigned_categories = [predicted_categories[0]]  # Default to first predicted
        
        # Calculate confidence based on total keyword matches
        confidence = min(sum(category_scores.values()) / 5.0, 1.0)  # Normalize to 0-1
        
        return assigned_categories, confidence, found_keywords[:10]  # Limit keywords
    
    def _group_by_categories(
        self, 
        categorized_results: List[CategoryResult]
    ) -> Dict[PolicyCategory, List[CategoryResult]]:
        """Group results by their assigned categories"""
        groups = defaultdict(list)
        
        for cat_result in categorized_results:
            for category in cat_result.categories:
                groups[category].append(cat_result)
        
        return dict(groups)
    
    def _calculate_combined_score(
        self,
        cat_result: CategoryResult,
        selected_results: List,
        diversity_weight: float
    ) -> float:
        """Calculate combined relevance + diversity score"""
        relevance_score = cat_result.result.score
        
        # Diversity bonus for underrepresented categories
        diversity_bonus = 0.0
        
        # Count how many results we already have from each category
        selected_category_counts = Counter()
        for result in selected_results:
            # Note: This is simplified - in real implementation, 
            # we'd need to re-analyze selected results for categories
            vertical = getattr(result, 'vertical', 'unknown')
            selected_category_counts[vertical] += 1
        
        # Give bonus for categories that are underrepresented
        for category in cat_result.categories:
            category_count = selected_category_counts.get(category.value, 0)
            if category_count == 0:
                diversity_bonus += 0.3  # Big bonus for first result in category
            elif category_count == 1:
                diversity_bonus += 0.1  # Small bonus for second result
        
        # Combine relevance and diversity
        combined_score = (
            (1.0 - diversity_weight) * relevance_score + 
            diversity_weight * diversity_bonus
        )
        
        return combined_score
    
    def get_category_coverage_report(
        self, 
        query: str, 
        results: List,
        predicted_categories: List[PolicyCategory]
    ) -> Dict:
        """Generate report on category coverage in results"""
        categorized_results = self._classify_results(results, predicted_categories)
        category_groups = self._group_by_categories(categorized_results)
        
        report = {
            'query': query,
            'predicted_categories': [cat.value for cat in predicted_categories],
            'total_results': len(results),
            'category_coverage': {},
            'missing_categories': [],
            'coverage_score': 0.0
        }
        
        # Analyze coverage for each predicted category
        covered_categories = 0
        for category in predicted_categories:
            count = len(category_groups.get(category, []))
            report['category_coverage'][category.value] = {
                'result_count': count,
                'covered': count > 0
            }
            
            if count > 0:
                covered_categories += 1
            else:
                report['missing_categories'].append(category.value)
        
        # Calculate overall coverage score
        if predicted_categories:
            report['coverage_score'] = covered_categories / len(predicted_categories)
        
        return report
    
    def explain_reranking(
        self,
        query: str,
        original_results: List,
        reranked_results: List,
        predicted_categories: List[PolicyCategory]
    ) -> Dict:
        """Explain the reranking decisions"""
        original_categorized = self._classify_results(original_results, predicted_categories)
        reranked_categorized = self._classify_results(reranked_results, predicted_categories)
        
        explanation = {
            'query': query,
            'predicted_categories': [cat.value for cat in predicted_categories],
            'original_coverage': self._get_coverage_summary(original_categorized, predicted_categories),
            'reranked_coverage': self._get_coverage_summary(reranked_categorized, predicted_categories),
            'diversity_improvements': [],
            'relevance_vs_diversity_tradeoffs': []
        }
        
        # Compare coverage before and after
        for category in predicted_categories:
            orig_count = len([r for r in original_categorized if category in r.categories])
            rerank_count = len([r for r in reranked_categorized if category in r.categories])
            
            if rerank_count > orig_count:
                explanation['diversity_improvements'].append({
                    'category': category.value,
                    'improvement': f"Increased from {orig_count} to {rerank_count} results"
                })
        
        return explanation
    
    def _get_coverage_summary(
        self, 
        categorized_results: List[CategoryResult], 
        predicted_categories: List[PolicyCategory]
    ) -> Dict:
        """Get summary of category coverage"""
        category_counts = Counter()
        for cat_result in categorized_results:
            for category in cat_result.categories:
                category_counts[category] += 1
        
        return {
            'categories_covered': len(category_counts),
            'categories_missing': len(predicted_categories) - len(category_counts),
            'coverage_by_category': {
                cat.value: category_counts.get(cat, 0) 
                for cat in predicted_categories
            }
        }


# Convenience function
def rerank_for_diversity(
    query: str,
    results: List,
    top_k: int = 20,
    diversity_weight: float = 0.4
) -> List:
    """Quick diversity reranking"""
    predictor = CategoryPredictor()
    predicted_categories = predictor.predict_categories(query)
    
    reranker = DiversityReranker(predictor)
    return reranker.rerank_with_diversity(
        query, results, predicted_categories, top_k, diversity_weight=diversity_weight
    )


if __name__ == "__main__":
    # Test diversity reranker
    print("Diversity Reranker Test")
    print("=" * 80)
    
    # This would normally use actual RetrievalResult objects
    # For testing, we'll simulate the structure
    
    test_query = "What are the current education policies in Andhra Pradesh?"
    predictor = CategoryPredictor()
    predicted_categories = predictor.predict_categories(test_query)
    
    print(f"Query: {test_query}")
    print(f"Predicted Categories: {[cat.value for cat in predicted_categories]}")
    
    reranker = DiversityReranker(predictor)
    
    # Simulate some test content for different categories
    test_contents = [
        "Digital education and technology integration in classrooms...",
        "Nadu-Nedu infrastructure development guidelines for school buildings...", 
        "Amma Vodi welfare scheme implementation procedures...",
        "Teacher recruitment and transfer policies in AP education department...",
        "Continuous comprehensive evaluation and assessment framework...",
        "Inclusive education policies for children with special needs...",
        "School governance and administration guidelines..."
    ]
    
    print(f"\nCategory Analysis for Sample Contents:")
    print("-" * 60)
    
    for i, content in enumerate(test_contents, 1):
        categories, confidence, keywords = reranker._analyze_content_categories(
            content, predicted_categories
        )
        print(f"{i}. Categories: {[cat.value for cat in categories]}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Keywords: {keywords[:3]}")
        print(f"   Content: {content[:50]}...")
        print()