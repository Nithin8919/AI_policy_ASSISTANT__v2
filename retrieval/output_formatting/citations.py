# Inline citations enforcement

"""
Citations
=========
Handles inline citations for results.
Ensures proper attribution of sources.
"""

from typing import List, Dict, Optional


class CitationManager:
    """Manages citations for search results"""
    
    def add_citations(
        self,
        results: List[Dict],
        format: str = "numbered"
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Add citation markers to results.
        
        Args:
            results: Search results
            format: Citation format ("numbered", "author_year", "footnote")
            
        Returns:
            Tuple of (results with citations, bibliography)
        """
        bibliography = []
        
        for idx, result in enumerate(results):
            citation_number = idx + 1
            
            # Add citation number to result
            result["citation_number"] = citation_number
            
            # Build bibliography entry
            bib_entry = self._build_bibliography_entry(result, citation_number)
            bibliography.append(bib_entry)
            
            # Add inline citation to text
            if format == "numbered":
                result["citation_marker"] = f"[{citation_number}]"
            elif format == "footnote":
                result["citation_marker"] = f"^{citation_number}"
            elif format == "author_year":
                result["citation_marker"] = self._get_author_year(result)
        
        return results, bibliography
    
    def _build_bibliography_entry(
        self,
        result: Dict,
        citation_number: int
    ) -> Dict:
        """
        Build bibliography entry for a result.
        
        Args:
            result: Search result
            citation_number: Citation number
            
        Returns:
            Bibliography entry dict
        """
        payload = result.get("payload", {})
        metadata = payload
        
        # Extract key fields
        source = metadata.get("source", "Unknown Source")
        doc_type = metadata.get("doc_type", "")
        year = metadata.get("year", "")
        section = metadata.get("section_number", "")
        go_number = metadata.get("go_number", "")
        case_number = metadata.get("case_number", "")
        vertical = result.get("vertical", "")
        
        # Build entry based on vertical
        if vertical == "legal":
            entry = self._format_legal_citation(source, section, year)
        elif vertical == "go":
            entry = self._format_go_citation(source, go_number, year)
        elif vertical == "judicial":
            entry = self._format_judicial_citation(source, case_number, year)
        elif vertical == "data":
            entry = self._format_data_citation(source, year)
        else:
            entry = self._format_generic_citation(source, year)
        
        return {
            "number": citation_number,
            "text": entry,
            "source": source,
            "vertical": vertical,
            "url": metadata.get("url"),
            "year": year
        }
    
    def _format_legal_citation(
        self,
        source: str,
        section: str,
        year: str
    ) -> str:
        """Format legal citation"""
        parts = [source]
        if section:
            parts.append(f"Section {section}")
        if year:
            parts.append(f"({year})")
        return ", ".join(parts)
    
    def _format_go_citation(
        self,
        source: str,
        go_number: str,
        year: str
    ) -> str:
        """Format GO citation"""
        parts = []
        if go_number:
            parts.append(f"G.O. Ms. No. {go_number}")
        parts.append(source)
        if year:
            parts.append(f"({year})")
        return ", ".join(parts)
    
    def _format_judicial_citation(
        self,
        source: str,
        case_number: str,
        year: str
    ) -> str:
        """Format judicial citation"""
        parts = []
        if case_number:
            parts.append(case_number)
        parts.append(source)
        if year:
            parts.append(f"({year})")
        return ", ".join(parts)
    
    def _format_data_citation(
        self,
        source: str,
        year: str
    ) -> str:
        """Format data report citation"""
        parts = [source]
        if year:
            parts.append(f"({year})")
        return ", ".join(parts)
    
    def _format_generic_citation(
        self,
        source: str,
        year: str
    ) -> str:
        """Format generic citation"""
        parts = [source]
        if year:
            parts.append(f"({year})")
        return ", ".join(parts)
    
    def _get_author_year(self, result: Dict) -> str:
        """Get author-year style citation"""
        payload = result.get("payload", {})
        source = payload.get("source", "Unknown")
        year = payload.get("year", "n.d.")
        
        # Extract author/organization
        author = source.split(",")[0] if "," in source else source
        author = author.split(".")[0] if "." in author else author
        
        return f"({author}, {year})"
    
    def format_inline_citation(
        self,
        text: str,
        citations: List[int]
    ) -> str:
        """
        Add inline citations to text.
        
        Args:
            text: Text to cite
            citations: List of citation numbers
            
        Returns:
            Text with inline citations
        """
        if not citations:
            return text
        
        citation_str = "[" + ", ".join(str(c) for c in citations) + "]"
        return f"{text} {citation_str}"
    
    def build_bibliography_section(
        self,
        bibliography: List[Dict]
    ) -> str:
        """
        Build formatted bibliography section.
        
        Args:
            bibliography: List of bibliography entries
            
        Returns:
            Formatted bibliography as string
        """
        lines = ["## References\n"]
        
        for entry in bibliography:
            lines.append(f"{entry['number']}. {entry['text']}")
        
        return "\n".join(lines)


# Global citation manager instance
_citation_manager_instance = None


def get_citation_manager() -> CitationManager:
    """Get global citation manager instance"""
    global _citation_manager_instance
    if _citation_manager_instance is None:
        _citation_manager_instance = CitationManager()
    return _citation_manager_instance