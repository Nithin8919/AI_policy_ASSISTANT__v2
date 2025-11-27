"""
Query Orchestrator Router
==========================
Main orchestrator that coordinates local RAG, internet, and theory retrieval.
Clean, battle-tested, no BS.
"""

import time
import logging
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import get_orchestrator_config
from .triggers import get_trigger_engine
from .fusion import get_context_fusion
from .prompts import build_fusion_prompt

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """
    Main orchestrator.
    Decides which sources to query, merges results, returns unified context.
    """
    
    def __init__(self, retrieval_router=None):
        """
        Initialize orchestrator.
        
        Args:
            retrieval_router: Existing RetrievalRouter instance (injected)
        """
        self.config = get_orchestrator_config()
        self.trigger_engine = get_trigger_engine()
        self.fusion = get_context_fusion()
        
        # Injected dependencies
        self.retrieval_router = retrieval_router
        
        # Lazy-loaded services
        self._internet_client = None
        self._theory_retriever = None
    
    @property
    def internet_client(self):
        """Lazy load internet client"""
        if self._internet_client is None:
            from internet_service.client import get_internet_client
            self._internet_client = get_internet_client()
        return self._internet_client
    
    @property
    def theory_retriever(self):
        """Lazy load theory retriever"""
        if self._theory_retriever is None and self.config.theory_enabled:
            from theory_corpus.retriever import get_theory_retriever
            self._theory_retriever = get_theory_retriever()
        return self._theory_retriever
    
    def orchestrate(
        self,
        query: str,
        mode: str = "qa",
        internet_toggle: bool = False,
        top_k: int = None
    ) -> Dict:
        """
        Main orchestration function.
        
        Args:
            query: User query
            mode: Query mode (qa, deep_think, brainstorm)
            internet_toggle: User explicitly enabled internet?
            top_k: Optional override for result count
            
        Returns:
            Complete orchestration result with all contexts
        """
        
        start_time = time.time()
        
        try:
            logger.info(f"🎯 Orchestrating query: '{query}' (mode={mode}, internet={internet_toggle})")
            
            # 1. Decide which sources to use
            decision = self.trigger_engine.decide(query, mode, internet_toggle)
            
            logger.info(f"📋 {decision.reason}")
            
            # 2. Query sources in parallel
            results = self._query_sources_parallel(
                query=query,
                mode=mode,
                use_local=decision.use_local,
                use_internet=decision.use_internet,
                use_theory=decision.use_theory,
                top_k=top_k
            )
            
            # 3. Merge contexts
            merged_results, merge_metadata = self.fusion.merge(
                local_results=results.get("local"),
                internet_results=results.get("internet"),
                theory_results=results.get("theory")
            )
            
            # 4. Build fusion prompt
            fusion_prompt = build_fusion_prompt(
                query=query,
                local_results=results.get("local", []),
                internet_results=results.get("internet"),
                theory_results=results.get("theory"),
                mode=mode
            )
            
            orchestration_time = time.time() - start_time
            
            logger.info(f"✅ Orchestration complete in {orchestration_time:.2f}s: "
                       f"{merge_metadata['local_count']} local, "
                       f"{merge_metadata['internet_count']} internet, "
                       f"{merge_metadata['theory_count']} theory")
            
            return {
                "success": True,
                "query": query,
                "mode": mode,
                "decision": {
                    "use_local": decision.use_local,
                    "use_internet": decision.use_internet,
                    "use_theory": decision.use_theory,
                    "reason": decision.reason
                },
                "results": merged_results,
                "fusion_prompt": fusion_prompt,
                "formatted_contexts": self.fusion.format_for_llm(
                    results.get("local", []),
                    results.get("internet"),
                    results.get("theory")
                ),
                "metadata": {
                    **merge_metadata,
                    "orchestration_time": orchestration_time
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "mode": mode
            }
    
    def _query_sources_parallel(
        self,
        query: str,
        mode: str,
        use_local: bool,
        use_internet: bool,
        use_theory: bool,
        top_k: int = None
    ) -> Dict[str, List[Dict]]:
        """
        Query multiple sources in parallel.
        
        Returns:
            Dict with keys: local, internet, theory
        """
        
        results = {
            "local": [],
            "internet": [],
            "theory": []
        }
        
        futures = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            
            # Submit local RAG query
            if use_local and self.retrieval_router:
                futures["local"] = executor.submit(
                    self._query_local,
                    query,
                    mode,
                    top_k
                )
            
            # Submit internet query
            if use_internet:
                futures["internet"] = executor.submit(
                    self._query_internet,
                    query
                )
            
            # Submit theory query
            if use_theory:
                futures["theory"] = executor.submit(
                    self._query_theory,
                    query
                )
            
            # Collect results
            for source, future in futures.items():
                try:
                    results[source] = future.result(timeout=self.config.total_timeout)
                except Exception as e:
                    logger.error(f"Error querying {source}: {e}")
                    results[source] = []
        
        return results
    
    def _query_local(self, query: str, mode: str, top_k: int = None) -> List[Dict]:
        """Query local RAG"""
        
        try:
            logger.info("🔍 Querying local RAG...")
            
            response = self.retrieval_router.query(
                query=query,
                mode=mode,
                top_k=top_k
            )
            
            if response.get("success"):
                results = response.get("results", [])
                logger.info(f"✅ Local RAG returned {len(results)} results")
                return results
            else:
                logger.warning(f"Local RAG failed: {response.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Local RAG error: {e}")
            return []
    
    def _query_internet(self, query: str) -> List[Dict]:
        """Query internet"""
        
        try:
            logger.info("🌐 Querying internet...")
            
            result = self.internet_client.search(query)
            
            if result.success and result.has_results:
                snippets = [s.to_dict() for s in result.snippets]
                logger.info(f"✅ Internet returned {len(snippets)} snippets")
                return snippets
            else:
                logger.warning("No internet results")
                return []
                
        except Exception as e:
            logger.error(f"Internet query error: {e}")
            return []
    
    def _query_theory(self, query: str) -> List[Dict]:
        """Query theory corpus"""
        
        try:
            if not self.theory_retriever:
                logger.debug("Theory corpus not enabled")
                return []
            
            logger.info("📚 Querying theory corpus...")
            
            results = self.theory_retriever.search(query, top_k=3)
            
            logger.info(f"✅ Theory corpus returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Theory query error: {e}")
            return []


# Singleton
_orchestrator = None

def get_query_orchestrator(retrieval_router=None) -> QueryOrchestrator:
    """
    Get global orchestrator instance.
    
    Args:
        retrieval_router: Optional RetrievalRouter to inject
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = QueryOrchestrator(retrieval_router)
    return _orchestrator