# Vertical Router - full verticals for deep queries

"""
Vertical Router - Intelligently route queries to relevant document verticals
Decides which collections to search (legal, go, judicial, data, schemes)
"""

from typing import List, Dict, Set
from enum import Enum
import re


class Vertical(Enum):
    """Document vertical types"""
    LEGAL = "legal"              # Acts, Rules, Regulations
    GO = "go"                    # Government Orders
    JUDICIAL = "judicial"        # Court judgments, case law
    DATA = "data"                # UDISE, statistical reports
    SCHEMES = "schemes"          # Policy schemes, programs
    

class VerticalRouter:
    """Route queries to appropriate document verticals"""
    
    # Keywords that trigger specific verticals
    VERTICAL_KEYWORDS = {
        Vertical.LEGAL: [
            'act', 'section', 'rule', 'regulation', 'statute', 'law',
            'rte', 'right to education', 'legal provision', 'amendment',
            'clause', 'subsection', 'article', 'chapter',
        ],
        
        Vertical.GO: [
            'go', 'government order', 'g.o.', 'circular', 'notification',
            'order', 'govt order', 'executive order', 'administrative order',
            'ms.no', 'rt.no', 'superseded', 'supersedes',
        ],
        
        Vertical.JUDICIAL: [
            'judgment', 'court', 'case', 'ruling', 'verdict', 'case law',
            'supreme court', 'high court', 'judicial', 'litigation',
            'writ', 'petition', 'appeal', 'case number',
        ],
        
        Vertical.DATA: [
            'data', 'statistics', 'report', 'udise', 'enrollment', 'attendance',
            'dropout', 'aser', 'nas', 'survey', 'census', 'figures',
            'numbers', 'metrics', 'indicators', 'trend', 'analysis',
        ],
        
        Vertical.SCHEMES: [
            'scheme', 'program', 'initiative', 'project', 'samagra shiksha',
            'nadu-nedu', 'midday meal', 'mdm', 'ssa', 'rmsa', 'npegel',
            'amma vodi', 'scholarship', 'jagananna', 'implementation',
            'ai', 'artificial intelligence', 'technology integration',
            'atal tinkering labs', 'atl', 'innovation', 'digital education',
            'educational technology', 'stem education', 'coding education',
            'robotics education', 'smart classroom', 'nep 2020',
        ],
    }
    
    # Entity patterns that indicate verticals
    ENTITY_PATTERNS = {
        Vertical.LEGAL: [
            r'\bSection\s+\d+',
            r'\b(RTE|SSA|RMSA)\s+Act\b',
            r'\bRule\s+\d+',
            r'\bChapter\s+[IVX]+',
        ],
        
        Vertical.GO: [
            r'GO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*\d+',
            r'G\.O\.(?:Ms|Rt)\.No\.\d+',
        ],
        
        Vertical.JUDICIAL: [
            r'\b\d{4}\s+\(\d+\)\s+[A-Z]+\s+\d+',  # Case citation
            r'\bW\.P\.No\.\d+',
            r'\bS\.L\.P\.\s*\(C\)',
        ],
        
        Vertical.DATA: [
            r'\bUDISE\+?',
            r'\b\d{4}-\d{2}\s+(?:enrollment|dropout)',
            r'\bASER\s+\d{4}',
        ],
        
        Vertical.SCHEMES: [
            r'\b(Nadu-Nedu|Samagra\s+Shiksha|Amma\s+Vodi)',
        ],
    }
    
    def __init__(self):
        """Initialize router with compiled patterns"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        self.compiled_patterns = {}
        
        for vertical, patterns in self.ENTITY_PATTERNS.items():
            self.compiled_patterns[vertical] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def route_query(
        self, 
        query: str,
        query_type: str = "qa",
        detected_entities: Dict = None
    ) -> List[Vertical]:
        """
        Route query to appropriate verticals
        
        Args:
            query: User query
            query_type: Type of query (qa, policy, framework, etc.)
            detected_entities: Entities detected in query
            
        Returns:
            List of Vertical enums to search
        """
        verticals = set()
        
        # Step 0: Check for broad policy queries that need ALL verticals
        if self._is_broad_policy_query(query) or query_type in ['deep_think', 'brainstorm']:
            # Force all 5 verticals for comprehensive coverage
            return list(Vertical)
        
        # Step 1: Check for entity-based routing (highest priority)
        entity_verticals = self._route_by_entities(query, detected_entities)
        verticals.update(entity_verticals)
        
        # Step 2: Keyword-based routing
        keyword_verticals = self._route_by_keywords(query)
        verticals.update(keyword_verticals)
        
        # Step 3: Query type-based routing
        type_verticals = self._route_by_type(query_type)
        verticals.update(type_verticals)
        
        # Step 4: If no verticals selected, use default strategy
        if not verticals:
            verticals = self._default_routing(query)
        
        # Convert to list and sort by priority
        return self._prioritize_verticals(list(verticals), query)
    
    def _route_by_entities(
        self, 
        query: str, 
        detected_entities: Dict = None
    ) -> Set[Vertical]:
        """Route based on detected entities"""
        verticals = set()
        
        # Check entity patterns in query
        for vertical, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    verticals.add(vertical)
        
        # Check provided entities
        if detected_entities:
            if 'sections' in detected_entities or 'acts' in detected_entities:
                verticals.add(Vertical.LEGAL)
            if 'go_refs' in detected_entities:
                verticals.add(Vertical.GO)
            if 'schemes' in detected_entities:
                verticals.add(Vertical.SCHEMES)
        
        return verticals
    
    def _route_by_keywords(self, query: str) -> Set[Vertical]:
        """Route based on keyword matching"""
        verticals = set()
        query_lower = query.lower()
        
        # Score each vertical
        scores = {v: 0 for v in Vertical}
        
        for vertical, keywords in self.VERTICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    # Longer keywords get higher weight
                    scores[vertical] += len(keyword.split())
        
        # Select verticals with score > 0
        for vertical, score in scores.items():
            if score > 0:
                verticals.add(vertical)
        
        return verticals
    
    def _route_by_type(self, query_type: str) -> Set[Vertical]:
        """Route based on query type"""
        verticals = set()
        
        if query_type in ['qa', 'compliance']:
            # QA queries: legal + GOs
            verticals.update([Vertical.LEGAL, Vertical.GO])
        
        elif query_type in ['framework', 'policy', 'brainstorm', 'deep_think']:
            # Comprehensive queries: all verticals
            verticals.update(list(Vertical))
        
        elif query_type == 'comparison':
            # Comparisons: schemes + data
            verticals.update([Vertical.SCHEMES, Vertical.DATA, Vertical.GO])
        
        elif query_type == 'history':
            # Historical: GOs + judicial
            verticals.update([Vertical.GO, Vertical.JUDICIAL, Vertical.LEGAL])
        
        return verticals
    
    def _is_broad_policy_query(self, query: str) -> bool:
        """Check if query requires comprehensive coverage across all verticals"""
        broad_patterns = [
            r'\b(?:current|latest|all|comprehensive|complete|overall)\s+(?:education\s+)?policies?\b',
            r'\beducation\s+(?:system|framework|structure|overview)\b',
            r'\b(?:list|overview|summary)\s+(?:of\s+)?(?:all\s+)?(?:education\s+)?(?:policies|initiatives|schemes)\b',
            r'\beducation\s+(?:in\s+)?(?:andhra\s+pradesh|AP)\b',
            r'\bap\s+education\s+(?:department|system|policies)\b',
            r'\bstate\s+education\s+policies?\b',
            r'\bpolicy\s+(?:landscape|ecosystem|framework)\b',
            r'\b(?:education|policy)\s+governance\b'
        ]
        
        for pattern in broad_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _default_routing(self, query: str) -> Set[Vertical]:
        """Default routing when no clear indicators"""
        # Start with legal and GOs (most common queries)
        return {Vertical.LEGAL, Vertical.GO}
    
    def _prioritize_verticals(
        self, 
        verticals: List[Vertical], 
        query: str
    ) -> List[Vertical]:
        """
        Prioritize verticals based on query characteristics
        Returns verticals in search order
        """
        if not verticals:
            return []
        
        # Priority order based on specificity
        priority_order = {
            Vertical.LEGAL: 1,      # Highest priority (authoritative)
            Vertical.GO: 2,          # Second (implementation)
            Vertical.JUDICIAL: 3,    # Third (interpretations)
            Vertical.SCHEMES: 4,     # Fourth (programs)
            Vertical.DATA: 5,        # Fifth (evidence)
        }
        
        # Sort by priority
        sorted_verticals = sorted(
            verticals,
            key=lambda v: priority_order.get(v, 99)
        )
        
        return sorted_verticals
    
    def get_collection_names(self, verticals: List[Vertical]) -> List[str]:
        """
        Convert Vertical enums to Qdrant collection names
        
        Returns:
            List of collection names for Qdrant
        """
        # Map to actual Qdrant collection names
        collection_map = {
            Vertical.LEGAL: 'ap_legal_documents',
            Vertical.GO: 'ap_government_orders',
            Vertical.JUDICIAL: 'ap_judicial_documents',
            Vertical.DATA: 'ap_data_reports',
            Vertical.SCHEMES: 'ap_schemes',
        }
        
        return [collection_map[v] for v in verticals if v in collection_map]


# Convenience function
def route_query(
    query: str,
    query_type: str = "qa",
    detected_entities: Dict = None
) -> List[str]:
    """
    Quick routing function
    
    Returns:
        List of Qdrant collection names
    """
    router = VerticalRouter()
    verticals = router.route_query(query, query_type, detected_entities)
    return router.get_collection_names(verticals)


# Example usage and tests
if __name__ == "__main__":
    router = VerticalRouter()
    
    test_cases = [
        {
            'query': "What is Section 12(1)(c) of RTE Act?",
            'type': "qa",
            'entities': {'sections': ['12(1)(c)'], 'acts': ['RTE']}
        },
        {
            'query': "Explain GO 54 on teacher transfers",
            'type': "qa",
            'entities': {'go_refs': ['54']}
        },
        {
            'query': "Nadu-Nedu scheme implementation guidelines",
            'type': "policy",
            'entities': {'schemes': ['Nadu-Nedu']}
        },
        {
            'query': "Compare enrollment trends 2020 vs 2024",
            'type': "comparison",
            'entities': {'years': ['2020', '2024']}
        },
        {
            'query': "Design comprehensive FLN framework",
            'type': "framework",
            'entities': {}
        },
        {
            'query': "Latest court judgment on RTE compliance",
            'type': "qa",
            'entities': {}
        },
    ]
    
    print("Vertical Router Tests:")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Query: {test['query']}")
        print(f"Type: {test['type']}")
        
        verticals = router.route_query(
            test['query'],
            test['type'],
            test['entities']
        )
        
        collections = router.get_collection_names(verticals)
        
        print(f"Verticals: {[v.value for v in verticals]}")
        print(f"Collections: {collections}")
        print("-" * 80)