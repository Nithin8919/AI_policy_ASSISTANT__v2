from fastapi import APIRouter
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """System health check"""
    start = time.time()
    
    checks = {
        'qdrant': _check_qdrant(),
        'bm25': _check_bm25(),
        'embedder': _check_embedder()
    }
    
    status = 'healthy' if all(c['ok'] for c in checks.values()) else 'degraded'
    
    return {
        'status': status,
        'timestamp': int(time.time()),
        'latency_ms': int((time.time() - start) * 1000),
        'components': checks
    }

def _check_qdrant():
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        return {'ok': True, 'collections': len(collections.collections)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def _check_bm25():
    try:
        import os
        bm25_path = 'bm25_index.pkl'
        exists = os.path.exists(bm25_path)
        return {'ok': exists, 'cached': exists}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def _check_embedder():
    try:
        from retrieval.embeddings.embedder import get_embedder
        embedder = get_embedder()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
