"""
LLM-Enhanced Query Enhancement
================================
Uses LLM for query expansion in Deep Think and Brainstorm modes.
Adds semantic understanding and domain expertise.

Performance:
- Deep Think: +2-3s but significantly better retrieval
- Brainstorm: +2-3s with creative query diversification
- QA: NOT used (rule-based only for speed)
"""

from typing import List, Dict, Optional
import json


class LLMQueryEnhancer:
    """LLM-based query enhancement for complex modes"""
    
    def __init__(self, llm_client=None):
        """
        Initialize LLM query enhancer.
        
        Args:
            llm_client: Anthropic client (will be initialized if None)
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
    
    def enhance_deep_think(self, query: str, entities: Dict) -> Dict:
        """
        Enhance query for Deep Think mode using LLM.
        
        Expands query with:
        - Synonyms and related terms
        - Policy-relevant framings
        - Legal terminology
        - Multi-perspective angles
        
        Args:
            query: Original query
            entities: Extracted entities
            
        Returns:
            Enhancement dict with expanded queries
        """
        if not self.llm_client:
            return {"expanded_queries": [query], "method": "fallback"}
        
        prompt = f"""You are a policy research expert. Expand this query for comprehensive policy document retrieval.

Original Query: "{query}"

Extracted Entities: {json.dumps(entities, indent=2)}

Generate 4-5 query variations that will help retrieve:
1. Legal/statutory provisions
2. Government orders and circulars
3. Judicial precedents
4. Data and statistics
5. Related schemes/programs

Each variation should:
- Use domain-specific terminology
- Target different aspects of the policy question
- Include relevant legal/administrative terms
- Cover both implementation and outcomes

Return ONLY a JSON array of query strings, no explanation:
["query1", "query2", "query3", "query4", "query5"]"""

        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-haiku-20241022",  # Fast, cheap model
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse JSON response
            expanded = json.loads(content)
            
            return {
                "expanded_queries": expanded,
                "original_query": query,
                "method": "llm_enhanced",
                "model": "claude-3-5-haiku-20241022"
            }
            
        except Exception as e:
            print(f"LLM enhancement failed: {e}, using fallback")
            return {
                "expanded_queries": [query],
                "method": "fallback_error",
                "error": str(e)
            }
    
    def enhance_brainstorm(self, query: str, entities: Dict) -> Dict:
        """
        Enhance query for Brainstorm mode using LLM.
        
        Expands query with:
        - Creative angles
        - International perspectives
        - Innovative approaches
        - Unconventional solutions
        
        Args:
            query: Original query
            entities: Extracted entities
            
        Returns:
            Enhancement dict with diverse queries
        """
        if not self.llm_client:
            return {"expanded_queries": [query], "method": "fallback"}
        
        prompt = f"""You are a creative policy innovation expert. Expand this query for brainstorming and discovering innovative solutions.

Original Query: "{query}"

Generate 4-5 creative query variations that will find:
1. International best practices and models
2. Innovative schemes from other states/countries
3. Experimental pilots and success stories
4. Unconventional solutions and approaches
5. Technology and innovation in policy

Each variation should:
- Think beyond conventional approaches
- Include international examples (Finland, Singapore, etc.)
- Look for creative/innovative implementations
- Cover technology and modern approaches

Return ONLY a JSON array of query strings, no explanation:
["query1", "query2", "query3", "query4", "query5"]"""

        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                temperature=0.7,  # Higher temperature for creativity
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            expanded = json.loads(content)
            
            return {
                "expanded_queries": expanded,
                "original_query": query,
                "method": "llm_creative",
                "model": "claude-3-5-haiku-20241022"
            }
            
        except Exception as e:
            print(f"LLM enhancement failed: {e}, using fallback")
            return {
                "expanded_queries": [query],
                "method": "fallback_error",
                "error": str(e)
            }
    
    def enhance_routing(self, query: str, entities: Dict) -> Dict:
        """
        Use LLM to intelligently route query to verticals.
        
        Args:
            query: Original query
            entities: Extracted entities
            
        Returns:
            Routing recommendations with reasoning
        """
        if not self.llm_client:
            return {"verticals": ["legal", "go"], "method": "fallback"}
        
        prompt = f"""You are a policy document routing expert. Analyze this query and recommend which document verticals to search.

Query: "{query}"
Entities: {json.dumps(entities, indent=2)}

Available Verticals:
- legal: Acts, Rules, Sections, Constitutional provisions
- go: Government Orders, Notifications, Circulars
- judicial: Court judgments, Cases, Precedents
- data: UDISE, ASER, Statistics, Reports
- schemes: Government schemes, Programs, International models

For each vertical, assign:
- priority: "high", "medium", "low", or "skip"
- reasoning: brief explanation

Return ONLY valid JSON:
{{
  "legal": {{"priority": "high", "reasoning": "..."}},
  "go": {{"priority": "medium", "reasoning": "..."}},
  "judicial": {{"priority": "low", "reasoning": "..."}},
  "data": {{"priority": "skip", "reasoning": "..."}},
  "schemes": {{"priority": "skip", "reasoning": "..."}}
}}"""

        try:
            response = self.llm_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=400,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            routing = json.loads(content)
            
            # Convert to prioritized list
            verticals = []
            for vertical, info in routing.items():
                priority = info.get("priority", "skip")
                if priority != "skip":
                    verticals.append({
                        "name": vertical,
                        "priority": priority,
                        "reasoning": info.get("reasoning", "")
                    })
            
            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            verticals.sort(key=lambda x: priority_order.get(x["priority"], 3))
            
            return {
                "verticals": verticals,
                "method": "llm_routing",
                "model": "claude-3-5-haiku-20241022"
            }
            
        except Exception as e:
            print(f"LLM routing failed: {e}, using fallback")
            return {
                "verticals": [
                    {"name": "legal", "priority": "high", "reasoning": "fallback"},
                    {"name": "go", "priority": "medium", "reasoning": "fallback"}
                ],
                "method": "fallback_error",
                "error": str(e)
            }


# Global singleton
_llm_enhancer_instance = None


def get_llm_query_enhancer() -> LLMQueryEnhancer:
    """Get global LLM query enhancer instance"""
    global _llm_enhancer_instance
    if _llm_enhancer_instance is None:
        _llm_enhancer_instance = LLMQueryEnhancer()
    return _llm_enhancer_instance