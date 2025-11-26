"""
GO Structure Parser
Extracts Government Order structure: Preamble, Orders, Annexures
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class GOSection:
    """Represents a GO section"""
    section_type: str  # preamble, order, annexure
    content: str
    start_pos: int
    end_pos: int


class GOStructureParser:
    """
    Parse Government Order structure
    
    GO Structure:
    1. Header (Department, Abstract, Subject)
    2. Preamble (Background, References)
    3. Orders (Numbered orders/instructions)
    4. Annexures (Attachments, if any)
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for GO structure"""
        
        # Subject line patterns
        self.subject_patterns = [
            re.compile(r'^Sub[ject]*\s*:(.+)$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^Subject\s*:(.+)$', re.IGNORECASE | re.MULTILINE)
        ]
        
        # Reference patterns - Fixed for the document format
        self.reference_patterns = [
            re.compile(r'^Ref\s*:\s*(.+?)(?=^\s*&{3}|^\s*[A-Z][a-z]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL),
            re.compile(r'^Read\s*:\s*(.+?)(?=^\s*&{3}|^\s*[A-Z][a-z]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL)
        ]
        
        # Order section markers
        self.order_markers = [
            re.compile(r'^ORDER[S]?\s*:?\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^ORDERS?\s*:?\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'Government\s+Order', re.IGNORECASE)
        ]
        
        # Numbered orders patterns
        self.numbered_order_pattern = re.compile(r'^\s*(\d+)\.\s+(.+?)(?=\n\s*\d+\.|\n\s*$|$)', re.MULTILINE | re.DOTALL)
        
        # Table detection patterns - Enhanced for GO documents
        self.table_patterns = [
            re.compile(r'\|[^\n]*\|[^\n]*\|'),  # Pipe-separated tables
            re.compile(r'(?:\s{4,}\S+){3,}'),  # Whitespace-separated columns
            re.compile(r'^\s*[-=]{10,}\s*$', re.MULTILINE),  # Table borders
            re.compile(r'^\s*S\.?\s*No\.?', re.IGNORECASE | re.MULTILINE),  # S.No tables
            re.compile(r'^\s*Day\s+.*Menu', re.IGNORECASE | re.MULTILINE),  # Menu tables
            re.compile(r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday.*Rice|Dal', re.IGNORECASE | re.DOTALL)  # Weekly menu
        ]
        
        # Signature patterns - Enhanced for GO documents
        self.signature_patterns = [
            re.compile(r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$', re.MULTILINE),  # Name on separate line
            re.compile(r'^\s*(DIRECTOR|COMMISSIONER|SECRETARY)\s*$', re.IGNORECASE | re.MULTILINE),  # Title on separate line
            re.compile(r'(Director|Commissioner|Secretary|Minister|Principal Secretary)\s+of\s+([A-Z][A-Za-z\s&]+)', re.IGNORECASE),
            re.compile(r'(Additional|Joint|Deputy)\s+(Secretary|Commissioner|Director)', re.IGNORECASE),
            re.compile(r'Government\s+of\s+Andhra\s+Pradesh', re.IGNORECASE),
            re.compile(r'^\s*To\s*$', re.IGNORECASE | re.MULTILINE)  # "To" section indicates end of signature
        ]
        
        # Preamble end markers
        self.preamble_end_markers = [
            r'NOW,?\s+THEREFORE',
            r'WHEREAS',
            r'In exercise of',
            r'The Government.*?(?:orders|directs)'
        ]
        
        # Annexure markers
        self.annexure_markers = [
            re.compile(r'^ANNEXURE[S]?\s*[:-]?', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^ANNEX[:\s]', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^APPENDIX', re.IGNORECASE | re.MULTILINE)
        ]
        
        # GO number pattern
        self.go_number_pattern = re.compile(r'G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*(\d+)', re.IGNORECASE)
        
        # Proceedings pattern
        self.proceedings_pattern = re.compile(r'Procs?\.?\s*Rc?\.?\s*No\.?\s*([\d\w/.-]+)', re.IGNORECASE)
    
    def parse(self, text: str) -> Dict:
        """
        Parse GO structure
        
        Args:
            text: Full GO text
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "has_structure": False,
                "sections": [],
                "go_number": None
            }
        
        # Extract GO number
        go_number = self._extract_go_number(text)
        
        # Find sections
        sections = self._identify_sections(text)
        
        # Enhanced structure detection
        has_structure = len(sections) > 1 or any(s.section_type != 'content' for s in sections)
        
        # Extract additional metadata
        dept = self.extract_department(text)
        proc_num = self.extract_proceedings_number(text)
        numbered_orders = self.extract_numbered_orders(text)
        
        return {
            "has_structure": has_structure,
            "sections": sections,
            "go_number": go_number,
            "proceedings_number": proc_num,
            "department": dept,
            "numbered_orders": numbered_orders,
            "section_types": [s.section_type for s in sections],
            "section_count": len(sections)
        }
    
    def _extract_go_number(self, text: str) -> Optional[str]:
        """Extract GO number from text"""
        match = self.go_number_pattern.search(text)
        if match:
            return match.group(1)
        return None
    
    def _identify_sections(self, text: str) -> List[GOSection]:
        """Identify GO sections with enhanced detection"""
        sections = []
        text_lines = text.split('\n')
        
        # Detect key positions
        subject_pos = self._find_subject_position(text)
        references_pos = self._find_references_position(text)
        order_pos = self._find_order_position(text)
        table_positions = self._find_table_positions(text)
        signature_pos = self._find_signature_position(text)
        annexure_pos = self._find_annexure_position(text)
        
        # Build section boundaries
        boundaries = []
        if subject_pos is not None:
            boundaries.append((subject_pos, 'subject'))
        if references_pos is not None:
            boundaries.append((references_pos, 'references'))
        if order_pos is not None:
            boundaries.append((order_pos, 'orders'))
        for table_pos in table_positions:
            boundaries.append((table_pos, 'table'))
        if signature_pos is not None:
            boundaries.append((signature_pos, 'signature'))
        if annexure_pos is not None:
            boundaries.append((annexure_pos, 'annexure'))
        
        # Sort boundaries by position
        boundaries.sort(key=lambda x: x[0])
        
        # Create sections
        if not boundaries:
            # Fallback: single content section
            sections.append(GOSection(
                section_type="content",
                content=text,
                start_pos=0,
                end_pos=len(text)
            ))
            return sections
        
        # Add preamble if first boundary isn't at start
        if boundaries[0][0] > 200:  # Allow more header content for GO documents
            sections.append(GOSection(
                section_type="preamble",
                content=text[:boundaries[0][0]].strip(),
                start_pos=0,
                end_pos=boundaries[0][0]
            ))
        
        # Process each boundary
        for i, (pos, section_type) in enumerate(boundaries):
            # Determine end position
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][0]
            else:
                end_pos = len(text)
            
            content = text[pos:end_pos].strip()
            if content:
                sections.append(GOSection(
                    section_type=section_type,
                    content=content,
                    start_pos=pos,
                    end_pos=end_pos
                ))
        
        return sections
    
    def _find_subject_position(self, text: str) -> Optional[int]:
        """Find subject line position"""
        for pattern in self.subject_patterns:
            match = pattern.search(text)
            if match:
                return match.start()
        return None
    
    def _find_references_position(self, text: str) -> Optional[int]:
        """Find references section position"""
        for pattern in self.reference_patterns:
            match = pattern.search(text)
            if match:
                return match.start()
        return None
    
    def _find_order_position(self, text: str) -> Optional[int]:
        """Find orders section position"""
        # Check for numbered orders first
        numbered_match = self.numbered_order_pattern.search(text)
        if numbered_match:
            return numbered_match.start()
        
        # Check for ORDER markers
        for pattern in self.order_markers:
            match = pattern.search(text)
            if match:
                return match.start()
        return None
    
    def _find_table_positions(self, text: str) -> List[int]:
        """Find table positions"""
        positions = []
        for pattern in self.table_patterns:
            for match in pattern.finditer(text):
                positions.append(match.start())
        return positions
    
    def _find_signature_position(self, text: str) -> Optional[int]:
        """Find signature section position"""
        # Look in the last 30% of the document for signature
        search_start = int(len(text) * 0.7)
        search_text = text[search_start:]
        
        # Look for patterns that indicate signature section
        signature_indicators = [
            re.compile(r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*^\s*(DIRECTOR|COMMISSIONER)', re.IGNORECASE | re.MULTILINE | re.DOTALL),
            re.compile(r'^\s*(DIRECTOR|COMMISSIONER|SECRETARY)\s*^\s*(MID DAY MEAL|SCHOOL EDUCATION)', re.IGNORECASE | re.MULTILINE | re.DOTALL),
            re.compile(r'The receipt of this order will be acknowledged', re.IGNORECASE)
        ]
        
        earliest_pos = None
        for pattern in signature_indicators:
            match = pattern.search(search_text)
            if match:
                pos = search_start + match.start()
                if earliest_pos is None or pos < earliest_pos:
                    earliest_pos = pos
        
        return earliest_pos
    
    def _find_annexure_position(self, text: str) -> Optional[int]:
        """Find annexure section position"""
        for pattern in self.annexure_markers:
            match = pattern.search(text)
            if match:
                return match.start()
        return None
    
    def extract_department(self, text: str) -> Optional[str]:
        """Extract department name from GO header"""
        # Department usually appears at the top
        first_500 = text[:500]
        
        # Pattern: "Department of X" or "X Department"
        dept_patterns = [
            re.compile(r'(?:Department|Dept\.?)\s+of\s+([A-Z][A-Za-z\s&]+?)(?:,|\.|\n)', re.IGNORECASE),
            re.compile(r'([A-Z][A-Za-z\s&]+?)\s+Department', re.IGNORECASE)
        ]
        
        for pattern in dept_patterns:
            match = pattern.search(first_500)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_proceedings_number(self, text: str) -> Optional[str]:
        """Extract proceedings number from document"""
        match = self.proceedings_pattern.search(text[:1000])
        if match:
            return match.group(1)
        return None
    
    def extract_numbered_orders(self, text: str) -> List[str]:
        """Extract numbered orders from the document"""
        orders = []
        for match in self.numbered_order_pattern.finditer(text):
            order_num = match.group(1)
            order_content = match.group(2).strip()
            orders.append(f"{order_num}. {order_content}")
        return orders