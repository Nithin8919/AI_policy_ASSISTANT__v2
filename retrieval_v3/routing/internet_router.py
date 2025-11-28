# Internet Router - when to call Google PSE

"""
Internet Router - Decide when to use internet search
Triggers: latest, recent, 2024+, current events
"""

import re
from typing import Dict, List
from datetime import datetime


class InternetRouter:
    """Determine when internet search is needed"""
    
    # Patterns that trigger internet search
    INTERNET_TRIGGERS = {
        'temporal_recent': [
            r'\blatest\b',
            r'\brecent\b',
            r'\bcurrent\b',
            r'\bnew\b',
            r'\bupdated\b',
            r'\bthis\s+year\b',
            r'\btoday\b',
            r'\bnow\b',
            r'\bpresent\b',
        ],
        
        'future_years': [
            r'\b202[4-9]\b',  # 2024-2029
            r'\b203\d\b',     # 2030-2039
        ],
        
        'news_events': [
            r'\bnews\b',
            r'\bannouncement\b',
            r'\blaunched?\b',
            r'\bintroduced\b',
            r'\bchanges?\b',
        ],
        
        'comparative': [
            r'\bversus\b',
            r'\bvs\.?\b',
            r'\bcompare.*(?:with|to)\b',
            r'\bdifference.*between\b',
        ]
    }
    
    def __init__(self):
        """Initialize router"""
        self.current_year = datetime.now().year
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns"""
        self.compiled_patterns = {}
        
        for category, patterns in self.INTERNET_TRIGGERS.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def should_use_internet(self, query: str, query_metadata: Dict = None) -> bool:
        """
        Determine if internet search should be used
        
        Args:
            query: User query
            query_metadata: Optional metadata (detected entities, etc.)
            
        Returns:
            True if internet search recommended
        """
        # Check pattern matches
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    return True
        
        # Check metadata if provided
        if query_metadata:
            # Check for future years in entities
            if 'years' in query_metadata:
                for year in query_metadata['years']:
                    try:
                        if int(year) >= self.current_year:
                            return True
                    except ValueError:
                        pass
            
            # Check if explicitly marked
            if query_metadata.get('needs_internet'):
                return True
        
        return False
    
    def get_internet_keywords(self, query: str) -> List[str]:
        """
        Extract keywords that triggered internet search
        
        Returns:
            List of trigger keywords/phrases
        """
        triggers = []
        
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(query)
                if matches:
                    triggers.extend(matches)
        
        return triggers
    
    def get_search_scope(self, query: str) -> str:
        """
        Determine scope of internet search
        
        Returns:
            'broad', 'recent', or 'specific'
        """
        # Recent events
        recent_indicators = ['latest', 'recent', 'today', 'this year']
        if any(ind in query.lower() for ind in recent_indicators):
            return 'recent'
        
        # Broad research
        broad_indicators = ['comprehensive', 'all', 'complete', 'overview']
        if any(ind in query.lower() for ind in broad_indicators):
            return 'broad'
        
        # Specific lookup
        return 'specific'
    
    def should_prioritize_internet(self, query: str) -> bool:
        """
        Determine if internet results should be prioritized over local
        
        Returns:
            True if internet should be primary source
        """
        # Strong internet indicators
        strong_triggers = [
            r'\blatest\s+news\b',
            r'\bbreaking\b',
            r'\bjust\s+announced\b',
            r'\btoday.*announced\b',
        ]
        
        for trigger in strong_triggers:
            if re.search(trigger, query, re.IGNORECASE):
                return True
        
        return False


# Convenience function
def should_use_internet(query: str) -> bool:
    """Quick internet routing decision"""
    router = InternetRouter()
    return router.should_use_internet(query)


if __name__ == "__main__":
    router = InternetRouter()
    
    test_queries = [
        "What is RTE Section 12?",  # No internet
        "Latest education policies 2025",  # Yes - future year + latest
        "What are the current FLN guidelines?",  # Yes - current
        "Teacher transfer rules in GO 54",  # No internet
        "Compare Nadu-Nedu with Samagra Shiksha",  # Maybe internet
        "News about new education schemes",  # Yes - news
        "Recent changes in midday meal policy",  # Yes - recent
    ]
    
    print("Internet Router Tests:")
    print("=" * 80)
    
    for query in test_queries:
        use_internet = router.should_use_internet(query)
        prioritize = router.should_prioritize_internet(query)
        scope = router.get_search_scope(query)
        triggers = router.get_internet_keywords(query)
        
        print(f"\nQuery: {query}")
        print(f"  Use Internet: {use_internet}")
        if use_internet:
            print(f"  Prioritize Internet: {prioritize}")
            print(f"  Scope: {scope}")
            print(f"  Triggers: {triggers}")
        print("-" * 80)