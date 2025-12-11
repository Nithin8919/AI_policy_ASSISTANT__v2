"""
Internet Reranker - Boost internet search results based on source authority
Prioritizes government sources, recent content, and authoritative domains
"""

from typing import List, Dict
from datetime import datetime
import re


class InternetReranker:
    """Rerank internet search results by authority and recency"""
    
    def __init__(
        self,
        gov_boost: float = 1.5,
        edu_boost: float = 1.3,
        recency_boost: float = 1.2
    ):
        """
        Initialize internet reranker
        
        Args:
            gov_boost: Multiplier for government sources
            edu_boost: Multiplier for educational sources
            recency_boost: Multiplier for recent content
        """
        self.gov_boost = gov_boost
        self.edu_boost = edu_boost
        self.recency_boost = recency_boost
        
        # Authoritative domains
        self.gov_domains = [
            'gov.in', 'nic.in', 'india.gov.in',
            'education.gov.in', 'mhrd.gov.in'
        ]
        
        self.edu_domains = [
            'ac.in', 'edu.in', 'ncert.nic.in',
            'ncte.gov.in', 'ugc.ac.in'
        ]
        
        self.international_authority = [
            'unesco.org', 'worldbank.org', 'oecd.org',
            'unicef.org'
        ]
    
    def rerank(
        self,
        results: List[Dict],
        top_k: int = 20
    ) -> List[Dict]:
        """
        Rerank internet results by authority
        
        Args:
            results: Internet search results
            top_k: Final result count
            
        Returns:
            Reranked results
        """
        scored_results = []
        
        for result in results:
            # Base score (inverse rank)
            base_score = 1.0 / result.get('rank', 1)
            
            # Calculate boosts
            authority_boost = self._get_authority_boost(result)
            recency_boost = self._get_recency_boost(result)
            
            # Final score
            final_score = base_score * authority_boost * recency_boost
            
            # Add score
            result['rerank_score'] = final_score
            result['authority_boost'] = authority_boost
            result['recency_boost'] = recency_boost
            
            scored_results.append(result)
        
        # Sort by rerank score
        scored_results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return scored_results[:top_k]
    
    def _get_authority_boost(self, result: Dict) -> float:
        """Calculate authority boost for a result"""
        url = result.get('url', '').lower()
        source = result.get('source', '').lower()
        
        boost = 1.0
        
        # Government domains
        if any(domain in url or domain in source for domain in self.gov_domains):
            boost *= self.gov_boost
        
        # Educational domains
        elif any(domain in url or domain in source for domain in self.edu_domains):
            boost *= self.edu_boost
        
        # International authority
        elif any(domain in url or domain in source for domain in self.international_authority):
            boost *= 1.2
        
        return boost
    
    def _get_recency_boost(self, result: Dict) -> float:
        """Calculate recency boost"""
        # Check title/snippet for year mentions
        title = result.get('title', '')
        snippet = result.get('snippet', '')
        
        current_year = datetime.now().year
        
        # Look for years in title/snippet
        years = re.findall(r'\b(20\d{2})\b', title + ' ' + snippet)
        
        if years:
            # Get most recent year mentioned
            max_year = max(int(y) for y in years)
            
            # Boost if current or recent year
            if max_year == current_year:
                return self.recency_boost
            elif max_year == current_year - 1:
                return 1.1
        
        return 1.0
    
    def filter_low_quality(
        self,
        results: List[Dict],
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Filter out low-quality results
        
        Args:
            results: Internet results
            min_score: Minimum score threshold
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            # Check for quality indicators
            has_snippet = bool(result.get('snippet'))
            has_title = bool(result.get('title'))
            
            if has_snippet and has_title:
                # Check snippet length (too short = low quality)
                snippet_len = len(result.get('snippet', ''))
                if snippet_len > 50:  # Reasonable snippet
                    filtered.append(result)
        
        return filtered
    
    def prioritize_official(
        self,
        results: List[Dict]
    ) -> List[Dict]:
        """
        Ensure official sources appear first
        
        Args:
            results: Internet results
            
        Returns:
            Reordered with official sources first
        """
        official = []
        others = []
        
        for result in results:
            url = result.get('url', '').lower()
            source = result.get('source', '').lower()
            
            is_official = any(
                domain in url or domain in source
                for domain in self.gov_domains
            )
            
            if is_official:
                official.append(result)
            else:
                others.append(result)
        
        # Official first, then others
        return official + others


# Convenience function
def rerank_internet_results(
    results: List[Dict],
    top_k: int = 20
) -> List[Dict]:
    """Quick internet reranking"""
    reranker = InternetReranker()
    return reranker.rerank(results, top_k)


if __name__ == "__main__":
    print("Internet Reranker")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.reranking import InternetReranker

reranker = InternetReranker(
    gov_boost=1.5,      # 50% boost for government
    edu_boost=1.3,      # 30% boost for education
    recency_boost=1.2   # 20% boost for recent
)

# Rerank internet results
reranked = reranker.rerank(
    results=internet_search_results,
    top_k=10
)

# Filter low quality
filtered = reranker.filter_low_quality(reranked)

# Prioritize official sources
prioritized = reranker.prioritize_official(filtered)

for result in prioritized:
    print(f"[{result['source']}] {result['title']}")
    print(f"  Score: {result['rerank_score']:.3f}")
    print(f"  Authority boost: {result['authority_boost']:.2f}x")
""")
    
    # Demo
    demo_results = [
        {
            'rank': 1,
            'title': 'Education Policy 2024',
            'url': 'https://education.gov.in/policy',
            'source': 'education.gov.in',
            'snippet': 'Official education policy 2024 guidelines...'
        },
        {
            'rank': 2,
            'title': 'Blog post about education',
            'url': 'https://myblog.com/education',
            'source': 'myblog.com',
            'snippet': 'Personal thoughts on education...'
        }
    ]
    
    reranker = InternetReranker()
    reranked = reranker.rerank(demo_results, top_k=2)
    
    print("\n\nDemo Results:")
    for i, result in enumerate(reranked, 1):
        print(f"{i}. [{result['source']}] {result['title']}")
        print(f"   Rerank score: {result['rerank_score']:.3f}")
        print(f"   Authority boost: {result['authority_boost']:.2f}x")
        print()




















