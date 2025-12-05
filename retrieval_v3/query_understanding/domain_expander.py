# Domain Expander - big keyword dictionary

"""
Domain Expander - Add domain-specific synonyms and keywords
Massive keyword dictionary for AP Education Policy domain
"""

from typing import List, Set, Dict
import re


class DomainExpander:
    """Expand queries with domain-specific synonyms and related terms"""
    
    # Comprehensive domain synonym dictionary covering all 7 policy categories
    DOMAIN_EXPANSIONS = {
        # INFRASTRUCTURE TERMS (Nadu-Nedu and facilities)
        'infrastructure': [
            'nadu nedu', 'facilities', 'buildings', 'construction', 'physical infrastructure',
            'school buildings', 'classrooms', 'premises', 'property', 'assets', 'TMF'
        ],
        'nadu nedu': [
            'infrastructure development', 'building construction', 'facility upgradation',
            'school infrastructure', 'physical infrastructure', 'construction work'
        ],
        'toilet': [
            'toilets', 'latrines', 'sanitation facilities', 'washrooms', 'restrooms',
            'urinals', 'water closets', 'sanitary facilities', 'hygiene facilities'
        ],
        'classroom': [
            'classrooms', 'teaching rooms', 'learning spaces', 'teaching spaces',
            'instruction rooms', 'class', 'classes', 'smart classroom'
        ],
        'electricity': [
            'power', 'electrical supply', 'power supply', 'electrification',
            'lighting', 'electric connection', 'power connection', 'electrical work'
        ],
        'water': [
            'drinking water', 'potable water', 'safe drinking water',
            'water supply', 'water source', 'water facility', 'bore well'
        ],
        'boundary': [
            'boundary wall', 'compound wall', 'perimeter wall', 'fencing',
            'school boundary', 'boundary fence', 'compound', 'gate'
        ],
        'furniture': [
            'benches', 'desks', 'chairs', 'tables', 'seating', 'school furniture',
            'student furniture', 'classroom furniture', 'blackboard'
        ],
        'playground': [
            'playgrounds', 'play area', 'sports ground', 'sports field',
            'playing field', 'recreation ground', 'outdoor space'
        ],
        'library': [
            'libraries', 'reading room', 'book room', 'resource room',
            'learning resource center', 'library facility'
        ],
        'lab': [
            'laboratory', 'labs', 'science lab', 'computer lab',
            'practical room', 'experimental room'
        ],
        'kitchen': [
            'cooking facility', 'food preparation', 'midday meal kitchen',
            'nutrition center', 'food storage', 'cooking area'
        ],
        'ramp': [
            'ramps', 'accessibility ramp', 'wheelchair access', 'barrier free access',
            'inclusive infrastructure', 'accessibility features'
        ],
        
        # SAFETY & SECURITY TERMS  
        'safety': [
            'security', 'safe', 'safety measures', 'safety provisions', 'protection',
            'safety standards', 'safety norms', 'fire safety', 'child protection'
        ],
        'cctv': [
            'surveillance', 'cameras', 'security cameras', 'monitoring cameras',
            'CCTV cameras', 'video surveillance', 'camera system'
        ],
        'fire safety': [
            'fire prevention', 'fire drill', 'fire extinguisher', 'emergency exit',
            'evacuation plan', 'fire safety measures', 'fire protection'
        ],
        'security': [
            'safety', 'protection', 'security guard', 'watchman', 'gate security',
            'visitor management', 'security protocol', 'campus security'
        ],
        
        # WELFARE SCHEMES TERMS
        'amma vodi': [
            'financial assistance', 'mother assistance', 'school fee support',
            'education financial aid', 'student welfare scheme'
        ],
        'vidya kanuka': [
            'school kit', 'learning material', 'educational kit', 'student kit',
            'free school supplies', 'textbook distribution'
        ],
        'vidya deevena': [
            'scholarship', 'merit scholarship', 'educational scholarship',
            'student scholarship', 'academic scholarship'
        ],
        'gorumudda': [
            'midday meal', 'nutrition program', 'school meal', 'free meal',
            'food program', 'nutritional support', 'meal scheme'
        ],
        'midday meal': [
            'gorumudda', 'nutrition program', 'school meal', 'free meal',
            'MDM', 'food program', 'nutritional support', 'meal scheme'
        ],
        'scholarship': [
            'financial aid', 'educational assistance', 'merit award',
            'student support', 'academic scholarship', 'financial support'
        ],
        'transport': [
            'transportation', 'bus service', 'school bus', 'vehicle',
            'conveyance', 'student transport', 'travel allowance'
        ],
        'hostel': [
            'residential facility', 'boarding', 'accommodation',
            'student hostel', 'residential school', 'boarding facility'
        ],
        'uniform': [
            'school dress', 'dress code', 'school uniform', 'clothing',
            'dress allowance', 'uniform provision'
        ],
        
        # HEALTH & MEDICAL TERMS
        'health': [
            'healthcare', 'medical', 'health services', 'health facilities',
            'medical care', 'hygiene', 'health and hygiene', 'wellness'
        ],
        'medical': [
            'health checkup', 'medical examination', 'medical screening',
            'health assessment', 'medical care', 'health services'
        ],
        'first aid': [
            'medical aid', 'emergency care', 'first aid kit', 'medical kit',
            'emergency medical care', 'first aid box'
        ],
        
        # TEACHER DEVELOPMENT TERMS
        'teacher': [
            'educator', 'instructor', 'faculty', 'teaching staff', 'academic staff',
            'teaching personnel', 'educational staff'
        ],
        'training': [
            'capacity building', 'professional development', 'skill development',
            'teacher training', 'in-service training', 'faculty development'
        ],
        'recruitment': [
            'appointment', 'selection', 'hiring', 'teacher recruitment',
            'staff selection', 'employment', 'DSC', 'TET'
        ],
        'transfer': [
            'posting', 'deployment', 'relocation', 'teacher transfer',
            'staff transfer', 'redeployment'
        ],
        
        # ASSESSMENT & EVALUATION TERMS
        'assessment': [
            'evaluation', 'examination', 'testing', 'appraisal', 'grading',
            'performance assessment', 'learning assessment'
        ],
        'cce': [
            'continuous comprehensive evaluation', 'continuous assessment',
            'ongoing evaluation', 'formative assessment', 'progress tracking'
        ],
        'examination': [
            'test', 'exam', 'assessment', 'evaluation', 'academic test',
            'performance test', 'achievement test'
        ],
        
        # FLN (Foundational Literacy & Numeracy)
        'fln': [
            'foundational literacy numeracy', 'foundational learning',
            'basic literacy', 'basic numeracy', 'foundational skills',
            'early learning', 'foundational competencies'
        ],
        
        # AI and Technology Integration
        'ai': [
            'artificial intelligence', 'technology integration', 'digital learning',
            'smart classroom', 'educational technology', 'atal tinkering labs',
            'atl', 'coding', 'robotics', 'innovation labs', 'stem education',
            'nep 2020', 'national education policy', 'digital education',
            'technology enhanced learning', 'computer education'
        ],
        'technology': [
            'artificial intelligence', 'ai', 'digital technology', 'educational technology',
            'atal tinkering labs', 'atl', 'innovation', 'coding', 'robotics',
            'smart classroom', 'digital learning', 'computer education',
            'technology integration', 'stem education', 'digital literacy'
        ],
        'integration': [
            'implementation', 'adoption', 'deployment', 'incorporation',
            'embedding', 'infusion', 'mainstream', 'curriculum integration'
        ],
        'curriculum': [
            'syllabus', 'course', 'course content', 'academic curriculum',
            'study program', 'educational program', 'course of study',
            'curriculum framework', 'learning framework', 'academic framework'
        ],
        'literacy': [
            'reading', 'reading skills', 'reading ability', 'literate',
            'reading proficiency', 'reading competency', 'language skills'
        ],
        'numeracy': [
            'mathematics', 'math', 'maths', 'numerical skills', 'number skills',
            'mathematical ability', 'arithmetic', 'calculation skills'
        ],
        'reading': [
            'reading comprehension', 'reading fluency', 'reading ability',
            'text comprehension', 'reading skills', 'literacy'
        ],
        'learning outcomes': [
            'learning goals', 'competencies', 'learning competencies',
            'achievement levels', 'learning levels', 'educational outcomes',
            'student outcomes', 'academic outcomes'
        ],
        
        # Teacher-related
        'teacher': [
            'teachers', 'educator', 'educators', 'faculty', 'teaching staff',
            'instructor', 'teaching personnel', 'school teacher'
        ],
        'training': [
            'teacher training', 'professional development', 'capacity building',
            'in-service training', 'orientation', 'workshop', 'training program'
        ],
        'transfer': [
            'transfers', 'posting', 'deployment', 'teacher posting',
            'teacher deployment', 'teacher movement', 'relocation'
        ],
        'recruitment': [
            'appointment', 'hiring', 'teacher appointment', 'teacher hiring',
            'teacher selection', 'employment', 'teacher employment'
        ],
        'tet': [
            'teacher eligibility test', 'TET exam', 'teacher qualification',
            'teaching eligibility', 'APTET', 'CTET'
        ],
        
        # Academic & Curriculum
        'curriculum': [
            'syllabus', 'course', 'course content', 'academic curriculum',
            'study program', 'educational program', 'course of study'
        ],
        'textbook': [
            'textbooks', 'books', 'course books', 'study material',
            'learning material', 'teaching material', 'study books'
        ],
        'tlm': [
            'teaching learning material', 'teaching aids', 'learning aids',
            'instructional material', 'educational aids', 'teaching resources'
        ],
        'assessment': [
            'evaluation', 'examination', 'testing', 'student assessment',
            'learning assessment', 'academic assessment', 'performance evaluation'
        ],
        'examination': [
            'exam', 'test', 'examinations', 'assessment', 'evaluation',
            'public examination', 'board exam', 'school exam'
        ],
        
        # Monitoring & Data
        'monitoring': [
            'supervision', 'oversight', 'tracking', 'monitoring system',
            'surveillance', 'observation', 'quality monitoring'
        ],
        'udise': [
            'UDISE+', 'unified district information', 'school data',
            'education data', 'UDISE data', 'district information system'
        ],
        'data': [
            'information', 'statistics', 'data collection', 'records',
            'database', 'data system', 'information system'
        ],
        'compliance': [
            'adherence', 'conformity', 'following norms', 'meeting standards',
            'regulatory compliance', 'compliance with rules'
        ],
        'quality': [
            'quality assurance', 'quality standards', 'quality improvement',
            'educational quality', 'quality control', 'quality monitoring'
        ],
        
        # Welfare & Schemes
        'mdm': [
            'mid day meal', 'midday meal', 'school meal', 'free meal',
            'noon meal', 'food program', 'nutrition program'
        ],
        'scholarship': [
            'scholarships', 'financial aid', 'educational grant', 'stipend',
            'financial assistance', 'scholarship scheme', 'student aid'
        ],
        'uniform': [
            'school uniform', 'uniforms', 'dress', 'school dress',
            'student uniform', 'uniform provision'
        ],
        'bicycle': [
            'bicycles', 'cycle', 'free bicycle', 'bicycle scheme',
            'student bicycle', 'transport aid'
        ],
        
        # Administrative & Legal
        'go': [
            'government order', 'GOs', 'G.O.', 'govt order',
            'government orders', 'official order', 'executive order'
        ],
        'act': [
            'legislation', 'law', 'statute', 'legal act', 'parliamentary act',
            'education act', 'legislative act'
        ],
        'rte': [
            'right to education', 'RTE Act', 'Right to Education Act',
            'free and compulsory education', 'education as right'
        ],
        'rule': [
            'rules', 'regulation', 'regulations', 'guidelines', 'norms',
            'provisions', 'legal provisions', 'statutory provisions'
        ],
        'section': [
            'clause', 'provision', 'sub-section', 'article', 'paragraph',
            'legal section', 'statutory section'
        ],
        'policy': [
            'policies', 'education policy', 'government policy', 'policy framework',
            'policy guidelines', 'policy document', 'policy provisions'
        ],
        
        # Special Needs & Inclusion
        'cwsn': [
            'children with special needs', 'special needs children',
            'differently abled', 'disabled children', 'children with disabilities',
            'specially abled', 'inclusive education'
        ],
        'inclusion': [
            'inclusive', 'inclusive education', 'inclusive practices',
            'mainstreaming', 'integration', 'inclusive schooling'
        ],
        
        # Community & Management
        'smc': [
            'school management committee', 'SMC', 'school committee',
            'management committee', 'school governance committee'
        ],
        'smdc': [
            'school management and development committee', 'SMDC',
            'development committee', 'school development committee'
        ],
        'pta': [
            'parent teacher association', 'parent association', 'PTA',
            'parents association', 'parent teacher organization'
        ],
    }
    
    # Phrase-level expansions (multi-word terms)
    PHRASE_EXPANSIONS = {
        'school infrastructure': [
            'school facilities', 'educational infrastructure', 'school premises',
            'school buildings and facilities', 'physical infrastructure of schools'
        ],
        'teacher transfer': [
            'teacher posting', 'teacher deployment', 'teacher mobility',
            'transfer of teachers', 'teacher relocation'
        ],
        'learning outcomes': [
            'student achievement', 'educational outcomes', 'academic performance',
            'learning achievements', 'student learning levels'
        ],
        'quality education': [
            'educational quality', 'quality of education', 'education standards',
            'quality schooling', 'quality learning'
        ],
    }
    
    def __init__(self):
        """Initialize domain expander"""
        # Compile patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for matching"""
        self.term_patterns = {}
        
        # Create patterns for each base term
        for term in self.DOMAIN_EXPANSIONS.keys():
            # Word boundary pattern for exact matches
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            self.term_patterns[term] = pattern
        
        # Phrase patterns
        self.phrase_patterns = {}
        for phrase in self.PHRASE_EXPANSIONS.keys():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            self.phrase_patterns[phrase] = pattern
    
    def expand_query(self, query: str, max_terms: int = 10) -> str:
        """
        Expand query with domain-specific synonyms
        
        Args:
            query: Original query
            max_terms: Maximum expansion terms to add
            
        Returns:
            Expanded query with synonyms appended
        """
        # Special handling for AI/technology integration queries
        if self._is_ai_technology_query(query):
            return self._expand_ai_technology_query(query, max_terms)
        
        expansion_terms = self._get_expansion_terms(query)
        
        if not expansion_terms:
            return query
        
        # Limit expansions
        expansion_terms = expansion_terms[:max_terms]
        
        # Append to original query
        expanded = f"{query} {' '.join(expansion_terms)}"
        
        return expanded
    
    def _is_ai_technology_query(self, query: str) -> bool:
        """Check if query is about AI/technology integration"""
        query_lower = query.lower()
        ai_indicators = ['ai', 'artificial intelligence', 'technology integration', 
                        'digital', 'coding', 'robotics', 'innovation']
        curriculum_indicators = ['curriculum', 'syllabus', 'school', 'education']
        
        has_ai = any(term in query_lower for term in ai_indicators)
        has_curriculum = any(term in query_lower for term in curriculum_indicators)
        
        return has_ai and (has_curriculum or 'integration' in query_lower)
    
    def _expand_ai_technology_query(self, query: str, max_terms: int) -> str:
        """Special expansion for AI/technology integration queries"""
        # High-priority education technology terms
        priority_terms = [
            'atal tinkering labs', 'atl', 'nep 2020', 'national education policy',
            'technology integration', 'digital education', 'educational technology',
            'smart classroom', 'stem education', 'innovation labs', 'coding education',
            'robotics education', 'digital literacy', 'computer education',
            'artificial intelligence curriculum', 'technology enhanced learning'
        ]
        
        # Get base expansion
        base_expansion = self._get_expansion_terms(query)
        
        # Combine with priority terms
        all_terms = priority_terms + base_expansion
        
        # Remove duplicates and terms already in query
        query_lower = query.lower()
        filtered_terms = [
            term for term in all_terms
            if term.lower() not in query_lower
        ]
        
        # Prioritize shorter, more specific terms
        filtered_terms.sort(key=lambda x: (len(x.split()), len(x)))
        
        # Take top terms
        selected_terms = filtered_terms[:max_terms * 2]  # More terms for AI queries
        
        return f"{query} {' '.join(selected_terms)}"
    
    def get_expansions(self, query: str) -> Dict[str, List[str]]:
        """
        Get all possible expansions for a query
        
        Returns:
            Dictionary mapping matched_term -> expansion_list
        """
        expansions = {}
        
        # Check phrase expansions first (longer matches)
        for phrase, expansion_list in self.PHRASE_EXPANSIONS.items():
            if phrase.lower() in query.lower():
                expansions[phrase] = expansion_list
        
        # Check single-term expansions
        for term, pattern in self.term_patterns.items():
            if pattern.search(query):
                expansions[term] = self.DOMAIN_EXPANSIONS[term]
        
        return expansions
    
    def _get_expansion_terms(self, query: str) -> List[str]:
        """Get unique expansion terms from all matches"""
        all_terms = set()
        
        # Get all expansions
        expansions = self.get_expansions(query)
        
        # Collect all expansion terms
        for term_list in expansions.values():
            all_terms.update(term_list)
        
        # Remove terms already in query
        query_lower = query.lower()
        filtered = [
            term for term in all_terms 
            if term.lower() not in query_lower
        ]
        
        return sorted(filtered, key=len, reverse=True)  # Longer terms first
    
    def expand_with_categories(
        self, 
        query: str, 
        categories: List[str]
    ) -> str:
        """
        Expand query focusing on specific categories
        
        Args:
            query: Original query
            categories: Category list (e.g., ['infrastructure', 'safety'])
            
        Returns:
            Category-focused expanded query
        """
        # Map categories to relevant terms
        category_terms = {
            'infrastructure': [
                'infrastructure', 'classroom', 'toilet', 'electricity',
                'water', 'boundary', 'furniture', 'playground', 'library', 'lab'
            ],
            'health': [
                'health', 'safety', 'medical', 'first aid', 'cctv'
            ],
            'safety': [
                'safety', 'cctv', 'security', 'health'
            ],
            'fln': [
                'fln', 'literacy', 'numeracy', 'reading', 'learning outcomes'
            ],
            'teacher': [
                'teacher', 'training', 'transfer', 'recruitment', 'tet'
            ],
            'academic': [
                'curriculum', 'textbook', 'tlm', 'assessment', 'examination'
            ],
            'monitoring': [
                'monitoring', 'udise', 'data', 'compliance', 'quality'
            ],
            'welfare': [
                'mdm', 'scholarship', 'uniform', 'bicycle'
            ]
        }
        
        # Collect relevant expansion terms
        expansion_terms = set()
        
        for category in categories:
            if category in category_terms:
                for base_term in category_terms[category]:
                    if base_term in self.DOMAIN_EXPANSIONS:
                        # Add some expansions from this term
                        expansion_terms.update(
                            self.DOMAIN_EXPANSIONS[base_term][:3]  # Top 3 per term
                        )
        
        # Remove duplicates from query
        query_lower = query.lower()
        filtered = [
            term for term in expansion_terms
            if term.lower() not in query_lower
        ]
        
        # Append to query
        if filtered:
            return f"{query} {' '.join(list(filtered)[:10])}"
        else:
            return query


