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
    
    # Legal clause expansion templates
    LEGAL_CLAUSE_TEMPLATES = {
        'rte_act': [
            "Right to Education Act 2009 Section {section} responsibilities of schools",
            "RTE Act free and compulsory education {section} provisions",
            "RTE Act responsibilities of schools clause {section} details", 
            "Legal text for Section {section} RTE Act",
            "Section {section} Right to Education Act implementation"
        ],
        'general_act': [
            "{act_name} Act Section {section} legal provisions",
            "{act_name} {section} clause interpretation",
            "Legal requirements under {act_name} Section {section}",
            "{act_name} Act {section} implementation guidelines",
            "Section {section} {act_name} responsibilities"
        ],
        'rules_regulations': [
            "AP {rule_name} Rule {section} detailed provisions",
            "{rule_name} Rules Section {section} implementation",
            "Rule {section} under {rule_name} requirements",
            "{rule_name} regulatory provision {section}",
            "Administrative rule {section} {rule_name} compliance"
        ]
    }
    
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
        
        # Legal clause pattern detection
        if self._is_legal_clause_query(query_lower):
            return 'legal_clause'
        elif re.search(r'\bwhat\s+is\b|\bwhat\s+are\b', query_lower):
            return 'what_is'
        elif re.search(r'\bhow\s+to\b|\bhow\s+do\b', query_lower):
            return 'how_to'
        elif re.search(r'\brequirements?\b|\bmust\b|\bshould\b', query_lower):
            return 'requirements'
        elif re.search(r'\blist\b|\ball\b|\btypes?\b', query_lower):
            return 'list'
        else:
            return 'general'
    
    def _is_legal_clause_query(self, query_lower: str) -> bool:
        """Check if query is asking for specific legal clause/section/rule"""
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
        
        # Handle legal clause queries specially
        if pattern == 'legal_clause':
            return self._generate_legal_clause_rewrite(query, domain)
        
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
    
    def _generate_legal_clause_rewrite(self, query: str, domain: str) -> QueryRewrite:
        """Generate specialized rewrite for legal clause queries"""
        query_lower = query.lower()
        
        # Extract section/clause number
        section_match = re.search(r'\b(?:section|clause|article|rule)\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', query_lower)
        section_num = section_match.group(1) if section_match else "12"
        
        # Detect act/rule type
        if 'rte' in query_lower or 'right to education' in query_lower:
            template_key = 'rte_act'
            templates = self.LEGAL_CLAUSE_TEMPLATES[template_key]
            # Add BM25 keywords for RTE queries
            rewrite = templates[0].format(section=section_num)
            if f'rte section {section_num}' in self.LEGAL_KEYWORD_MAPPINGS:
                keywords = self.LEGAL_KEYWORD_MAPPINGS[f'rte section {section_num}']
                rewrite += f" {' '.join(keywords[:3])}"
        elif 'rule' in query_lower:
            template_key = 'rules_regulations'
            templates = self.LEGAL_CLAUSE_TEMPLATES[template_key]
            rule_name = self._extract_rule_name(query)
            rewrite = templates[0].format(rule_name=rule_name, section=section_num)
        else:
            template_key = 'general_act'
            templates = self.LEGAL_CLAUSE_TEMPLATES[template_key]
            act_name = self._extract_act_name(query)
            rewrite = templates[0].format(act_name=act_name, section=section_num)
        
        return QueryRewrite(
            text=rewrite,
            target_domain='legal',
            rationale=f"Legal clause expansion for {template_key} with BM25 keyword boosting"
        )
    
    def _extract_act_name(self, query: str) -> str:
        """Extract act name from query"""
        query_lower = query.lower()
        
        if 'rte' in query_lower or 'right to education' in query_lower:
            return "Right to Education"
        elif 'cce' in query_lower:
            return "CCE"
        elif 'apsermc' in query_lower:
            return "APSERMC" 
        elif 'education' in query_lower:
            return "Education"
        else:
            return "Act"
    
    def _extract_rule_name(self, query: str) -> str:
        """Extract rule name from query"""
        query_lower = query.lower()
        
        if 'rte' in query_lower:
            return "RTE"
        elif 'cce' in query_lower:
            return "CCE"
        elif 'admission' in query_lower:
            return "Admission"
        else:
            return "Education"
    
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
        api_key: Optional[str] = None # Deprecated, kept for signature compatibility
    ) -> List[QueryRewrite]:
        """
        Generate rewrites using Gemini Flash via Vertex AI (OAuth/ADC ONLY).
        NO API KEY FALLBACK - strictly OAuth/ADC.
        
        Args:
            query: Original query
            num_rewrites: Number of rewrites (3-5)
            api_key: Ignored (OAuth enforced)
            
        Returns:
            List of QueryRewrite objects
        """
        try:
            # STRICTLY OAuth / Vertex AI - no API key fallback
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
            # Default to us-central1 where Gemini 2.5 is available
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            
            if not project_id:
                # No project ID = no OAuth, skip Gemini entirely
                return self.generate_rewrites(query, num_rewrites)
            
            model_names_to_try = [
                'gemini-2.5-flash',
            ]

            client = None
            last_error = None
            selected_model_name = None

            # Vertex AI - Get credentials with proper scopes
            import google.auth
            from google import genai as genai_new
            
            try:
                # Get credentials with proper scopes
                service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if service_account_file and os.path.exists(service_account_file):
                    from google.oauth2 import service_account
                    scopes = [
                        'https://www.googleapis.com/auth/cloud-platform'
                    ]
                    creds = service_account.Credentials.from_service_account_file(
                        service_account_file, 
                        scopes=scopes
                    )
                    if not project_id:
                        import json
                        with open(service_account_file, 'r') as f:
                            project_id = json.load(f).get('project_id')
                else:
                    # Use ADC (gcloud auth application-default login)
                    creds, computed_project = google.auth.default(scopes=[
                        'https://www.googleapis.com/auth/cloud-platform'
                    ])
                    if not project_id:
                        project_id = computed_project
                
                if not project_id:
                    return self.generate_rewrites(query, num_rewrites)

                # Initialize Vertex AI client
                client = genai_new.Client(
                    vertexai=True,
                    project=project_id,
                    location=location,
                    credentials=creds,
                )
                
            except google.auth.exceptions.DefaultCredentialsError as e:
                # ADC not available - skip Gemini, use rule-based
                return self.generate_rewrites(query, num_rewrites)
            except Exception as e:
                # Any other credential error - skip Gemini
                return self.generate_rewrites(query, num_rewrites)
            
            if not client:
                return self.generate_rewrites(query, num_rewrites)
            
            # Try models with Vertex AI
            for model_name in model_names_to_try:
                try:
                    # Quick test/warmup
                    test_response = client.models.generate_content(
                        model=model_name,
                        contents=[{"role": "user", "parts": [{"text": "test"}]}],
                        config={'max_output_tokens': 10},
                    )
                    # Check if response has text (some models return empty)
                    if hasattr(test_response, 'text') and test_response.text:
                        selected_model_name = model_name
                        break
                except Exception as e:
                    error_str = str(e)
                    last_error = e
                    # If it's a permission error (403), don't try other models - fall back immediately
                    if "403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str:
                        print(f"⚠️ Vertex AI permission denied (403) for {model_name}, falling back to rule-based rewrites")
                        return self.generate_rewrites(query, num_rewrites)
                    continue # Try next model

            if not selected_model_name:
                # All models failed - use rule-based, don't try API key
                if last_error:
                    error_str = str(last_error)
                    if "403" in error_str or "PERMISSION_DENIED" in error_str:
                        print(f"⚠️ All Vertex AI models failed with permission error (403), using rule-based rewrites")
                    else:
                        print(f"⚠️ All Vertex AI models failed: {error_str[:200]}, using rule-based rewrites")
                return self.generate_rewrites(query, num_rewrites)
            
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

            # Generate with Gemini via Vertex AI
            generation_config = {
                'temperature': 0.7,
                'max_output_tokens': 500,
            }
            
            try:
                response = client.models.generate_content(
                    model=selected_model_name,
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                    config=generation_config,
                )
                
                # Parse response
                if hasattr(response, 'text') and response.text:
                    rewrites = self._parse_llm_response(response.text)
                    if rewrites:
                        return rewrites[:num_rewrites]
                
                # If parsing failed or no response, fallback to rule-based
                return self.generate_rewrites(query, num_rewrites)
                
            except Exception as e:
                error_str = str(e)
                # Check for permission errors (403)
                if "403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str:
                    print(f"⚠️ Vertex AI query rewriting permission denied (403), using rule-based rewrites")
                else:
                    print(f"⚠️ Vertex AI query rewriting failed: {error_str[:200]}, using rule-based rewrites")
                # Vertex AI call failed - use rule-based, NO API key fallback
                return self.generate_rewrites(query, num_rewrites)
            
        except ImportError:
            # Missing dependencies - use rule-based
            return self.generate_rewrites(query, num_rewrites)
        except Exception as e:
            # Any other error - use rule-based, NO API key fallback
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
