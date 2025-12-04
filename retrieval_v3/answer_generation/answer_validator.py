# Answer Validator - gov-first citations + hallucination check

"""
Answer Validator - Validate answer quality and correctness
Checks: hallucinations, citations, coverage, government-first citations
"""

from typing import List, Dict, Tuple
import re


class AnswerValidator:
    """Validate generated answers"""
    
    def __init__(self):
        """Initialize validator"""
        pass
    
    def validate_answer(
        self,
        answer: Dict,
        results: List[Dict],
        query: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate answer quality
        
        Args:
            answer: Generated answer
            results: Source results used
            query: Original query
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check 1: Has content
        if not answer.get('summary'):
            issues.append("Missing summary")
        
        # Check 2: Has citations
        if not answer.get('citations'):
            issues.append("No citations provided")
        
        # Check 3: Citations match sources
        citation_issues = self._check_citations(answer, results)
        issues.extend(citation_issues)
        
        # Check 4: Government sources prioritized
        if not self._check_gov_first(answer):
            issues.append("Government sources not prioritized in citations")
        
        # Check 5: Coverage (query terms present)
        if not self._check_coverage(answer, query):
            issues.append("Answer doesn't address key query terms")
        
        # Check 6: Hallucination check (basic)
        if self._check_hallucination(answer, results):
            issues.append("Possible hallucination detected")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _check_citations(
        self,
        answer: Dict,
        results: List[Dict]
    ) -> List[str]:
        """Check if citations are valid"""
        issues = []
        
        citations = answer.get('citations', [])
        
        if not citations:
            return ["No citations"]
        
        # Check if citation IDs are valid
        result_ids = set(r.get('chunk_id') or r.get('doc_id') for r in results)
        
        for citation in citations:
            cited_id = citation.get('doc_id')
            if cited_id and cited_id not in result_ids:
                issues.append(f"Citation {cited_id} not in source results")
        
        return issues
    
    def _check_gov_first(self, answer: Dict) -> bool:
        """Check if government sources are cited first"""
        citations = answer.get('citations', [])
        
        if not citations:
            return False
        
        # Check first citation
        first_citation = citations[0]
        source = first_citation.get('source', '').lower()
        vertical = first_citation.get('vertical', '').lower()
        
        # Government indicators
        gov_indicators = ['act', 'rule', 'go', 'government', 'legal', 'official']
        
        return any(indicator in source or indicator in vertical for indicator in gov_indicators)
    
    def _check_coverage(self, answer: Dict, query: str) -> bool:
        """Check if answer covers query terms"""
        summary = answer.get('summary', '').lower()
        
        # Extract key terms from query (simple)
        query_terms = query.lower().split()
        
        # Filter stopwords
        stopwords = {'what', 'is', 'are', 'the', 'a', 'an', 'how', 'why', 'when', 'where'}
        key_terms = [t for t in query_terms if t not in stopwords and len(t) > 2]
        
        # Check if at least 50% of key terms are in summary
        if not key_terms:
            return True
        
        covered = sum(1 for term in key_terms if term in summary)
        coverage = covered / len(key_terms)
        
        return coverage >= 0.5
    
    def _check_hallucination(
        self,
        answer: Dict,
        results: List[Dict]
    ) -> bool:
        """Basic hallucination check"""
        summary = answer.get('summary', '')
        
        # Collect all source content
        source_content = ' '.join([
            r.get('content', '') for r in results[:10]
        ]).lower()
        
        # Extract specific claims (numbers, names, etc.)
        claims = self._extract_claims(summary)
        
        # Check if claims appear in sources
        hallucinations = []
        for claim in claims:
            if claim.lower() not in source_content:
                hallucinations.append(claim)
        
        # If >30% of claims not found, possible hallucination
        if claims and len(hallucinations) / len(claims) > 0.3:
            return True
        
        return False
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract specific factual claims"""
        claims = []
        
        # Extract numbers with context
        number_patterns = [
            r'\d+%',  # Percentages
            r'\d{4}',  # Years
            r'Section\s+\d+',  # Section numbers
            r'GO\.?\s*\w*\.?\s*No\.?\s*\d+',  # GO numbers
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend(matches)
        
        return claims
    
    def get_quality_score(
        self,
        answer: Dict,
        results: List[Dict],
        query: str
    ) -> float:
        """
        Calculate answer quality score (0-1)
        
        Returns:
            Quality score between 0 and 1
        """
        score = 1.0
        
        # Validate
        is_valid, issues = self.validate_answer(answer, results, query)
        
        # Deduct points for each issue
        score -= len(issues) * 0.15
        
        # Bonus for government citations first
        if self._check_gov_first(answer):
            score += 0.1
        
        # Bonus for good coverage
        if self._check_coverage(answer, query):
            score += 0.1
        
        # Ensure 0-1 range
        return max(0.0, min(1.0, score))
    
    def suggest_improvements(
        self,
        answer: Dict,
        results: List[Dict],
        query: str
    ) -> List[str]:
        """Suggest improvements for answer"""
        suggestions = []
        
        is_valid, issues = self.validate_answer(answer, results, query)
        
        if not is_valid:
            for issue in issues:
                if "citation" in issue.lower():
                    suggestions.append("Add proper citations to sources")
                elif "government" in issue.lower():
                    suggestions.append("Prioritize government/legal sources")
                elif "coverage" in issue.lower():
                    suggestions.append("Ensure answer addresses all query terms")
                elif "hallucination" in issue.lower():
                    suggestions.append("Verify all factual claims against sources")
        
        return suggestions


# Convenience function
def validate_answer(
    answer: Dict,
    results: List[Dict],
    query: str
) -> Tuple[bool, List[str]]:
    """Quick validation"""
    validator = AnswerValidator()
    return validator.validate_answer(answer, results, query)


if __name__ == "__main__":
    print("Answer Validator")
    print("=" * 60)
    print("\nExample usage:")
    print("""
from retrieval_v3.answer_generation import AnswerValidator

validator = AnswerValidator()

# Validate answer
is_valid, issues = validator.validate_answer(
    answer=generated_answer,
    results=source_results,
    query=original_query
)

if not is_valid:
    print("Issues found:")
    for issue in issues:
        print(f"  - {issue}")

# Get quality score
score = validator.get_quality_score(answer, results, query)
print(f"Quality score: {score:.2f}")

# Get suggestions
suggestions = validator.suggest_improvements(answer, results, query)
for suggestion in suggestions:
    print(f"  → {suggestion}")
""")







