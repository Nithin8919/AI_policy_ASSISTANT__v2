# Category Predictor - LLM-based category prediction

"""
Category Predictor - Predict expected document categories
Categories: infrastructure, safety, FLN, teacher, academic, monitoring, welfare
"""

from typing import List, Dict, Set
import re


class CategoryPredictor:
    """Predict which document categories are relevant for a query"""
    
    # Category keywords (from domain taxonomy)
    CATEGORY_KEYWORDS = {
        'infrastructure': [
            'infrastructure', 'building', 'classroom', 'toilet', 'water',
            'electricity', 'furniture', 'playground', 'library', 'lab',
            'construction', 'renovation', 'maintenance', 'facilities',
            'boundary wall', 'compound', 'ramp', 'accessibility'
        ],
        
        'safety': [
            'safety', 'security', 'cctv', 'fire', 'emergency', 'fence',
            'guard', 'watchman', 'gate', 'lighting', 'first aid',
            'medical', 'hygiene', 'sanitation', 'health'
        ],
        
        'fln': [
            'fln', 'literacy', 'numeracy', 'reading', 'writing', 'math',
            'mathematics', 'foundational', 'learning outcomes', 'basic skills',
            'grade level', 'competencies', 'early grade'
        ],
        
        'teacher': [
            'teacher', 'educator', 'faculty', 'staff', 'training',
            'recruitment', 'transfer', 'posting', 'promotion', 'appraisal',
            'tet', 'qualification', 'professional development', 'headmaster',
            'principal', 'subject teacher'
        ],
        
        'academic': [
            'curriculum', 'syllabus', 'textbook', 'tlm', 'pedagogy',
            'assessment', 'examination', 'evaluation', 'grades', 'marks',
            'promotion', 'academic', 'subject', 'timetable', 'calendar'
        ],
        
        'monitoring': [
            'monitoring', 'supervision', 'inspection', 'udise', 'data',
            'reporting', 'compliance', 'quality', 'performance', 'indicators',
            'metrics', 'dashboard', 'enrollment', 'attendance', 'dropout'
        ],
        
        'welfare': [
            'midday meal', 'mdm', 'scholarship', 'uniform', 'bicycle',
            'hostel', 'nutrition', 'incentive', 'stipend', 'cwsn',
            'special needs', 'inclusion', 'sc/st', 'minority', 'girl'
        ],
        
        'governance': [
            'smc', 'smdc', 'pta', 'management', 'committee', 'community',
            'participation', 'policy', 'guideline', 'rule', 'regulation',
            'act', 'government order', 'circular'
        ]
    }
    
    def __init__(self):
        """Initialize predictor"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile keyword patterns"""
        self.patterns = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            # Create pattern for each keyword
            self.patterns[category] = [
                re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                for kw in keywords
            ]
    
    def predict_categories(
        self, 
        query: str, 
        top_k: int = 3,
        threshold: float = 0.1
    ) -> List[str]:
        """
        Predict relevant categories for a query
        
        Args:
            query: User query
            top_k: Return top K categories
            threshold: Minimum score to include (0-1)
            
        Returns:
            List of category names
        """
        # Score each category
        scores = {}
        
        for category, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(query):
                    # Weight by keyword length (longer = more specific)
                    score += len(pattern.pattern.split())
            scores[category] = score
        
        # Normalize scores
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            scores = {k: v/max_score for k, v in scores.items()}
        
        # Filter by threshold
        filtered = {k: v for k, v in scores.items() if v >= threshold}
        
        # Sort and return top K
        sorted_categories = sorted(
            filtered.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [cat for cat, score in sorted_categories[:top_k]]
    
    def get_category_keywords(self, category: str) -> List[str]:
        """Get keywords for a specific category"""
        return self.CATEGORY_KEYWORDS.get(category, [])
    
    def predict_with_scores(self, query: str) -> Dict[str, float]:
        """
        Get category predictions with confidence scores
        
        Returns:
            Dict mapping category -> score
        """
        scores = {}
        
        for category, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(query):
                    score += len(pattern.pattern.split())
            scores[category] = score
        
        # Normalize
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            scores = {k: v/max_score for k, v in scores.items()}
        
        return scores


# Convenience function
def predict_categories(query: str, top_k: int = 3) -> List[str]:
    """Quick category prediction"""
    predictor = CategoryPredictor()
    return predictor.predict_categories(query, top_k)


if __name__ == "__main__":
    predictor = CategoryPredictor()
    
    test_queries = [
        "How to improve school toilet facilities?",
        "Teacher transfer rules and procedures",
        "FLN implementation in primary schools",
        "CCTV installation requirements for safety",
        "Midday meal quality standards",
        "UDISE data collection and reporting",
    ]
    
    print("Category Predictor Tests:")
    print("=" * 80)
    
    for query in test_queries:
        categories = predictor.predict_categories(query, top_k=3)
        scores = predictor.predict_with_scores(query)
        
        print(f"\nQuery: {query}")
        print(f"Predicted Categories: {categories}")
        print("Scores:")
        for cat in categories:
            print(f"  {cat}: {scores[cat]:.3f}")
        print("-" * 80)




