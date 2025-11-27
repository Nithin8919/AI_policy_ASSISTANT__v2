"""
Trigger Rules
=============
Determines which sources to query based on user input and mode.
Clean, deterministic logic. No LLM needed.
"""

from typing import Dict, List, Set
from dataclasses import dataclass

from .config import get_orchestrator_config


@dataclass
class TriggerDecision:
    """What sources should we query?"""
    use_local: bool = True
    use_internet: bool = False
    use_theory: bool = False
    reason: str = ""


class TriggerEngine:
    """
    Decides which sources to query.
    Rule-based, deterministic, fast.
    """
    
    def __init__(self):
        self.config = get_orchestrator_config()
    
    def decide(
        self,
        query: str,
        mode: str,
        internet_toggle: bool = False
    ) -> TriggerDecision:
        """
        Main decision function.
        
        Args:
            query: User query
            mode: Query mode (qa, deep_think, brainstorm)
            internet_toggle: User explicitly enabled internet?
            
        Returns:
            TriggerDecision with source flags
        """
        
        query_lower = query.lower()
        
        # Always use local RAG
        use_local = True
        
        # Internet triggers
        use_internet = self._should_use_internet(query_lower, mode, internet_toggle)
        
        # Theory triggers
        use_theory = self._should_use_theory(query_lower, mode)
        
        # Build reason
        reason = self._build_reason(use_local, use_internet, use_theory, mode, internet_toggle)
        
        return TriggerDecision(
            use_local=use_local,
            use_internet=use_internet,
            use_theory=use_theory,
            reason=reason
        )
    
    def _should_use_internet(self, query: str, mode: str, toggle: bool) -> bool:
        """Decide if internet search needed"""
        
        # 1. User explicitly enabled it
        if toggle:
            return True
        
        # 2. Brainstorm mode ALWAYS uses internet
        if mode in self.config.internet_always_on_modes:
            return True
        
        # 3. Query contains "recent", "latest", "current", "new", "today"
        recency_keywords = {
            "recent", "latest", "current", "new", "today", "yesterday",
            "this week", "this month", "this year", "2024", "2025",
            "update", "progress", "status", "now", "currently"
        }
        if any(keyword in query for keyword in recency_keywords):
            return True
        
        # 4. Query explicitly asks for external info
        external_keywords = {
            "international", "global", "worldwide", "other states",
            "other countries", "comparison", "benchmarking", "best practices",
            "external", "outside AP", "outside andhra pradesh"
        }
        if any(keyword in query for keyword in external_keywords):
            return True
        
        # 5. Query asks about something we might not have
        uncertainty_keywords = {
            "internet", "search", "online", "web", "google",
            "find out", "look up", "check", "verify"
        }
        if any(keyword in query for keyword in uncertainty_keywords):
            return True
        
        # Default: no internet
        return False
    
    def _should_use_theory(self, query: str, mode: str) -> bool:
        """Decide if theory corpus needed"""
        
        if not self.config.theory_enabled:
            return False
        
        # Check for theory keywords
        for keyword in self.config.theory_trigger_keywords:
            if keyword in query:
                return True
        
        # Theory is useful in brainstorm mode for foundational ideas
        if mode == "brainstorm":
            # Check if query is conceptual (not specific policy)
            conceptual_indicators = {
                "how to", "what is", "why", "improve", "enhance",
                "strategy", "approach", "framework", "model", "method"
            }
            if any(indicator in query for indicator in conceptual_indicators):
                return True
        
        return False
    
    def _build_reason(
        self,
        local: bool,
        internet: bool,
        theory: bool,
        mode: str,
        toggle: bool
    ) -> str:
        """Build human-readable reason"""
        
        parts = []
        
        if local:
            parts.append("local RAG")
        if internet:
            if toggle:
                parts.append("internet (user enabled)")
            elif mode == "brainstorm":
                parts.append("internet (brainstorm mode)")
            else:
                parts.append("internet (recency/external)")
        if theory:
            parts.append("theory corpus")
        
        return f"Using: {', '.join(parts)}"


# Singleton
_trigger_engine = None

def get_trigger_engine() -> TriggerEngine:
    """Get global trigger engine"""
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = TriggerEngine()
    return _trigger_engine