import re
from typing import List, Dict

class EntityExtractor:
    """Extract entities with strict patterns"""
    
    # Strict GO regex - only matches valid GO formats
    GO_PATTERN = re.compile(
        r'G\.O\.(Ms|Rt)\.No\.\s*(\d+)',
        r'G\.O\.(Ms|Rt)\.No\.\s*(\d+)',
        re.IGNORECASE
    )
    
    # HR/Staffing patterns
    HR_PATTERN = re.compile(
        r'\b(salary|payscale|recruitment|hiring|contract|private|appointment|vacancy|post|remuneration|staffing|service rules)\b',
        re.IGNORECASE
    )
    
    # Department pattern (simple)
    DEPT_PATTERN = re.compile(
        r'\b(education|finance|revenue|general administration|school education|higher education)\s+department\b',
        re.IGNORECASE
    )
    
    # Act pattern
    ACT_PATTERN = re.compile(
        r'\b(RTE|Right to Education|APSERMC|CCE)\s+Act\b',
        re.IGNORECASE
    )
    
    def extract_go_numbers(self, text: str) -> List[str]:
        """
        Extract GO numbers with strict pattern
        
        Args:
            text: Input text
            
        Returns:
            List of GO numbers in format "G.O.Ms.No.123"
        """
        matches = self.GO_PATTERN.findall(text)
        return [f"G.O.{type}.No.{num}" for type, num in matches]
    
    def extract_all_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all entities from text
        
        Returns:
            Dict with 'go_numbers', 'departments', etc.
        """
        return {
            'go_numbers': self.extract_go_numbers(text),
            'departments': self.DEPT_PATTERN.findall(text),
            'acts': self.ACT_PATTERN.findall(text),
            'hr_terms': self.HR_PATTERN.findall(text)
        }
