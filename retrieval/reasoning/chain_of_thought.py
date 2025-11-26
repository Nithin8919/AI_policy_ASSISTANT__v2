# Deep Think multi-step logic

"""
Chain of Thought
================
Multi-step reasoning for Deep Think mode.
Optional LLM integration for synthesis (not required for retrieval).
"""

from typing import List, Dict, Optional


class ChainOfThoughtReasoner:
    """
    Chain-of-thought reasoning for policy analysis.
    
    Note: This is optional and NOT used in the core retrieval pipeline.
    It's here for future LLM synthesis integration.
    """
    
    def build_reasoning_chain(
        self,
        query: str,
        results: List[Dict],
        reasoning_structure: Dict
    ) -> List[Dict]:
        """
        Build chain-of-thought reasoning steps.
        
        Args:
            query: Original query
            results: Retrieved results
            reasoning_structure: Reasoning structure from Deep Think mode
            
        Returns:
            List of reasoning steps
        """
        steps = []
        
        # Step 1: Constitutional Foundation
        if reasoning_structure.get("constitutional_foundation"):
            steps.append({
                "step": 1,
                "title": "Constitutional Foundation",
                "description": "Identify constitutional provisions and fundamental rights",
                "sources": reasoning_structure["constitutional_foundation"],
                "key_points": self._extract_key_points(
                    reasoning_structure["constitutional_foundation"]
                )
            })
        
        # Step 2: Statutory Framework
        if reasoning_structure.get("statutory_framework"):
            steps.append({
                "step": 2,
                "title": "Acts and Rules",
                "description": "Review relevant acts, rules, and legal provisions",
                "sources": reasoning_structure["statutory_framework"],
                "key_points": self._extract_key_points(
                    reasoning_structure["statutory_framework"]
                )
            })
        
        # Step 3: Administrative Orders
        if reasoning_structure.get("administrative_orders"):
            steps.append({
                "step": 3,
                "title": "Government Orders",
                "description": "Examine implementation through government orders",
                "sources": reasoning_structure["administrative_orders"],
                "key_points": self._extract_key_points(
                    reasoning_structure["administrative_orders"]
                )
            })
        
        # Step 4: Judicial Interpretation
        if reasoning_structure.get("judicial_precedents"):
            steps.append({
                "step": 4,
                "title": "Judicial Precedents",
                "description": "Consider court interpretations and legal constraints",
                "sources": reasoning_structure["judicial_precedents"],
                "key_points": self._extract_key_points(
                    reasoning_structure["judicial_precedents"]
                )
            })
        
        # Step 5: Data Evidence
        if reasoning_structure.get("data_evidence"):
            steps.append({
                "step": 5,
                "title": "Empirical Evidence",
                "description": "Review data, statistics, and ground realities",
                "sources": reasoning_structure["data_evidence"],
                "key_points": self._extract_key_points(
                    reasoning_structure["data_evidence"]
                )
            })
        
        # Step 6: Implementation Mechanisms
        if reasoning_structure.get("implementation_schemes"):
            steps.append({
                "step": 6,
                "title": "Implementation Schemes",
                "description": "Examine delivery mechanisms and programs",
                "sources": reasoning_structure["implementation_schemes"],
                "key_points": self._extract_key_points(
                    reasoning_structure["implementation_schemes"]
                )
            })
        
        return steps
    
    def _extract_key_points(self, sources: List[Dict]) -> List[str]:
        """Extract key points from sources (simple extraction)"""
        key_points = []
        
        for source in sources[:3]:  # Top 3 sources
            text = source.get("text", "")
            if text:
                # Extract first sentence as key point
                sentences = text.split(".")
                if sentences:
                    key_points.append(sentences[0].strip() + ".")
        
        return key_points
    
    def build_synthesis_prompt(
        self,
        query: str,
        reasoning_steps: List[Dict]
    ) -> str:
        """
        Build prompt for LLM synthesis (optional).
        
        Args:
            query: Original query
            reasoning_steps: Reasoning steps
            
        Returns:
            Prompt string
        """
        prompt = f"""Provide a comprehensive policy analysis for the following query:

Query: {query}

Using the following chain-of-thought reasoning:

"""
        
        for step in reasoning_steps:
            prompt += f"\n{step['step']}. {step['title']}\n"
            prompt += f"{step['description']}\n"
            
            if step.get("key_points"):
                prompt += "Key Points:\n"
                for point in step["key_points"]:
                    prompt += f"- {point}\n"
            
            prompt += "\n"
        
        prompt += """
Based on this multi-layered analysis, provide:
1. Legal foundation and constraints
2. Administrative implementation realities
3. Judicial considerations
4. Data-backed insights
5. Practical recommendations

Format the response with clear sections and citations."""
        
        return prompt


# Global reasoner instance
_reasoner_instance = None


def get_chain_of_thought_reasoner() -> ChainOfThoughtReasoner:
    """Get global chain-of-thought reasoner instance"""
    global _reasoner_instance
    if _reasoner_instance is None:
        _reasoner_instance = ChainOfThoughtReasoner()
    return _reasoner_instance