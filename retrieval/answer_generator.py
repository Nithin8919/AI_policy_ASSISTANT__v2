"""
Answer Generator - FIXED VERSION
=================================
Generates final answers with EXPLICIT citation instructions.

CRITICAL FIX: Strengthened prompts to ensure Gemini always generates citations.
"""

import logging
import os
from typing import List, Dict, Optional

# For API-key path (AI Studio)
import google.generativeai as genai
# For ADC/Vertex path
from google import genai as genai_client

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Generates final answers from retrieved context.
    Now with BATTLE-TESTED citation prompts!
    """
    
    def __init__(self):
        """Initialize answer generator"""
        # Allow opting out of Vertex even when project/ADC is configured
        disable_vertex = os.getenv("GOOGLE_DISABLE_VERTEX_AI", "").lower() in ("1", "true", "yes")
        genai_vertex_enabled = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() not in ("0", "false", "no")

        # Choose auth: OAuth/ADC (gcloud) or API key
        use_oauth = os.getenv("GOOGLE_USE_OAUTH", "").lower() in ("1", "true", "yes")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        self.client = None
        self.model = None
        self.model_name = "gemini-2.5-flash"
        self._llm_disabled = False

        if use_oauth and project_id and not disable_vertex and genai_vertex_enabled:
            # ADC path (requires `gcloud auth application-default login`)
            import google.auth
            try:
                # Use only valid cloud-platform scope
                creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                self.client = genai_client.Client(
                    vertexai=True,
                    project=project_id,
                    location=location,
                    credentials=creds,
                )
                logger.info("✅ Answer generator initialized with Vertex AI (ADC) using gemini-2.5-flash")
            except Exception as e:
                logger.warning(f"⚠️ ADC credentials not available: {e}. Falling back to API key if present.")
        
        if self.client is None:
            # API key path (AI Studio)
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                # Stay up but mark LLM disabled; backend can still run with retrieval only
                self._llm_disabled = True
                logger.warning(
                    "⚠️ No ADC credentials and no API key set. Answer generation LLM disabled; "
                    "retrieval will still run and return sources."
                )
            else:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info("✅ Answer generator initialized with API key using gemini-2.5-flash")
    
    def _normalize_year_query(self, query: str) -> str:
        """Normalize year queries to match academic year format (e.g., 2025 -> 2024-25)"""
        import re
        # Match standalone years like "2025", "2024"
        year_pattern = r'\b(20\d{2})\b'
        matches = re.findall(year_pattern, query)
        
        if matches:
            for year_str in matches:
                year = int(year_str)
                # Convert to academic year format
                academic_year = f"{year-1}-{str(year)[2:]}"
                # Add both formats to improve matching
                query = query + f" {academic_year}"
        
        return query
    
    def generate(
        self,
        query: str,
        results: List[Dict],
        mode: str = "qa",
        max_context_chunks: int = 5,
        external_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict:
        """
        Generate answer with proper citations.
        
        Args:
            query: User query
            results: Retrieved results
            mode: Query mode
            max_context_chunks: Max chunks to include
            external_context: Additional context (e.g. from uploaded files)
            conversation_history: Previous conversation turns for context
            
        Returns:
            Dict with answer, citations, bibliography
        """
        if not results and not external_context:
            return {
                "answer": "I couldn't find relevant information to answer your query.",
                "citations": [],
                "bibliography": [],
                "confidence": 0.0
            }
        
        # Normalize year query for better matching with academic year data
        normalized_query = self._normalize_year_query(query)
        
        # Limit context
        context_results = results[:max_context_chunks]
        
        # Format context with doc numbers
        context_text = self._format_context(context_results)
        
        # Calculate max score to detect weak retrieval
        # CRITICAL FIX: Use raw_score from metadata if available (before normalization)
        # V3 retrieval normalizes scores to 0-1, making weak detection broken
        max_score = 0.0
        if results:
            # Try to get raw_score from metadata first (preserved before normalization)
            raw_scores = []
            for r in results:
                metadata = r.get('metadata', {})
                raw_score = metadata.get('raw_score')
                if raw_score is not None:
                    raw_scores.append(raw_score)
                else:
                    # Fallback to current score if raw_score not available
                    raw_scores.append(r.get('score', 0))
            
            if raw_scores:
                max_score = max(raw_scores)
            else:
                # Fallback: use normalized scores
                max_score = max(r.get('score', 0) for r in results)
        
        # Query intent detection: Check if query asks for policy design, strategy, or global models
        policy_design_keywords = [
            'recommend', 'suggest', 'strategy', 'strategic', 'plan', 'planning',
            'singapore', 'finland', 'estonia', 'international', 'global', 'world-class',
            'how to improve', 'fastest', 'effective intervention',
            'policy design', 'intervention', 'approach', 'framework',
            'best practice', 'innovation', 'creative solution'
        ]
        
        query_lower = normalized_query.lower()
        is_policy_design_query = any(keyword in query_lower for keyword in policy_design_keywords)
        
        # Weak retrieval threshold (0.7 chosen as safe cutoff - only use strict mode for highly relevant docs)
        # For vector similarity scores, 0.7 is a reasonable threshold (cosine similarity typically 0.5-0.9 for good matches)
        # If score is lower OR if it's a policy design query, we allow general knowledge fallback
        is_weak_retrieval = max_score < 0.7 or is_policy_design_query
        
        if is_policy_design_query:
            logger.info(f"🌍 Policy design query detected, activating mixed mode (max_score={max_score:.2f})")
        elif is_weak_retrieval:
            logger.info(f"📉 Weak retrieval detected (max_score={max_score:.2f} < 0.7), activating mixed mode")
        
        
        # Detect if internet results are present
        has_internet_results = any(r.get('vertical') == 'internet' for r in results)
        
        # Build prompt based on mode (use normalized query for better context)
        prompt = self._build_prompt(normalized_query, context_text, mode, external_context, conversation_history, is_weak_retrieval=is_weak_retrieval, has_internet_results=has_internet_results)
        
        # Generate answer with optimized config based on mode
        try:
            if self._llm_disabled and not self.client and not self.model:
                # Fallback: return a structured response using retrieved sources only
                top_sources = [r.get("title") or r.get("source") or "source" for r in context_results]
                answer_text = "LLM is disabled (no Vertex/API key). Showing top retrieved sources:\n- " + "\n- ".join(top_sources or ["No sources found"])
                citations = self._extract_citations(answer_text)
                bibliography = []
                return {
                    "answer": answer_text,
                    "citations": citations,
                    "bibliography": bibliography,
                    "confidence": max_score if results else 0.0
                }

            # Optimize generation config based on mode for better quality
            mode_configs = {
                'qa': {
                    'temperature': 0.2,  # Lower for factual accuracy
                    'max_output_tokens': 4000,  # Increased from 2000 to prevent truncation
                    'top_p': 0.95,
                    'top_k': 40
                },
                'deep_think': {
                    'temperature': 0.4,  # Balanced for analysis
                    'max_output_tokens': 4000,  # More tokens for comprehensive analysis
                    'top_p': 0.95,
                    'top_k': 40
                },
                'brainstorm': {
                    'temperature': 0.6,  # Higher for creative ideas
                    'max_output_tokens': 3000,
                    'top_p': 0.95,
                    'top_k': 40
                }
            }
            
            # Get config for mode, default to QA if mode not found
            gen_config = mode_configs.get(mode, mode_configs['qa'])
            
            # Add safety settings to prevent blocking
            # Import safety settings types if using Vertex AI
            safety_settings = None
            if self.client:
                try:
                    from google.genai import types
                    safety_settings = [
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="OFF"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="OFF"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="OFF"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="OFF"
                        )
                    ]
                except ImportError:
                    # Fallback if types not available
                    pass
            
            if self.client:
                # Vertex AI path (ADC)
                # Format: contents must have "text" key in parts
                config_dict = {
                    "temperature": gen_config.get('temperature', 0.2),
                    "max_output_tokens": gen_config.get('max_output_tokens', 4000),
                    "top_p": gen_config.get('top_p', 0.95),
                    "top_k": gen_config.get('top_k', 40),
                }
                if safety_settings:
                    config_dict["safety_settings"] = safety_settings
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                    config=config_dict,
                )
                # Check for truncation or blocking
                answer_text = response.text or ""
                logger.info(f"📝 Generated answer: {len(answer_text)} chars")
                
                # Track if we've already retried to prevent double retries
                has_retried = False
                
                # Check finish_reason to detect truncation
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        # Handle both enum and string formats
                        finish_reason_str = str(finish_reason)
                        if hasattr(finish_reason, 'name'):
                            finish_reason_str = finish_reason.name
                        
                        if "MAX_TOKENS" in finish_reason_str or finish_reason_str == "MAX_TOKENS":
                            logger.warning(f"⚠️ Response truncated due to MAX_TOKENS limit. Answer length: {len(answer_text)} chars")
                            # Retry with higher token limit if answer is suspiciously short
                            if len(answer_text) < 500 and mode == 'qa' and not has_retried:
                                logger.info("🔄 Retrying with higher token limit due to short truncated answer")
                                config_dict["max_output_tokens"] = 8000
                                try:
                                    retry_response = self.client.models.generate_content(
                                        model=self.model_name,
                                        contents=[{"role": "user", "parts": [{"text": prompt}]}],
                                        config=config_dict,
                                    )
                                    retry_text = retry_response.text or ""
                                    if len(retry_text) > len(answer_text):
                                        answer_text = retry_text
                                        has_retried = True
                                        logger.info(f"✅ Retry successful: {len(answer_text)} chars")
                                except Exception as e:
                                    logger.warning(f"⚠️ Retry failed: {e}, using original answer")
                        elif "SAFETY" in finish_reason_str or "RECITATION" in finish_reason_str:
                            logger.warning(f"⚠️ Response blocked by safety filter: {finish_reason_str}")
                            # Try to get partial content if available
                            if hasattr(candidate, 'content') and candidate.content:
                                if hasattr(candidate.content, 'parts'):
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            answer_text = part.text
                                            break
                
                # Additional check: If answer is suspiciously short (< 500 chars) and doesn't end properly, retry
                # Only retry if we haven't already retried above
                if len(answer_text) < 500 and mode == 'qa' and answer_text and not has_retried:
                    # Check if answer ends mid-sentence (likely truncated)
                    if not answer_text.rstrip().endswith(('.', '!', '?', ':', ';')) and not answer_text.rstrip().endswith(']'):
                        logger.warning(f"⚠️ Answer appears truncated (ends mid-sentence): {len(answer_text)} chars")
                        logger.info("🔄 Retrying with higher token limit due to suspicious truncation")
                        config_dict["max_output_tokens"] = 8000
                        try:
                            retry_response = self.client.models.generate_content(
                                model=self.model_name,
                                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                                config=config_dict,
                            )
                            retry_text = retry_response.text or ""
                            if len(retry_text) > len(answer_text) * 1.5:  # Only use if significantly longer
                                answer_text = retry_text
                                has_retried = True
                                logger.info(f"✅ Retry successful: {len(answer_text)} chars")
                        except Exception as e:
                            logger.warning(f"⚠️ Retry failed: {e}, using original answer")
            else:
                # API key path - add safety settings if supported
                try:
                    import google.generativeai.types as genai_types
                    safety_config = [
                        {
                            "category": genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            "threshold": genai_types.HarmBlockThreshold.BLOCK_NONE,
                        },
                        {
                            "category": genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            "threshold": genai_types.HarmBlockThreshold.BLOCK_NONE,
                        },
                        {
                            "category": genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            "threshold": genai_types.HarmBlockThreshold.BLOCK_NONE,
                        },
                        {
                            "category": genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            "threshold": genai_types.HarmBlockThreshold.BLOCK_NONE,
                        },
                    ]
                    gen_config['safety_settings'] = safety_config
                except (ImportError, AttributeError):
                    # Fallback if safety settings not available
                    pass
                
                response = self.model.generate_content(prompt, generation_config=gen_config)
                # API responses can also come back with None; normalize for downstream processing
                answer_text = response.text or ""
                logger.info(f"📝 Generated answer: {len(answer_text)} chars")
                
                # Track if we've already retried to prevent double retries
                has_retried = False
                
                # Check for truncation in API response
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = str(candidate.finish_reason)
                        if "MAX_TOKENS" in finish_reason or finish_reason == "MAX_TOKENS":
                            logger.warning(f"⚠️ Response truncated due to MAX_TOKENS limit. Answer length: {len(answer_text)} chars")
                            # Retry with higher token limit if answer is suspiciously short
                            if len(answer_text) < 500 and mode == 'qa' and not has_retried:
                                logger.info("🔄 Retrying with higher token limit due to short truncated answer")
                                gen_config['max_output_tokens'] = 8000
                                try:
                                    retry_response = self.model.generate_content(prompt, generation_config=gen_config)
                                    retry_text = retry_response.text or ""
                                    if len(retry_text) > len(answer_text):
                                        answer_text = retry_text
                                        has_retried = True
                                        logger.info(f"✅ Retry successful: {len(answer_text)} chars")
                                except Exception as e:
                                    logger.warning(f"⚠️ Retry failed: {e}, using original answer")
                        elif "SAFETY" in finish_reason or "RECITATION" in finish_reason:
                            logger.warning(f"⚠️ Response blocked by safety filter: {finish_reason}")
                
                # Additional check: If answer is suspiciously short (< 500 chars) and doesn't end properly, retry
                # Only retry if we haven't already retried above
                if len(answer_text) < 500 and mode == 'qa' and answer_text and not has_retried:
                    # Check if answer ends mid-sentence (likely truncated)
                    if not answer_text.rstrip().endswith(('.', '!', '?', ':', ';')) and not answer_text.rstrip().endswith(']'):
                        logger.warning(f"⚠️ Answer appears truncated (ends mid-sentence): {len(answer_text)} chars")
                        logger.info("🔄 Retrying with higher token limit due to suspicious truncation")
                        gen_config['max_output_tokens'] = 8000
                        try:
                            retry_response = self.model.generate_content(prompt, generation_config=gen_config)
                            retry_text = retry_response.text or ""
                            if len(retry_text) > len(answer_text) * 1.5:  # Only use if significantly longer
                                answer_text = retry_text
                                has_retried = True
                                logger.info(f"✅ Retry successful: {len(answer_text)} chars")
                        except Exception as e:
                            logger.warning(f"⚠️ Retry failed: {e}, using original answer")
            
            # POST-GENERATION CHECK: Detect refusal phrases and auto-retry with mixed mode
            refusal_phrases = [
                "don't have the required information",
                "don't have the information",
                "do not have the required information",
                "do not have the information",
                "doesn't contain the required information",
                "does not contain the required information",
                "cannot find",
                "not found in the provided documents",
                "not available in the provided documents",
                "not present in the provided documents",
                "insufficient information",
                "lack the necessary information",
                "unable to find",
                "no information available"
            ]
            
            answer_lower = answer_text.lower()
            has_refusal = any(phrase in answer_lower for phrase in refusal_phrases)
            
            # If we detect refusal AND we're not already in weak-retrieval mode, retry with mixed mode
            if has_refusal and not is_weak_retrieval and not is_policy_design_query:
                logger.warning(f"⚠️ Detected refusal phrase in answer, retrying with mixed mode (max_score={max_score:.2f})")
                # Retry with weak retrieval mode enabled
                retry_prompt = self._build_prompt(
                    normalized_query, context_text, mode, external_context, 
                    conversation_history, is_weak_retrieval=True, has_internet_results=has_internet_results
                )
                
                try:
                    if self.client:
                        retry_response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=[{"role": "user", "parts": [{"text": retry_prompt}]}],
                            config=gen_config,
                        )
                        answer_text = retry_response.text or answer_text
                    else:
                        retry_response = self.model.generate_content(retry_prompt, generation_config=gen_config)
                        answer_text = retry_response.text or answer_text
                    
                    logger.info("✅ Retry with mixed mode succeeded")
                except Exception as e:
                    logger.warning(f"⚠️ Retry with mixed mode failed: {e}, using original answer")
            
            # Extract citations
            citations = self._extract_citations(answer_text)
            
            # Build bibliography
            bibliography = self._build_bibliography(context_results)
            
            return {
                "answer": answer_text,
                "citations": citations,
                "bibliography": bibliography,
                "confidence": self._estimate_confidence(answer_text, citations)
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ Error generating answer: {e}")
            
            # If Vertex AI path hit permission issues, disable and fall back to rule-based summary
            if self.client and ("403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str):
                logger.warning("Vertex AI permission denied. Disabling client and falling back to rule-based summary.")
                self.client = None
                return self._fallback_rule_based(context_results)
            
            # If API-key path or other failure, fall back to rule-based summary
            return self._fallback_rule_based(context_results)
    
    def _format_context(self, results: List[Dict]) -> str:
        """
        Format context with clear doc numbers and GO NUMBERS EXPLICIT.
        
        CRITICAL FIX: Extract and prominently display GO numbers
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            # Get basic info
            text = result.get("text", "") or result.get("content", "")
            vertical = result.get("vertical", "")
            
            # Get metadata for GO numbers and source info
            metadata = result.get("metadata", {})
            
            # CRITICAL FIX: Extract GO number from multiple possible fields
            go_number = None
            possible_go_fields = ['go_number', 'go_num', 'go_id', 'doc_id', 'source', 'chunk_id']
            
            for field in possible_go_fields:
                value = metadata.get(field) or result.get(field)
                if value and isinstance(value, str):
                    # Check if this looks like a GO number
                    if any(pattern in value.lower() for pattern in ['ms', 'rt', 'go', '20']):
                        go_number = value
                        break
            
            # If still no GO number, try to extract from text
            if not go_number and text:
                import re
                go_matches = re.search(r'(?:G\.O\.?|GO)[\s\.]?(?:MS|RT)[\s\.]?No[\s\.]?(\d+)', text, re.IGNORECASE)
                if go_matches:
                    go_number = f"G.O.MS.No.{go_matches.group(1)}"
            
            # Get source for fallback
            source = metadata.get("source", go_number or result.get("chunk_id", "Unknown"))
            
            # CRITICAL: Format with GO number prominently displayed
            if go_number:
                doc_header = f"Doc {i}: {go_number}"
                if vertical:
                    doc_header += f" ({vertical})"
            else:
                doc_header = f"Doc {i}: {source}"
                if vertical:
                    doc_header += f" ({vertical})"
            
            # Add year if available
            year = metadata.get("year")
            if year:
                doc_header += f" - Year: {year}"
            
            context_parts.append(f"""
{doc_header}
Content: {text[:800]}{"..." if len(text) > 800 else ""}
""")
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, mode: str, external_context: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None, is_weak_retrieval: bool = False, has_internet_results: bool = False) -> str:
        """
        Build prompt with EXPLICIT citation instructions.
        
        CRITICAL FIX: Uploaded files are now PRIMARY SOURCE, database results are supporting.
        """
        # Format conversation history if provided
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            # Limit to last 5 turns (10 messages)
            recent_history = conversation_history[-10:]
            history_parts = []
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("CONVERSATION HISTORY (for context)")
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("")
            
            for msg in recent_history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    history_parts.append(f"User: {content}")
                elif role == 'assistant':
                    history_parts.append(f"Assistant: {content}")
                    history_parts.append("")  # Blank line after assistant response
            
            history_parts.append("-----------------------------------------------------------")
            history_parts.append("")
            history_text = "\n".join(history_parts)

        # Build context section with uploaded files FIRST (as primary source)
        if external_context:
            full_context = f"""
═══════════════════════════════════════════════════════════════
🔵 PRIMARY SOURCE - UPLOADED FILES
═══════════════════════════════════════════════════════════════

IMPORTANT: These are files uploaded by the user. Use this content as your PRIMARY source 
for answering questions. The user's question is most likely about THIS content.

{external_context}

═══════════════════════════════════════════════════════════════
📚 SUPPORTING DOCUMENTS FROM DATABASE
═══════════════════════════════════════════════════════════════

These are additional relevant documents from the database. Use these to:
- Find related information mentioned in the uploaded files
- Provide supporting context
- Answer questions about connections and relationships

{context}
"""
        else:
            # No uploaded files - use database results as primary source
            full_context = f"""
Context Documents:
{context}
"""

        if mode == "qa":
            # Select instructions based on whether a file is uploaded
            if external_context:
                # ---------------- FILE UPLOADED MODE ----------------
                instructions = """1. **PRIMARY SOURCE: UPLOADED FILES**: 
   - You have been provided with one or more uploaded files. Use these as your **PRIMARY** source.
   - Answer the question specifically based on the content of these files.
   - **CROSS-REFERENCING**: If the user asks about related documents or circulars, search for them in the **SUPPORTING DOCUMENTS** from the database to provide a complete answer.
   - **SYNTHESIS**: Combine insights from the uploaded file and supporting database documents.
   - **CITATION**: Cite the uploaded file as [UPLOADED] or by its name."""
            else:
                # ---------------- NO FILE MODE ----------------
                # Check for weak retrieval fallback
                if is_weak_retrieval:
                     instructions = """1. **SOURCE: MIXED (DOCUMENTS + GENERAL KNOWLEDGE)**:
   - **Use provided documents when relevant, but if they lack the needed details, rely on global research and best practices.**
   - **Do not reply that the documents don't contain the information.**
   - **When the question explicitly asks for global inspiration or international models** (e.g., Singapore, Finland, Estonia), **prioritize global best practices** and use the documents only to contextualize Andhra Pradesh's starting point.
   - **Do not restrict answers to the documents when the user asks for global policy design.**
   - **STRICT ANTI-FILE-BEGGING**: NEVER ask for files."""
                else:
                    instructions = """1. **SOURCE: DATABASE & INTERNET**: 
   - Answer using the text from the **SUPPORTING DOCUMENTS** provided below.
   - **STRICT ANTI-FILE-BEGGING RULE**: 
     - **NEVER** ask the user to upload a file.
     - **NEVER** say "I need access to your file" or "Please upload the document".
     - If the user uses words like "our", "my", "current", or "this" (e.g., "our learning outcomes"), **ASSUME** they are referring to the general state of affairs described in the internal documents or general knowledge.
     - **DEFAULT TO DATABASE**: Always answer based on the information you have. If specific data is missing, state what *is* available in the documents."""

            return f"""You are a policy assistant providing precise answers from official documents.

CRITICAL INSTRUCTIONS FOR ANSWERING:

{instructions}



CITATION RULES:

1. **When to cite**: If a sentence directly uses information from the retrieved documents, cite it with [1], [2], etc.
2. **When NOT to cite**: If the sentence is based on general global knowledge or educational best practices, do NOT cite anything.
3. **Never fabricate citations**: Only cite when the fact truly came from a retrieved document. NEVER attach a citation unless the information came from the documents below.
4. **Prioritize relevance**: If using general knowledge, ensure recommendations are logically related to Andhra Pradesh, Indian education systems, or similar high-performing models (Singapore, Finland, Estonia, etc.).
5. Place citations IMMEDIATELY after each relevant sentence that uses document information
6. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
7. If info comes from multiple documents, cite all: [1][2][3]
8. The numbers correspond to "Doc #:" in the context below

**FALLBACK FOR WEAK RETRIEVAL:**
If the retrieved documents do not contain enough information to answer the question fully, expand the answer using general educational best practices and global policy knowledge. State the general knowledge plainly without requiring citations. Never say that the documents don't contain the information.

SPECIAL INSTRUCTIONS FOR GOVERNMENT ORDERS AND UPLOADED FILES:

9. When analyzing uploaded GO files, extract:
   - GO numbers (e.g., G.O.MS.No.XXX)
   - Departments mentioned
   - Dates and years
   - Key subjects and topics
   - References to other GOs or policies
   
10. When asked about "related GOs" or similar questions:
   - Look for GO numbers, departments, or topics in the uploaded file
   - Find matching information in the supporting documents
   - Explain the nature of the relationship (e.g., "amends", "cites", "supersedes", "clarifies").
   - **MANDATORY**: When mentioning a related GO, **ALWAYS briefly summarize its subject or purpose** (e.g., "G.O.Ms.No. 1, which deals with Service Rules..."). Do not just list the number.
   - **CRITICAL: EXPLAIN THE CHANGE**: If a GO amends or supersedes another, clearly state:
     * What was the old provision/rule?
     * What is the new provision/rule?
     * Why was the change made?
   - "G.O.Ms.No. 123 amends G.O.Ms.No. 1 by changing [X] to [Y]..."

11. **SPECIAL INSTRUCTIONS FOR SERVICE RULES AND ACTS**:
    - If the user asks about a specific **Service Rule**, **Act**, or **Section**, you MUST:
      - Cite the **EXACT RULE NUMBER** or **SECTION** (e.g., "Rule 10(a)", "Section 12(1)(c)").
      - Quote or closely paraphrase the **official text** of the rule.
      - Explain the **REASONING** or "Why" behind the rule based on the document text.
      - **DO NOT** give a vague summary. Be legally precise.

12. **CRITICAL: HANDLING TABLES, STATISTICS, AND NUMERICAL DATA**:
    - **TABLES ARE VALID SOURCES**: If you see tables with numbers, treat them as authoritative data.
    - **INTERPRETATION REQUIRED**: When you see table data:
      * Look at column headers and row labels to understand what the numbers represent
      * Check surrounding text for context (e.g., "UDISE 2024-25", "Teacher Statistics")
      * Extract the specific numbers that answer the question
      * Explain what the numbers mean in plain language
    - **UDISE/Statistical Reports**: 
      * Academic year "2024-25" should match queries for "2025" or "2024"
      * Tables showing teacher counts, enrollment, infrastructure are PRIMARY sources
      * Even if table lacks descriptive text, infer meaning from structure
    - **Example**: If you see a table with rows like "Total Teachers | 45,231" under a UDISE header, 
      you should answer: "According to UDISE+ 2024-25 data, there are 45,231 teachers [1]."
    - **BE CONFIDENT**: Don't say "I cannot find the information" if tables contain the data - interpret them!


9. Format GO numbers as shown in the source: "G.O.MS.No.XXX" or exact format from document

GOOD EXAMPLE:
"According to **Rule 15 of the AP State Service Rules** [1], transfers are prohibited during the academic year to ensure continuity of instruction [2]. The specific provision states that 'no teacher shall be transferred...' [1]."
"The uploaded file is G.O.MS.No.190 (2022) from the Education Department regarding teacher transfers [UPLOADED]. Related orders include G.O.MS.No.155 (2022) on educational policies [1] and G.O.MS.No.203 (2023) on the same topic [2]."

{history_text}

{full_context}

Question: {query}

Provide a concise, accurate answer focusing on uploaded content (if present) with mandatory citations:
"""
        
        elif mode == "deep_think":
            # Select instructions for Deep Think based on file presence and internet results
            if has_internet_results:
                 instructions = """1. **SOURCE: DATABASE + INTERNET**:
   - **INTEGRATED ANALYSIS**: Synthesize information from BOTH internal database documents and the provided Internet search results.
   - **GLOBAL CONTEXT**: Use the Internet results as the PRIMARY source for international examples (e.g., Singapore, Finland), global best practices, and external data.
   - **LOCAL CONTEXT**: Use the internal database documents to describe the current Andhra Pradesh/India context.
   - **COMPARATIVE APPROACH**: actively compare local policies (from database) with global models (from internet)."""
            elif external_context:
                instructions = """1. **PRIMARY SOURCE: UPLOADED FILES**: 
   - Analyze the UPLOADED FILES as your **PRIMARY** source for the deep dive.
   - Extract key provisions, entities, and policy logic from these files.
   - **CONTEXTUALIZATION**: Use supporting documents from the database to validate or expand on findings from the uploaded file.
   - **CITATION**: Cite findings from the uploaded file clearly."""
            else:
                instructions = """1. **SOURCE: DATABASE**: 
   - Analyze using the context documents from the database.
   - **STRICT ANTI-FILE-BEGGING**: 
     - **NEVER** ask the user to upload a file.
     - If the user implies "our" or "my" context regarding data/outcomes, **ASSUME** they mean the general system state described in the database documents.
     - Provide a comprehensive analysis based ONLY on available documents."""

            return f"""You are a policy analyst providing comprehensive analysis with legal citations.

CRITICAL INSTRUCTIONS FOR ANSWERING:

{instructions}

CITATION RULES:
1. **When to cite**: If a sentence directly uses information from the retrieved documents, cite it with [1], [2], etc.
2. **When NOT to cite**: If the sentence is based on general global knowledge or educational best practices, do NOT cite anything.
3. **Never fabricate citations**: Only cite when the fact truly came from a retrieved document. NEVER attach a citation unless the information came from the documents below.
4. **Prioritize relevance**: If using general knowledge, ensure recommendations are logically related to Andhra Pradesh, Indian education systems, or similar high-performing models (Singapore, Finland, Estonia, etc.).
5. Place citations IMMEDIATELY after each sentence that uses document information
6. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
7. If analyzing multiple sources, cite all relevant ones: [1][2][3]
8. The numbers correspond to "Doc #:" in the context below

**FALLBACK FOR WEAK RETRIEVAL:**
If the retrieved documents do not contain enough information to answer the question fully, expand the answer using general educational best practices and global policy knowledge. State the general knowledge plainly without requiring citations. Never say that the documents don't contain the information.

Structure your analysis:
- Overview (cite document-backed claims with bracketed numbers, state general knowledge plainly)
- Key provisions from uploaded files (if present)
- Legal framework (cite document-backed claims with bracketed numbers)
- Implications (cite document-backed claims with bracketed numbers, enhance with general knowledge where needed)
- Related policies and connections (cite document-backed claims with bracketed numbers; **ALWAYS summarize the subject/purpose of each related GO mentioned**)

**CRITICAL: INTERPRETING TABLES AND STATISTICAL DATA**:
- Tables with numbers are PRIMARY sources for statistical questions
- Extract exact figures from tables and cite them
- Infer context from table headers, surrounding text, and document metadata
- Academic year formats (e.g., "2024-25") match queries for individual years (e.g., "2025", "2024")
- Be confident in interpreting structured data - don't claim information is missing if tables contain it


{history_text}

{full_context}

Question: {query}

Provide comprehensive policy analysis with mandatory bracketed citations:
"""
        
        else:  # brainstorm
            # Select instructions for Brainstorm based on file presence
            if external_context:
                instructions = """1. **BASE: UPLOADED FILES**: 
   - Use the uploaded content to understand the specific context/problem.
   - Suggest innovations that directly address issues found in the uploaded file."""
            else:
                instructions = """1. **BASE: DATABASE CONTEXT**: 
   - Use context documents to understand the existing landscape.
   - **STRICT ANTI-FILE-BEGGING**: 
     - **NEVER** ask for filenames or uploads.
     - Generate ideas based on the general context provided in the database."""

            return f"""You are a creative policy advisor suggesting innovative approaches.

CRITICAL INSTRUCTIONS FOR ANSWERING:

{instructions}

CITATION RULES FOR BRAINSTORM MODE:

1. **When to cite**: When referencing existing policies, examples, or approaches from the retrieved documents, cite using bracketed numbers
2. **When NOT to cite**: New suggestions, innovations, and general educational best practices do NOT need citations
3. **Never fabricate citations**: Only cite when the reference truly came from a retrieved document
4. **Prioritize relevance**: Ensure all suggestions (cited or not) are logically related to Andhra Pradesh, Indian education systems, or similar high-performing models (Singapore, Finland, Estonia, etc.)
5. Place citations after each reference to existing policy/practice
6. Use bracketed format: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
7. Clearly distinguish between existing approaches (cite with bracketed numbers) and your new suggestions (no citation needed)

**FALLBACK FOR WEAK RETRIEVAL:**
If the retrieved documents do not contain sufficient policy context, freely draw from global educational best practices, innovation frameworks, and world-class education systems to generate suggestions. No citations needed for general knowledge.

Example:
"Current policy focuses on infrastructure [1]. However, we could also consider:
- Teacher training programs using peer observation models (inspired by lesson study in Japan)
- Community engagement initiatives similar to Finland's parent participation framework"


{history_text}

{full_context}

Question: {query}

Suggest innovative approaches, citing existing policies with bracketed numbers where relevant:
"""
    
    def _extract_citations(self, text: Optional[str]) -> List[str]:
        """
        Extract citation numbers from text (bracketed format).
        
        Returns:
            List of cited doc numbers (e.g., ["1", "2", "3"])
        """
        import re
        
        if not text:
            return []
        
        # Pattern: [1] [2] [3] etc.
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        
        return sorted(set(matches), key=lambda x: int(x))
    
    def _build_bibliography(self, results: List[Dict]) -> List[Dict]:
        """
        Build bibliography from results.
        
        FIXED: Use correct result structure - data is directly on result, not in 'payload'
        
        Returns:
            List of bibliography entries
        """
        bibliography = []
        
        for i, result in enumerate(results, 1):
            # FIXED: Get metadata from correct location
            metadata = result.get("metadata", {})
            vertical = result.get("vertical", "")
            
            # Extract URL from multiple locations (critical for internet results)
            url = (
                result.get('url') or 
                metadata.get('url') or 
                metadata.get('source_url') or
                None
            )
            
            # For internet results, use title and URL
            if vertical == "internet" and url:
                source = metadata.get("title") or metadata.get("source") or url
            else:
                source = metadata.get("source", result.get("chunk_id", "Unknown Source"))
            
            entry = {
                "number": i,
                "source": source,
                "vertical": vertical,
                "doc_type": metadata.get("doc_type", ""),
                "year": metadata.get("year", ""),
                "url": url  # Always include URL if available
            }
            
            # Add vertical-specific fields from metadata
            if vertical == "legal":
                entry["section"] = metadata.get("section", "")
            elif vertical == "go":
                entry["go_number"] = metadata.get("go_number", "")
            elif vertical == "judicial":
                entry["case_number"] = metadata.get("case_number", "")
            elif vertical == "internet":
                # For internet, add title if available
                if metadata.get("title"):
                    entry["title"] = metadata.get("title")
            
            bibliography.append(entry)
        
        return bibliography
    
    def _estimate_confidence(self, answer: str, citations: List[str]) -> float:
        """
        Estimate confidence based on answer quality.
        
        Returns:
            Confidence score 0-1
        """
        # Base confidence
        confidence = 0.5
        
        # Boost if has citations
        if citations:
            confidence += 0.3
        
        # Boost if answer is substantial
        if len(answer or "") > 200:
            confidence += 0.1
        
        # Boost if has multiple citations
        if len(citations) >= 3:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _fallback_rule_based(self, context_results: List[Dict]) -> Dict:
        """
        Fallback summarization when LLM is unavailable (e.g., 403 / no API key).
        """
        if not context_results:
            return {
                "answer": "I couldn't generate the answer because the model is unavailable and no documents were retrieved.",
                "citations": [],
                "bibliography": [],
                "confidence": 0.0,
            }

        bullets = []
        for i, res in enumerate(context_results, 1):
            title = res.get("title") or res.get("doc_id") or f"Document {i}"
            snippet = res.get("summary") or res.get("text") or res.get("content") or ""
            snippet = snippet.strip().replace("\n", " ")
            if len(snippet) > 220:
                snippet = snippet[:220].rstrip() + "..."
            bullets.append(f"- [{i}] {title}: {snippet}")

        answer_text = "Model access failed; providing a direct summary from retrieved documents:\n" + "\n".join(bullets)
        citations = [str(i) for i in range(1, len(context_results) + 1)]
        bibliography = self._build_bibliography(context_results)

        return {
            "answer": answer_text,
            "citations": citations,
            "bibliography": bibliography,
            "confidence": 0.2 if context_results else 0.0,
        }
    
    # Backward compatibility aliases
    def generate_qa_answer(self, query: str, results: List[Dict], max_tokens: int = 500) -> Dict:
        """Alias for QA mode generation (backward compatibility)"""
        return self.generate(query, results, "qa", max_context_chunks=5)
    
    def generate_deep_think_answer(self, query: str, results: List[Dict], max_tokens: int = 3000) -> Dict:
        """Alias for Deep Think mode generation (backward compatibility)"""
        return self.generate(query, results, "deep_think", max_context_chunks=20)
    
    def generate_brainstorm_answer(self, query: str, results: List[Dict], max_tokens: int = 2000) -> Dict:
        """Alias for Brainstorm mode generation (backward compatibility)"""
        return self.generate(query, results, "brainstorm", max_context_chunks=15)


# Global instance
_generator_instance = None


def get_answer_generator() -> AnswerGenerator:
    """Get global answer generator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AnswerGenerator()
    return _generator_instance


# Export
__all__ = ["AnswerGenerator", "get_answer_generator"]