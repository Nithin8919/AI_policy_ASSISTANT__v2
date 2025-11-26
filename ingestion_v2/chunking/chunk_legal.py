"""
Legal Chunker - Legal Document Specific Chunking
Understands legal structure: Sections, Subsections, Clauses
"""
import re
from typing import List, Dict, Tuple
from .base_chunker import BaseChunker, Chunk


class LegalChunker(BaseChunker):
    """
    Legal document specific chunker
    Preserves legal section boundaries and hierarchies
    """
    
    def __init__(self):
        # Legal-specific sizes
        super().__init__(min_size=800, max_size=1500, overlap=150)
        
        # Legal structure patterns
        self.section_pattern = re.compile(
            r'^(?:SECTION|Section|Sec\.?)\s+(\d+[A-Z]?)\s*[.:-]?\s*(.*?)$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.subsection_pattern = re.compile(
            r'^\s*\((\d+|[a-z]|[ivx]+)\)\s+',
            re.MULTILINE
        )
        
        self.chapter_pattern = re.compile(
            r'^(?:CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\s*[.:-]?\s*(.*?)$',
            re.MULTILINE | re.IGNORECASE
        )
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk legal document with section awareness
        
        Strategy:
        1. Identify sections
        2. Keep complete sections together when possible
        3. Split large sections at subsection boundaries
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Try to identify sections
        sections = self._identify_sections(text)
        
        if not sections:
            # No clear sections, fall back to paragraph-based chunking
            paragraphs = self._split_paragraphs(text)
            return self._group_paragraphs(paragraphs, doc_id, metadata)
        
        # Chunk each section
        chunks = []
        chunk_index = 0
        
        for section_num, section_title, section_text in sections:
            section_meta = {
                **metadata,
                "section_number": section_num,
                "section_title": section_title
            }
            
            section_chunks = self._chunk_section(
                section_text, section_num, doc_id, chunk_index, section_meta
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _identify_sections(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Identify legal sections
        Returns list of (section_num, title, text) tuples
        """
        sections = []
        section_matches = list(self.section_pattern.finditer(text))
        
        if not section_matches:
            return []
        
        for i, match in enumerate(section_matches):
            section_num = match.group(1)
            section_title = match.group(2).strip() if match.group(2) else ""
            
            # Get section text
            start = match.start()
            end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
            section_text = text[start:end].strip()
            
            sections.append((section_num, section_title, section_text))
        
        return sections
    
    def _chunk_section(
        self,
        text: str,
        section_num: str,
        doc_id: str,
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Chunk a legal section appropriately"""
        
        # If section fits in one chunk, keep it together
        if len(text) <= self.max_size:
            return [self._create_chunk(text, doc_id, start_index, metadata)]
        
        # Try to split at subsection boundaries
        subsections = self._identify_subsections(text)
        
        if subsections:
            return self._chunk_subsections(subsections, doc_id, start_index, metadata)
        
        # Otherwise use paragraph-based chunking
        paragraphs = self._split_paragraphs(text)
        return self._group_paragraphs(paragraphs, doc_id, metadata)
    
    def _identify_subsections(self, text: str) -> List[Tuple[str, str]]:
        """
        Identify subsections within a section
        Returns list of (subsection_num, text) tuples
        """
        subsections = []
        subsection_matches = list(self.subsection_pattern.finditer(text))
        
        if not subsection_matches:
            return []
        
        for i, match in enumerate(subsection_matches):
            subsection_num = match.group(1)
            start = match.start()
            end = subsection_matches[i + 1].start() if i + 1 < len(subsection_matches) else len(text)
            subsection_text = text[start:end].strip()
            
            subsections.append((subsection_num, subsection_text))
        
        return subsections
    
    def _chunk_subsections(
        self,
        subsections: List[Tuple[str, str]],
        doc_id: str,
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Group subsections into optimal chunks"""
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = start_index
        
        for subsection_num, subsection_text in subsections:
            subsection_size = len(subsection_text)
            
            if current_size + subsection_size > self.max_size and current_group:
                # Finalize current chunk
                chunk_text = "\n\n".join([text for _, text in current_group])
                chunk_metadata = {
                    **metadata,
                    "subsections": [num for num, _ in current_group]
                }
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                if self.overlap > 0 and current_group:
                    current_group = [current_group[-1], (subsection_num, subsection_text)]
                    current_size = len(current_group[-1][1]) + subsection_size
                else:
                    current_group = [(subsection_num, subsection_text)]
                    current_size = subsection_size
                
                chunk_index += 1
            else:
                current_group.append((subsection_num, subsection_text))
                current_size += subsection_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join([text for _, text in current_group])
            chunk_metadata = {
                **metadata,
                "subsections": [num for num, _ in current_group]
            }
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks