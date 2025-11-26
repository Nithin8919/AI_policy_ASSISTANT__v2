"""
Legal Structure Parser
Extracts Legal Document structure: Sections, Subsections, Clauses
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LegalSection:
    """Represents a legal section"""
    section_type: str  # section, chapter, part
    section_number: str
    title: Optional[str]
    content: str
    start_pos: int
    end_pos: int


class LegalStructureParser:
    """
    Parse Legal Document structure
    
    Legal Structure:
    1. Preamble/Introduction
    2. Chapters/Parts (optional)
    3. Sections (mandatory)
    4. Subsections
    5. Clauses/Subclauses
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for legal structure"""
        
        # Section patterns
        self.section_pattern = re.compile(
            r'^(?:Section|Sec\.?)\s+(\d+(?:\([a-zA-Z0-9]+\))?)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Chapter pattern
        self.chapter_pattern = re.compile(
            r'^CHAPTER\s+([IVXLCDM]+|\d+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Part pattern
        self.part_pattern = re.compile(
            r'^PART\s+([IVXLCDM]+|\d+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Clause pattern
        self.clause_pattern = re.compile(
            r'^\(([a-z]|[ivx]+)\)\s+',
            re.IGNORECASE | re.MULTILINE
        )
    
    def parse(self, text: str) -> Dict:
        """
        Parse legal document structure
        
        Args:
            text: Full legal document text
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "has_structure": False,
                "sections": [],
                "chapters": [],
                "act_name": None
            }
        
        # Extract act name
        act_name = self._extract_act_name(text)
        
        # Find chapters
        chapters = self._find_chapters(text)
        
        # Find sections
        sections = self._find_sections(text)
        
        return {
            "has_structure": len(sections) > 0 or len(chapters) > 0,
            "sections": sections,
            "chapters": chapters,
            "act_name": act_name,
            "section_count": len(sections),
            "chapter_count": len(chapters)
        }
    
    def _extract_act_name(self, text: str) -> Optional[str]:
        """Extract act name from document"""
        # Act name usually in first 500 chars
        first_500 = text[:500]
        
        # Pattern: "The ... Act, YYYY"
        act_pattern = re.compile(
            r'(?:The\s+)?([A-Z][A-Za-z\s,\(\)]+?)\s+Act(?:,?\s+(\d{4}))?',
            re.IGNORECASE
        )
        
        match = act_pattern.search(first_500)
        if match:
            act_name = match.group(1).strip()
            year = match.group(2)
            if year:
                return f"{act_name} Act, {year}"
            return f"{act_name} Act"
        
        return None
    
    def _find_chapters(self, text: str) -> List[LegalSection]:
        """Find all chapters in the document"""
        chapters = []
        
        for match in self.chapter_pattern.finditer(text):
            chapter_num = match.group(1)
            chapter_title = match.group(2) if match.group(2) else None
            
            chapters.append(LegalSection(
                section_type="chapter",
                section_number=chapter_num,
                title=chapter_title.strip() if chapter_title else None,
                content="",  # Will be filled with sections
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        return chapters
    
    def _find_sections(self, text: str) -> List[LegalSection]:
        """Find all sections in the document"""
        sections = []
        
        for match in self.section_pattern.finditer(text):
            section_num = match.group(1)
            section_title = match.group(2) if match.group(2) else None
            
            # Find section content (until next section or end)
            start_pos = match.end()
            
            # Find next section
            next_match = None
            remaining_text = text[start_pos:]
            next_match = self.section_pattern.search(remaining_text)
            
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                end_pos = len(text)
            
            section_content = text[start_pos:end_pos].strip()
            
            sections.append(LegalSection(
                section_type="section",
                section_number=section_num,
                title=section_title.strip() if section_title else None,
                content=section_content,
                start_pos=match.start(),
                end_pos=end_pos
            ))
        
        return sections
    
    def get_section_text(self, text: str, section_number: str) -> Optional[str]:
        """Get text of a specific section"""
        sections = self._find_sections(text)
        
        for section in sections:
            if section.section_number == section_number:
                return section.content
        
        return None