# Multi-Hop Retrieval - expand and re-retrieve

"""
Multi-Hop Retrieval - Iterative query expansion
Extract terms from initial results → re-search
"""

from typing import List, Dict
import re


class MultiHopRetriever:
    """Multi-hop iterative retrieval"""
    
    def __init__(self, base_retriever):
        """
        Args:
            base_retriever: VerticalRetriever instance
        """
        self.retriever = base_retriever
    
    def multi_hop_search(
        self,
        initial_query: str,
        verticals: List[str],
        num_hops: int = 2,
        top_k_per_hop: int = 20
    ) -> List[Dict]:
        """
        Perform multi-hop retrieval
        
        Args:
            initial_query: Starting query
            verticals: Collections to search
            num_hops: Number of hops (1-3)
            top_k_per_hop: Results per hop
            
        Returns:
            Combined results from all hops
        """
        all_results = []
        current_query = initial_query
        
        for hop in range(num_hops):
            # Search current query
            results = self.retriever.search_multiple_verticals(
                verticals=verticals,
                query=current_query,
                top_k_per_vertical=top_k_per_hop
            )
            
            # Tag with hop number
            for r in results:
                r.metadata['hop_number'] = hop + 1
            
            all_results.extend(results)
            
            # Extract terms for next hop
            if hop < num_hops - 1:
                current_query = self._extract_hop_query(results[:10])
        
        return all_results
    
    def _extract_hop_query(self, results: List) -> str:
        """Extract key terms from results for next hop"""
        # Extract GO refs, sections, etc.
        terms = set()
        
        for result in results:
            content = result.content
            
            # GO references
            go_refs = re.findall(
                r'GO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*\d+',
                content,
                re.IGNORECASE
            )
            terms.update(go_refs[:2])
            
            # Sections
            sections = re.findall(r'Section\s+\d+', content, re.IGNORECASE)
            terms.update(sections[:2])
        
        return ' '.join(list(terms)[:5])


if __name__ == "__main__":
    print("Multi-hop retriever - requires base retriever")
























