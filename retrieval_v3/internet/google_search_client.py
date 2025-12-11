import logging
import os
from typing import List, Dict, Optional, Any
from google import genai
from google.genai import types
import concurrent.futures
import time

logger = logging.getLogger(__name__)

class GoogleSearchClient:
    """
    Client for Google Search using the google.genai SDK.
    Adopts the user's preferred implementation style using Vertex AI and streaming.
    """

    def _is_international_query(self, query: str) -> bool:
        """Heuristic: does the user explicitly want international patterns?"""
        q = query.lower()
        international_keywords = [
            "international", "global", "world", "overseas",
            "singapore", "finland", "estonia", "uk", "usa", "us",
            "canada", "australia", "philippines", "japan", "korea",
            "germany", "france", "europe", "oecd", "unicef", "unesco"
        ]
        return any(k in q for k in international_keywords)

    def _filter_results(self, query: str, results: list[dict]) -> list[dict]:
        """
        Prefer India/AP government domains unless the query explicitly asks for international context.
        """
        if self._is_international_query(query):
            return results

        allowed_domains = [
            "ap.gov.in",
            "gov.in",
            ".nic.in",
            ".in",
        ]

        filtered = []
        for r in results:
            url = (r.get("url") or r.get("source") or "").lower()
            if any(dom in url for dom in allowed_domains):
                filtered.append(r)

        # If we filtered everything out, fall back to originals to avoid empty results.
        if filtered:
            logger.info(f"🌐 Filtered internet results to {len(filtered)}/{len(results)} India/AP domains")
            return filtered

        logger.info("🌐 No India/AP domains found; returning unfiltered internet results")
        return results

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google Search Client.

        Auth strategy (API-key-free):
        - Try Vertex AI via OAuth/ADC when a project is set and not explicitly disabled.
        - If Vertex AI is unavailable or permission-denied, internet search is disabled (no API key fallback).
        """
        # Optional project/location for Vertex AI
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        # Default to us-central1 because Gemini 2.5 is available there; some regions return 404
        self.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.use_vertex_ai = False
        self.client = None

        # Explicit opt-out flag to skip Vertex AI
        disable_vertex = os.environ.get("GOOGLE_DISABLE_VERTEX_AI", "").lower() in {"1", "true", "yes"}
        # Also respect global GENAI flag to skip Vertex
        genai_vertex_enabled = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() not in {"0", "false", "no"}
        if not genai_vertex_enabled:
            disable_vertex = True

        # Try Vertex AI if a project is configured and not disabled
        if self.project_id and not disable_vertex:
            try:
                logger.info(
                    f"Initializing GoogleSearchClient with Vertex AI (project={self.project_id}, "
                    f"location={self.location})"
                )
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
                self.use_vertex_ai = True
                logger.info("✅ Initialized GoogleSearchClient with Vertex AI (ADC/gcloud)")
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Vertex AI initialization failed: {e}")
                # Detect permission denied and disable Vertex AI for this process
                if "403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str:
                    logger.warning("Vertex AI permission denied (403). Internet search will be disabled (no API key fallback).")
                else:
                    logger.warning("Vertex AI unavailable. Internet search will be disabled (no API key fallback).")
                self.use_vertex_ai = False
                self.client = None
        else:
            logger.info("Vertex AI disabled via config or missing project. Internet search will be disabled (no API key fallback).")

        # Default model name
        self.model = "gemini-2.5-flash"
        
        # Initialize query rewriter for search optimization
        try:
            from retrieval_v3.query_understanding.query_rewriter import QueryRewriter
            self.query_rewriter = QueryRewriter()
            logger.info("✅ Query rewriter initialized for internet search optimization")
        except Exception as e:
            logger.warning(f"Query rewriter initialization failed: {e}, will use raw queries")
            self.query_rewriter = None

    def search(self, query: str, max_results: int = 5, timeout: float = 5.0) -> List[Dict[str, str]]:
        """
        Perform an internet search and return structured results.
        OPTIMIZED for speed: non-streaming, reduced timeout, minimal tokens.
        
        Args:
            query: Original user query
            max_results: Maximum number of results to return (default: 5)
            timeout: Timeout in seconds for the search operation (default: 5.0, REDUCED for speed)
            
        Returns:
            List of search results with title, snippet, url, and source
        """
        if not self.client:
            logger.error("GoogleSearchClient not initialized.")
            return []
        
        # OPTIMIZATION: Skip query rewriting to save time (~200-500ms)
        # Use query directly for internet search
        search_query = query

        try:
            # Use timeout protection for internet search
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._perform_search, search_query, max_results)
                try:
                    results = future.result(timeout=timeout)
                    return results
                except concurrent.futures.TimeoutError:
                    logger.warning(f"⏱️ Internet search timeout ({timeout}s), returning empty results")
                    return []
                except Exception as e:
                    logger.error(f"Internet search failed: {e}")
                    return []
        except Exception as exc:
            logger.error("Internet search failed: %s", exc)
            return []
    
    def _perform_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Internal method to perform the actual search (called with timeout protection)"""
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=query)
                    ]
                )
            ]
            
            tools = [
                types.Tool(google_search=types.GoogleSearch()),
            ]

            # OPTIMIZATION: Reduced max_output_tokens for faster responses
            # 1024 tokens is ~750 words, sufficient for summaries
            config_kwargs = {
                "temperature": 0.7,  # Reduced from 1 for more focused responses
                "top_p": 0.95,
                "max_output_tokens": 1024,  # REDUCED from 4096 for speed (3-4x faster)
                "safety_settings": [
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
                ],
                "tools": tools,
            }

            # Adjust model list based on backend
            if self.use_vertex_ai:
                models_to_try = [
                    "gemini-2.5-flash",  # Try newest first; avoid 2.0 (404 in some regions)
                ]
            else:
                # AI Studio: Try newest model first
                models_to_try = [
                    "gemini-2.5-flash",   # Newest, most reliable
                ]

            generate_content_config = types.GenerateContentConfig(**config_kwargs)

            response = None
            last_error = None

            for model_name in models_to_try:
                try:
                    backend = "Vertex AI" if self.use_vertex_ai else "AI Studio"
                    logger.info(f"Calling {backend} model: {model_name}")
                    
                    # OPTIMIZATION: Use non-streaming for 2-3x faster response
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=generate_content_config,
                    )

                    # Success: remember working model and break
                    self.model = model_name
                    logger.info(f"✅ Internet search succeeded with model: {model_name}")
                    break

                except Exception as e:
                    error_str = str(e)
                    last_error = e
                    
                    # Log the error and continue to next model
                    if self.use_vertex_ai and ("403" in error_str or "PERMISSION_DENIED" in error_str or "IAM_PERMISSION_DENIED" in error_str):
                        logger.warning(f"⚠️ Vertex AI permission denied for {model_name}: {e}")
                        logger.error(f"💡 Service account needs 'roles/aiplatform.user' role. Contact your GCP admin.")
                        response = None
                        continue
                    else:
                        logger.warning(f"Model {model_name} failed: {e}")
                        response = None
                        continue

            if not response or not response.text:
                error_msg = f"Internet search failed for all tried models"
                if last_error:
                    error_msg += f". Last error: {last_error}"
                logger.error(error_msg)
                
                # If using Vertex AI and got permission error, suggest fix
                if self.use_vertex_ai and last_error and ("403" in str(last_error) or "PERMISSION_DENIED" in str(last_error)):
                    logger.error("💡 TIP: Vertex AI requires 'aiplatform.endpoints.predict' permission. "
                               "Either grant this permission to your service account, or unset GOOGLE_CLOUD_PROJECT_ID "
                               "to use AI Studio with API key instead.")
                
                return []

            full_response_text = response.text

            # CRITICAL FIX: Extract actual URLs from grounding metadata
            results = []
            grounding_metadata = None
            
            # Extract grounding metadata from the response
            try:
                if response and hasattr(response, 'candidates'):
                    for candidate in response.candidates:
                        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                            grounding_metadata = candidate.grounding_metadata
                            logger.info(f"📌 Found grounding metadata")
                            break
            except Exception as e:
                logger.warning(f"Failed to extract grounding metadata: {e}")
            
            # Extract URLs from grounding chunks
            if grounding_metadata and hasattr(grounding_metadata, 'grounding_chunks'):
                for chunk in grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        results.append({
                            "title": chunk.web.title if hasattr(chunk.web, 'title') else "Search Result",
                            "snippet": full_response_text[:500],  # Share the summary across results
                            "url": chunk.web.uri,
                            "source": chunk.web.uri
                        })
                logger.info(f"✅ Extracted {len(results)} source URLs from grounding metadata")
            
            # Fallback: If no grounding metadata, create a single result with the summary
            if not results:
                logger.warning("⚠️ No grounding URLs found, returning summary only")
                results = [{
                    "title": "Google Search Summary",
                    "snippet": full_response_text,
                    "url": None,  # No URL available
                    "source": "Google Search (no sources)"
                }]
            
            # Filter out unrelated international results unless query demands international
            results = self._filter_results(query, results)
            
            logger.info(f"✅ Internet search returned {len(results)} result(s) after filtering")
            return results[:max_results]

        except Exception as exc:
            logger.error("Internet search failed: %s", exc)
            return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = GoogleSearchClient()
    if client.client:
        print("Searching for 'AP Education Policy 2024'...")
        results = client.search("AP Education Policy 2024")
        for res in results:
            print(f"- [{res['title']}]")
            print(f"  Snippet: {res['snippet'][:100]}...")
