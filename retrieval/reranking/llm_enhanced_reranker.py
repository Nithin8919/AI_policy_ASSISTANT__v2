"""
LLM-Enhanced Reranking
=======================
Uses LLM for semantic reranking in Deep Think mode.
Provides true semantic understanding of relevance.

Performance:
- Deep Think: +3-5s but much better result quality
- Only used for top 30 results (not all results)
- Batch processing for efficiency
"""

from typing import List, Dict
import json


class LLMReranker:
    """LLM-based semantic reranking"""
    
    def __init__(self, llm_client=None):
        """
        Initialize LLM reranker.
        
        Args:
            llm_client: Anthropic client
        """
        self.llm_client = llm_client
        self._ensure_client()
    
    def _ensure_client(self):
        """Ensure LLM client is initialized"""
        if self.llm_client is None:
            try:
                import anthropic
                import os
                self.llm_client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
            except Exception as e:
                print(f"Warning: Could not initialize Anthropic client: {e}")
                self.llm_client = None
    
    def rerank_deep_think(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 20
    ) -> List[Dict]:
        """
        Rerank results using LLM for Deep Think mode.
        
        Only reranks top 30 results from initial retrieval.
        Uses LLM to understand semantic relevance and policy importance.
        
        Args:
            query: User query
            results: Retrieved results
            top_k: Number of results to return
            
        Returns:
            Reranked results
        """
        if not self.llm_client or len(results) == 0:
            return results[:top_k]
        
        # Only rerank top 30 (cost optimization)
        candidates = results[:30]
        
        # Prepare documents for LLM
        docs_text = self._prepare_documents(candidates)
        
        prompt = f"""You are a policy research expert. Rank these policy documents by relevance to the query.

Query: "{query}"

Documents:
{docs_text}

Consider:
1. Direct relevance to query intent
2. Policy hierarchy (Constitutional > Acts > GOs > Judgments > Data > Schemes)
3. Recency and current applicability
4. Authority and binding nature
5. Comprehensiveness of information

Return ONLY a JSON array of document IDs ranked by relevance (most relevant first):
["doc_id_1", "doc_id_2", "doc_id_3", ...]

Include ALL document IDs, no explanations."""

        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # More capable for analysis
                max_tokens=500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            ranked_ids = json.loads(content)
            
            # Reorder results based on LLM ranking
            reranked = self._reorder_by_ids(candidates, ranked_ids)
            
            # Add remaining results (if any)
            reranked.extend(results[30:])
            
            # Mark as LLM reranked
            for i, result in enumerate(reranked[:top_k]):
                result["llm_reranked"] = True
                result["llm_rank"] = i + 1
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"LLM reranking failed: {e}, using original ranking")
            return results[:top_k]
    
    def _prepare_documents(self, results: List[Dict], max_length: int = 200) -> str:
        """Prepare documents for LLM prompt"""
        docs = []
        for i, result in enumerate(results):
            doc_id = result.get("id", f"doc_{i}")
            text = result.get("text", "")[:max_length]
            vertical = result.get("vertical", "unknown")
            score = result.get("score", 0.0)
            
            metadata = result.get("metadata", {})
            meta_str = ""
            
            # Add relevant metadata
            if vertical == "legal":
                act = metadata.get("act_name", "")
                section = metadata.get("section_number", "")
                if act or section:
                    meta_str = f" [{act} Section {section}]"
            elif vertical == "go":
                go_num = metadata.get("go_number", "")
                year = metadata.get("year", "")
                if go_num:
                    meta_str = f" [GO {go_num}, {year}]"
            elif vertical == "judicial":
                case = metadata.get("case_number", "")
                court = metadata.get("court_name", "")
                if case:
                    meta_str = f" [{case}, {court}]"
            
            doc = f"ID: {doc_id}\nVertical: {vertical}{meta_str}\nScore: {score:.3f}\nText: {text}...\n"
            docs.append(doc)
        
        return "\n---\n".join(docs)
    
    def _reorder_by_ids(self, results: List[Dict], ranked_ids: List[str]) -> List[Dict]:
        """Reorder results based on LLM ranking"""
        # Create ID to result mapping
        id_map = {r.get("id", f"doc_{i}"): r for i, r in enumerate(results)}
        
        # Reorder
        reranked = []
        for doc_id in ranked_ids:
            if doc_id in id_map:
                reranked.append(id_map[doc_id])
        
        # Add any missing results at the end
        reranked_ids = set(ranked_ids)
        for result in results:
            doc_id = result.get("id", "")
            if doc_id not in reranked_ids:
                reranked.append(result)
        
        return reranked
    
    def rerank_with_reasoning(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 10
    ) -> Dict:
        """
        Rerank with explicit reasoning for each result.
        More expensive but provides transparency.
        
        Args:
            query: User query
            results: Retrieved results
            top_k: Number to analyze
            
        Returns:
            Dict with reranked results and reasoning
        """
        if not self.llm_client or len(results) == 0:
            return {"results": results[:top_k], "method": "fallback"}
        
        candidates = results[:top_k]
        docs_text = self._prepare_documents(candidates)
        
        prompt = f"""Analyze relevance of each document to the query and provide rankings with reasoning.

Query: "{query}"

Documents:
{docs_text}

For each document, provide:
1. Relevance score (0-10)
2. Brief reasoning (one sentence)

Return ONLY valid JSON:
{{
  "doc_id_1": {{"score": 9, "reasoning": "..."}},
  "doc_id_2": {{"score": 7, "reasoning": "..."}},
  ...
}}"""

        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            scores = json.loads(content)
            
            # Add LLM scores to results
            for result in candidates:
                doc_id = result.get("id", "")
                if doc_id in scores:
                    result["llm_score"] = scores[doc_id].get("score", 0)
                    result["llm_reasoning"] = scores[doc_id].get("reasoning", "")
            
            # Sort by LLM score
            candidates.sort(key=lambda x: x.get("llm_score", 0), reverse=True)
            
            return {
                "results": candidates,
                "method": "llm_reasoning",
                "model": "claude-3-5-sonnet-20241022"
            }
            
        except Exception as e:
            print(f"LLM reasoning failed: {e}")
            return {
                "results": results[:top_k],
                "method": "fallback_error",
                "error": str(e)
            }


# Global singleton
_llm_reranker_instance = None


def get_llm_reranker() -> LLMReranker:
    """Get global LLM reranker instance"""
    global _llm_reranker_instance
    if _llm_reranker_instance is None:
        _llm_reranker_instance = LLMReranker()
    return _llm_reranker_instance