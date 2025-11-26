"""
Vertical classifier using Gemini LLM.

Simple, accurate classification into 5 verticals.
Uses LLM ONLY for classification - nothing else.
"""
from typing import Dict, Optional
import logging
import os
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from ..config.constants import VERTICAL_KEYWORDS
from ..utils.llm_cache import get_cache

logger = logging.getLogger(__name__)


class VerticalClassifier:
    """Classify documents into verticals using Gemini."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "models/gemini-2.0-flash"):
        """
        Initialize vertical classifier.
        
        Args:
            api_key: Gemini API key
            model: Gemini model name
        """
        # Check both GEMINI_API_KEY and GOOGLE_API_KEY
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.use_llm = GEMINI_AVAILABLE and bool(self.api_key)
        
        # Initialize cache
        self.cache = get_cache()
        
        if self.use_llm:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"✓ Gemini classifier initialized: {self.model_name}")
        else:
            logger.warning("Gemini not available - using fallback classification")
    
    def classify(self, text: str, file_name: str = "") -> Dict:
        """
        Classify document into vertical.
        
        Args:
            text: Document text (first 3000 chars)
            file_name: Optional file name for hints
            
        Returns:
            Classification result with vertical and confidence
        """
        if self.use_llm:
            return self._classify_with_llm(text, file_name)
        else:
            return self._classify_with_keywords(text, file_name)
    
    def _classify_with_llm(self, text: str, file_name: str) -> Dict:
        """Classify using Gemini LLM."""
        try:
            # Take first 3000 chars for classification
            sample = text[:3000]
            
            # Check cache first
            cache_key_content = f"{file_name}|{sample}"
            cached_result = self.cache.get(
                content=cache_key_content,
                model=self.model_name,
                task_type="vertical_classification"
            )
            
            if cached_result:
                logger.debug("Using cached classification result")
                return cached_result["response"]
            
            prompt = f"""You are a document classifier for Indian government education documents.

Classify this document into EXACTLY ONE of these 5 categories:
1. "go" - Government Orders (GOs) - documents with G.O.Ms.No or G.O.Rt.No, preambles, official orders
2. "legal" - Legal Documents - Acts, Rules, Sections, Amendments, Regulations
3. "judicial" - Judicial Documents - Court cases, judgments, petitions, legal proceedings
4. "data" - Data Reports - Statistics, tables, enrollment data, UDISE reports, metrics
5. "scheme" - Government Schemes - Scheme guidelines, eligibility, benefits, implementation

Document filename: {file_name}

Document text (first 3000 chars):
{sample}

Respond with ONLY a valid JSON object:
{{
    "vertical": "one of: go, legal, judicial, data, scheme",
    "confidence": <float between 0.0 and 1.0>,
    "reasoning": "<brief 1-sentence explanation>"
}}

DO NOT include any text outside the JSON object."""

            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Strip markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            vertical = result.get("vertical", "data")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            # Validate vertical
            valid_verticals = ["go", "legal", "judicial", "data", "scheme"]
            if vertical not in valid_verticals:
                logger.warning(f"Invalid vertical '{vertical}', defaulting to 'data'")
                vertical = "data"
                confidence = 0.3
            
            logger.info(f"✓ Classified as '{vertical}' (confidence: {confidence:.2f})")
            logger.debug(f"Reasoning: {reasoning}")
            
            result_dict = {
                "vertical": vertical,
                "confidence": confidence,
                "reasoning": reasoning,
                "method": "llm",
            }
            
            # Cache the result
            self.cache.set(
                content=cache_key_content,
                response=result_dict,
                model=self.model_name,
                task_type="vertical_classification"
            )
            
            return result_dict
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {response_text}")
            return self._classify_with_keywords(text, file_name)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return self._classify_with_keywords(text, file_name)
    
    def _classify_with_keywords(self, text: str, file_name: str) -> Dict:
        """Fallback classification using keywords."""
        text_lower = text.lower()
        file_lower = file_name.lower()
        
        scores = {vertical: 0 for vertical in ["go", "legal", "judicial", "data", "scheme"]}
        
        # Check keywords
        for vertical, keywords in VERTICAL_KEYWORDS.items():
            for keyword in keywords:
                # Count occurrences
                count = text_lower.count(keyword)
                scores[vertical] += count
                
                # Bonus for filename match
                if keyword in file_lower:
                    scores[vertical] += 5
        
        # Find best match
        best_vertical = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[best_vertical] / max(total_score, 1)
        
        # If all scores are low, default to 'data'
        if scores[best_vertical] < 3:
            best_vertical = "data"
            confidence = 0.3
        
        logger.info(f"✓ Classified as '{best_vertical}' (confidence: {confidence:.2f}) [keyword-based]")
        
        return {
            "vertical": best_vertical,
            "confidence": min(confidence, 0.8),  # Cap confidence for keyword method
            "method": "keyword",
            "scores": scores,
        }


def classify_vertical(text: str, file_name: str = "") -> str:
    """
    Convenience function for vertical classification.
    
    Args:
        text: Document text
        file_name: Optional file name
        
    Returns:
        Vertical name (go, legal, judicial, data, or scheme)
    """
    classifier = VerticalClassifier()
    result = classifier.classify(text, file_name)
    return result["vertical"]