# Query Normalization

"""
Query Normalizer - Clean and standardize user queries
Handles: lowercase, whitespace, abbreviations, special characters
"""

import re
from typing import Dict, List


class QueryNormalizer:
    """Clean and standardize user queries"""
    
    # Domain-specific abbreviations (AP Education context)
    ABBREVIATIONS = {
        # Education domain
        'go': 'government order',
        'gos': 'government orders',
        'rte': 'right to education',
        'fln': 'foundational literacy numeracy',
        'ssa': 'sarva shiksha abhiyan',
        'mdm': 'mid day meal',
        'rmsa': 'rashtriya madhyamik shiksha abhiyan',
        'npegel': 'national programme for education of girls at elementary level',
        'niepa': 'national institute of educational planning and administration',
        'ncert': 'national council of educational research and training',
        'ncte': 'national council for teacher education',
        'tet': 'teacher eligibility test',
        'ctet': 'central teacher eligibility test',
        'aptet': 'andhra pradesh teacher eligibility test',
        
        # Administrative
        'cse': 'commissioner of school education',
        'dee': 'director of elementary education',
        'dse': 'director of school education',
        'spo': 'state project office',
        'dpo': 'district project office',
        'mpo': 'mandal project office',
        'brcc': 'block resource centre coordinator',
        'crc': 'cluster resource centre',
        
        # Programs
        'pwds': 'persons with disabilities',
        'cwsn': 'children with special needs',
        'oosc': 'out of school children',
        'ecce': 'early childhood care and education',
        'npe': 'national policy on education',
        
        # Infrastructure
        'smdc': 'school management and development committee',
        'vmc': 'village monitoring committee',
        'pta': 'parent teacher association',
    }
    
    def __init__(self):
        """Initialize normalizer with patterns"""
        # Compile patterns for efficiency
        self.go_pattern = re.compile(r'GO\.?\s*(?:Ms\.?|Rt\.?)?\s*No\.?\s*(\d+)', re.IGNORECASE)
        self.section_pattern = re.compile(r'Section\s+(\d+(?:\([a-z0-9]+\))?)', re.IGNORECASE)
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    
    def normalize_query(self, text: str) -> str:
        """
        Main normalization pipeline
        
        Args:
            text: Raw user query
            
        Returns:
            Normalized query string
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Step 1: Basic cleaning
        text = self._basic_clean(text)
        
        # Step 2: Preserve important patterns (before lowercasing)
        preserved = self._preserve_patterns(text)
        
        # Step 3: Lowercase (except preserved patterns)
        text = self._selective_lowercase(text, preserved)
        
        # Step 4: Expand abbreviations
        text = self._expand_abbreviations(text)
        
        # Step 5: Fix common OCR/typing errors
        text = self._fix_common_errors(text)
        
        # Step 6: Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Step 7: Restore preserved patterns
        text = self._restore_patterns(text, preserved)
        
        return text.strip()
    
    def _basic_clean(self, text: str) -> str:
        """Remove or fix basic formatting issues"""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")
        
        # Remove excessive punctuation (but keep single instances)
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        
        return text
    
    def _preserve_patterns(self, text: str) -> Dict[str, List[str]]:
        """
        Preserve important patterns before normalization
        Returns dict of pattern_type -> [matches]
        """
        preserved = {
            'go_refs': [],
            'sections': [],
            'years': []
        }
        
        # Preserve GO references (e.g., "GO.Ms.No.42")
        for match in self.go_pattern.finditer(text):
            preserved['go_refs'].append(match.group(0))
        
        # Preserve section references (e.g., "Section 12(1)(c)")
        for match in self.section_pattern.finditer(text):
            preserved['sections'].append(match.group(0))
        
        # Preserve years
        for match in self.year_pattern.finditer(text):
            preserved['years'].append(match.group(0))
        
        return preserved
    
    def _selective_lowercase(self, text: str, preserved: Dict) -> str:
        """Lowercase but keep preserved patterns intact"""
        # Replace preserved patterns with placeholders
        placeholder_map = {}
        counter = 0
        
        for pattern_type, patterns in preserved.items():
            for pattern in patterns:
                placeholder = f"__PRESERVED_{counter}__"
                text = text.replace(pattern, placeholder)
                placeholder_map[placeholder] = pattern
                counter += 1
        
        # Now lowercase everything
        text = text.lower()
        
        # Store for later restoration
        self._placeholder_map = placeholder_map
        
        return text
    
    def _expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations"""
        words = text.split()
        expanded_words = []
        
        for word in words:
            # Remove trailing punctuation for matching
            clean_word = word.rstrip('.,!?;:')
            punctuation = word[len(clean_word):]
            
            # Check if abbreviation
            if clean_word in self.ABBREVIATIONS:
                expanded_words.append(self.ABBREVIATIONS[clean_word] + punctuation)
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def _fix_common_errors(self, text: str) -> str:
        """Fix common OCR and typing errors"""
        # Common OCR errors in legal documents
        replacements = {
            # Number/letter confusion
            r'\bl\b': '1',  # lowercase L as number 1
            r'\bO\b': '0',  # uppercase O as zero
            
            # Common typos in education domain
            'goverment': 'government',
            'govenment': 'government',
            'committe': 'committee',
            'recieve': 'receive',
            'occured': 'occurred',
            
            # Spacing issues
            'andhra pradesh': 'andhra pradesh',
            'right toeducation': 'right to education',
        }
        
        for error, correction in replacements.items():
            if error.startswith('\\b') or error.endswith('\\b'):
                # It's a regex pattern
                text = re.sub(error, correction, text, flags=re.IGNORECASE)
            else:
                # Simple string replacement
                text = text.replace(error, correction)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize all whitespace to single spaces"""
        # Replace tabs, newlines with spaces
        text = re.sub(r'[\t\n\r]+', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s*([,;:.!?])\s*', r'\1 ', text)
        
        return text.strip()
    
    def _restore_patterns(self, text: str, preserved: Dict) -> str:
        """Restore preserved patterns"""
        if hasattr(self, '_placeholder_map'):
            for placeholder, original in self._placeholder_map.items():
                text = text.replace(placeholder, original)
        
        return text
    
    def get_normalized_variants(self, text: str) -> List[str]:
        """
        Get multiple normalized variants of a query
        Useful for generating search variations
        
        Returns:
            List of normalized variants
        """
        variants = []
        
        # Original normalized
        normalized = self.normalize_query(text)
        variants.append(normalized)
        
        # Without abbreviation expansion
        text_basic = self._basic_clean(text)
        text_basic = self._normalize_whitespace(text_basic.lower())
        if text_basic != normalized:
            variants.append(text_basic)
        
        # With aggressive abbreviation expansion (expand even partial matches)
        text_expanded = self._expand_abbreviations(normalized)
        if text_expanded != normalized:
            variants.append(text_expanded)
        
        return list(set(variants))  # Deduplicate


# Convenience function
def normalize_query(query: str) -> str:
    """
    Quick normalization function
    
    Args:
        query: Raw user query
        
    Returns:
        Normalized query
    """
    normalizer = QueryNormalizer()
    return normalizer.normalize_query(query)


# Example usage and tests
if __name__ == "__main__":
    normalizer = QueryNormalizer()
    
    # Test cases
    test_queries = [
        "What is GO 42?",
        "Explain   RTE  Section 12(1)(c)",
        "FLN implementation in govt schools",
        "SHOW ME GO.Ms.No.54 details!!!",
        "Teacher transfer rules 2023",
        "What are CWSN provisions?",
    ]
    
    print("Query Normalizer Tests:")
    print("=" * 60)
    
    for query in test_queries:
        normalized = normalizer.normalize_query(query)
        print(f"Original:   {query}")
        print(f"Normalized: {normalized}")
        print("-" * 60)
    
    # Test variants
    print("\nVariant Generation Test:")
    print("=" * 60)
    query = "FLN in GO 42"
    variants = normalizer.get_normalized_variants(query)
    for i, variant in enumerate(variants, 1):
        print(f"{i}. {variant}")