# Convenience function
def expand_query(query: str, max_terms: int = 10) -> str:
    """Quick query expansion"""
    expander = DomainExpander()
    return expander.expand_query(query, max_terms)


# Example usage and tests
if __name__ == "__main__":
    expander = DomainExpander()
    
    test_queries = [
        "Improve school toilets",
        "Teacher transfer rules",
        "FLN implementation",
        "CCTV in schools",
        "RTE compliance",
        "MDM scheme guidelines",
    ]
    
    print("Domain Expander Tests:")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\nOriginal Query: {query}")
        print("-" * 80)
        
        # Get expansions
        expansions = expander.get_expansions(query)
        print("Matched Terms:")
        for term, expansion_list in expansions.items():
            print(f"  {term}: {', '.join(expansion_list[:5])}")
        
        # Get expanded query
        expanded = expander.expand_query(query, max_terms=8)
        print(f"\nExpanded Query: {expanded}")
        print("=" * 80)
    
    # Test category-focused expansion
    print("\n\nCategory-Focused Expansion Test:")
    print("=" * 80)
    query = "Improve school quality"
    categories = ['infrastructure', 'teacher', 'monitoring']
    
    expanded = expander.expand_with_categories(query, categories)
    print(f"Query: {query}")
    print(f"Categories: {categories}")
    print(f"Expanded: {expanded}")











