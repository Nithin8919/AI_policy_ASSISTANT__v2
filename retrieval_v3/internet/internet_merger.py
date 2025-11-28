# Internet Merger - merges internet results with Qdrant

"""
Internet Merger - Merge internet search results with local Qdrant results
Intelligently combines and ranks results from both sources
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MergedResult:
    """Result from merged search"""
    content: str
    source: str  # 'qdrant' or 'internet'
    score: float
    url: Optional[str] = None
    vertical: Optional[str] = None
    metadata: Dict = None


class InternetMerger:
    """Merge internet results with local database results"""
    
    def __init__(
        self,
        internet_weight: float = 0.3,
        qdrant_weight: float = 0.7,
        boost_gov_sources: bool = True
    ):
        """
        Initialize merger
        
        Args:
            internet_weight: Weight for internet results (0-1)
            qdrant_weight: Weight for Qdrant results (0-1)
            boost_gov_sources: Give higher weight to .gov.in sources
        """
        self.internet_weight = internet_weight
        self.qdrant_weight = qdrant_weight
        self.boost_gov_sources = boost_gov_sources
        
        # Normalize weights
        total = internet_weight + qdrant_weight
        self.internet_weight /= total
        self.qdrant_weight /= total
    
    def merge(
        self,
        qdrant_results: List[Dict],
        internet_results: List[Dict],
        top_k: int = 20
    ) -> List[MergedResult]:
        """
        Merge results from both sources
        
        Args:
            qdrant_results: Results from Qdrant
            internet_results: Results from web search
            top_k: Final result count
            
        Returns:
            Merged and ranked results
        """
        merged = []
        
        # Process Qdrant results
        for result in qdrant_results:
            score = result.get('score', 0.0) * self.qdrant_weight
            
            merged.append(MergedResult(
                content=result.get('content', ''),
                source='qdrant',
                score=score,
                vertical=result.get('vertical'),
                metadata=result.get('metadata', {})
            ))
        
        # Process internet results
        for result in internet_results:
            # Base score (from rank)
            rank = result.get('rank', 1)
            base_score = 1.0 / rank  # Higher rank = higher score
            
            # Apply boost for gov sources
            if self.boost_gov_sources:
                source = result.get('source', '')
                if 'gov.in' in source or 'nic.in' in source:
                    base_score *= 1.5  # 50% boost
            
            # Apply internet weight
            score = base_score * self.internet_weight
            
            merged.append(MergedResult(
                content=result.get('snippet', ''),
                source='internet',
                score=score,
                url=result.get('url'),
                metadata={
                    'title': result.get('title'),
                    'source_domain': result.get('source')
                }
            ))
        
        # Sort by final score
        merged.sort(key=lambda x: x.score, reverse=True)
        
        return merged[:top_k]
    
    def interleave(
        self,
        qdrant_results: List[Dict],
        internet_results: List[Dict],
        ratio: str = "2:1"
    ) -> List[MergedResult]:
        """
        Interleave results in a pattern (e.g., 2 Qdrant, 1 internet)
        
        Args:
            qdrant_results: Qdrant results
            internet_results: Internet results
            ratio: Interleaving ratio (e.g., "2:1", "3:1")
            
        Returns:
            Interleaved results
        """
        qdrant_n, internet_n = map(int, ratio.split(':'))
        
        merged = []
        q_idx = 0
        i_idx = 0
        
        while q_idx < len(qdrant_results) or i_idx < len(internet_results):
            # Add Qdrant results
            for _ in range(qdrant_n):
                if q_idx < len(qdrant_results):
                    result = qdrant_results[q_idx]
                    merged.append(MergedResult(
                        content=result.get('content', ''),
                        source='qdrant',
                        score=result.get('score', 0.0),
                        vertical=result.get('vertical'),
                        metadata=result.get('metadata', {})
                    ))
                    q_idx += 1
            
            # Add internet results
            for _ in range(internet_n):
                if i_idx < len(internet_results):
                    result = internet_results[i_idx]
                    merged.append(MergedResult(
                        content=result.get('snippet', ''),
                        source='internet',
                        score=1.0 / (result.get('rank', 1)),
                        url=result.get('url'),
                        metadata={
                            'title': result.get('title'),
                            'source_domain': result.get('source')
                        }
                    ))
                    i_idx += 1
        
        return merged


# Convenience function
def merge_results(
    qdrant_results: List[Dict],
    internet_results: List[Dict],
    top_k: int = 20
) -> List[MergedResult]:
    """Quick merge"""
    merger = InternetMerger()
    return merger.merge(qdrant_results, internet_results, top_k)


if __name__ == "__main__":
    print("Internet Merger")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.internet import InternetMerger

merger = InternetMerger(
    internet_weight=0.3,
    qdrant_weight=0.7,
    boost_gov_sources=True
)

# Merge results
merged = merger.merge(
    qdrant_results=local_results,
    internet_results=web_results,
    top_k=20
)

# Or interleave (2 local, 1 internet)
interleaved = merger.interleave(
    qdrant_results=local_results,
    internet_results=web_results,
    ratio="2:1"
)

for result in merged:
    print(f"[{result.source}] {result.content[:100]}...")
""")