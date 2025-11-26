"""
Judicial Structure Parser
Extracts Court Case structure: Facts, Arguments, Ratio, Judgment
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class JudicialSection:
    """Represents a judicial section"""
    section_type: str  # facts, arguments, ratio, judgment
    content: str
    start_pos: int
    end_pos: int


class JudicialStructureParser:
    """
    Parse Judicial Document structure
    
    Judicial Structure:
    1. Case Information (parties, case number, court)
    2. Facts
    3. Arguments/Submissions
    4. Ratio Decidendi/Analysis
    5. Judgment/Order
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for judicial structure"""
        
        # Section markers
        self.facts_pattern = re.compile(
            r'^(?:FACTS?|BACKGROUND|FACTUAL BACKGROUND)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.arguments_pattern = re.compile(
            r'^(?:ARGUMENTS?|SUBMISSIONS?|CONTENTIONS?)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.ratio_pattern = re.compile(
            r'^(?:RATIO|RATIO DECIDENDI|REASONING|ANALYSIS|DISCUSSION)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.judgment_pattern = re.compile(
            r'^(?:JUDGMENT|DECISION|ORDER|HELD|CONCLUSION)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Case number pattern
        self.case_number_pattern = re.compile(
            r'(?:Case|Petition|Appeal)\s+No\.?\s*(\d+(?:/\d+)?)',
            re.IGNORECASE
        )
        
        # Court pattern
        self.court_pattern = re.compile(
            r'(?:Supreme Court|High Court|District Court)',
            re.IGNORECASE
        )
    
    def parse(self, text: str) -> Dict:
        """
        Parse judicial document structure
        
        Args:
            text: Full judgment text
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "has_structure": False,
                "sections": [],
                "case_number": None,
                "court": None
            }
        
        # Extract case metadata
        case_number = self._extract_case_number(text)
        court = self._extract_court(text)
        
        # Find sections
        sections = self._identify_sections(text)
        
        return {
            "has_structure": len(sections) > 1,
            "sections": sections,
            "case_number": case_number,
            "court": court,
            "section_types": [s.section_type for s in sections]
        }
    
    def _extract_case_number(self, text: str) -> Optional[str]:
        """Extract case number"""
        # Check first 1000 chars
        header = text[:1000]
        
        match = self.case_number_pattern.search(header)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_court(self, text: str) -> Optional[str]:
        """Extract court name"""
        # Check first 1000 chars
        header = text[:1000]
        
        match = self.court_pattern.search(header)
        if match:
            return match.group(0)
        
        return None
    
    def _identify_sections(self, text: str) -> List[JudicialSection]:
        """Identify judicial sections"""
        sections = []
        
        # Find all section markers
        markers = []
        
        for pattern, section_type in [
            (self.facts_pattern, "facts"),
            (self.arguments_pattern, "arguments"),
            (self.ratio_pattern, "ratio"),
            (self.judgment_pattern, "judgment")
        ]:
            match = pattern.search(text)
            if match:
                markers.append((match.start(), section_type))
        
        # Sort by position
        markers.sort(key=lambda x: x[0])
        
        if not markers:
            # No clear structure
            return [JudicialSection(
                section_type="content",
                content=text,
                start_pos=0,
                end_pos=len(text)
            )]
        
        # Extract sections
        for i, (start, section_type) in enumerate(markers):
            # Find end position
            if i + 1 < len(markers):
                end = markers[i + 1][0]
            else:
                end = len(text)
            
            section_content = text[start:end].strip()
            
            if section_content:
                sections.append(JudicialSection(
                    section_type=section_type,
                    content=section_content,
                    start_pos=start,
                    end_pos=end
                ))
        
        # Add preamble if exists (before first marker)
        if markers[0][0] > 0:
            preamble = text[:markers[0][0]].strip()
            if preamble:
                sections.insert(0, JudicialSection(
                    section_type="preamble",
                    content=preamble,
                    start_pos=0,
                    end_pos=markers[0][0]
                ))
        
        return sections