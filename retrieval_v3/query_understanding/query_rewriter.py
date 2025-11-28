# Query Rewriter - LLM rewrites (infra/health/FLN/etc)

"""
Query Rewriter - Generate domain-specific query rewrites
Creates 3-5 semantic variations targeting different education verticals
Uses Gemini Flash for LLM-based rewrites (fast & cheap)
"""

import re
import os
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class QueryRewrite:
    """A single query rewrite"""
    text: str
    target_domain: str  # infra, health, fln, teacher, academic, etc.
    rationale: str


class QueryRewriter:
    """Generate comprehensive domain-specific query rewrites for 7 policy areas"""
    
    # Comprehensive domain vocabularies covering all 7 policy categories
    DOMAIN_VOCABULARIES = {
        'access_inclusion': [
            'admission', 'enrollment', 'enrolment', 'dropout', 'out-of-school children',
            'inclusion', 'equity', 'girl child education', 'SC ST students', 'minority education',
            'disabled children', 'CWSN', 'vulnerable children', 'disadvantaged groups',
            'school mapping', 'catchment area', 'distance norms', 'accessibility',
            'barrier-free education', 'inclusive classroom', 'special needs education'
        ],
        
        'infrastructure_safety': [
            'infrastructure', 'nadu nedu', 'facilities', 'buildings', 'classrooms', 'toilets',
            'drinking water', 'electricity', 'boundary walls', 'compound walls', 'ramps',
            'furniture', 'benches', 'desks', 'blackboards', 'labs', 'libraries',
            'playgrounds', 'sports facilities', 'kitchen', 'construction', 'maintenance',
            'CCTV', 'security', 'fire safety', 'emergency exits', 'TMF', 'sanitation'
        ],
        
        'governance_administration': [
            'governance', 'administration', 'management', 'inspection', 'monitoring',
            'supervision', 'compliance', 'regulation', 'DEO', 'MEO', 'DIET', 'SCERT',
            'RJD', 'CCE coordinator', 'headmaster', 'principal', 'district collector',
            'authority', 'responsibility', 'accountability', 'oversight', 'quality assurance',
            'institutional framework', 'policy implementation', 'government orders'
        ],
        
        'welfare_schemes': [
            'amma vodi', 'vidya kanuka', 'vidya deevena', 'gorumudda', 'mid day meal',
            'midday meal', 'school kit', 'uniform', 'scholarship', 'financial assistance',
            'transport', 'hostel', 'residential school', 'welfare scheme', 'benefit',
            'incentive', 'support', 'assistance', 'allowance', 'stipend', 'nutrition',
            'health checkup', 'medical care', 'student welfare', 'social security'
        ],
        
        'curriculum_pedagogy': [
            'curriculum', 'syllabus', 'textbook', 'subject', 'course', 'content',
            'learning material', 'digital content', 'e-content', 'pedagogy',
            'teaching method', 'learning outcome', 'competency', 'skill development',
            'FLN', 'foundational literacy', 'foundational numeracy', 'lesson plan',
            'activity based learning', 'project based learning', 'experiential learning',
            'academic standards', 'learning objectives', 'educational technology'
        ],
        
        'assessment_evaluation': [
            'assessment', 'evaluation', 'examination', 'test', 'CCE',
            'continuous comprehensive evaluation', 'grading', 'marking', 'scoring',
            'progress tracking', 'learning assessment', 'achievement', 'performance',
            'result', 'pass', 'fail', 'promotion', 'measurement', 'feedback',
            'report card', 'academic performance', 'learning level', 'standardized test',
            'formative assessment', 'summative assessment', 'diagnostic assessment'
        ],
        
        'teacher_development': [
            'teacher', 'teaching', 'faculty', 'staff', 'recruitment', 'appointment',
            'transfer', 'posting', 'training', 'capacity building', 'professional development',
            'in-service training', 'pre-service training', 'teacher education', 'B.Ed',
            'TET', 'DSC', 'educator', 'instructor', 'human resource', 'personnel',
            'qualification', 'certification', 'competency', 'skill enhancement',
            'teacher welfare', 'service conditions', 'career progression'
        ]
    }
    
    # Comprehensive rewrite templates for all 7 policy domains
    REWRITE_TEMPLATES = {
        'access_inclusion': [
            "What are the admission and enrollment policies for {topic} in AP schools?",
            "List all inclusive education initiatives for disadvantaged students regarding {topic}",
            "How do AP policies address barriers to education access for {topic}?",
            "What provisions exist for SC/ST/minority/CWSN students in {topic}?",
            "Describe school mapping and catchment area norms for {topic}"
        ],
        
        'infrastructure_safety': [
            "What are the Nadu-Nedu infrastructure guidelines for {topic}?", 
            "List all building and facility requirements for AP schools regarding {topic}",
            "What safety and security measures are mandated for {topic}?",
            "Describe the TMF and maintenance procedures for {topic}",
            "What are the CCTV, fire safety, and emergency protocols for {topic}?"
        ],
        
        'governance_administration': [
            "What are the governance and administration rules for {topic}?",
            "List all inspection and monitoring procedures for {topic}", 
            "What roles do DEO/MEO/DIET/SCERT play in {topic}?",
            "Describe compliance and quality assurance measures for {topic}",
            "What government orders and regulations govern {topic}?"
        ],
        
        'welfare_schemes': [
            "List all welfare schemes like Amma Vodi, Vidya Kanuka related to {topic}",
            "What financial assistance and benefits are available for {topic}?",
            "Describe midday meal, transport, and hostel provisions for {topic}",
            "What student support schemes cover {topic}?",
            "List Gorumudda and other nutritional programs for {topic}"
        ],
        
        'curriculum_pedagogy': [
            "What curriculum and syllabus guidelines exist for {topic}?",
            "List all teaching methodologies and pedagogical approaches for {topic}",
            "What learning outcomes and competencies are defined for {topic}?", 
            "Describe FLN (foundational literacy numeracy) aspects of {topic}",
            "What digital content and educational technology supports {topic}?"
        ],
        
        'assessment_evaluation': [
            "What assessment and evaluation procedures apply to {topic}?",
            "List all CCE (continuous comprehensive evaluation) guidelines for {topic}",
            "What examination and testing protocols exist for {topic}?",
            "Describe grading, marking, and promotion criteria for {topic}",
            "What performance tracking measures are used for {topic}?"
        ],
        
        'teacher_development': [
            "What teacher recruitment, training, and development policies cover {topic}?",
            "List all professional development requirements for {topic}",
            "What transfer, posting, and career progression rules apply to {topic}?",
            "Describe in-service and capacity building programs for {topic}",
            "What TET, DSC, and qualification requirements exist for {topic}?"
        ]
    }
    
    def __init__(self):
        """Initialize rewriter"""
        pass
    
    def generate_rewrites(
        self, 
        query: str,
        num_rewrites: int = 3,
        target_domains: Optional[List[str]] = None
    ) -> List[QueryRewrite]:
        """
        Generate domain-specific query rewrites (rule-based)
        
        Args:
            query: Original query
            num_rewrites: Number of rewrites to generate (3-5)
            target_domains: Specific domains to target (None = auto-detect)
            
        Returns:
            List of QueryRewrite objects
        """
        rewrites = []
        
        # Step 1: Detect query pattern
        pattern = self._detect_pattern(query)
        
        # Step 2: For broad queries, ensure all 7 domains are covered
        if self._is_broad_policy_query(query):
            # Generate one rewrite per domain for comprehensive coverage
            all_domains = list(self.DOMAIN_VOCABULARIES.keys())
            for i, domain in enumerate(all_domains):
                if i >= num_rewrites:
                    break
                rewrite = self._generate_domain_rewrite(query, domain, pattern)
                rewrites.append(rewrite)
        else:
            # Step 2: Auto-detect target domains if not specified
            if target_domains is None:
                target_domains = self._detect_target_domains(query)
            
            # Step 3: Generate domain-specific rewrites
            for domain in target_domains[:num_rewrites]:
                rewrite = self._generate_domain_rewrite(query, domain, pattern)
                rewrites.append(rewrite)
        
        # Step 4: Add a generic comprehensive rewrite if needed
        if len(rewrites) < num_rewrites:
            comprehensive = self._generate_comprehensive_rewrite(query)
            rewrites.append(comprehensive)
        
        return rewrites[:num_rewrites]
    
    def _detect_pattern(self, query: str) -> str:
        """Detect query pattern for template selection"""
        query_lower = query.lower()
        
        if re.search(r'\bwhat\s+is\b|\bwhat\s+are\b', query_lower):
            return 'what_is'
        elif re.search(r'\bhow\s+to\b|\bhow\s+do\b', query_lower):
            return 'how_to'
        elif re.search(r'\brequirements?\b|\bmust\b|\bshould\b', query_lower):
            return 'requirements'
        elif re.search(r'\blist\b|\ball\b|\btypes?\b', query_lower):
            return 'list'
        else:
            return 'general'
    
    def _detect_target_domains(self, query: str) -> List[str]:
        """
        Auto-detect which domains are relevant to the query
        Returns domains in priority order
        """
        query_lower = query.lower()
        domain_scores = {}
        
        # Score each domain based on vocabulary overlap
        for domain, vocabulary in self.DOMAIN_VOCABULARIES.items():
            score = 0
            for term in vocabulary:
                if term.lower() in query_lower:
                    # Longer terms get higher weight
                    score += len(term.split())
            domain_scores[domain] = score
        
        # Sort by score descending
        sorted_domains = sorted(
            domain_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return domains with non-zero scores
        relevant = [d for d, s in sorted_domains if s > 0]
        
        # If no domains detected, return default priority order
        if not relevant:
            return ['governance', 'academic', 'teacher', 'infrastructure', 'fln']
        
        return relevant
    
    def _is_broad_policy_query(self, query: str) -> bool:
        """Check if query is asking for broad policy coverage across domains"""
        broad_patterns = [
            r'\b(?:current|latest|all|comprehensive|complete|overall)\s+(?:education\s+)?policies?\b',
            r'\beducation\s+(?:system|framework|structure|overview)\b',
            r'\b(?:list|overview|summary)\s+(?:of\s+)?(?:all\s+)?(?:education\s+)?(?:policies|initiatives|schemes)\b',
            r'\beducation\s+(?:in\s+)?(?:andhra\s+pradesh|AP)\b',
            r'\bap\s+education\s+(?:department|system|policies)\b',
            r'\bstate\s+education\s+policies?\b'
        ]
        
        for pattern in broad_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _generate_domain_rewrite(
        self, 
        query: str, 
        domain: str, 
        pattern: str
    ) -> QueryRewrite:
        """Generate a rewrite targeting a specific domain"""
        
        # Get domain vocabulary
        domain_terms = self.DOMAIN_VOCABULARIES.get(domain, [])
        
        # Extract key terms from original query
        key_terms = self._extract_key_terms(query)
        
        # Build rewrite by injecting domain vocabulary
        if pattern == 'what_is':
            rewrite = f"{' '.join(key_terms)} {domain.replace('_', ' ')} policy provisions"
        elif pattern == 'how_to':
            rewrite = f"Implementation of {' '.join(key_terms)} in {domain.replace('_', ' ')}"
        elif pattern == 'requirements':
            rewrite = f"{' '.join(key_terms)} {domain.replace('_', ' ')} requirements standards"
        elif pattern == 'list':
            rewrite = f"All {' '.join(key_terms)} related to {domain.replace('_', ' ')}"
        else:
            # Generic: add domain-specific terms
            rewrite = f"{query} {' '.join(domain_terms[:3])}"
        
        rationale = f"Targeting {domain} vertical with domain-specific vocabulary"
        
        return QueryRewrite(
            text=rewrite,
            target_domain=domain,
            rationale=rationale
        )
    
    def _generate_comprehensive_rewrite(self, query: str) -> QueryRewrite:
        """Generate a comprehensive rewrite covering multiple domains"""
        key_terms = self._extract_key_terms(query)
        
        # Add cross-domain terms
        cross_domain = [
            'policy', 'implementation', 'guidelines', 'provisions',
            'requirements', 'standards', 'norms', 'compliance'
        ]
        
        rewrite = f"{' '.join(key_terms)} comprehensive {' '.join(cross_domain[:2])}"
        
        return QueryRewrite(
            text=rewrite,
            target_domain='comprehensive',
            rationale='Broad cross-domain rewrite for maximum coverage'
        )
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query (remove stopwords)"""
        stopwords = {
            'what', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but', 
            'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how',
            'do', 'does', 'can', 'could', 'should', 'would', 'will',
            'tell', 'me', 'about', 'explain', 'describe', 'list'
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        return key_terms[:5]  # Top 5 key terms
    
    def generate_rewrites_with_gemini(
        self,
        query: str,
        num_rewrites: int = 3,
        api_key: Optional[str] = None
    ) -> List[QueryRewrite]:
        """
        Generate rewrites using Gemini Flash (fast and cheap)
        
        Args:
            query: Original query
            num_rewrites: Number of rewrites (3-5)
            api_key: Google API key for Gemini (or set GEMINI_API_KEY env var)
            
        Returns:
            List of QueryRewrite objects
        """
        try:
            import google.generativeai as genai
            
            # Get API key from env if not provided
            if not api_key:
                api_key = os.getenv('GEMINI_API_KEY')
            
            if not api_key:
                print("No Gemini API key found, falling back to rule-based rewrites")
                return self.generate_rewrites(query, num_rewrites)
            
            # Configure Gemini Flash (fastest, cheapest)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-8b')  # Ultra-fast, ultra-cheap
            
            # Create prompt for domain-specific rewrites
            prompt = f"""You are an expert in Indian education policy. Generate {num_rewrites} different rewrites of this query, each targeting different aspects of education policy:

Original Query: {query}

Generate rewrites targeting these domains:
1. Infrastructure (buildings, facilities, classrooms, toilets)
2. Health & Safety (hygiene, security, CCTV, medical)
3. Academic (curriculum, textbooks, teaching methods)
4. Teacher Policy (recruitment, training, transfers)
5. FLN (foundational literacy and numeracy)
6. Monitoring (UDISE, data, compliance, quality assurance)

Format each rewrite as:
DOMAIN: <domain>
REWRITE: <rewritten query>
REASON: <why this rewrite is useful>

Keep rewrites concise (10-15 words) and focused on policy/legal documents."""

            # Generate with Gemini Flash (ultra-fast)
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 500,
                }
            )
            
            # Parse response
            rewrites = self._parse_llm_response(response.text)
            
            if rewrites:
                return rewrites[:num_rewrites]
            else:
                # Fallback if parsing failed
                return self.generate_rewrites(query, num_rewrites)
            
        except ImportError:
            print("google-generativeai not installed, falling back to rule-based")
            return self.generate_rewrites(query, num_rewrites)
        except Exception as e:
            print(f"Gemini rewrite failed: {e}, falling back to rule-based")
            return self.generate_rewrites(query, num_rewrites)
    
    def _parse_llm_response(self, response_text: str) -> List[QueryRewrite]:
        """Parse Gemini response into QueryRewrite objects"""
        rewrites = []
        
        # Split into blocks (separated by blank lines)
        blocks = re.split(r'\n\s*\n', response_text.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            
            domain = None
            rewrite_text = None
            reason = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('DOMAIN:'):
                    domain = line.replace('DOMAIN:', '').strip()
                elif line.startswith('REWRITE:'):
                    rewrite_text = line.replace('REWRITE:', '').strip()
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()
            
            if domain and rewrite_text:
                rewrites.append(QueryRewrite(
                    text=rewrite_text,
                    target_domain=domain.lower(),
                    rationale=reason or 'Gemini-generated rewrite'
                ))
        
        return rewrites


# Convenience functions
def generate_rewrites(query: str, num_rewrites: int = 3) -> List[QueryRewrite]:
    """Quick rewrite generation (rule-based, no API needed)"""
    rewriter = QueryRewriter()
    return rewriter.generate_rewrites(query, num_rewrites)


def generate_rewrites_with_gemini(
    query: str, 
    num_rewrites: int = 3,
    api_key: Optional[str] = None
) -> List[QueryRewrite]:
    """Quick rewrite generation with Gemini Flash (requires API key)"""
    rewriter = QueryRewriter()
    return rewriter.generate_rewrites_with_gemini(query, num_rewrites, api_key)


# Example usage and tests
if __name__ == "__main__":
    rewriter = QueryRewriter()
    
    test_queries = [
        "What is RTE Section 12(1)(c)?",
        "How to improve school infrastructure?",
        "List all teacher transfer rules",
        "Requirements for FLN implementation",
        "Midday meal scheme guidelines",
    ]
    
    print("Query Rewriter Tests (Rule-Based):")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\nOriginal Query: {query}")
        print("-" * 80)
        
        rewrites = rewriter.generate_rewrites(query, num_rewrites=3)
        
        for i, rewrite in enumerate(rewrites, 1):
            print(f"\nRewrite {i}:")
            print(f"  Domain: {rewrite.target_domain}")
            print(f"  Text: {rewrite.text}")
            print(f"  Rationale: {rewrite.rationale}")
        
        print("=" * 80)
    
    # Test Gemini-based (if API key available)
    api_key = os.getenv('GEMINI_API_KEY')
    
    if api_key:
        print("\n\nTesting Gemini Flash LLM Rewrites:")
        print("=" * 80)
        
        query = "Improve foundational literacy in primary schools"
        print(f"Query: {query}\n")
        
        llm_rewrites = rewriter.generate_rewrites_with_gemini(query, 3, api_key)
        
        for i, rewrite in enumerate(llm_rewrites, 1):
            print(f"\nGemini Rewrite {i}:")
            print(f"  Domain: {rewrite.target_domain}")
            print(f"  Text: {rewrite.text}")
            print(f"  Rationale: {rewrite.rationale}")
    else:
        print("\n\nSkipping Gemini tests (no API key found)")
        print("Set GEMINI_API_KEY environment variable to test LLM rewrites")