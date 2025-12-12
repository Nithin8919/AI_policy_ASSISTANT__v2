# Query Understanding Coordinator

"""
Coordinates query understanding: normalization, interpretation, rewriting, expansion
"""

import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from query_understanding.query_normalizer import QueryNormalizer
from query_understanding.query_interpreter import QueryInterpreter, QueryInterpretation
from query_understanding.query_rewriter import QueryRewriter
from query_understanding.domain_expander import DomainExpander

logger = logging.getLogger(__name__)


class QueryUnderstandingCoordinator:
    """Coordinates query understanding pipeline"""
    
    def __init__(
        self,
        normalizer: QueryNormalizer,
        interpreter: QueryInterpreter,
        rewriter: QueryRewriter,
        expander: DomainExpander,
        executor: ThreadPoolExecutor,
        use_llm_rewrites: bool = False
    ):
        self.normalizer = normalizer
        self.interpreter = interpreter
        self.rewriter = rewriter
        self.expander = expander
        self.executor = executor
        self.use_llm_rewrites = use_llm_rewrites
    
    def extract_entities_from_text(self, text: str) -> List[str]:
        """Extract explicit entities like GOs, Acts, Sections from text"""
        if not text:
            return []
            
        import re
        entities = []
        
        # GO patterns: GO Ms No 123, G.O.Rt.No. 456, G.O.Ms.No. 789, GO Number 123
        go_pattern = r'G\.?O\.?\s*(?:Ms\.?|Rt\.?|P\.?)?[\s\.]?(?:No\.?|Number)?\s*\d+'
        entities.extend(re.findall(go_pattern, text, re.IGNORECASE))
        
        # Act patterns: X Act, 2020 (simple heuristic)
        act_pattern = r'(?:The\s+)?([A-Z][a-zA-Z\s]+Act(?:,?\s+\d{4})?)'
        matches = re.findall(act_pattern, text)
        entities.extend([m for m in matches if len(m) > 10 and len(m) < 50])
        
        return list(set(entities))
    
    def understand_query(
        self,
        query: str,
        normalized_query: Optional[str] = None,
        external_context: Optional[str] = None,
        is_qa_mode: bool = False,
        num_rewrites: Optional[int] = None
    ) -> tuple[QueryInterpretation, List[str], List[str]]:
        """
        Understand query: interpret, rewrite, expand
        
        Args:
            query: Original query
            normalized_query: Pre-normalized query (if already normalized)
            external_context: External context from uploaded files
            is_qa_mode: Whether this is QA mode (lightweight)
        
        Returns:
            (interpretation, rewrites, expanded_rewrites)
        """
        # Normalize query if not already normalized
        if normalized_query is None:
            normalized_query = self.normalizer.normalize_query(query)
            logger.info(f"📝 Normalized query: {normalized_query}")
        else:
            # Use provided normalized query
            logger.info(f"📝 Using pre-normalized query: {normalized_query}")
        
        # Extract entities from external context (uploaded files)
        context_entities = []
        if external_context:
            context_entities = self.extract_entities_from_text(external_context)
            if context_entities:
                logger.info(f"📄 Extracted entities from file: {context_entities}")
        
        # Submit parallel tasks for query understanding
        understanding_futures = {}
        
        # Interpretation task (pass both normalized and original for context)
        understanding_futures['interpretation'] = self.executor.submit(
            self.interpreter.interpret_query, normalized_query, query
        )
        
        # Rewrites task
        # Use provided num_rewrites if available, otherwise default based on mode
        if num_rewrites is None:
            num_rewrites = 1 if is_qa_mode else 3  # Default: QA minimal, others moderate
        
        if self.use_llm_rewrites and not is_qa_mode:
            # Skip LLM rewrites for QA mode (saves ~10s)
            understanding_futures['rewrites'] = self.executor.submit(
                self.rewriter.generate_rewrites_with_gemini,
                normalized_query, num_rewrites
            )
        else:
            understanding_futures['rewrites'] = self.executor.submit(
                self.rewriter.generate_rewrites,
                normalized_query, num_rewrites
            )
        
        # Wait for parallel tasks to complete
        # OPTIMIZATION: Reduced timeouts for faster failure detection
        try:
            interpretation = understanding_futures['interpretation'].result(timeout=3)  # Reduced from 5s
            rewrites_obj = understanding_futures['rewrites'].result(timeout=5)  # Reduced from 10s
            # Add context entities to rewrites to ensure they are searched
            rewrites = [normalized_query] + [r.text for r in rewrites_obj] + context_entities
        except Exception as e:
            # Log error but don't print full trace (may contain API key errors from libraries)
            error_msg = str(e)
            # Filter out API key related errors in logs (they're expected when using OAuth)
            if "API key" not in error_msg and "API_KEY" not in error_msg:
                logger.warning(f"Parallel query understanding failed: {error_msg[:200]}")
            # Fallback to sequential (rule-based rewrites)
            interpretation = self.interpreter.interpret_query(normalized_query, query)
            rewrites = [normalized_query]
        
        # Expand with domain keywords (parallel)
        # OPTIMIZATION: Mode-aware expansion
        # Deep think/brainstorm need more expansion for comprehensive retrieval
        if is_qa_mode:
            expansion_keywords = 3  # QA: minimal expansion
        elif num_rewrites and num_rewrites >= 5:
            expansion_keywords = 10  # Deep think/brainstorm: more expansion
        else:
            expansion_keywords = 8  # Default: moderate expansion
        expansion_futures = {
            self.executor.submit(self.expander.expand_query, r, expansion_keywords): r 
            for r in rewrites
        }
        
        expanded_rewrites = []
        for future in as_completed(expansion_futures, timeout=2):  # Reduced from 3s
            try:
                expanded = future.result()
                expanded_rewrites.append(expanded)
            except Exception as e:
                original_query = expansion_futures[future]
                print(f"Expansion failed for '{original_query}': {e}")
                expanded_rewrites.append(original_query)  # Use original as fallback
        
        return interpretation, rewrites, expanded_rewrites
