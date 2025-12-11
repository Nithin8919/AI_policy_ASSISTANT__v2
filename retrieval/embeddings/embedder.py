# Unified embedding API (local + Google API)

"""
Unified Embedder
================
Supports both local models and Google embedding API.
Lighter resource usage with API fallback to local.
"""

import hashlib
import importlib
import math
import os
import random
import subprocess
import sys
from typing import List, Sequence, Union

from ..config.settings import EMBEDDING_CONFIG


class Embedder:
    """
    Unified embedder supporting Google API and local models.
    Prefers API for lighter resource usage, but never crashes when heavy deps are missing.
    """
    
    def __init__(self):
        """Initialize embedder"""
        self._fast_model = None
        self._deep_model = None
        self._torch = None
        self._sentence_transformer_cls = None
        self._google_client = None
        self._vertex_project = None
        self._vertex_location = None
        self._vertex_creds = None
        self._google_available = False
        self._use_google = False
        self._use_vertex_ai = False
        self._backend = "lite"
        self._lite_dim = EMBEDDING_CONFIG.fast_dim
        self.device = "cpu"
        self._probe_ran = False
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Figure out best backend without crashing the interpreter"""
        self._setup_google_api()
        if self._use_google:
            self._backend = "google"
            return
        
        if self._can_use_sentence_transformers():
            self._backend = "sentence_transformer"
            self.device = self._detect_device()
            return
        
        print("⚠️ sentence-transformers unavailable, using deterministic lite embedder")
        self._backend = "lite"
    
    def _detect_device(self) -> str:
        """Detect available device for sentence transformers"""
        if self._torch is None:
            return "cpu"
        if self._torch.cuda.is_available():
            return "cuda"
        if getattr(self._torch.backends, "mps", None) and self._torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _setup_google_api(self):
        """Setup Google API if available - supports OAuth/ADC for Vertex AI embeddings"""
        # Allow opt-out even when project/ADC is set (e.g., use local or API key only)
        disable_vertex = os.getenv("GOOGLE_DISABLE_VERTEX_AI", "").lower() in ("1", "true", "yes")
        genai_vertex_enabled = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() not in ("0", "false", "no")
        if disable_vertex or not genai_vertex_enabled:
            return

        if EMBEDDING_CONFIG.provider != "google":
            return
        
        # Try OAuth/ADC first (Vertex AI)
        use_oauth = os.getenv("GOOGLE_USE_OAUTH", "").lower() in ("1", "true", "yes")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
        
        if use_oauth and project_id:
            try:
                import google.auth
                from google.auth.transport.requests import Request
                
                # Get credentials with proper scope
                service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if service_account_file and os.path.exists(service_account_file):
                    from google.oauth2 import service_account
                    creds = service_account.Credentials.from_service_account_file(
                        service_account_file,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                else:
                    creds, _ = google.auth.default(
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                
                # Store Vertex AI config for REST API calls
                self._vertex_project = project_id
                self._vertex_location = location
                self._vertex_creds = creds
                self._use_google = True
                self._use_vertex_ai = True
                print(f"✅ Google embedding API configured with Vertex AI (OAuth): {EMBEDDING_CONFIG.model}")
                return
            except Exception as e:
                print(f"⚠️ Vertex AI embedding setup failed: {e}, trying API key fallback...")
        
        # Fallback to API key (AI Studio) - only if OAuth not available
        if not self._can_use_google_api():
            return
        
        if EMBEDDING_CONFIG.google_api_key:
            api_key = EMBEDDING_CONFIG.google_api_key
            try:
                self._google_client.configure(api_key=api_key)
                self._use_google = True
                self._use_vertex_ai = False
                print(f"✅ Google embedding API configured with API key: {EMBEDDING_CONFIG.model}")
            except Exception as e:
                print(f"⚠️ Failed to configure Google API, falling back to local: {e}")
        else:
            print("⚠️ GOOGLE_API_KEY not found and OAuth not configured, falling back to local models")

    def _can_use_google_api(self) -> bool:
        """Safely check whether google.generativeai can be imported"""
        if self._google_client is not None:
            return True
        
        if self._google_available:
            return False
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import google.generativeai"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                self._google_available = False
                return False
        except Exception:
            self._google_available = False
            return False
        
        try:
            module = importlib.import_module("google.generativeai")
            self._google_client = module
            self._google_available = True
            return True
        except Exception as exc:
            print(f"⚠️ Failed to import google.generativeai: {exc}")
            self._google_available = False
            self._google_client = None
            return False
    
    def _can_use_sentence_transformers(self) -> bool:
        """
        Determine whether importing sentence_transformers would succeed.
        Uses a subprocess probe so we don't crash the main process.
        """
        if os.getenv("DISABLE_SENTENCE_TRANSFORMERS") == "1":
            return False
        
        if self._probe_ran:
            return self._sentence_transformer_cls is not None
        
        self._probe_ran = True
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import sentence_transformers"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                return False
        except Exception:
            return False
        
        try:
            import torch  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:
            print(f"⚠️ Failed to import sentence-transformers, using lite embedder: {exc}")
            return False
        
        self._torch = torch
        self._sentence_transformer_cls = SentenceTransformer
        return True
    
    @property
    def fast_model(self):
        """Get or load fast model (cached)"""
        if self._fast_model is None:
            if self._sentence_transformer_cls is None:
                raise RuntimeError("SentenceTransformer backend not available")
            print(f"Loading fast model: {EMBEDDING_CONFIG.fast_model}")
            self._fast_model = self._sentence_transformer_cls(
                EMBEDDING_CONFIG.fast_model,
                device=self.device
            )
        return self._fast_model
    
    @property
    def deep_model(self):
        """Get or load deep model (cached)"""
        if self._deep_model is None:
            if self._sentence_transformer_cls is None:
                raise RuntimeError("SentenceTransformer backend not available")
            print(f"Loading deep model: {EMBEDDING_CONFIG.deep_model}")
            self._deep_model = self._sentence_transformer_cls(
                EMBEDDING_CONFIG.deep_model,
                device=self.device
            )
        return self._deep_model
    
    def embed(
        self,
        texts: Union[str, List[str]],
        model_type: str = "fast"
    ) -> List[List[float]]:
        """
        Embed text(s) using available backend.
        
        Args:
            texts: Single text or list of texts
            model_type: "fast" or "deep" (ignored for Google API and lite)
            
        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if self._backend == "google":
            try:
                return self._embed_google(texts)
            except (PermissionError, RuntimeError) as e:
                error_str = str(e)
                # Check if it's a permission error (403) - should fall back gracefully
                if isinstance(e, PermissionError) or "403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str:
                    print(f"⚠️ Vertex AI embedding permission denied, falling back to local models")
                    # Disable Vertex AI for future calls
                    self._use_vertex_ai = False
                    self._backend = "sentence_transformer" if self._sentence_transformer_cls else "lite"
                else:
                    print(f"⚠️ Google API failed, falling back to local models: {error_str[:200]}")
                    self._backend = "sentence_transformer" if self._sentence_transformer_cls else "lite"
                
                # Retry with fallback backend
                if self._backend == "sentence_transformer":
                    if model_type == "fast":
                        model = self.fast_model
                    elif model_type == "deep":
                        model = self.deep_model
                    else:
                        model = self.fast_model
                    
                    embeddings = model.encode(
                        texts,
                        batch_size=EMBEDDING_CONFIG.batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=False,
                        convert_to_tensor=False
                    )
                    return [self._ensure_list(vec) for vec in embeddings]
                else:
                    # Fall back to lite embedder
                    return self._lite_embed(texts)
            except Exception as e:
                # Catch any other exceptions and fall back
                error_str = str(e)
                print(f"⚠️ Google API failed with unexpected error, falling back to local models: {error_str[:200]}")
                self._backend = "sentence_transformer" if self._sentence_transformer_cls else "lite"
                
                # Retry with fallback backend
                if self._backend == "sentence_transformer":
                    if model_type == "fast":
                        model = self.fast_model
                    elif model_type == "deep":
                        model = self.deep_model
                    else:
                        model = self.fast_model
                    
                    embeddings = model.encode(
                        texts,
                        batch_size=EMBEDDING_CONFIG.batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=False,
                        convert_to_tensor=False
                    )
                    return [self._ensure_list(vec) for vec in embeddings]
                else:
                    # Fall back to lite embedder
                    return self._lite_embed(texts)
        
        if self._backend == "sentence_transformer":
            if model_type == "fast":
                model = self.fast_model
            elif model_type == "deep":
                model = self.deep_model
            else:
                raise ValueError(f"Unknown model_type: {model_type}")
            
            embeddings = model.encode(
                texts,
                batch_size=EMBEDDING_CONFIG.batch_size,
                show_progress_bar=False,
                convert_to_numpy=False,
                convert_to_tensor=False
            )
            return [self._ensure_list(vec) for vec in embeddings]
        
        # Lite deterministic fallback
        return self._lite_embed(texts)
    
    def _lite_embed(self, texts: List[str]) -> List[List[float]]:
        """Deterministic hashing-based embedding fallback"""
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], "little", signed=False)
            rng = random.Random(seed)
            vec = [rng.gauss(0, 1) for _ in range(self._lite_dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors
    
    def _embed_google(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using Google API (Vertex AI OAuth or API key)"""
        embeddings = []
        
        # Use Vertex AI REST API if OAuth is configured
        if self._use_vertex_ai and self._vertex_project:
            try:
                import requests
            except ImportError:
                raise RuntimeError("'requests' library required for Vertex AI embeddings. Install with: pip install requests")
            
            from google.auth.transport.requests import Request
            
            # Refresh credentials if needed
            if not self._vertex_creds.valid:
                self._vertex_creds.refresh(Request())
            
            # Vertex AI embedding endpoint
            endpoint = f"https://{self._vertex_location}-aiplatform.googleapis.com/v1beta1/projects/{self._vertex_project}/locations/{self._vertex_location}/publishers/google/models/text-embedding-004:predict"
            
            headers = {
                "Authorization": f"Bearer {self._vertex_creds.token}",
                "Content-Type": "application/json"
            }
            
            for text in texts:
                try:
                    # Prepare request payload for Vertex AI embedding API
                    # Note: Vertex AI uses a different payload structure
                    payload = {
                        "instances": [{
                            "content": text,
                            "task_type": "RETRIEVAL_DOCUMENT"
                        }],
                        "parameters": {
                            "outputDimensionality": EMBEDDING_CONFIG.dimension
                        }
                    }
                    
                    response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
                    
                    # Check for errors
                    if response.status_code != 200:
                        error_detail = response.text
                        # Check if it's a permission error (403) - disable Vertex AI immediately
                        if response.status_code == 403 or "PERMISSION_DENIED" in error_detail or "aiplatform.endpoints.predict" in error_detail:
                            print(f"⚠️ Vertex AI embedding permission denied (403). Disabling Vertex AI and falling back to local models.")
                            self._use_vertex_ai = False  # Disable Vertex AI for future calls
                            # Raise a specific exception that will trigger fallback
                            raise PermissionError(f"Vertex AI embedding permission denied: {error_detail}")
                        print(f"⚠️ Vertex AI embedding API error ({response.status_code}): {error_detail}")
                        raise RuntimeError(f"Vertex AI embedding failed: {response.status_code} - {error_detail}")
                    
                    result = response.json()
                    
                    # Parse response - Vertex AI returns predictions array
                    if "predictions" in result and len(result["predictions"]) > 0:
                        prediction = result["predictions"][0]
                        
                        # Try different response formats
                        embedding = None
                        if "embeddings" in prediction:
                            # Format: {"embeddings": {"values": [...]}}
                            if isinstance(prediction["embeddings"], dict):
                                embedding = prediction["embeddings"].get("values", [])
                            else:
                                embedding = prediction["embeddings"]
                        elif "embedding" in prediction:
                            # Direct embedding field
                            embedding = prediction["embedding"]
                        elif "values" in prediction:
                            # Direct values field
                            embedding = prediction["values"]
                        else:
                            # Try to find any list-like field
                            for key, value in prediction.items():
                                if isinstance(value, list) and len(value) > 100:  # Likely an embedding vector
                                    embedding = value
                                    break
                        
                        if embedding is None or len(embedding) == 0:
                            raise ValueError(f"No embedding found in Vertex AI response. Response structure: {list(prediction.keys())}")
                        
                        embeddings.append(embedding)
                    else:
                        raise ValueError(f"No predictions in Vertex AI response: {result}")
                        
                except requests.exceptions.RequestException as e:
                    error_str = str(e)
                    # Check if it's a permission error in the response
                    if hasattr(e, 'response') and e.response is not None:
                        if e.response.status_code == 403 or "PERMISSION_DENIED" in e.response.text:
                            print(f"⚠️ Vertex AI embedding permission denied (403). Disabling Vertex AI.")
                            self._use_vertex_ai = False
                            raise PermissionError(f"Vertex AI embedding permission denied: {e.response.text}")
                        print(f"   Response: {e.response.text}")
                    print(f"⚠️ Vertex AI embedding request failed: {e}")
                    raise
                except PermissionError:
                    # Re-raise permission errors to trigger fallback
                    raise
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a permission error
                    if "403" in error_str or "PERMISSION_DENIED" in error_str or "aiplatform.endpoints.predict" in error_str:
                        print(f"⚠️ Vertex AI embedding permission denied. Disabling Vertex AI.")
                        self._use_vertex_ai = False
                        raise PermissionError(f"Vertex AI embedding permission denied: {error_str}")
                    print(f"⚠️ Vertex AI embedding failed: {e}")
                    print(f"   Text length: {len(text)}")
                    raise
        
        # Fallback to API key (AI Studio)
        elif self._google_client:
            for text in texts:
                try:
                    # Try with output_dimensionality first
                    result = self._google_client.embed_content(
                        model=EMBEDDING_CONFIG.model,
                        content=text,
                        task_type="retrieval_document",
                        output_dimensionality=EMBEDDING_CONFIG.dimension
                    )
                except TypeError:
                    # Fallback without output_dimensionality for older API versions
                    result = self._google_client.embed_content(
                        model=EMBEDDING_CONFIG.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                embeddings.append(result['embedding'])
        else:
            raise RuntimeError("No Google embedding client available")
        
        return [self._ensure_list(vec) for vec in embeddings]
    
    def embed_query(self, query: str, model_type: str = "fast") -> List[float]:
        """Embed a single query."""
        return self.embed(query, model_type)[0]
    
    def get_embedding_dim(self, model_type: str = "fast") -> int:
        """Get embedding dimension for a model"""
        if self._backend == "google":
            return EMBEDDING_CONFIG.dimension
        if self._backend == "sentence_transformer":
            if model_type == "fast":
                return EMBEDDING_CONFIG.fast_dim
            if model_type == "deep":
                return EMBEDDING_CONFIG.deep_dim
            raise ValueError(f"Unknown model_type: {model_type}")
        return self._lite_dim
    
    def _ensure_list(self, vector: Union[Sequence[float], List[float]]) -> List[float]:
        """Convert any sequence (numpy array, list, etc.) to a plain Python list"""
        if isinstance(vector, list):
            return [float(x) for x in vector]
        if hasattr(vector, "tolist"):
            return [float(x) for x in vector.tolist()]
        return [float(x) for x in vector]


# Global embedder instance (singleton)
_embedder_instance = None


def get_embedder() -> Embedder:
    """Get global embedder instance"""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance
