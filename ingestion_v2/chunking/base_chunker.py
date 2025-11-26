"""
Base Chunker - Base class for all vertical-specific chunkers
Provides common chunking utilities and structure
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple
import re


@dataclass
class Chunk:
    """Represents a text chunk"""
    content: str
    chunk_id: str
    doc_id: str
    chunk_index: int
    word_count: int
    metadata: Dict


class BaseChunker:
    """
    Base class for all chunkers
    Provides common chunking utilities
    """
    
    def __init__(self, min_size: int = 500, max_size: int = 1000, overlap: int = 100):
        """
        Initialize base chunker
        
        Args:
            min_size: Minimum chunk size in characters
            max_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters
        """
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk text (to be implemented by subclasses)
        
        Args:
            text: Text to chunk
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of chunks
        """
        raise NotImplementedError("Subclasses must implement chunk()")
    
    def _create_chunk(
        self, 
        text: str, 
        doc_id: str, 
        chunk_index: int, 
        metadata: Dict
    ) -> Chunk:
        """
        Create a Chunk object
        
        Args:
            text: Chunk text
            doc_id: Document ID
            chunk_index: Chunk index
            metadata: Chunk metadata
            
        Returns:
            Chunk object
        """
        chunk_id = f"{doc_id}_chunk_{chunk_index}"
        word_count = len(text.split())
        
        return Chunk(
            content=text,
            chunk_id=chunk_id,
            doc_id=doc_id,
            chunk_index=chunk_index,
            word_count=word_count,
            metadata=metadata
        )
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs
        
        Args:
            text: Text to split
            
        Returns:
            List of paragraphs
        """
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _group_paragraphs(
        self, 
        paragraphs: List[str], 
        doc_id: str, 
        metadata: Dict
    ) -> List[Chunk]:
        """
        Group paragraphs into chunks
        
        Args:
            paragraphs: List of paragraphs
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of chunks
        """
        if not paragraphs:
            return []
        
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph would exceed max_size
            if current_size + para_size > self.max_size and current_group:
                # Create chunk from current group
                chunk_text = "\n\n".join(current_group)
                
                # Only create if meets minimum size
                if len(chunk_text) >= self.min_size:
                    chunk = self._create_chunk(chunk_text, doc_id, chunk_index, metadata)
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    # Start new group with overlap
                    if self.overlap > 0 and current_group:
                        # Keep last paragraph for overlap
                        overlap_text = current_group[-1]
                        if len(overlap_text) <= self.overlap:
                            current_group = [overlap_text, para]
                            current_size = len(overlap_text) + para_size
                        else:
                            # Take last N chars for overlap
                            overlap_chars = overlap_text[-self.overlap:]
                            current_group = [overlap_chars, para]
                            current_size = len(overlap_chars) + para_size
                    else:
                        current_group = [para]
                        current_size = para_size
                else:
                    # Too small, just add to current group
                    current_group.append(para)
                    current_size += para_size
            else:
                current_group.append(para)
                current_size += para_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join(current_group)
            if len(chunk_text) >= self.min_size:
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, metadata)
                chunks.append(chunk)
        
        return chunks

