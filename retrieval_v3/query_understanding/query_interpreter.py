# Query Interpreter - LLM + heuristics

"""
Query Interpreter - Understand user intent and query characteristics
Uses rules + optional small LLM fallback for intent detection
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class QueryType(Enum):
    """Types of queries users ask"""
    QA = "qa"                      # Simple question-answer
    POLICY = "policy"              # Policy explanation/analysis
    LIST = "list"                  # List/enumerate items
    FRAMEWORK = "framework"        # Design/create framework
    COMPLIANCE = "compliance"      # Check compliance
    COMPARISON = "comparison"      # Compare policies/rules
    HISTORY = "history"            # Historical changes
    BRAINSTORM = "brainstorm"      # Generate ideas/strategies
    HR = "hr"                      # HR/Staffing/Recruitment


class QueryScope(Enum):
    """Scope/breadth of query"""
    NARROW = "narrow"      # Specific fact/document
    MEDIUM = "medium"      # Multiple related facts
    BROAD = "broad"        # Comprehensive analysis


@dataclass
class QueryInterpretation:
    """Complete query interpretation"""
    query_type: QueryType
    scope: QueryScope
    needs_internet: bool
    needs_deep_mode: bool
    confidence: float
    detected_entities: Dict[str, List[str]]
    keywords: List[str]
    temporal_references: List[str]
    reasoning: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result['query_type'] = self.query_type.value
        result['scope'] = self.scope.value
        return result


class QueryInterpreter:
    """Interpret user queries to understand intent and requirements"""
    
    # Query type detection patterns
    QA_PATTERNS = [
        r'\bwhat\s+is\b',
        r'\bwhat\s+are\b',
        r'\bwho\s+is\b',
        r'\bwhen\s+was\b',
        r'\bwhere\s+is\b',
        r'\bhow\s+many\b',
        r'\bdefine\b',
        r'\bexplain\b(?!\s+how\s+to)',  # "explain" but not "explain how to"
        r'\btell\s+me\s+about\b',
    ]
    
    FRAMEWORK_PATTERNS = [
        r'\bdesign\b',
        r'\bcreate\s+a\s+framework\b',
        r'\bdevelop\s+a\s+plan\b',
        r'\bpropose\b',
        r'\bcomprehensive\s+(framework|plan|strategy)\b',
        r'\bhow\s+to\s+(implement|design|create|build)\b',
        r'\bstrategy\s+for\b',
        r'\bapproach\s+to\b',
    ]
    
    LIST_PATTERNS = [
        r'\blist\s+(all|the)?\b',
        r'\benumerate\b',
        r'\bwhat\s+are\s+(all|the)\s+\w+\s+(for|in|of)\b',
        r'\bshow\s+me\s+all\b',
        r'\bgive\s+me\s+(all|the)\s+\w+\b',
        r'\btypes\s+of\b',
        r'\bcategories\s+of\b',
    ]
    
    COMPLIANCE_PATTERNS = [
        r'\bcheck\s+compliance\b',
        r'\bis\s+\w+\s+compliant\b',
        r'\bvalidate\b',
        r'\bverify\b',
        r'\bmeets?\s+requirements?\b',
        r'\badhere\s+to\b',
        r'\bfollows?\s+the\s+rules?\b',
    ]
    
    COMPARISON_PATTERNS = [
        r'\bcompare\b',
        r'\bdifference\s+between\b',
        r'\bvs\.?\b',
        r'\bversus\b',
        r'\bhow\s+does\s+\w+\s+differ\b',
        r'\bsimilarities\s+and\s+differences\b',
    ]
    
    HISTORY_PATTERNS = [
        r'\bhistory\s+of\b',
        r'\bhow\s+has\s+\w+\s+changed\b',
        r'\bevolution\s+of\b',
        r'\bover\s+time\b',
        r'\bprevious\b',
        r'\bold\s+(version|rule|policy)\b',
        r'\bsuperseded\b',
        r'\bsuperseded\b',
        r'\bamended\b',
    ]
    
    HR_PATTERNS = [
        r'\bhiring\b',
        r'\brecruitment\b',
        r'\bappointment\b',
        r'\bvacancy\b',
        r'\bpost\b',
        r'\bjob\b',
        r'\bsalary\b',
        r'\bpayscale\b',
        r'\bremuneration\b',
        r'\bcontract\s+teacher\b',
        r'\bprivate\s+sector\b',
        r'\boutsourcing\b',
        r'\bstaffing\b',
        r'\bhuman\s+resource\b',
        r'\bservice\s+rules\b',
        r'\bemployment\b',
    ]
    
    # Scope detection patterns
    NARROW_INDICATORS = [
        r'\bspecific\b',
        r'\bexact\b',
        r'\bsection\s+\d+\b',
        r'\bGO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*\d+\b',
        r'\bclause\s+\d+\b',
        r'\bparagraph\s+\d+\b',
        r'\bone\s+\w+\b',  # "one rule", "one policy"
    ]
    
    BROAD_INDICATORS = [
        r'\ball\b',
        r'\bcomplete\b',
        r'\bcomprehensive\b',
        r'\bentire\b',
        r'\bfull\b',
        r'\beverything\s+about\b',
        r'\boverall\b',
        r'\bholistic\b',
        r'\bmultiple\b',
    ]
    
    # Internet/recency indicators
    INTERNET_TRIGGERS = [
        r'\blatest\b',
        r'\brecent\b',
        r'\bcurrent\b',
        r'\b202[4-9]\b',  # Years 2024-2029
        r'\b203\d\b',     # Years 2030-2039
        r'\bthis\s+year\b',
        r'\bnew\b',
        r'\bupdated\b',
        r'\btoday\b',
        r'\bnow\b',
    ]
    
    # Entity patterns
    ENTITY_PATTERNS = {
        'go_refs': r'GO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*(\d+)',
        'sections': r'Section\s+(\d+(?:\([a-z0-9]+\))?)',
        'acts': r'(RTE|Right\s+to\s+Education|SSA|RMSA|MDM)\s+Act',
        'years': r'\b(19|20)\d{2}\b',
        'schemes': r'(Nadu-Nedu|Samagra\s+Shiksha|Mid\s+Day\s+Meal|Amma\s+Vodi)',
        'hr_terms': r'(salary|payscale|recruitment|hiring|contract|private|appointment|vacancy|post)',
    }
    
    def __init__(self, use_llm_fallback: bool = False):
        """
        Initialize interpreter
        
        Args:
            use_llm_fallback: Whether to use LLM for ambiguous cases
        """
        self.use_llm_fallback = use_llm_fallback
        
        # Compile patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns"""
        self.compiled_patterns = {
            'qa': [re.compile(p, re.IGNORECASE) for p in self.QA_PATTERNS],
            'framework': [re.compile(p, re.IGNORECASE) for p in self.FRAMEWORK_PATTERNS],
            'list': [re.compile(p, re.IGNORECASE) for p in self.LIST_PATTERNS],
            'compliance': [re.compile(p, re.IGNORECASE) for p in self.COMPLIANCE_PATTERNS],
            'comparison': [re.compile(p, re.IGNORECASE) for p in self.COMPARISON_PATTERNS],
            'history': [re.compile(p, re.IGNORECASE) for p in self.HISTORY_PATTERNS],
            'narrow': [re.compile(p, re.IGNORECASE) for p in self.NARROW_INDICATORS],
            'broad': [re.compile(p, re.IGNORECASE) for p in self.BROAD_INDICATORS],
            'internet': [re.compile(p, re.IGNORECASE) for p in self.INTERNET_TRIGGERS],
            'hr': [re.compile(p, re.IGNORECASE) for p in self.HR_PATTERNS],
        }
        
        self.entity_patterns = {
            k: re.compile(v, re.IGNORECASE) 
            for k, v in self.ENTITY_PATTERNS.items()
        }
    
    def interpret_query(self, query: str) -> QueryInterpretation:
        """
        Main interpretation function
        
        Args:
            query: Normalized user query
            
        Returns:
            QueryInterpretation object
        """
        # Detect query type
        query_type, type_confidence = self._detect_query_type(query)
        
        # Detect scope
        scope = self._detect_scope(query)
        
        # Check if internet needed
        needs_internet = self._needs_internet(query)
        
        # Determine if deep mode needed
        needs_deep_mode = self._needs_deep_mode(query_type, scope)
        
        # Extract entities
        entities = self._extract_entities(query)
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        # Detect temporal references
        temporal_refs = self._detect_temporal_references(query)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            query_type, scope, needs_internet, needs_deep_mode
        )
        
        return QueryInterpretation(
            query_type=query_type,
            scope=scope,
            needs_internet=needs_internet,
            needs_deep_mode=needs_deep_mode,
            confidence=type_confidence,
            detected_entities=entities,
            keywords=keywords,
            temporal_references=temporal_refs,
            reasoning=reasoning
        )
    
    def _detect_query_type(self, query: str) -> tuple[QueryType, float]:
        """
        Detect query type using pattern matching
        
        Returns:
            (QueryType, confidence_score)
        """
        scores = {
            QueryType.QA: 0.0,
            QueryType.FRAMEWORK: 0.0,
            QueryType.LIST: 0.0,
            QueryType.COMPLIANCE: 0.0,
            QueryType.COMPARISON: 0.0,
            QueryType.HISTORY: 0.0,
            QueryType.HR: 0.0,
        }
        
        # Score each type based on pattern matches
        for qtype, patterns in [
            (QueryType.QA, self.compiled_patterns['qa']),
            (QueryType.FRAMEWORK, self.compiled_patterns['framework']),
            (QueryType.LIST, self.compiled_patterns['list']),
            (QueryType.COMPLIANCE, self.compiled_patterns['compliance']),
            (QueryType.COMPARISON, self.compiled_patterns['comparison']),
            (QueryType.HISTORY, self.compiled_patterns['history']),
            (QueryType.HR, self.compiled_patterns['hr']),
        ]:
            for pattern in patterns:
                if pattern.search(query):
                    scores[qtype] += 1.0
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        # Get top scoring type
        if total == 0:
            # Default to QA with low confidence
            return QueryType.QA, 0.3
        
        top_type = max(scores.items(), key=lambda x: x[1])
        
        # If score is very low, might be brainstorm
        if top_type[1] < 0.3:
            # Check for brainstorm indicators
            brainstorm_words = ['ideas', 'suggestions', 'brainstorm', 'innovate']
            if any(word in query.lower() for word in brainstorm_words):
                return QueryType.BRAINSTORM, 0.7
        
        return top_type[0], top_type[1]
    
    def _detect_scope(self, query: str) -> QueryScope:
        """Detect query scope (narrow/medium/broad)"""
        narrow_score = 0
        broad_score = 0
        
        # Check narrow indicators
        for pattern in self.compiled_patterns['narrow']:
            if pattern.search(query):
                narrow_score += 1
        
        # Check broad indicators
        for pattern in self.compiled_patterns['broad']:
            if pattern.search(query):
                broad_score += 1
        
        # Query length heuristic
        word_count = len(query.split())
        if word_count <= 5:
            narrow_score += 1
        elif word_count > 15:
            broad_score += 1
        
        # Decide scope
        if broad_score > narrow_score:
            return QueryScope.BROAD
        elif narrow_score > broad_score:
            return QueryScope.NARROW
        else:
            return QueryScope.MEDIUM
    
    def _needs_internet(self, query: str) -> bool:
        """Check if query needs internet search"""
        for pattern in self.compiled_patterns['internet']:
            if pattern.search(query):
                return True
        return False
    
    def _needs_deep_mode(self, query_type: QueryType, scope: QueryScope) -> bool:
        """Determine if deep retrieval mode needed"""
        # Deep mode for framework, broad queries, or comprehensive analysis
        if query_type in [QueryType.FRAMEWORK, QueryType.BRAINSTORM]:
            return True
        
        if scope == QueryScope.BROAD:
            return True
        
        if query_type == QueryType.POLICY and scope == QueryScope.MEDIUM:
            return True
        
        return False
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(query)
            if matches:
                # Handle both simple and group matches
                if isinstance(matches[0], tuple):
                    matches = [m[0] if m[0] else m for m in matches]
                entities[entity_type] = list(set(matches))
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'what',
            'when', 'where', 'who', 'how', 'why', 'which'
        }
        
        # Split and clean
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords[:10]  # Top 10 keywords
    
    def _detect_temporal_references(self, query: str) -> List[str]:
        """Detect temporal references in query"""
        temporal = []
        
        # Years
        years = self.entity_patterns['years'].findall(query)
        temporal.extend(years)
        
        # Relative time
        relative_patterns = [
            r'\blast\s+year\b',
            r'\bthis\s+year\b',
            r'\bnext\s+year\b',
            r'\brecent\b',
            r'\bcurrent\b',
            r'\bprevious\b',
        ]
        
        for pattern in relative_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            temporal.extend(matches)
        
        return list(set(temporal))
    
    def _generate_reasoning(
        self, 
        query_type: QueryType, 
        scope: QueryScope,
        needs_internet: bool,
        needs_deep_mode: bool
    ) -> str:
        """Generate human-readable reasoning for interpretation"""
        parts = []
        
        parts.append(f"Query classified as {query_type.value}")
        parts.append(f"scope is {scope.value}")
        
        if needs_internet:
            parts.append("requires internet search for current information")
        
        if needs_deep_mode:
            parts.append("requires deep retrieval mode for comprehensive results")
        
        return ", ".join(parts)


# Convenience function
def interpret_query(query: str) -> QueryInterpretation:
    """Quick interpretation function"""
    interpreter = QueryInterpreter()
    return interpreter.interpret_query(query)


# Example usage and tests
if __name__ == "__main__":
    interpreter = QueryInterpreter()
    
    test_queries = [
        "What is Section 12(1)(c) of RTE Act?",
        "Design a comprehensive FLN framework for primary schools",
        "List all teacher transfer rules in GO 54",
        "Compare Nadu-Nedu with Samagra Shiksha scheme",
        "What are the latest 2025 education policies?",
        "Explain the history of midday meal scheme",
        "Check if our school meets RTE compliance requirements",
        "Give me ideas for improving student attendance",
    ]
    
    print("Query Interpreter Tests:")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        interpretation = interpreter.interpret_query(query)
        print(f"  Type: {interpretation.query_type.value} (confidence: {interpretation.confidence:.2f})")
        print(f"  Scope: {interpretation.scope.value}")
        print(f"  Internet needed: {interpretation.needs_internet}")
        print(f"  Deep mode: {interpretation.needs_deep_mode}")
        if interpretation.detected_entities:
            print(f"  Entities: {interpretation.detected_entities}")
        print(f"  Keywords: {', '.join(interpretation.keywords[:5])}")
        print(f"  Reasoning: {interpretation.reasoning}")
        print("-" * 80)













