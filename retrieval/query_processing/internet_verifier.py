"""
Internet Verification Layer
===========================
Verifies numerical answers and recent claims using web search.

CRITICAL NEW FEATURE: Fact-checks answers before sending to user.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Verification:
    """Verification result for a claim"""
    claim: str
    verified: bool
    confidence: float  # 0.0 to 1.0
    web_result: Optional[str] = None
    source_url: Optional[str] = None
    discrepancy: Optional[str] = None


@dataclass
class VerificationResult:
    """Complete verification result"""
    should_verify: bool
    verifications: List[Verification]
    overall_confidence: float
    verification_note: str


class InternetVerifier:
    """
    Verifies answers using web search.
    Focuses on numerical claims and recent events.
    """
    
    # Keywords that trigger verification
    VERIFICATION_TRIGGERS = {
        "numbers": [
            r'\d+(?:,\d{3})*(?:\.\d+)?',  # Numbers with optional commas/decimals
            r'\d+\s*(?:schools?|students?|teachers?|percent|%|crore|lakh|thousand)',
        ],
        "recent": [
            "latest", "current", "recent", "now", "today", "2024", "2025",
            "as of", "up to date", "newest"
        ],
        "statistics": [
            "enrollment", "dropout", "attendance", "achievement", "performance",
            "ratio", "rate", "percentage", "count", "total", "number of"
        ]
    }
    
    def __init__(self, web_search_func=None):
        """
        Initialize verifier.
        
        Args:
            web_search_func: Function to call for web search
                            Signature: func(query: str) -> List[Dict]
        """
        self.web_search = web_search_func
    
    def should_verify(
        self,
        answer: str,
        query: str,
        confidence: float = 1.0
    ) -> bool:
        """
        Decide if answer needs verification.
        
        Args:
            answer: Generated answer
            query: Original query
            confidence: Answer confidence score
            
        Returns:
            True if verification needed
        """
        answer_lower = answer.lower()
        query_lower = query.lower()
        
        # Check for numerical claims
        has_numbers = bool(re.search(self.VERIFICATION_TRIGGERS["numbers"][0], answer))
        
        # Check for statistics keywords
        has_statistics = any(kw in answer_lower for kw in self.VERIFICATION_TRIGGERS["statistics"])
        
        # Check for recent keywords
        has_recent = any(kw in query_lower for kw in self.VERIFICATION_TRIGGERS["recent"])
        
        # Check low confidence
        low_confidence = confidence < 0.7
        
        # Verify if any condition is met
        should_verify = has_numbers or (has_statistics and has_recent) or low_confidence
        
        if should_verify:
            logger.info(f"🔍 Verification triggered - Numbers: {has_numbers}, "
                       f"Stats: {has_statistics}, Recent: {has_recent}, "
                       f"Low confidence: {low_confidence}")
        
        return should_verify
    
    def verify(
        self,
        answer: str,
        query: str,
        confidence: float = 1.0
    ) -> VerificationResult:
        """
        Verify answer using web search.
        
        Args:
            answer: Generated answer
            query: Original query
            confidence: Answer confidence
            
        Returns:
            VerificationResult with findings
        """
        # Check if verification needed
        if not self.should_verify(answer, query, confidence):
            return VerificationResult(
                should_verify=False,
                verifications=[],
                overall_confidence=confidence,
                verification_note=""
            )
        
        # Check if web search is available
        if self.web_search is None:
            logger.warning("⚠️ Web search not available, skipping verification")
            return VerificationResult(
                should_verify=True,
                verifications=[],
                overall_confidence=confidence,
                verification_note="⚠️ Verification unavailable (web search disabled)"
            )
        
        # Extract claims to verify
        claims = self._extract_claims(answer, query)
        
        if not claims:
            return VerificationResult(
                should_verify=True,
                verifications=[],
                overall_confidence=confidence,
                verification_note=""
            )
        
        # Verify each claim
        verifications = []
        for claim in claims[:3]:  # Limit to top 3 claims to avoid latency
            verification = self._verify_claim(claim, query)
            verifications.append(verification)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(verifications, confidence)
        
        # Generate verification note
        verification_note = self._generate_note(verifications)
        
        return VerificationResult(
            should_verify=True,
            verifications=verifications,
            overall_confidence=overall_confidence,
            verification_note=verification_note
        )
    
    def _extract_claims(self, answer: str, query: str) -> List[str]:
        """Extract numerical/statistical claims from answer"""
        claims = []
        
        # Extract sentences with numbers
        sentences = re.split(r'[.!?]+', answer)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence has numbers
            if re.search(self.VERIFICATION_TRIGGERS["numbers"][0], sentence):
                claims.append(sentence)
        
        return claims
    
    def _verify_claim(self, claim: str, query: str) -> Verification:
        """Verify a single claim using web search"""
        
        try:
            # Build search query
            search_query = self._build_search_query(claim, query)
            
            logger.info(f"🌐 Searching web: '{search_query}'")
            
            # Search web
            search_results = self.web_search(search_query)
            
            if not search_results:
                return Verification(
                    claim=claim,
                    verified=False,
                    confidence=0.5,
                    discrepancy="No web results found"
                )
            
            # Check consistency
            verified, confidence, web_result, discrepancy = self._check_consistency(
                claim, search_results
            )
            
            return Verification(
                claim=claim,
                verified=verified,
                confidence=confidence,
                web_result=web_result,
                source_url=search_results[0].get("url") if search_results else None,
                discrepancy=discrepancy
            )
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return Verification(
                claim=claim,
                verified=False,
                confidence=0.5,
                discrepancy=f"Verification error: {str(e)}"
            )
    
    def _build_search_query(self, claim: str, original_query: str) -> str:
        """Build optimized search query"""
        
        # Extract key terms from claim
        # Remove common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
        
        words = claim.lower().split()
        key_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Add location context (Andhra Pradesh)
        search_query = ' '.join(key_words[:10]) + ' Andhra Pradesh'
        
        # Add year if mentioned
        year_match = re.search(r'20\d{2}', claim)
        if year_match:
            search_query += f' {year_match.group()}'
        
        return search_query
    
    def _check_consistency(
        self,
        claim: str,
        search_results: List[Dict]
    ) -> Tuple[bool, float, str, Optional[str]]:
        """
        Check if claim is consistent with web results.
        
        Returns:
            (verified, confidence, web_result, discrepancy)
        """
        # Extract numbers from claim
        claim_numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', claim)
        
        if not claim_numbers:
            return False, 0.5, "", "No numbers to verify"
        
        # Check top 3 search results
        for result in search_results[:3]:
            snippet = result.get("snippet", "") or result.get("description", "")
            
            # Extract numbers from snippet
            snippet_numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', snippet)
            
            # Check for overlap
            for claim_num in claim_numbers:
                claim_val = float(claim_num.replace(',', ''))
                
                for snippet_num in snippet_numbers:
                    snippet_val = float(snippet_num.replace(',', ''))
                    
                    # Check if numbers are close (within 10%)
                    ratio = abs(claim_val - snippet_val) / max(claim_val, snippet_val)
                    
                    if ratio < 0.1:  # Within 10%
                        return True, 0.9, snippet, None
                    elif ratio < 0.3:  # Within 30%
                        discrepancy = f"Our data: {claim_num}, Web: {snippet_num} (slight difference)"
                        return True, 0.7, snippet, discrepancy
        
        # No match found
        return False, 0.4, search_results[0].get("snippet", ""), "Numbers don't match web results"
    
    def _calculate_overall_confidence(
        self,
        verifications: List[Verification],
        initial_confidence: float
    ) -> float:
        """Calculate overall confidence after verification"""
        
        if not verifications:
            return initial_confidence
        
        # Average verification confidence
        avg_verification_confidence = sum(v.confidence for v in verifications) / len(verifications)
        
        # Combine with initial confidence (weighted average)
        overall = 0.6 * initial_confidence + 0.4 * avg_verification_confidence
        
        return overall
    
    def _generate_note(self, verifications: List[Verification]) -> str:
        """Generate human-readable verification note"""
        
        if not verifications:
            return ""
        
        verified_count = sum(1 for v in verifications if v.verified)
        total = len(verifications)
        
        if verified_count == total:
            return "✓ All claims verified via web search"
        elif verified_count > 0:
            notes = []
            for v in verifications:
                if v.verified:
                    if v.discrepancy:
                        notes.append(f"✓ {v.discrepancy}")
                    else:
                        notes.append(f"✓ Verified: {v.claim[:60]}...")
                else:
                    notes.append(f"⚠ Could not verify: {v.claim[:60]}...")
            
            return "\n".join(notes)
        else:
            return "⚠ Could not verify claims via web search"


# Factory function
def create_internet_verifier(web_search_func=None) -> InternetVerifier:
    """Create internet verifier with web search function"""
    return InternetVerifier(web_search_func)


# Export
__all__ = ["InternetVerifier", "Verification", "VerificationResult", "create_internet_verifier"]