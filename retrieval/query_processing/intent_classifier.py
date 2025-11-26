# Detects: QA / Deep Think / Brainstorm

"""
Intent Classifier
=================
Detects query mode: QA, Deep Think, or Brainstorm.
Rule-based, fast, deterministic.
"""

import re
from typing import Tuple
from ..config.mode_config import QueryMode


class IntentClassifier:
    """Classifies query intent to determine mode"""
    
    # Keywords that indicate each mode
    QA_KEYWORDS = {
        "what is", "define", "who is", "when was", "where is",
        "how many", "list", "show me", "section", "rule",
        "go number", "notification", "order", "judgment", "case"
    }
    
    DEEP_THINK_KEYWORDS = {
        "analyze", "explain in detail", "comprehensive", "deep dive",
        "policy analysis", "constitutional", "legal framework",
        "360", "holistic", "integrated", "synthesis", "implications",
        "impact", "assessment", "evaluation", "review"
    }
    
    BRAINSTORM_KEYWORDS = {
        "ideas", "suggestions", "brainstorm", "innovative", "creative",
        "new approaches", "best practices", "global models", "alternatives",
        "options", "possibilities", "improvements", "recommendations",
        "international", "comparison", "benchmarking", "Finland", "Singapore"
    }
    
    def classify(self, query: str) -> Tuple[QueryMode, float]:
        """
        Classify query into a mode.
        
        Args:
            query: User query
            
        Returns:
            Tuple of (mode, confidence)
        """
        query_lower = query.lower()
        
        # Count keyword matches for each mode
        qa_score = self._score_keywords(query_lower, self.QA_KEYWORDS)
        deep_score = self._score_keywords(query_lower, self.DEEP_THINK_KEYWORDS)
        brainstorm_score = self._score_keywords(query_lower, self.BRAINSTORM_KEYWORDS)
        
        # Additional heuristics
        
        # Very short queries (< 5 words) are usually QA
        word_count = len(query_lower.split())
        if word_count <= 5 and qa_score > 0:
            return QueryMode.QA, 0.9
        
        # Questions with specific entities (Section X, GO Y) are QA
        if self._has_specific_entity(query_lower):
            return QueryMode.QA, 0.85
        
        # Long queries (> 15 words) without specific keywords lean toward Deep Think
        if word_count > 15 and deep_score == 0 and brainstorm_score == 0:
            return QueryMode.DEEP_THINK, 0.7
        
        # Determine mode by highest score
        max_score = max(qa_score, deep_score, brainstorm_score)
        
        if max_score == 0:
            # Default to QA for simple queries
            return QueryMode.QA, 0.6
        
        if brainstorm_score == max_score and brainstorm_score > 0:
            return QueryMode.BRAINSTORM, min(0.6 + brainstorm_score * 0.1, 0.95)
        elif deep_score == max_score and deep_score > 0:
            return QueryMode.DEEP_THINK, min(0.6 + deep_score * 0.1, 0.95)
        else:
            return QueryMode.QA, min(0.7 + qa_score * 0.05, 0.95)
    
    def _score_keywords(self, query: str, keywords: set) -> int:
        """Count how many keywords appear in query"""
        score = 0
        for keyword in keywords:
            if keyword in query:
                score += 1
        return score
    
    def _has_specific_entity(self, query: str) -> bool:
        """Check if query contains specific entities"""
        patterns = [
            r'section\s+\d+',
            r'article\s+\d+',
            r'rule\s+\d+',
            r'go\s*[\d-]+',
            r'notification\s*no',
            r'case\s*no',
            r'\d{4}\s*\(\d+\)'  # Year (number) pattern for cases
        ]
        
        for pattern in patterns:
            if re.search(pattern, query):
                return True
        
        return False
    
    def classify_explicit(self, mode_str: str) -> QueryMode:
        """
        Explicitly set mode from string.
        
        Args:
            mode_str: "qa", "deep_think", or "brainstorm"
            
        Returns:
            QueryMode enum
        """
        mode_map = {
            "qa": QueryMode.QA,
            "deep_think": QueryMode.DEEP_THINK,
            "deep": QueryMode.DEEP_THINK,
            "brainstorm": QueryMode.BRAINSTORM,
            "ideate": QueryMode.BRAINSTORM
        }
        
        mode_str = mode_str.lower()
        if mode_str not in mode_map:
            raise ValueError(f"Unknown mode: {mode_str}")
        
        return mode_map[mode_str]


# Global classifier instance
_classifier_instance = None


def get_intent_classifier() -> IntentClassifier:
    """Get global intent classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance