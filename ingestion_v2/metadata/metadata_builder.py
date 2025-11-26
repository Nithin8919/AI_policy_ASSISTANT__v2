"""
Metadata Builder
Builds clean, minimal, retrieval-optimized metadata for Qdrant
NO bloat, only what helps retrieval
"""
import re
from typing import Dict, List, Optional
from datetime import datetime


class MetadataBuilder:
    """
    Builds optimized metadata for vector search
    
    Philosophy:
    - Only include metadata that helps retrieval
    - Keep it flat and simple
    - No nested complexity
    - No processing timestamps (irrelevant for search)
    """
    
    def __init__(self):
        # GO number extraction pattern
        self.go_pattern = re.compile(r'G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*(\d+)', re.IGNORECASE)
        
        # Year extraction pattern
        self.year_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        
        # Section extraction pattern
        self.section_pattern = re.compile(r'Section\s+(\d+(?:\([a-z]\))?)', re.IGNORECASE)
    
    def build_chunk_metadata(
        self,
        chunk: Dict,
        doc_metadata: Dict,
        entities: Dict,
        relations: List[Dict],
        vertical: str
    ) -> Dict:
        """
        Build complete metadata for a single chunk
        
        Args:
            chunk: Chunk dictionary
            doc_metadata: Document-level metadata
            entities: Extracted entities
            relations: Extracted relations
            vertical: Document vertical (go, legal, etc.)
            
        Returns:
            Clean metadata dictionary for Qdrant
        """
        content = chunk.get('content', '')
        chunk_id = chunk.get('chunk_id', '')
        doc_id = chunk.get('doc_id', '')
        
        # Start with minimal core metadata
        metadata = {
            # Core identifiers
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "vertical": vertical,
            "doc_type": vertical,  # For backward compatibility
            
            # Position info
            "chunk_position": chunk.get('chunk_index', chunk.get('position', 0)),
            
            # Content stats (helpful for ranking)
            "word_count": chunk.get('word_count', len(content.split())),
            "char_count": len(content)
        }
        
        # Add vertical-specific metadata
        if vertical == "go":
            metadata.update(self._build_go_metadata(content, doc_metadata))
        elif vertical == "legal":
            metadata.update(self._build_legal_metadata(content, doc_metadata))
        elif vertical == "judicial":
            metadata.update(self._build_judicial_metadata(content, doc_metadata))
        elif vertical == "data":
            metadata.update(self._build_data_metadata(content, chunk))
        elif vertical == "scheme":
            metadata.update(self._build_scheme_metadata(content, doc_metadata))
        
        # Add key entities (only if extracted)
        if entities:
            entity_metadata = self._extract_key_entities(entities, content)
            metadata.update(entity_metadata)
        
        # Add relation info (only targets, not full relations)
        if relations:
            metadata["has_relations"] = True
            metadata["relation_types"] = list(set(r.get("relation_type", "") for r in relations))
        else:
            metadata["has_relations"] = False
        
        # Add chunk type if present
        if "chunk_type" in chunk:
            metadata["chunk_type"] = chunk["chunk_type"]
        
        if "section_type" in chunk.get("metadata", {}):
            metadata["section_type"] = chunk["metadata"]["section_type"]
        
        return metadata
    
    def _build_go_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build GO-specific metadata"""
        metadata = {}
        
        # Extract GO number
        go_match = self.go_pattern.search(content)
        if go_match:
            metadata["go_number"] = go_match.group(1)
        elif "go_number" in doc_metadata:
            metadata["go_number"] = doc_metadata["go_number"]
        
        # Extract year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        # Department (if present in doc metadata)
        if "department" in doc_metadata:
            metadata["department"] = doc_metadata["department"]
        
        return metadata
    
    def _build_legal_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build legal document-specific metadata"""
        metadata = {}
        
        # Extract section numbers
        section_matches = self.section_pattern.findall(content)
        if section_matches:
            # Store first section (primary)
            metadata["section"] = section_matches[0]
            
            # Store all sections if multiple
            if len(section_matches) > 1:
                metadata["sections"] = section_matches[:5]  # Limit to 5
        
        # Extract year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        # Act name (if present in doc metadata)
        if "act_name" in doc_metadata:
            metadata["act_name"] = doc_metadata["act_name"]
        
        return metadata
    
    def _build_judicial_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build judicial document-specific metadata"""
        metadata = {}
        
        # Case number (from doc metadata)
        if "case_number" in doc_metadata:
            metadata["case_number"] = doc_metadata["case_number"]
        
        # Court name
        if "court" in doc_metadata:
            metadata["court"] = doc_metadata["court"]
        
        # Year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        return metadata
    
    def _build_data_metadata(self, content: str, chunk: Dict) -> Dict:
        """Build data document-specific metadata with enhanced table support"""
        metadata = {}
        
        # Set default table status
        metadata["is_table"] = False
        metadata["has_table"] = False
        
        # Check if this is a table chunk
        chunk_metadata = chunk.get("metadata", {})
        if chunk.get("chunk_type") == "table" or chunk_metadata.get("is_table", False) or chunk_metadata.get("has_table", False):
            metadata["is_table"] = True
            metadata["has_table"] = True
            
            # Add table-specific metadata
            if "table_name" in chunk_metadata:
                metadata["table_name"] = chunk_metadata["table_name"]
            if "table_number" in chunk_metadata:
                metadata["table_number"] = chunk_metadata["table_number"]
            if "table_title" in chunk_metadata:
                metadata["table_title"] = chunk_metadata["table_title"]
            if "table_source" in chunk_metadata:
                metadata["table_source"] = chunk_metadata["table_source"]
            
            # Table structure metadata
            if "headers" in chunk_metadata and chunk_metadata["headers"]:
                metadata["columns"] = chunk_metadata["headers"][:10]  # Limit to 10 columns
                metadata["column_count"] = len(chunk_metadata["headers"])
            if "columns" in chunk_metadata and chunk_metadata["columns"]:
                metadata["columns"] = chunk_metadata["columns"][:10]
                metadata["column_count"] = len(chunk_metadata["columns"])
            if "row_count" in chunk_metadata:
                metadata["row_count"] = chunk_metadata["row_count"]
            if "col_count" in chunk_metadata:
                metadata["column_count"] = chunk_metadata["col_count"]
            
            # Page information for extracted tables
            if "page_num" in chunk_metadata:
                metadata["page_number"] = chunk_metadata["page_num"]
            if "table_num_on_page" in chunk_metadata:
                metadata["table_index_on_page"] = chunk_metadata["table_num_on_page"]
        
        # Year extraction
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        # Detect table references even in non-table chunks
        table_refs = re.findall(r'Table\s+(\d+(?:\.\d+)?)', content, re.IGNORECASE)
        if table_refs:
            metadata["references_tables"] = list(set(table_refs))[:5]  # Limit to 5
        
        return metadata
    
    def _build_scheme_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build scheme document-specific metadata"""
        metadata = {}
        
        # Scheme name (from doc metadata or content)
        if "scheme_name" in doc_metadata:
            metadata["scheme_name"] = doc_metadata["scheme_name"]
        else:
            # Try to extract scheme name from content
            scheme_match = re.search(r'(Jagananna\s+[A-Za-z\s]+)', content, re.IGNORECASE)
            if scheme_match:
                metadata["scheme_name"] = scheme_match.group(1).strip()
        
        # Year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        return metadata
    
    def _extract_key_entities(self, entities: Dict, content: str) -> Dict:
        """
        Extract key entities for metadata
        Only include entities that are ACTUALLY in this chunk
        """
        metadata = {}
        
        # GO numbers
        if "go_numbers" in entities and entities["go_numbers"]:
            # Filter to only GOs mentioned in this chunk
            chunk_gos = [go for go in entities["go_numbers"] if go in content]
            if chunk_gos:
                metadata["mentioned_gos"] = chunk_gos[:3]  # Limit to 3
        
        # Sections
        if "sections" in entities and entities["sections"]:
            chunk_sections = [sec for sec in entities["sections"] if sec in content]
            if chunk_sections:
                metadata["mentioned_sections"] = chunk_sections[:3]
        
        # Departments
        if "departments" in entities and entities["departments"]:
            chunk_depts = [dept for dept in entities["departments"] if dept.lower() in content.lower()]
            if chunk_depts:
                metadata["departments"] = chunk_depts[:2]
        
        # Schemes
        if "schemes" in entities and entities["schemes"]:
            chunk_schemes = [scheme for scheme in entities["schemes"] if scheme.lower() in content.lower()]
            if chunk_schemes:
                metadata["schemes"] = chunk_schemes[:2]
        
        return metadata
    
    def build_document_metadata(
        self,
        doc_id: str,
        file_path: str,
        vertical: str,
        entities: Dict,
        relations: List[Dict],
        chunks_count: int
    ) -> Dict:
        """
        Build document-level metadata (for manifest/summary)
        
        Args:
            doc_id: Document ID
            file_path: Path to source file
            vertical: Document vertical
            entities: All extracted entities
            relations: All extracted relations
            chunks_count: Number of chunks created
            
        Returns:
            Document metadata dictionary
        """
        metadata = {
            "doc_id": doc_id,
            "file_path": file_path,
            "vertical": vertical,
            "chunks_count": chunks_count,
            "processed_at": datetime.utcnow().isoformat(),
            
            # Entity counts
            "entity_counts": {
                entity_type: len(entity_list) if isinstance(entity_list, list) else 0
                for entity_type, entity_list in entities.items()
            },
            
            # Relation counts
            "relations_count": len(relations),
            "relation_types": list(set(r.get("relation_type", "") for r in relations)) if relations else []
        }
        
        return metadata