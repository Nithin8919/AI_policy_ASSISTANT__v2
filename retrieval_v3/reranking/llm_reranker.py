# LLM Reranker - semantic reranking with small LLM

"""
LLM Reranker - Use Gemini Flash for semantic reranking
"""

import os
from typing import List, Dict


class LLMReranker:
    """Rerank using Gemini Flash"""
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
    
    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 20
    ) -> List[Dict]:
        """
        Rerank results using Gemini
        
        Args:
            query: User query
            results: Initial results
            top_k: Final count
            
        Returns:
            Reranked results
        """
        if not self.api_key:
            # Fall back to score-based
            return sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:top_k]
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-8b')
            
            # Build prompt
            candidates_text = "\n\n".join([
                f"ID: {i}\nContent: {r.get('content', '')[:200]}..."
                for i, r in enumerate(results[:30])
            ])
            
            prompt = f"""Rank these by relevance to: {query}

{candidates_text}

Return only IDs comma-separated (most relevant first):"""

            response = model.generate_content(prompt)
            
            # Parse
            ranked_ids = [
                int(x.strip())
                for x in response.text.split(',')
                if x.strip().isdigit()
            ]
            
            # Reorder
            reranked = []
            for rank_id in ranked_ids:
                if rank_id < len(results):
                    result = results[rank_id]
                    result['llm_rank'] = len(reranked) + 1
                    reranked.append(result)
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"LLM rerank failed: {e}")
            return sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:top_k]

