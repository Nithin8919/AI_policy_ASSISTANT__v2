"""
Smart LLM-Based Filter Adapter
===============================
Radical new approach: Use Gemini to dynamically map filter fields to actual Qdrant schema.

NO MORE CONFIG FILES. NO MORE MANUAL MAPPINGS.
The LLM figures it out automatically by inspecting Qdrant collections.

This is MUCH smarter than static config because:
1. Adapts automatically to schema changes
2. No manual maintenance
3. Works with any data structure
4. Self-documenting
"""

import os
import json
import logging
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
import google.generativeai as genai

logger = logging.getLogger(__name__)


class SmartFilterAdapter:
    """
    LLM-powered filter adapter that automatically maps query filters
    to actual Qdrant payload fields.
    
    Example:
        User filter: {"section": ["12"]}
        Qdrant has: "sections", "section", "mentioned_sections"
        
        LLM automatically maps to the best field(s) to search.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        """
        Initialize smart filter adapter.
        
        Args:
            qdrant_client: Qdrant client for schema inspection
        """
        self.qdrant_client = qdrant_client
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Cache schema for collections
        self.schema_cache = {}
        
        logger.info("✅ Smart filter adapter initialized")
    
    def inspect_collection_schema(self, collection_name: str) -> Dict[str, List[str]]:
        """
        Inspect Qdrant collection and extract actual payload field names.
        
        Args:
            collection_name: Collection to inspect
            
        Returns:
            Dict mapping field names to example values
        """
        # Check cache first
        if collection_name in self.schema_cache:
            return self.schema_cache[collection_name]
        
        try:
            # Get a few sample points
            results = self.qdrant_client.scroll(
                collection_name=collection_name,
                limit=10,
                with_payload=True
            )
            
            # Extract all field names from payloads
            field_names = set()
            field_examples = {}
            
            for point in results[0]:
                payload = point.payload
                for key, value in payload.items():
                    field_names.add(key)
                    if key not in field_examples:
                        field_examples[key] = str(value)[:100]  # Sample
            
            schema = {
                "fields": list(field_names),
                "examples": field_examples
            }
            
            # Cache it
            self.schema_cache[collection_name] = schema
            
            logger.info(f"📋 Inspected {collection_name}: {len(field_names)} fields found")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to inspect {collection_name}: {e}")
            return {"fields": [], "examples": {}}
    
    def adapt_filters(
        self,
        query_filters: Dict[str, List[str]],
        collection_name: str
    ) -> Dict[str, any]:
        """
        Use LLM to adapt query filters to actual Qdrant schema.
        
        Args:
            query_filters: User-specified filters (e.g., {"section": ["12"]})
            collection_name: Qdrant collection to query
            
        Returns:
            Adapted filters ready for Qdrant
        """
        if not query_filters:
            return {}
        
        # Get schema
        schema = self.inspect_collection_schema(collection_name)
        
        if not schema["fields"]:
            logger.warning(f"No schema found for {collection_name}")
            return query_filters  # Return as-is
        
        # Ask LLM to map filters
        prompt = f"""You are a database query adapter. Your job is to map user filter fields to actual database fields.

USER'S FILTER INTENT:
{json.dumps(query_filters, indent=2)}

ACTUAL DATABASE FIELDS IN COLLECTION "{collection_name}":
{json.dumps(schema["fields"], indent=2)}

FIELD EXAMPLES:
{json.dumps(schema["examples"], indent=2)}

TASK:
1. Map each user filter field to the BEST matching database field(s)
2. If a filter should check multiple fields (e.g., section, sections, mentioned_sections), return ALL relevant fields
3. Preserve the filter values exactly as given
4. If no match exists, omit that filter

Return ONLY valid JSON in this format:
{{
    "database_field_1": ["value1", "value2"],
    "database_field_2": ["value3"]
}}

Example:
User filter: {{"section": ["12"]}}
Database has: ["section", "sections", "mentioned_sections"]
Your response: {{"sections": ["12"], "mentioned_sections": ["12"]}}

Now map the user's filters:"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            adapted_filters = json.loads(response_text)
            
            logger.info(f"🎯 Adapted filters: {query_filters} → {adapted_filters}")
            return adapted_filters
            
        except Exception as e:
            logger.error(f"Filter adaptation failed: {e}")
            logger.warning("Falling back to original filters")
            return query_filters


# Global instance
_adapter_instance = None


def get_smart_filter_adapter(qdrant_client: QdrantClient) -> SmartFilterAdapter:
    """Get global smart filter adapter"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = SmartFilterAdapter(qdrant_client)
    return _adapter_instance