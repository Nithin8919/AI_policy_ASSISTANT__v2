"""
Data Structure Parser
Extracts Data Report structure: Tables, Charts, Analysis Sections
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DataSection:
    """Represents a data report section"""
    section_type: str  # table, chart, analysis, summary
    title: Optional[str]
    content: str
    start_pos: int
    end_pos: int
    table_number: Optional[str] = None
    table_data: Optional[List[List[str]]] = None
    columns: Optional[List[str]] = None


class DataStructureParser:
    """
    Parse Data Report structure
    
    Data Structure:
    1. Executive Summary
    2. Tables
    3. Charts/Figures
    4. Analysis Sections
    5. Conclusions
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for data structure"""
        
        # Enhanced table caption patterns
        self.table_caption_patterns = [
            re.compile(r'(?:Table|TABLE)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?=\n|$)', re.IGNORECASE),
            re.compile(r'(?:Table|TABLE)\s+(\d+(?:\.\d+)?)\s*[:-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            re.compile(r'(?:Annexure|ANNEXURE)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?=\n|$)', re.IGNORECASE)
        ]
        
        # Table content detection patterns
        self.table_content_patterns = [
            re.compile(r'(\s{3,}\S+){3,}'),  # Multiple columns separated by spaces
            re.compile(r'\|[^\n]*\|[^\n]*\|'),  # Pipe-separated data
            re.compile(r'\t[^\n]*\t[^\n]*\t'),  # Tab-separated data
            re.compile(r'^\s*\d+[\.\)]\s+[^\n]*\d+[^\n]*$', re.MULTILINE)  # Numbered rows with data
        ]
        
        # Chart/Figure markers
        self.chart_pattern = re.compile(
            r'(?:Figure|Chart|Graph|FIGURE|CHART|GRAPH)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?:\n|$)',
            re.IGNORECASE
        )
        
        # Chapter/Section markers
        self.section_pattern = re.compile(
            r'^(?:Chapter|Section|CHAPTER|SECTION)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)$',
            re.MULTILINE
        )
        
        # Summary markers
        self.summary_pattern = re.compile(
            r'^(?:SUMMARY|EXECUTIVE SUMMARY|CONCLUSION|CONCLUSIONS)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Single table pattern for backwards compatibility
        self.table_pattern = self.table_content_patterns[0] if self.table_content_patterns else re.compile(r'\|[^\n]*\|[^\n]*\|')
    
    def parse(self, text: str) -> Dict:
        """
        Parse data report structure
        
        Args:
            text: Full report text
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "has_structure": False,
                "tables": [],
                "charts": [],
                "sections": []
            }
        
        # Find tables
        tables = self._find_tables(text)
        
        # Find charts
        charts = self._find_charts(text)
        
        # Find sections
        sections = self._find_sections(text)
        
        return {
            "has_structure": len(tables) > 0 or len(charts) > 0 or len(sections) > 0,
            "tables": tables,
            "charts": charts,
            "sections": sections,
            "table_count": len(tables),
            "chart_count": len(charts),
            "section_count": len(sections),
            "table_numbers": [t.table_number for t in tables if t.table_number],
            "structured_tables": [t for t in tables if t.table_data]
        }
    
    def _find_tables(self, text: str) -> List[DataSection]:
        """Find all tables in the document with enhanced detection"""
        tables = []
        
        # Find table captions first
        table_captions = self.detect_table_captions(text)
        
        for caption in table_captions:
            table_num = caption['number']
            table_title = caption['title']
            caption_pos = caption['position']
            
            # Find table content after caption
            table_block = self.detect_table_block(text, caption_pos)
            
            if table_block:
                tables.append(DataSection(
                    section_type="table",
                    title=f"Table {table_num}: {table_title}" if table_title else f"Table {table_num}",
                    content=table_block['content'],
                    start_pos=caption_pos,
                    end_pos=table_block['end_pos'],
                    table_number=table_num,
                    table_data=table_block.get('table_data'),
                    columns=table_block.get('columns')
                ))
        
        return tables
    
    def detect_table_captions(self, text: str) -> List[Dict]:
        """Detect table captions using enhanced patterns"""
        captions = []
        
        for pattern in self.table_caption_patterns:
            for match in pattern.finditer(text):
                table_num = match.group(1)
                table_title = match.group(2).strip() if match.group(2) else ""
                
                captions.append({
                    'number': table_num,
                    'title': table_title,
                    'position': match.start(),
                    'caption_end': match.end()
                })
        
        # Sort by position
        captions.sort(key=lambda x: x['position'])
        return captions
    
    def detect_table_block(self, text: str, caption_pos: int) -> Optional[Dict]:
        """Detect table content block after caption"""
        # Start search after caption
        search_start = caption_pos
        caption_match = None
        
        # Find the caption end
        for pattern in self.table_caption_patterns:
            match = pattern.search(text[caption_pos:caption_pos+200])
            if match:
                caption_match = match
                break
        
        if not caption_match:
            return None
        
        content_start = caption_pos + caption_match.end()
        
        # Look for table content in next 2000 characters
        search_text = text[content_start:content_start+2000]
        
        # Find table boundaries
        table_content_lines = []
        table_data = []
        columns = []
        
        lines = search_text.split('\n')
        in_table = False
        table_end_pos = content_start
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines at start
            if not line_stripped and not in_table:
                continue
            
            # Check if this line looks like table content
            if self.is_table_content_line(line):
                in_table = True
                table_content_lines.append(line)
                
                # Parse table data
                row_data = self.parse_table_row(line)
                if row_data:
                    table_data.append(row_data)
                    
                    # Extract column headers from first data row
                    if len(table_data) == 1 and not columns:
                        columns = row_data[:]
                
                table_end_pos = content_start + len('\n'.join(lines[:i+1]))
            
            # Stop if we hit another table caption or section
            elif in_table and (self.is_new_section(line) or len(table_content_lines) > 50):
                break
            
            # Continue collecting if we're in a table
            elif in_table:
                table_content_lines.append(line)
                table_end_pos = content_start + len('\n'.join(lines[:i+1]))
        
        if table_content_lines:
            full_content = text[caption_pos:table_end_pos]
            return {
                'content': full_content,
                'end_pos': table_end_pos,
                'table_data': table_data if table_data else None,
                'columns': columns if columns else None
            }
        
        # Fallback: include some text after caption
        fallback_end = min(content_start + 1000, len(text))
        return {
            'content': text[caption_pos:fallback_end],
            'end_pos': fallback_end,
            'table_data': None,
            'columns': None
        }
    
    def is_table_content_line(self, line: str) -> bool:
        """Check if a line contains table content"""
        if not line.strip():
            return False
        
        # Check against table content patterns
        for pattern in self.table_content_patterns:
            if pattern.search(line):
                return True
        
        # Additional heuristics
        # High digit density
        digits = sum(c.isdigit() for c in line)
        if digits > 5 and digits / len(line) > 0.1:
            return True
        
        # Multiple numeric values
        numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', line)
        if len(numbers) >= 3:
            return True
        
        return False
    
    def parse_table_row(self, line: str) -> Optional[List[str]]:
        """Parse a table row into columns"""
        line = line.strip()
        
        # Try different separators
        separators = ['|', '\t', '  ', '   ', '    ']
        
        for sep in separators:
            if sep in line:
                cols = [col.strip() for col in line.split(sep)]
                # Filter out empty columns
                cols = [col for col in cols if col]
                if len(cols) >= 2:
                    return cols
        
        # Fallback: split on multiple spaces
        cols = re.split(r'\s{2,}', line)
        if len(cols) >= 2:
            return [col.strip() for col in cols if col.strip()]
        
        return None
    
    def is_new_section(self, line: str) -> bool:
        """Check if line starts a new section"""
        for pattern in self.table_caption_patterns + [self.chart_pattern, self.section_pattern]:
            if pattern.search(line):
                return True
        return False
    
    def _find_charts(self, text: str) -> List[DataSection]:
        """Find all charts/figures in the document"""
        charts = []
        
        for match in self.chart_pattern.finditer(text):
            chart_num = match.group(1)
            chart_title = match.group(2).strip() if match.group(2) else None
            
            # Extract chart content (description)
            start_pos = match.end()
            
            # Find end (next marker or 500 chars)
            remaining_text = text[start_pos:]
            next_marker = None
            

            # Check for next table or chart
            for pattern in self.table_caption_patterns + [self.chart_pattern]:
                next_match = pattern.search(remaining_text)
                if next_match:
                    if next_marker is None or next_match.start() < next_marker:
                        next_marker = next_match.start()
            
            if next_marker:
                end_pos = start_pos + next_marker
            else:
                end_pos = min(start_pos + 500, len(text))
            
            chart_content = text[match.start():end_pos].strip()
            
            charts.append(DataSection(
                section_type="chart",
                title=f"Figure {chart_num}: {chart_title}" if chart_title else f"Figure {chart_num}",
                content=chart_content,
                start_pos=match.start(),
                end_pos=end_pos
            ))
        
        return charts
    
    def _find_sections(self, text: str) -> List[DataSection]:
        """Find analysis sections"""
        sections = []
        
        for match in self.section_pattern.finditer(text):
            section_num = match.group(1)
            section_title = match.group(2).strip() if match.group(2) else None
            
            # Find section content (until next section)
            start_pos = match.end()
            
            remaining_text = text[start_pos:]
            next_match = self.section_pattern.search(remaining_text)
            
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                end_pos = len(text)
            
            section_content = text[start_pos:end_pos].strip()
            
            sections.append(DataSection(
                section_type="analysis",
                title=f"Section {section_num}: {section_title}" if section_title else f"Section {section_num}",
                content=section_content,
                start_pos=match.start(),
                end_pos=end_pos
            ))
        
        return sections
    
    def is_table_content(self, text: str) -> bool:
        """
        Heuristic to detect if text is a table
        Checks for high density of numbers, pipes, tabs
        """
        if not text:
            return False
        
        # Count indicators
        pipe_count = text.count('|')
        tab_count = text.count('\t')
        digit_count = sum(c.isdigit() for c in text)
        total_chars = len(text)
        
        # High ratio suggests table
        if pipe_count / max(1, total_chars) > 0.05:
            return True
        if tab_count / max(1, total_chars) > 0.03:
            return True
        if digit_count / max(1, total_chars) > 0.2:
            return True
        
        return False