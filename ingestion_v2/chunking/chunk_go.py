"""
GO Chunker - Government Order Specific Chunking
Understands GO structure: Preamble, Orders, Annexures
"""
import re
from typing import List, Dict, Tuple
from .base_chunker import BaseChunker, Chunk


class GOChunker(BaseChunker):
    """
    Government Order specific chunker
    Preserves GO structure while maintaining semantic coherence
    """
    
    def __init__(self):
        # GO-specific sizes (from config)
        super().__init__(min_size=600, max_size=1200, overlap=100)
        
        # GO structure patterns
        self.order_pattern = re.compile(r'^(?:ORDER[S]?|ORDERS?)\s*:?\s*$', re.IGNORECASE | re.MULTILINE)
        self.preamble_end = re.compile(r'(?:NOW,?\s+THEREFORE|WHEREAS|In exercise of)', re.IGNORECASE)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk GO document with structure awareness
        
        Strategy:
        1. Identify GO structure (preamble, orders, annexure)
        2. Keep complete orders together when possible
        3. Split only if order is too large
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Detect GO structure
        sections = self._detect_go_structure(text)
        
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
    
    def _detect_go_structure(self, text: str) -> List[Tuple[str, str]]:
        """
        Detect GO structure sections
        Returns list of (section_type, text) tuples
        """
        sections = []
        
        # Find ORDER marker
        order_match = self.order_pattern.search(text)
        
        if order_match:
            # Split into preamble and orders
            preamble = text[:order_match.start()].strip()
            orders = text[order_match.end():].strip()
            
            if preamble:
                sections.append(("preamble", preamble))
            if orders:
                sections.append(("orders", orders))
        else:
            # No clear ORDER marker, treat as single section
            sections.append(("content", text))
        
        return sections
    
    def _chunk_section(
        self, 
        text: str, 
        section_type: str, 
        doc_id: str, 
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Chunk a GO section appropriately"""
        
        # If section is small enough, keep as single chunk
        if len(text) <= self.max_size:
            chunk_metadata = {**metadata, "section_type": section_type}
            return [self._create_chunk(text, doc_id, start_index, chunk_metadata)]
        
        # For orders section, try to split by numbered orders
        if section_type == "orders":
            return self._chunk_orders(text, doc_id, start_index, metadata)
        
        # Otherwise use base paragraph-based chunking
        paragraphs = self._split_paragraphs(text)
        section_metadata = {**metadata, "section_type": section_type}
        return self._group_paragraphs(paragraphs, doc_id, section_metadata)
    
    def _chunk_orders(self, text: str, doc_id: str, start_index: int, metadata: Dict) -> List[Chunk]:
        """
        Chunk the orders section, trying to keep individual orders together
        """
        # Try to identify numbered orders: 1., 2., (i), (ii), etc.
        order_pattern = re.compile(r'^(?:\d+\.|\([ivxIVX]+\)|\([a-z]\))\s+', re.MULTILINE)
        
        # Find all order starts
        order_starts = [m.start() for m in order_pattern.finditer(text)]
        
        if not order_starts:
            # No clear numbering, fall back to paragraph chunking
            paragraphs = self._split_paragraphs(text)
            section_metadata = {**metadata, "section_type": "orders"}
            return self._group_paragraphs(paragraphs, doc_id, section_metadata)
        
        # Split into individual orders
        orders = []
        for i, start in enumerate(order_starts):
            end = order_starts[i + 1] if i + 1 < len(order_starts) else len(text)
            order_text = text[start:end].strip()
            if order_text:
                orders.append(order_text)
        
        # Group orders into chunks
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = start_index
        
        for order in orders:
            order_size = len(order)
            
            if current_size + order_size > self.max_size and current_group:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_group)
                chunk_metadata = {**metadata, "section_type": "orders"}
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                
                current_group = [order]
                current_size = order_size
                chunk_index += 1
            else:
                current_group.append(order)
                current_size += order_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join(current_group)
            chunk_metadata = {**metadata, "section_type": "orders"}
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks