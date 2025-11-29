# Retrieval Plan - decides top_k, hops, rewrites, internet yes/no

"""
Retrieval Plan Builder - Create adaptive retrieval strategies
Determines: number of rewrites, hops, top_k, internet usage
"""

from typing import Dict, List
from dataclasses import dataclass, asdict
from enum import Enum


@dataclass
class RetrievalPlan:
    """Complete retrieval execution plan"""
    num_rewrites: int          # How many query rewrites to generate
    num_hops: int              # Multi-hop iterations (1-2)
    top_k_per_vertical: int    # Chunks to retrieve per vertical
    top_k_total: int           # Total chunks after aggregation
    use_internet: bool         # Whether to use internet search
    use_hybrid: bool           # Vector + BM25 hybrid search
    rerank_top_k: int          # How many to rerank with LLM
    diversity_weight: float    # Diversity vs relevance (0-1)
    mode: str                  # qa | policy | framework | deepthink
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class RetrievalMode(Enum):
    """Predefined retrieval modes"""
    QA = "qa"                    # Quick factual Q&A
    POLICY = "policy"            # Policy explanation
    FRAMEWORK = "framework"      # Framework design
    DEEPTHINK = "deepthink"      # Deep comprehensive analysis
    COMPLIANCE = "compliance"    # Compliance checking
    BRAINSTORM = "brainstorm"    # Idea generation


class RetrievalPlanBuilder:
    """Build adaptive retrieval plans based on query characteristics"""
    
    # Predefined mode configurations
    MODE_CONFIGS = {
        RetrievalMode.QA: {
            'num_rewrites': 2,
            'num_hops': 1,
            'top_k_per_vertical': 20,
            'top_k_total': 40,
            'use_hybrid': True,
            'rerank_top_k': 10,
            'diversity_weight': 0.2,
        },
        
        RetrievalMode.POLICY: {
            'num_rewrites': 3,
            'num_hops': 2,
            'top_k_per_vertical': 30,
            'top_k_total': 60,
            'use_hybrid': True,
            'rerank_top_k': 15,
            'diversity_weight': 0.4,
        },
        
        RetrievalMode.FRAMEWORK: {
            'num_rewrites': 5,
            'num_hops': 2,
            'top_k_per_vertical': 40,
            'top_k_total': 100,
            'use_hybrid': True,
            'rerank_top_k': 20,
            'diversity_weight': 0.5,
        },
        
        RetrievalMode.DEEPTHINK: {
            'num_rewrites': 5,
            'num_hops': 2,
            'top_k_per_vertical': 50,
            'top_k_total': 120,
            'use_hybrid': True,
            'rerank_top_k': 25,
            'diversity_weight': 0.6,
        },
        
        RetrievalMode.COMPLIANCE: {
            'num_rewrites': 2,
            'num_hops': 1,
            'top_k_per_vertical': 15,
            'top_k_total': 30,
            'use_hybrid': True,
            'rerank_top_k': 10,
            'diversity_weight': 0.1,  # High precision
        },
        
        RetrievalMode.BRAINSTORM: {
            'num_rewrites': 5,
            'num_hops': 2,
            'top_k_per_vertical': 40,
            'top_k_total': 100,
            'use_hybrid': True,
            'rerank_top_k': 20,
            'diversity_weight': 0.7,  # High diversity
        },
    }
    
    def __init__(self):
        """Initialize plan builder"""
        pass
    
    def build_plan(
        self,
        query_type: str,
        scope: str,
        needs_internet: bool = False,
        num_verticals: int = 2,
        custom_params: Dict = None
    ) -> RetrievalPlan:
        """
        Build retrieval plan based on query characteristics
        
        Args:
            query_type: Type from QueryInterpreter (qa, policy, etc.)
            scope: Scope from QueryInterpreter (narrow, medium, broad)
            needs_internet: Whether internet search needed
            num_verticals: Number of verticals being searched
            custom_params: Override specific parameters
            
        Returns:
            RetrievalPlan object
        """
        # Map query_type to mode
        mode = self._map_type_to_mode(query_type)
        
        # Get base config for mode
        config = self.MODE_CONFIGS[mode].copy()
        
        # Adjust based on scope
        config = self._adjust_for_scope(config, scope)
        
        # Adjust based on number of verticals
        config = self._adjust_for_verticals(config, num_verticals)
        
        # Add internet flag
        config['use_internet'] = needs_internet
        
        # Apply custom overrides
        if custom_params:
            config.update(custom_params)
        
        # Build plan
        plan = RetrievalPlan(
            num_rewrites=config['num_rewrites'],
            num_hops=config['num_hops'],
            top_k_per_vertical=config['top_k_per_vertical'],
            top_k_total=config['top_k_total'],
            use_internet=config['use_internet'],
            use_hybrid=config['use_hybrid'],
            rerank_top_k=config['rerank_top_k'],
            diversity_weight=config['diversity_weight'],
            mode=mode.value
        )
        
        return plan
    
    def _map_type_to_mode(self, query_type: str) -> RetrievalMode:
        """Map QueryType to RetrievalMode"""
        mapping = {
            'qa': RetrievalMode.QA,
            'policy': RetrievalMode.POLICY,
            'framework': RetrievalMode.FRAMEWORK,
            'list': RetrievalMode.QA,  # Lists are like QA
            'compliance': RetrievalMode.COMPLIANCE,
            'comparison': RetrievalMode.POLICY,  # Comparisons need moderate depth
            'history': RetrievalMode.POLICY,
            'brainstorm': RetrievalMode.BRAINSTORM,
        }
        
        return mapping.get(query_type, RetrievalMode.QA)
    
    def _adjust_for_scope(self, config: Dict, scope: str) -> Dict:
        """Adjust config based on query scope"""
        if scope == "narrow":
            # Narrow queries: fewer retrievals, higher precision
            config['num_rewrites'] = max(1, config['num_rewrites'] - 1)
            config['top_k_per_vertical'] = int(config['top_k_per_vertical'] * 0.7)
            config['top_k_total'] = int(config['top_k_total'] * 0.7)
            config['diversity_weight'] = config['diversity_weight'] * 0.5
        
        elif scope == "broad":
            # Broad queries: more retrievals, higher diversity
            config['num_rewrites'] = min(5, config['num_rewrites'] + 1)
            config['top_k_per_vertical'] = int(config['top_k_per_vertical'] * 1.3)
            config['top_k_total'] = int(config['top_k_total'] * 1.3)
            config['diversity_weight'] = min(0.9, config['diversity_weight'] * 1.3)
        
        # Medium scope: use defaults
        return config
    
    def _adjust_for_verticals(self, config: Dict, num_verticals: int) -> Dict:
        """Adjust config based on number of verticals"""
        if num_verticals == 1:
            # Single vertical: can retrieve more from it
            config['top_k_per_vertical'] = int(config['top_k_per_vertical'] * 1.5)
        
        elif num_verticals >= 4:
            # Many verticals: reduce per-vertical to avoid overload
            config['top_k_per_vertical'] = int(config['top_k_per_vertical'] * 0.8)
            config['top_k_total'] = int(config['top_k_total'] * 1.2)  # But increase total
        
        return config
    
    def get_mode_config(self, mode: str) -> Dict:
        """Get configuration for a specific mode"""
        try:
            mode_enum = RetrievalMode(mode)
            return self.MODE_CONFIGS[mode_enum].copy()
        except (ValueError, KeyError):
            return self.MODE_CONFIGS[RetrievalMode.QA].copy()


# Convenience function
def build_retrieval_plan(
    query_type: str,
    scope: str = "medium",
    needs_internet: bool = False,
    num_verticals: int = 2
) -> RetrievalPlan:
    """Quick plan building"""
    builder = RetrievalPlanBuilder()
    return builder.build_plan(query_type, scope, needs_internet, num_verticals)


# Example usage and tests
if __name__ == "__main__":
    builder = RetrievalPlanBuilder()
    
    test_cases = [
        {
            'query_type': 'qa',
            'scope': 'narrow',
            'needs_internet': False,
            'num_verticals': 1,
            'description': 'Simple factual question'
        },
        {
            'query_type': 'policy',
            'scope': 'medium',
            'needs_internet': False,
            'num_verticals': 2,
            'description': 'Policy explanation'
        },
        {
            'query_type': 'framework',
            'scope': 'broad',
            'needs_internet': True,
            'num_verticals': 4,
            'description': 'Comprehensive framework design'
        },
        {
            'query_type': 'compliance',
            'scope': 'narrow',
            'needs_internet': False,
            'num_verticals': 2,
            'description': 'Compliance check'
        },
        {
            'query_type': 'brainstorm',
            'scope': 'broad',
            'needs_internet': True,
            'num_verticals': 5,
            'description': 'Idea generation'
        },
    ]
    
    print("Retrieval Plan Builder Tests:")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Query Type: {test['query_type']}, Scope: {test['scope']}")
        print(f"Internet: {test['needs_internet']}, Verticals: {test['num_verticals']}")
        print("-" * 80)
        
        plan = builder.build_plan(
            query_type=test['query_type'],
            scope=test['scope'],
            needs_internet=test['needs_internet'],
            num_verticals=test['num_verticals']
        )
        
        print(f"Mode: {plan.mode}")
        print(f"Rewrites: {plan.num_rewrites}, Hops: {plan.num_hops}")
        print(f"Top-K per vertical: {plan.top_k_per_vertical}")
        print(f"Top-K total: {plan.top_k_total}")
        print(f"Rerank top-K: {plan.rerank_top_k}")
        print(f"Use hybrid: {plan.use_hybrid}, Use internet: {plan.use_internet}")
        print(f"Diversity weight: {plan.diversity_weight:.2f}")
        print("=" * 80)
    
    # Test mode configs
    print("\n\nMode Configurations:")
    print("=" * 80)
    
    for mode in RetrievalMode:
        config = builder.get_mode_config(mode.value)
        print(f"\n{mode.value.upper()}:")
        for key, value in config.items():
            print(f"  {key}: {value}")
