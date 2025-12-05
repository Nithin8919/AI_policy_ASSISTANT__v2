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

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google Search Client.

        Auth strategy:
        - If a Google Cloud project is configured, we FIRST try Vertex AI using gcloud / ADC.
        - If that fails OR no project is set, we fall back to API-key-only AI Studio.
        - API key is read from (in order): GOOGLE_CLOUD_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY.
        """
        # Optional project/location for Vertex AI
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.use_vertex_ai = False

        self.api_key = (
            api_key 
            or os.environ.get("GOOGLE_CLOUD_API_KEY") 
            or os.environ.get("GEMINI_API_KEY") 
            or os.environ.get("GOOGLE_API_KEY")
        )
        
        self.client = None

        # 1) Try Vertex AI if project is configured (uses gcloud / ADC, no API key)
        if self.project_id:
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
                logger.warning(f"Vertex AI initialization failed: {e}")
                logger.info("Falling back to API-key AI Studio client...")
                self.client = None

        # 2) Fall back to API-key AI Studio if Vertex AI is not used / failed
        if self.client is None:
            if not self.api_key:
                logger.error(
                    "No API key found. Please set GOOGLE_API_KEY (or GOOGLE_CLOUD_API_KEY / GEMINI_API_KEY) "
                    "in your .env or environment."
                )
                self.model = "gemini-1.5-flash"
                return

            try:
                # Pure AI Studio client: API key, no project, no vertexai=True
                # NOTE: google-genai handles the correct API version internally for AI Studio.
                logger.info(
                    "Initializing GoogleSearchClient with API Key (AI Studio, vertexai=False)"
                )
                self.client = genai.Client(
                    vertexai=False,
                    api_key=self.api_key,
                )
                self.use_vertex_ai = False
                logger.info("✅ Initialized GoogleSearchClient (AI Studio)")
            except Exception as e:
                logger.error(f"Failed to initialize GoogleSearchClient with API key: {e}")
                self.client = None

        # Default model name (starting point); search() will try multiple variants
        # For Vertex AI and AI Studio, "gemini-1.5-flash" is usually a good first try.
        self.model = "gemini-1.5-flash"
        
        # Initialize query rewriter for search optimization
        try:
            from retrieval_v3.query_understanding.query_rewriter import QueryRewriter
            self.query_rewriter = QueryRewriter()
            logger.info("✅ Query rewriter initialized for internet search optimization")
        except Exception as e:
            logger.warning(f"Query rewriter initialization failed: {e}, will use raw queries")
            self.query_rewriter = None

    def search(self, query: str, max_results: int = 5, timeout: float = 3.0) -> List[Dict[str, str]]:
        """
        Perform an internet search and return structured results.
        
        Args:
            query: Original user query
            max_results: Maximum number of results to return (default: 5, increased from 1)
            timeout: Timeout in seconds for the search operation (default: 3.0)
            
        Returns:
            List of search results with title, snippet, url, and source
        """
        if not self.client:
            logger.error("GoogleSearchClient not initialized.")
            return []
        
        # OPTIMIZATION: Rewrite query for better search results
        search_query = query
        if self.query_rewriter:
            try:
                rewrites = self.query_rewriter.generate_rewrites(query, num_rewrites=1)
                if rewrites:
                    search_query = rewrites[0].text
                    logger.info(f"🔄 Query rewritten for internet search: '{query}' → '{search_query}'")
            except Exception as e:
                logger.warning(f"Query rewriting failed: {e}, using original query")
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

            # Base config; we will tweak per backend (Vertex vs AI Studio)
            config_kwargs = {
                "temperature": 1,
                "top_p": 0.95,
                # max_output_tokens limit differs between Vertex and AI Studio
                # - Vertex (e.g. gemini-2.0-flash) typically supports up to 8192
                # - AI Studio can support larger, but 4096 is plenty for our summaries
                "max_output_tokens": 4096,
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

            # Adjust token limit and model list based on backend
            if self.use_vertex_ai:
                # Vertex AI: respect the 1–8192 maxOutputTokens range
                config_kwargs["max_output_tokens"] = 2048
                models_to_try = [
                    "gemini-2.0-flash",
                ]
            else:
                # AI Studio: use common AI Studio model IDs
                models_to_try = [
                    self.model,          # default, usually "gemini-1.5-flash"
                    "gemini-1.5-pro",
                    "gemini-2.0-flash",
                    "gemini-1.0-pro",
                    "gemini-pro",
                ]

            generate_content_config = types.GenerateContentConfig(**config_kwargs)

            full_response_text = ""

            last_error: Any = None

            for model_name in models_to_try:
                try:
                    backend = "Vertex AI" if self.use_vertex_ai else "AI Studio"
                    logger.info(f"Calling {backend} model: {model_name}")
                    response_stream = self.client.models.generate_content_stream(
                        model=model_name,
                        contents=contents,
                        config=generate_content_config,
                    )

                    for chunk in response_stream:
                        if (
                            chunk.candidates
                            and chunk.candidates[0].content
                            and chunk.candidates[0].content.parts
                        ):
                            full_response_text += chunk.text

                    # Success: remember working model and break
                    self.model = model_name
                    logger.info(f"✅ Internet search succeeded with model: {model_name}")
                    break

                except Exception as e:
                    last_error = e
                    logger.warning(f"Model {model_name} failed: {e}")
                    full_response_text = ""
                    continue

            if not full_response_text:
                logger.error(f"Internet search failed for all tried models. Last error: {last_error}")
                return []

            # Parse response to extract multiple results if possible
            # For now, return as a single comprehensive result
            # TODO: Parse structured results if the model returns them
            results = [{
                "title": "Google Search Summary",
                "snippet": full_response_text,
                "url": "https://google.com",
                "source": "Google Search"
            }]
            
            # If max_results > 1, we could split the response or make multiple calls
            # For now, we return the single comprehensive result
            logger.info(f"✅ Internet search returned {len(results)} result(s)")
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
