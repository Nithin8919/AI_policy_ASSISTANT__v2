"""
Answer Formatter - Post-process LLM answers for consistency
============================================================
Ensures GO numbers have dates, citations are valid, and markdown is properly structured.
"""

import re
from typing import List, Dict, Optional


class AnswerFormatter:
    """Post-process LLM answers for consistency and quality"""
    
    def format_answer(self, raw_answer: str, results: List[Dict]) -> str:
        """
        Apply formatting rules to LLM answer
        
        Args:
            raw_answer: Raw LLM output
            results: Enriched results used for answer generation
            
        Returns:
            Formatted answer text
        """
        formatted = raw_answer
        
        # 1. Standardize GO numbers
        formatted = self._standardize_go_numbers(formatted)
        
        # 2. Add missing dates where GO numbers are mentioned
        formatted = self._add_missing_dates(formatted, results)
        
        # 3. Validate and fix citations
        formatted = self._fix_citations(formatted, len(results))
        
        # 4. Ensure markdown structure
        formatted = self._ensure_markdown_structure(formatted)
        
        # 5. Highlight recent documents
        formatted = self._highlight_recent_docs(formatted, results)
        
        return formatted
    
    def _standardize_go_numbers(self, text: str) -> str:
        """Standardize GO number formatting"""
        # Pattern: G.O.Ms.No.123 or GO.Ms.No.123 or G.O Ms No 123
        patterns = [
            (r'GO\.?Ms\.?No\.?(\d+)', r'G.O.Ms.No.\1'),
            (r'G\.?O\.?\s*Ms\.?\s*No\.?\s*(\d+)', r'G.O.Ms.No.\1'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _add_missing_dates(self, text: str, results: List[Dict]) -> str:
        """Add dates next to GO numbers if missing"""
        # Find GO numbers in text
        go_pattern = r'G\.O\.Ms\.No\.(\d+)'
        
        def add_date(match):
            go_num = match.group(1)
            
            # Find corresponding result
            for result in results:
                result_go = result.get('go_number', '')
                if result_go and str(go_num) in str(result_go):
                    date = result.get('date_formatted')
                    if date:
                        # Check if date already follows
                        full_match = match.group(0)
                        # Look ahead in text to see if date is already there
                        match_end = match.end()
                        next_chars = text[match_end:match_end+50] if match_end < len(text) else ''
                        
                        # If date pattern not found nearby, add it
                        if not re.search(r'\d{2}-\d{2}-\d{4}', next_chars[:20]):
                            return f"{full_match} ({date})"
            
            return match.group(0)  # Return unchanged if no date found
        
        return re.sub(go_pattern, add_date, text)
    
    def _fix_citations(self, text: str, num_results: int) -> str:
        """Validate and fix citation references"""
        # Find all [Doc N] or [N] citations
        citation_pattern = r'\[(?:Doc\s*)?(\d+)\]'
        
        def validate_citation(match):
            cite_num = int(match.group(1))
            
            # Check if citation number is valid
            if cite_num > num_results:
                # Invalid citation - remove or cap it
                return f"[Doc {min(cite_num, num_results)}]"
            else:
                # Standardize format
                return f"[Doc {cite_num}]"
        
        return re.sub(citation_pattern, validate_citation, text)
    
    def _ensure_markdown_structure(self, text: str) -> str:
        """Ensure proper markdown structure"""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Ensure headers have proper spacing
            if stripped.startswith('#'):
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')  # Add blank line before header
                formatted_lines.append(stripped)
                formatted_lines.append('')  # Add blank line after header
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _highlight_recent_docs(self, text: str, results: List[Dict]) -> str:
        """Add visual indicators for recent documents (2024-2025)"""
        # Find GO numbers and check if they're recent
        go_pattern = r'(G\.O\.Ms\.No\.\d+)'
        
        def highlight_if_recent(match):
            go_text = match.group(1)
            
            # Extract GO number
            go_num = re.search(r'(\d+)', go_text).group(1)
            
            # Check if recent
            for result in results:
                result_go = result.get('go_number', '')
                if result_go and str(go_num) in str(result_go):
                    if result.get('is_recent'):
                        return f"**{go_text}** 🆕"
            
            return go_text
        
        return re.sub(go_pattern, highlight_if_recent, text)


# Convenience function
def format_answer(raw_answer: str, results: List[Dict]) -> str:
    """Quick answer formatting"""
    formatter = AnswerFormatter()
    return formatter.format_answer(raw_answer, results)


if __name__ == "__main__":
    print("Answer Formatter")
    print("=" * 60)
    
    # Example usage
    raw_answer = """
Recent Government Orders include GO.Ms.No.26 which amends previous orders [1].
The policy is detailed in G.O Ms No 190 [2].

## Key Provisions
The order establishes new guidelines [3].
"""
    
    results = [
        {
            'go_number': '26',
            'date_formatted': '16-02-2019',
            'is_recent': False
        },
        {
            'go_number': '190',
            'date_formatted': '15-08-2022',
            'is_recent': False
        },
        {
            'go_number': '22',
            'date_formatted': '20-05-2025',
            'is_recent': True
        }
    ]
    
    formatted = format_answer(raw_answer, results)
    print("\nFormatted Answer:")
    print(formatted)
