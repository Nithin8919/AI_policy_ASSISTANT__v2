"""
Data Chunker - Reports and Statistical Documents
Optimized for tables, charts, and data analysis sections
"""
import re
from typing import List, Dict
from .base_chunker import BaseChunker, Chunk


class DataChunker(BaseChunker):
    """
    Data document specific chunker
    Handles tables, charts, and analytical content
    """
    
    def __init__(self):
        # Data-specific sizes (smaller for dense tabular data)
        super().__init__(min_size=500, max_size=1000, overlap=80)
        
        # Table detection patterns
        self.table_marker = re.compile(r'(?:Table|Chart|Figure)\s+\d+', re.IGNORECASE)
        self.section_marker = re.compile(r'^(?:Chapter|Section)\s+\d+', re.IGNORECASE | re.MULTILINE)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk data document with enhanced table awareness
        
        Strategy:
        1. Detect tables from structure parser and extraction
        2. Create dedicated table chunks
        3. Split analytical text by sections
        4. Keep related content together
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Check if we have structured table data from extraction
        extracted_tables = metadata.get('extracted_tables', [])
        structured_tables = metadata.get('structured_tables', [])
        
        # Convert DataSection objects to dicts if needed
        if structured_tables:
            converted_tables = []
            for table in structured_tables:
                if hasattr(table, '__dict__'):
                    # It's a DataSection object
                    converted_tables.append({
                        'type': 'structured',
                        'content': getattr(table, 'content', ''),
                        'table_number': getattr(table, 'table_number', None),
                        'title': getattr(table, 'title', None),
                        'table_data': getattr(table, 'table_data', None),
                        'columns': getattr(table, 'columns', None),
                        'start_pos': getattr(table, 'start_pos', 0),
                        'end_pos': getattr(table, 'end_pos', 0),
                        'section_type': getattr(table, 'section_type', 'table')
                    })
                else:
                    # Already a dict
                    converted_tables.append(table)
            structured_tables = converted_tables
        
        if extracted_tables or structured_tables:
            chunks = self._chunk_with_structured_tables(
                text, doc_id, metadata, extracted_tables, structured_tables
            )
        else:
            # Fallback to pattern-based table detection
            chunks = self._chunk_with_table_awareness(text, doc_id, metadata)
        
        return chunks
    
    def _chunk_with_structured_tables(
        self,
        text: str,
        doc_id: str,
        metadata: Dict,
        extracted_tables: List[Dict],
        structured_tables: List[Dict]
    ) -> List[Chunk]:
        """
        Chunk text using structured table information from extraction
        """
        chunks = []
        chunk_index = 0
        
        # Combine all table information
        all_tables = []
        
        # Add extracted tables from pdfplumber
        for table in extracted_tables:
            all_tables.append({
                'type': 'extracted',
                'content': table.get('formatted_text', ''),
                'table_data': table.get('raw_data', []),
                'headers': table.get('headers', []),
                'page_num': table.get('page_num', 0),
                'table_num': table.get('table_num', 0)
            })
        
        # Add structured tables from structure parser
        for table in structured_tables:
            # Handle both dict and object formats
            if isinstance(table, dict):
                all_tables.append(table)
            else:
                all_tables.append({
                    'type': 'structured',
                    'content': getattr(table, 'content', ''),
                    'table_number': getattr(table, 'table_number', None),
                    'title': getattr(table, 'title', None),
                    'table_data': getattr(table, 'table_data', None),
                    'columns': getattr(table, 'columns', None),
                    'start_pos': getattr(table, 'start_pos', 0),
                    'end_pos': getattr(table, 'end_pos', 0)
                })
        
        # Create table chunks - ONE CHUNK PER TABLE
        for table_info in all_tables:
            table_content = table_info['content']
            
            if not table_content or len(table_content.strip()) < 20:
                continue
            
            # Enhanced table metadata
            table_metadata = {
                **metadata,
                "chunk_type": "table",
                "is_table": True,
                "has_table": True,  # Add this for metadata builder
                "table_source": table_info['type'],
                "table_info": f"Table {table_info.get('table_number', table_info.get('table_num', 'Unknown'))}"
            }
            
            # Add table-specific metadata based on source
            if table_info['type'] == 'extracted':
                table_metadata.update({
                    "page_num": table_info.get('page_num'),
                    "table_num_on_page": table_info.get('table_num'),
                    "headers": table_info.get('headers', []),
                    "row_count": len(table_info.get('table_data', [])),
                    "col_count": len(table_info.get('headers', []))
                })
            elif table_info['type'] == 'structured':
                table_metadata.update({
                    "table_number": table_info.get('table_number'),
                    "table_title": table_info.get('title'),
                    "columns": table_info.get('columns', []),
                    "structured_data": table_info.get('table_data', [])
                })
            
            # Create single chunk for entire table
            table_chunk = self._create_chunk(
                table_content, doc_id, chunk_index, table_metadata
            )
            chunks.append(table_chunk)
            chunk_index += 1
        
        # Process remaining non-table text
        non_table_text = self._remove_table_content(text, all_tables)
        
        if non_table_text and len(non_table_text.strip()) > 100:
            # Chunk remaining text normally
            paras = self._split_paragraphs(non_table_text)
            para_chunks = self._group_paragraphs(paras, doc_id, metadata)
            for chunk in para_chunks:
                chunk.chunk_index = chunk_index
                chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                # Mark as non-table content
                chunk.metadata["is_table"] = False
                chunk.metadata["chunk_type"] = "text"
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _remove_table_content(self, text: str, tables: List[Dict]) -> str:
        """
        Remove table content from text to get non-table sections
        """
        remaining_text = text
        
        # Remove structured table content based on positions
        for table in tables:
            if table['type'] == 'structured' and 'start_pos' in table:
                start_pos = table['start_pos']
                end_pos = table.get('end_pos', start_pos + len(table['content']))
                
                # Remove this section from text
                before = remaining_text[:start_pos]
                after = remaining_text[end_pos:]
                remaining_text = before + "\n\n" + after
        
        # Clean up multiple newlines
        remaining_text = re.sub(r'\n{3,}', '\n\n', remaining_text)
        
        return remaining_text.strip()
    
    def _chunk_with_table_awareness(
        self, 
        text: str, 
        doc_id: str, 
        metadata: Dict
    ) -> List[Chunk]:
        """
        Fallback: Chunk text while preserving table integrity using pattern detection
        """
        chunks = []
        chunk_index = 0
        
        # Find table positions
        table_positions = [(m.start(), m.end(), m.group()) 
                          for m in self.table_marker.finditer(text)]
        
        if not table_positions:
            # No tables, use standard paragraph chunking
            paragraphs = self._split_paragraphs(text)
            return self._group_paragraphs(paragraphs, doc_id, metadata)
        
        # Split text around tables
        current_pos = 0
        
        for table_start, table_end, table_name in table_positions:
            # Get text before table
            before_table = text[current_pos:table_start].strip()
            
            if before_table:
                # Chunk the text before table
                paras = self._split_paragraphs(before_table)
                para_chunks = self._group_paragraphs(paras, doc_id, metadata)
                for chunk in para_chunks:
                    chunk.chunk_index = chunk_index
                    chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                    chunks.append(chunk)
                    chunk_index += 1
            
            # Extract table content (table + description)
            # Find the end of table (next double newline or next table)
            next_table_start = table_positions[table_positions.index((table_start, table_end, table_name)) + 1][0] \
                if table_positions.index((table_start, table_end, table_name)) + 1 < len(table_positions) \
                else len(text)
            
            # Look for double newline as end of table section
            table_section_end = text.find('\n\n\n', table_start)
            if table_section_end == -1 or table_section_end > next_table_start:
                table_section_end = next_table_start
            
            table_content = text[table_start:table_section_end].strip()
            
            if table_content:
                # Create table chunk with enhanced metadata
                table_metadata = {
                    **metadata,
                    "chunk_type": "table",
                    "is_table": True,
                    "table_name": table_name,
                    "table_source": "pattern_detected"
                }
                table_chunk = self._create_chunk(
                    table_content, doc_id, chunk_index, table_metadata
                )
                chunks.append(table_chunk)
                chunk_index += 1
            
            current_pos = table_section_end
        
        # Get remaining text after last table
        remaining = text[current_pos:].strip()
        if remaining:
            paras = self._split_paragraphs(remaining)
            para_chunks = self._group_paragraphs(paras, doc_id, metadata)
            for chunk in para_chunks:
                chunk.chunk_index = chunk_index
                chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                chunk.metadata["is_table"] = False
                chunk.metadata["chunk_type"] = "text"
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _is_table_content(self, text: str) -> bool:
        """
        Detect if text is likely a table
        Simple heuristic: high ratio of digits, pipes, or tabs
        """
        if not text:
            return False
        
        # Count special characters
        special_chars = text.count('|') + text.count('\t')
        digit_count = sum(c.isdigit() for c in text)
        total_chars = len(text)
        
        # High ratio suggests table
        if special_chars / max(1, total_chars) > 0.05:
            return True
        if digit_count / max(1, total_chars) > 0.2:
            return True
        
        return False