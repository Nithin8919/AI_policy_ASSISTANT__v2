import os
import logging
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from dataclasses import dataclass

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class DiagnosticResult:
    """Result of a diagnostic test"""
    test_name: str
    output: str
    status: str = "completed"

class DiagnosticRunner:
    """
    Runs diagnostic tests on the retrieval and generation pipeline.
    Implements the 5 specific tests requested for debugging.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize diagnostic runner
        
        Args:
            api_key: Gemini API key
        """
        # Prefer explicit arg, then GEMINI_API_KEY, then GOOGLE_API_KEY
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        else:
            logger.warning("No API key provided for DiagnosticRunner. Diagnostics will fail.")
            self.model = None

    def _format_docs(self, results: List[Any]) -> str:
        """Format retrieval results for the prompt"""
        doc_text = ""
        for i, res in enumerate(results, 1):
            # Handle both object and dict results
            if isinstance(res, dict):
                content = res.get('content', '')
                meta = res.get('metadata', {})
                doc_id = res.get('doc_id', 'unknown')
            else:
                content = getattr(res, 'content', '')
                meta = getattr(res, 'metadata', {})
                doc_id = getattr(res, 'doc_id', 'unknown')
                
            doc_text += f"Document {i} (ID: {doc_id}):\n{content}\nMetadata: {meta}\n\n"
        return doc_text

    def run_retrieval_sanity_test(self, query: str, results: List[Any]) -> DiagnosticResult:
        """
        Test 1: Retrieval sanity test
        'What exact documents did you retrieve? List them and summarize each in 2 lines.'
        """
        if not self.model:
            return DiagnosticResult("Retrieval Sanity", "Error: No API key")
            
        docs = self._format_docs(results)
        prompt = f"""
        You are diagnosing a retrieval system.
        
        User Query: "{query}"
        
        Retrieved Documents:
        {docs}
        
        Task: What exact documents did you retrieve? List them and summarize each in 2 lines.
        If the documents are irrelevant to the query, explicitly state that.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return DiagnosticResult("Retrieval Sanity Test", response.text)
        except Exception as e:
            return DiagnosticResult("Retrieval Sanity Test", f"Error: {str(e)}", "failed")

    def run_missing_info_test(self, query: str, results: List[Any]) -> DiagnosticResult:
        """
        Test 2: Missing-information test
        'Based on the retrieved docs, list what information you still don’t have but is needed for a full answer.'
        """
        if not self.model:
            return DiagnosticResult("Missing Info", "Error: No API key")
            
        docs = self._format_docs(results)
        prompt = f"""
        You are diagnosing a retrieval system.
        
        User Query: "{query}"
        
        Retrieved Documents:
        {docs}
        
        Task: Based on the retrieved docs, list what information you still don’t have but is needed for a full answer.
        Be specific about what is missing.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return DiagnosticResult("Missing Information Test", response.text)
        except Exception as e:
            return DiagnosticResult("Missing Information Test", f"Error: {str(e)}", "failed")

    def run_policy_structure_test(self, query: str, results: List[Any]) -> DiagnosticResult:
        """
        Test 3: Policy-grade structure test
        'Answer using: 1) background, 2) current rules, 3) gaps, 4) recommendations.'
        """
        if not self.model:
            return DiagnosticResult("Policy Structure", "Error: No API key")
            
        docs = self._format_docs(results)
        prompt = f"""
        You are a policy assistant.
        
        User Query: "{query}"
        
        Context:
        {docs}
        
        Task: Answer the query using EXACTLY this structure:
        1) Background
        2) Current Rules (cited from context)
        3) Gaps (what is not clear from context)
        4) Recommendations
        """
        
        try:
            response = self.model.generate_content(prompt)
            return DiagnosticResult("Policy Structure Test", response.text)
        except Exception as e:
            return DiagnosticResult("Policy Structure Test", f"Error: {str(e)}", "failed")

    def run_reasoning_test(self, query: str, results: List[Any]) -> DiagnosticResult:
        """
        Test 4: Explain-your-reasoning test
        'Explain step-by-step how you formed this answer from the retrieved text.'
        """
        if not self.model:
            return DiagnosticResult("Reasoning", "Error: No API key")
            
        docs = self._format_docs(results)
        prompt = f"""
        You are diagnosing a retrieval system.
        
        User Query: "{query}"
        
        Retrieved Documents:
        {docs}
        
        Task: Explain step-by-step how you would form an answer from the retrieved text.
        Connect specific facts in the text to the user's query.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return DiagnosticResult("Reasoning Test", response.text)
        except Exception as e:
            return DiagnosticResult("Reasoning Test", f"Error: {str(e)}", "failed")

    def run_contradiction_test(self, query: str, results: List[Any]) -> DiagnosticResult:
        """
        Test 5: Contradiction test
        'Tell me what parts of your answer might be inaccurate or need verification.'
        """
        if not self.model:
            return DiagnosticResult("Contradiction", "Error: No API key")
            
        docs = self._format_docs(results)
        prompt = f"""
        You are diagnosing a retrieval system.
        
        User Query: "{query}"
        
        Retrieved Documents:
        {docs}
        
        Task: Draft an answer, and then tell me what parts of your answer might be inaccurate or need verification based ONLY on the provided text.
        Identify any assumptions you had to make.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return DiagnosticResult("Contradiction Test", response.text)
        except Exception as e:
            return DiagnosticResult("Contradiction Test", f"Error: {str(e)}", "failed")

    def run_full_diagnostic(self, query: str, results: List[Any]) -> Dict[str, str]:
        """
        Run the single diagnostic prompt that breaks down everything.
        """
        if not self.model:
            return {"error": "No API key"}
            
        docs = self._format_docs(results)
        prompt = f"""
        You are a rigorous system evaluator.
        
        User Query: "{query}"
        
        Retrieved Documents:
        {docs}
        
        Task: Break down your answer into:
        
        1. What the retrieved documents actually say (Cite specific docs)
        2. What gaps exist (What is missing to fully answer the user)
        3. What assumptions you made (If any)
        4. What else you would need for a complete policy answer
        5. A corrected version based ONLY on verifiable information
        
        Be brutally honest about the quality of the retrieval.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return {
                "diagnostic_output": response.text,
                "query": query,
                "doc_count": len(results)
            }
        except Exception as e:
            return {"error": str(e)}

    def run_all_tests(self, query: str, results: List[Any]) -> Dict[str, Any]:
        """Run all diagnostic tests"""
        return {
            "sanity": self.run_retrieval_sanity_test(query, results),
            "missing_info": self.run_missing_info_test(query, results),
            "structure": self.run_policy_structure_test(query, results),
            "reasoning": self.run_reasoning_test(query, results),
            "contradiction": self.run_contradiction_test(query, results),
            "full_diagnostic": self.run_full_diagnostic(query, results)
        }
