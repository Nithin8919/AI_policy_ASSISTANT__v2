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
        self._google_available = False
        self._use_google = False
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
        """Setup Google API if available"""
        if EMBEDDING_CONFIG.provider != "google":
            return
        
        if not self._can_use_google_api():
            return
        
        if EMBEDDING_CONFIG.google_api_key:
            api_key = EMBEDDING_CONFIG.google_api_key
            try:
                self._google_client.configure(api_key=api_key)
                self._use_google = True
                print(f"✅ Google embedding API configured: {EMBEDDING_CONFIG.model}")
            except Exception as e:
                print(f"⚠️ Failed to configure Google API, falling back to local: {e}")
        else:
            print("⚠️ GOOGLE_API_KEY not found, falling back to local models")

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
            except Exception as e:
                print(f"⚠️ Google API failed, falling back to {self._backend}: {e}")
                self._backend = "sentence_transformer" if self._sentence_transformer_cls else "lite"
        
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
        """Embed texts using Google API"""
        embeddings = []
        for text in texts:
            result = self._google_client.embed_content(
                model=EMBEDDING_CONFIG.model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=EMBEDDING_CONFIG.dimension
            )
            embeddings.append(result['embedding'])
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
