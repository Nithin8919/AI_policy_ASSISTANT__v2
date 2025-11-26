"""
Judicial Chunker - Court Cases and Judgments
Understands judicial structure: Facts, Arguments, Ratio, Orders
"""
import re
from typing import List, Dict
from .base_chunker import BaseChunker, Chunk


class JudicialChunker(BaseChunker):
    """
    Judicial document specific chunker
    Preserves case structure while maintaining semantic coherence
    """
    
    def __init__(self):
        # Judicial-specific sizes (slightly smaller for dense legal text)
        super().__init__(min_size=700, max_size=1300, overlap=120)
        
        # Judicial structure patterns
        self.facts_pattern = re.compile(r'^(?:FACTS?|BACKGROUND)[:\s]', re.IGNORECASE | re.MULTILINE)
        self.arguments_pattern = re.compile(r'^(?:ARGUMENTS?|SUBMISSIONS?)[:\s]', re.IGNORECASE | re.MULTILINE)
        self.ratio_pattern = re.compile(r'^(?:RATIO|REASONING|ANALYSIS)[:\s]', re.IGNORECASE | re.MULTILINE)
        self.judgment_pattern = re.compile(r'^(?:JUDGMENT|DECISION|ORDER)[:\s]', re.IGNORECASE | re.MULTILINE)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk judicial document with structure awareness
        
        Strategy:
        1. Identify case structure (facts, arguments, ratio, judgment)
        2. Keep sections coherent
        3. Split only if section is too large
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Detect judicial structure
        sections = self._detect_judicial_structure(text)
        
        # Chunk each section appropriately
        chunks = []
        chunk_index = 0
        
        for section_type, section_text in sections:
            section_chunks = self._chunk_section(
                section_text, section_type, doc_id, chunk_index, metadata
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _detect_judicial_structure(self, text: str) -> List[tuple]:
        """
        Detect judicial document structure
        Returns list of (section_type, text) tuples
        """
        sections = []
        
        # Find section markers
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
            # No clear structure, treat as single section
            return [("content", text)]
        
        # Extract sections
        for i, (start, section_type) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
            section_text = text[start:end].strip()
            
            if section_text:
                sections.append((section_type, section_text))
        
        # Add any text before first marker
        if markers[0][0] > 0:
            preamble = text[:markers[0][0]].strip()
            if preamble:
                sections.insert(0, ("preamble", preamble))
        
        return sections
    
    def _chunk_section(
        self, 
        text: str, 
        section_type: str, 
        doc_id: str, 
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Chunk a judicial section appropriately"""
        
        # If section is small enough, keep as single chunk
        if len(text) <= self.max_size:
            chunk_metadata = {**metadata, "section_type": section_type}
            return [self._create_chunk(text, doc_id, start_index, chunk_metadata)]
        
        # For ratio/arguments sections, try to preserve numbered points
        if section_type in ("ratio", "arguments"):
            return self._chunk_numbered_points(text, doc_id, start_index, metadata, section_type)
        
        # Otherwise use base paragraph-based chunking
        paragraphs = self._split_paragraphs(text)
        section_metadata = {**metadata, "section_type": section_type}
        return self._group_paragraphs(paragraphs, doc_id, section_metadata)
    
    def _chunk_numbered_points(
        self, 
        text: str, 
        doc_id: str, 
        start_index: int, 
        metadata: Dict,
        section_type: str
    ) -> List[Chunk]:
        """
        Chunk numbered points/arguments, trying to keep them together
        """
        # Try to identify numbered points: 1., 2., (i), (ii), etc.
        point_pattern = re.compile(r'^(?:\d+\.|\([ivxIVX]+\)|\([a-z]\))\s+', re.MULTILINE)
        
        # Find all point starts
        point_starts = [m.start() for m in point_pattern.finditer(text)]
        
        if not point_starts:
            # No clear numbering, fall back to paragraph chunking
            paragraphs = self._split_paragraphs(text)
            section_metadata = {**metadata, "section_type": section_type}
            return self._group_paragraphs(paragraphs, doc_id, section_metadata)
        
        # Split into individual points
        points = []
        for i, start in enumerate(point_starts):
            end = point_starts[i + 1] if i + 1 < len(point_starts) else len(text)
            point_text = text[start:end].strip()
            if point_text:
                points.append(point_text)
        
        # Group points into chunks
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = start_index
        
        for point in points:
            point_size = len(point)
            
            if current_size + point_size > self.max_size and current_group:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_group)
                chunk_metadata = {**metadata, "section_type": section_type}
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                
                current_group = [point]
                current_size = point_size
                chunk_index += 1
            else:
                current_group.append(point)
                current_size += point_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join(current_group)
            chunk_metadata = {**metadata, "section_type": section_type}
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks