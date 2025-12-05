# Query Classifier - QA / DeepThink / Brainstorm / Policy

"""
Query Classifier - Classify queries into retrieval modes
Maps to: QA, DeepThink, Brainstorm, Policy, Compliance
"""

from typing import Dict, List, Tuple
from enum import Enum
import re


class QueryMode(Enum):
    """Query execution modes"""
    QA = "qa"                        # Quick factual Q&A
    DEEPTHINK = "deepthink"          # Deep comprehensive analysis
    BRAINSTORM = "brainstorm"        # Idea generation
    POLICY = "policy"                # Policy explanation
    COMPLIANCE = "compliance"        # Compliance checking
    

class QueryClassifier:
    """Classify queries into appropriate retrieval modes"""
    
    # Mode detection patterns
    MODE_PATTERNS = {
        QueryMode.QA: [
            r'\bwhat\s+is\b',
            r'\bwhat\s+are\b',
            r'\bwho\s+is\b',
            r'\bwhen\s+was\b',
            r'\bwhere\s+is\b',
            r'\bhow\s+many\b',
            r'\bdefine\b',
            r'\bexplain\b(?!\s+how\s+to)',
        ],
        
        QueryMode.DEEPTHINK: [
            r'\bcomprehensive\b',
            r'\bcomplete\s+analysis\b',
            r'\bin-depth\b',
            r'\bdetailed\s+study\b',
            r'\bexhaustive\b',
            r'\bfull\s+picture\b',
        ],
        
        QueryMode.BRAINSTORM: [
            r'\bideas?\b',
            r'\bsuggestions?\b',
            r'\bbrainstorm\b',
            r'\binnovate\b',
            r'\bcreative\b',
            r'\bpropose\b',
            r'\bgenerate\b',
        ],
        
        QueryMode.POLICY: [
            r'\bpolicy\b',
            r'\bguidelines?\b',
            r'\bframework\b',
            r'\bimplementation\b',
            r'\bstrategy\b',
            r'\bapproach\b',
        ],
        
        QueryMode.COMPLIANCE: [
            r'\bcompl(?:y|iance)\b',
            r'\bmeets?\s+requirements?\b',
            r'\badhere\b',
            r'\bvalidate\b',
            r'\bcheck\b.*\brequirements?\b',
        ],
    }
    
    def __init__(self):
        """Initialize classifier"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile patterns"""
        self.compiled_patterns = {
            mode: [re.compile(p, re.IGNORECASE) for p in patterns]
            for mode, patterns in self.MODE_PATTERNS.items()
        }
    
    def classify_mode(self, query: str) -> str:
        """
        Classify query into retrieval mode
        
        Args:
            query: User query
            
        Returns:
            Mode string (qa, deepthink, brainstorm, policy, compliance)
        """
        scores = {mode: 0 for mode in QueryMode}
        
        # Score each mode
        for mode, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[mode] += 1
        
        # Find best match
        if max(scores.values()) == 0:
            return QueryMode.QA.value  # Default
        
        best_mode = max(scores.items(), key=lambda x: x[1])
        return best_mode[0].value
    
    def get_mode_config(self, mode: str) -> Dict:
        """Get configuration for a mode"""
        configs = {
            'qa': {
                'top_k': 20,
                'use_rerank': True,
                'diversity_weight': 0.2,
            },
            'deepthink': {
                'top_k': 50,
                'use_rerank': True,
                'diversity_weight': 0.6,
            },
            'brainstorm': {
                'top_k': 40,
                'use_rerank': True,
                'diversity_weight': 0.7,
            },
            'policy': {
                'top_k': 30,
                'use_rerank': True,
                'diversity_weight': 0.4,
            },
            'compliance': {
                'top_k': 15,
                'use_rerank': True,
                'diversity_weight': 0.1,
            },
        }
        
        return configs.get(mode, configs['qa'])


# Convenience function
def classify_mode(query: str) -> str:
    """Quick classification"""
    classifier = QueryClassifier()
    return classifier.classify_mode(query)


if __name__ == "__main__":
    classifier = QueryClassifier()
    
    test_queries = [
        "What is RTE Section 12?",
        "Give me a comprehensive analysis of FLN policies",
        "Brainstorm ideas for improving attendance",
        "Explain the midday meal policy framework",
        "Check if our school meets RTE compliance",
    ]
    
    print("Query Classifier Tests:")
    print("=" * 60)
    
    for query in test_queries:
        mode = classifier.classify_mode(query)
        config = classifier.get_mode_config(mode)
        print(f"Query: {query}")
        print(f"Mode: {mode}")
        print(f"Config: {config}")
        print("-" * 60)











