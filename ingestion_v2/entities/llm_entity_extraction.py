"""
LLM Entity Extractor
Uses Gemini to extract complex entities that regex might miss
Only used for important documents in go/legal/judicial verticals
"""
import json
import re
import logging
from typing import Dict, List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class LLMEntityExtractor:
    """
    LLM-powered entity extractor using Gemini
    
    Purpose:
    - Catch entities that regex patterns miss
    - Extract context-dependent entities
    - Improve entity quality for critical documents
    
    Philosophy:
    - Use sparingly (expensive and slow)
    - Only for documents where regex finds few entities
    - Complement, don't replace regex
    """
    
    def __init__(self, api_key: str = "", model_name: str = "models/gemini-2.0-flash"):
        """
        Initialize LLM extractor
        
        Args:
            api_key: Gemini API key
            model_name: Model to use
        """
        self.model_name = model_name
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
                self.enabled = True
                logger.info("✅ LLM entity extractor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            self.enabled = False
            logger.warning("No Gemini API key - LLM entity extraction disabled")
    
    def extract(
        self, 
        text: str, 
        vertical: str, 
        doc_id: str = ""
    ) -> Dict[str, List[str]]:
        """
        Extract entities using LLM
        
        Args:
            text: Document text
            vertical: Document vertical
            doc_id: Document ID
            
        Returns:
            Dictionary of entity types and values
        """
        if not self.enabled:
            return {}
        
        if not text or len(text) < 500:
            return {}
        
        try:
            # Truncate if too long
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            # Build prompt
            prompt = self._build_prompt(text, vertical)
            
            # Call Gemini
            response = self.model.generate_content(prompt)
            
            # Parse response
            entities = self._parse_response(response.text)
            
            logger.info(f"LLM extracted {sum(len(v) for v in entities.values())} entities from {doc_id}")
            
            return entities
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed for {doc_id}: {e}")
            return {}
    
    def _build_prompt(self, text: str, vertical: str) -> str:
        """Build extraction prompt based on vertical"""
        
        if vertical == "go":
            entity_types = """
1. GO_NUMBERS - Government Order numbers (e.g., G.O.MS.No.123)
2. DEPARTMENTS - Department/Ministry names
3. SCHEMES - Scheme names (e.g., Jagananna Vidya Deevena)
4. DATES - Important dates
5. SECTIONS - Section/Rule references
6. BENEFICIARIES - Target groups/beneficiaries
"""
        elif vertical == "legal":
            entity_types = """
1. ACT_NAMES - Act names (e.g., Right to Education Act, 2009)
2. SECTIONS - Section numbers and references
3. RULES - Rule references
4. AMENDMENTS - Amendment references
5. DATES - Enactment/amendment dates
6. AUTHORITIES - Implementing authorities
"""
        elif vertical == "judicial":
            entity_types = """
1. CASE_NUMBERS - Case/petition numbers
2. PARTIES - Petitioner/Respondent names
3. COURTS - Court names
4. JUDGES - Judge names
5. ACTS_CITED - Acts and sections cited
6. DATES - Important dates (filing, hearing, judgment)
"""
        else:
            entity_types = """
1. KEY_TERMS - Important domain-specific terms
2. ORGANIZATIONS - Organizations mentioned
3. DATES - Important dates
4. REFERENCES - Document references
"""
        
        prompt = f"""You are an expert in Indian policy documents. Extract entities from this {vertical} document.

Document text:
{text}

Extract the following entity types:
{entity_types}

Return ONLY a JSON object in this EXACT format:
{{
  "go_numbers": ["G.O.MS.No.123", "G.O.MS.No.456"],
  "departments": ["School Education", "Higher Education"],
  "schemes": ["Jagananna Vidya Deevena"],
  "dates": ["15.08.2023", "01.04.2024"],
  "sections": ["Section 5", "Section 12(1)"],
  "acts": ["Right to Education Act, 2009"]
}}

Rules:
- Only extract entities actually present in the text
- Normalize formats (e.g., "G.O. MS No 123" → "G.O.MS.No.123")
- Remove duplicates
- Limit each type to max 10 entities
- If a type has no entities, use empty array: []

JSON only, no explanation:"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, List[str]]:
        """Parse LLM JSON response"""
        try:
            # Clean response
            response_text = response_text.strip()
            
            # Remove markdown if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            if not isinstance(data, dict):
                logger.error("LLM response is not a dict")
                return {}
            
            # Validate and clean
            entities = {}
            valid_keys = {
                "go_numbers", "sections", "rules", "dates", 
                "departments", "schemes", "acts", "case_numbers",
                "parties", "courts", "judges", "acts_cited",
                "organizations", "beneficiaries", "authorities"
            }
            
            for key, values in data.items():
                # Normalize key
                key_lower = key.lower().replace(" ", "_")
                
                # Skip if not valid key
                if key_lower not in valid_keys:
                    continue
                
                # Validate values
                if isinstance(values, list):
                    # Clean values
                    cleaned_values = []
                    for v in values[:10]:  # Limit to 10
                        if isinstance(v, str) and v.strip():
                            cleaned_values.append(v.strip())
                    
                    if cleaned_values:
                        entities[key_lower] = cleaned_values
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {}


def create_llm_entity_extractor(api_key: str = "") -> Optional[LLMEntityExtractor]:
    """
    Factory function to create LLM entity extractor
    
    Args:
        api_key: Gemini API key
        
    Returns:
        LLMEntityExtractor instance or None if failed
    """
    try:
        extractor = LLMEntityExtractor(api_key=api_key)
        return extractor if extractor.enabled else None
    except Exception as e:
        logger.error(f"Failed to create LLM entity extractor: {e}")
        return None