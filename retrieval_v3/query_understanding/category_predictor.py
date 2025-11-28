# Category Predictor - Predict policy domains for comprehensive coverage

"""
Category Predictor for AP Education Policies
===========================================
Predicts which policy categories a query should cover to ensure comprehensive answers.
Enforces mandatory coverage across all 7 key policy domains.
"""

import re
from typing import List, Dict, Set
from enum import Enum


class PolicyCategory(Enum):
    """7 Core AP Education Policy Categories"""
    ACCESS = "access"                    # Access, enrollment, dropouts, barriers
    INFRASTRUCTURE = "infrastructure"    # Nadu-Nedu, buildings, toilets, safety
    GOVERNANCE = "governance"           # Administration, inspection, compliance
    WELFARE = "welfare"                 # Schemes: Amma Vodi, Vidya Kanuka, Gorumudda
    CURRICULUM = "curriculum"           # Syllabus, textbooks, subjects, digital content
    ASSESSMENT = "assessment"           # Exams, evaluation, CCE, grading
    TEACHER = "teacher"                # Recruitment, transfer, training, management


class CategoryPredictor:
    """Predict which policy categories should be covered for a query"""
    
    # Category-specific keywords and patterns
    CATEGORY_KEYWORDS = {
        PolicyCategory.ACCESS: {
            'primary': [
                'admission', 'enrollment', 'enrolment', 'dropout', 'out of school',
                'access', 'inclusion', 'equity', 'girl child', 'SC/ST', 'minority',
                'disabled children', 'CWSN', 'vulnerable', 'disadvantaged',
                'school mapping', 'catchment area', 'distance norms'
            ],
            'secondary': [
                'barrier', 'retention', 'attendance', 'participation',
                'inclusive education', 'special needs', 'tribal', 'urban slum'
            ]
        },
        
        PolicyCategory.INFRASTRUCTURE: {
            'primary': [
                'nadu nedu', 'infrastructure', 'building', 'classroom', 'toilet',
                'drinking water', 'electricity', 'playground', 'library',
                'laboratory', 'kitchen', 'boundary wall', 'ramp', 'CCTV',
                'fire safety', 'TMF', 'maintenance', 'construction'
            ],
            'secondary': [
                'facility', 'equipment', 'furniture', 'sanitation', 'hygiene',
                'safety', 'security', 'accessibility', 'barrier free'
            ]
        },
        
        PolicyCategory.GOVERNANCE: {
            'primary': [
                'administration', 'governance', 'management', 'inspection',
                'monitoring', 'supervision', 'compliance', 'regulation',
                'DEO', 'MEO', 'DIET', 'SCERT', 'RJD', 'CCE coordinator',
                'headmaster', 'principal', 'district collector'
            ],
            'secondary': [
                'authority', 'responsibility', 'accountability', 'oversight',
                'quality assurance', 'institutional framework'
            ]
        },
        
        PolicyCategory.WELFARE: {
            'primary': [
                'amma vodi', 'vidya kanuka', 'vidya deevena', 'gorumudda',
                'mid day meal', 'midday meal', 'school kit', 'uniform',
                'scholarship', 'financial assistance', 'transport', 'hostel',
                'residential school', 'welfare scheme', 'benefit'
            ],
            'secondary': [
                'incentive', 'support', 'assistance', 'allowance', 'stipend',
                'nutrition', 'health checkup', 'medical care'
            ]
        },
        
        PolicyCategory.CURRICULUM: {
            'primary': [
                'curriculum', 'syllabus', 'textbook', 'subject', 'course',
                'content', 'learning material', 'digital content', 'e-content',
                'pedagogy', 'teaching method', 'learning outcome',
                'competency', 'skill development', 'FLN', 'foundational literacy'
            ],
            'secondary': [
                'academic', 'educational content', 'lesson plan', 'activity',
                'project based learning', 'experiential learning'
            ]
        },
        
        PolicyCategory.ASSESSMENT: {
            'primary': [
                'assessment', 'evaluation', 'examination', 'test', 'CCE',
                'continuous comprehensive evaluation', 'grading', 'marking',
                'progress tracking', 'learning assessment', 'achievement',
                'performance', 'result', 'pass', 'fail', 'promotion'
            ],
            'secondary': [
                'measurement', 'scoring', 'feedback', 'report card',
                'academic performance', 'learning level'
            ]
        },
        
        PolicyCategory.TEACHER: {
            'primary': [
                'teacher', 'teaching', 'faculty', 'staff', 'recruitment',
                'appointment', 'transfer', 'posting', 'training', 'capacity building',
                'professional development', 'in-service training', 'pre-service',
                'teacher education', 'B.Ed', 'TET', 'DSC'
            ],
            'secondary': [
                'educator', 'instructor', 'human resource', 'personnel',
                'qualification', 'certification', 'competency', 'skill enhancement'
            ]
        }
    }
    
    # Broad query patterns that should trigger multiple categories
    BROAD_QUERY_PATTERNS = [
        r'\b(?:current|latest|all|comprehensive|complete|overall)\s+(?:education\s+)?policies?\b',
        r'\beducation\s+(?:system|framework|structure|overview)\b',
        r'\b(?:list|overview|summary)\s+(?:of\s+)?(?:all\s+)?(?:education\s+)?(?:policies|initiatives|schemes)\b',
        r'\beducation\s+(?:in\s+)?(?:andhra\s+pradesh|AP)\b',
        r'\bap\s+education\s+(?:department|system|policies)\b',
        r'\bstate\s+education\s+policies?\b'
    ]
    
    # Category combinations for different query types
    MANDATORY_COMBINATIONS = {
        'broad_policy': [  # For "current education policies", "AP education system"
            PolicyCategory.ACCESS,
            PolicyCategory.INFRASTRUCTURE, 
            PolicyCategory.GOVERNANCE,
            PolicyCategory.WELFARE,
            PolicyCategory.CURRICULUM,
            PolicyCategory.ASSESSMENT,
            PolicyCategory.TEACHER
        ],
        'implementation': [  # For "policy implementation", "execution"
            PolicyCategory.GOVERNANCE,
            PolicyCategory.INFRASTRUCTURE,
            PolicyCategory.WELFARE,
            PolicyCategory.TEACHER
        ],
        'quality': [  # For "education quality", "learning outcomes"
            PolicyCategory.CURRICULUM,
            PolicyCategory.ASSESSMENT,
            PolicyCategory.TEACHER,
            PolicyCategory.INFRASTRUCTURE
        ],
        'equity': [  # For "inclusive education", "equity"
            PolicyCategory.ACCESS,
            PolicyCategory.WELFARE,
            PolicyCategory.INFRASTRUCTURE,
            PolicyCategory.GOVERNANCE
        ]
    }
    
    def __init__(self):
        """Initialize category predictor"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        self.broad_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.BROAD_QUERY_PATTERNS]
        
        # Compile keyword patterns for each category
        self.keyword_patterns = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            patterns = []
            for keyword in keywords['primary'] + keywords['secondary']:
                # Create word boundary pattern for each keyword
                pattern = r'\b' + re.escape(keyword) + r'\b'
                patterns.append(re.compile(pattern, re.IGNORECASE))
            self.keyword_patterns[category] = patterns
    
    def predict_categories(self, query: str, query_type: str = "lookup") -> List[PolicyCategory]:
        """
        Predict which policy categories should be covered
        
        Args:
            query: User query
            query_type: Type of query (lookup, deep_think, brainstorm)
            
        Returns:
            List of PolicyCategory enums that should be covered
        """
        predicted_categories = set()
        
        # Check for broad query patterns first
        if self._is_broad_query(query):
            if query_type in ["deep_think", "brainstorm"]:
                # For complex queries, ensure all categories
                return list(PolicyCategory)
            else:
                # For simple broad queries, return top 5 categories
                predicted_categories.update(self.MANDATORY_COMBINATIONS['broad_policy'][:5])
        
        # Detect specific categories from keywords
        category_scores = self._score_categories(query)
        
        # Add high-confidence categories
        for category, score in category_scores.items():
            if score >= 2.0:  # Primary keyword match
                predicted_categories.add(category)
        
        # Ensure minimum coverage based on query patterns
        predicted_categories.update(self._get_mandatory_categories(query))
        
        # Convert to sorted list (by priority)
        return self._prioritize_categories(list(predicted_categories), category_scores)
    
    def _is_broad_query(self, query: str) -> bool:
        """Check if query is asking for broad policy coverage"""
        for pattern in self.broad_patterns:
            if pattern.search(query):
                return True
        return False
    
    def _score_categories(self, query: str) -> Dict[PolicyCategory, float]:
        """Score each category based on keyword matches"""
        category_scores = {category: 0.0 for category in PolicyCategory}
        
        for category, patterns in self.keyword_patterns.items():
            score = 0.0
            
            # Check primary keywords (higher weight)
            for keyword in self.CATEGORY_KEYWORDS[category]['primary']:
                keyword_pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                matches = len(keyword_pattern.findall(query))
                score += matches * 2.0  # Primary keywords worth 2 points each
            
            # Check secondary keywords (lower weight) 
            for keyword in self.CATEGORY_KEYWORDS[category]['secondary']:
                keyword_pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                matches = len(keyword_pattern.findall(query))
                score += matches * 1.0  # Secondary keywords worth 1 point each
            
            category_scores[category] = score
        
        return category_scores
    
    def _get_mandatory_categories(self, query: str) -> List[PolicyCategory]:
        """Get categories that should always be included for certain query types"""
        mandatory = []
        
        # Policy implementation queries
        if re.search(r'\b(?:implementation|execution|roll|deploy)\b', query, re.IGNORECASE):
            mandatory.extend(self.MANDATORY_COMBINATIONS['implementation'])
        
        # Quality and learning outcome queries  
        if re.search(r'\b(?:quality|outcome|performance|improvement)\b', query, re.IGNORECASE):
            mandatory.extend(self.MANDATORY_COMBINATIONS['quality'])
        
        # Equity and inclusion queries
        if re.search(r'\b(?:inclusive|equity|equal|disadvantaged|vulnerable)\b', query, re.IGNORECASE):
            mandatory.extend(self.MANDATORY_COMBINATIONS['equity'])
        
        return mandatory
    
    def _prioritize_categories(self, categories: List[PolicyCategory], scores: Dict[PolicyCategory, float]) -> List[PolicyCategory]:
        """Sort categories by priority and relevance scores"""
        # Default priority order (most fundamental first)
        priority_order = [
            PolicyCategory.ACCESS,      # Foundation of education system
            PolicyCategory.INFRASTRUCTURE,  # Physical foundation  
            PolicyCategory.GOVERNANCE,  # System management
            PolicyCategory.WELFARE,     # Student support
            PolicyCategory.TEACHER,     # Human resource
            PolicyCategory.CURRICULUM,  # Academic content
            PolicyCategory.ASSESSMENT   # Measurement
        ]
        
        # Sort by: 1) Score (if available), 2) Priority order
        def sort_key(category):
            score = scores.get(category, 0)
            priority = priority_order.index(category) if category in priority_order else 999
            return (-score, priority)  # Negative score for descending order
        
        return sorted(categories, key=sort_key)
    
    def get_category_keywords(self, category: PolicyCategory) -> List[str]:
        """Get all keywords for a specific category"""
        if category in self.CATEGORY_KEYWORDS:
            keywords = self.CATEGORY_KEYWORDS[category]
            return keywords['primary'] + keywords['secondary']
        return []
    
    def explain_prediction(self, query: str) -> Dict:
        """Explain why certain categories were predicted"""
        category_scores = self._score_categories(query)
        predicted = self.predict_categories(query)
        
        explanation = {
            'query': query,
            'is_broad_query': self._is_broad_query(query),
            'predicted_categories': [cat.value for cat in predicted],
            'category_scores': {cat.value: score for cat, score in category_scores.items()},
            'reasoning': []
        }
        
        # Add reasoning for each predicted category
        for category in predicted:
            score = category_scores.get(category, 0)
            keywords_found = []
            
            # Find which keywords triggered this category
            for keyword in self.get_category_keywords(category):
                if re.search(r'\b' + re.escape(keyword) + r'\b', query, re.IGNORECASE):
                    keywords_found.append(keyword)
            
            reasoning = {
                'category': category.value,
                'score': score,
                'keywords_found': keywords_found,
                'confidence': 'high' if score >= 2.0 else 'medium' if score >= 1.0 else 'low'
            }
            explanation['reasoning'].append(reasoning)
        
        return explanation


# Convenience functions
def predict_categories(query: str, query_type: str = "lookup") -> List[str]:
    """Quick category prediction - returns category names"""
    predictor = CategoryPredictor()
    categories = predictor.predict_categories(query, query_type)
    return [cat.value for cat in categories]


if __name__ == "__main__":
    # Test the category predictor
    predictor = CategoryPredictor()
    
    test_queries = [
        "What are the current education policies in Andhra Pradesh?",
        "Nadu-Nedu infrastructure development guidelines",
        "Amma Vodi scheme implementation",
        "Teacher transfer policies and procedures",
        "Comprehensive evaluation and assessment framework",
        "Inclusive education for disabled children",
        "Digital content and curriculum development"
    ]
    
    print("Category Predictor Test Results")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        categories = predictor.predict_categories(query)
        explanation = predictor.explain_prediction(query)
        
        print(f"Predicted Categories ({len(categories)}):")
        for i, category in enumerate(categories, 1):
            score = explanation['category_scores'][category.value]
            print(f"  {i}. {category.value.title()} (score: {score:.1f})")
        
        print(f"Is Broad Query: {explanation['is_broad_query']}")
        
        if explanation['reasoning']:
            print("Top Keywords Found:")
            for reasoning in explanation['reasoning'][:3]:
                if reasoning['keywords_found']:
                    print(f"  • {reasoning['category']}: {', '.join(reasoning['keywords_found'][:3])}")
        
        print("=" * 80)