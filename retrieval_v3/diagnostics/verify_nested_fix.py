import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "retrieval_v3"))

from retrieval_v3.retrieval.relation_reranker import BidirectionalRelationFinder, RelationResult

def verify_fix():
    print("🧪 Verifying Qdrant Nested Filter Fix...")
    
    # Mock Qdrant client
    mock_client = MagicMock()
    # Mock query_points to return empty list so we don't need real connection
    mock_client.query_points.return_value.points = []
    
    finder = BidirectionalRelationFinder(qdrant_client=mock_client)
    
    # Create a dummy result
    result = RelationResult(
        chunk_id="test_chunk",
        doc_id="GO 123",
        content="test content",
        score=1.0,
        vertical="go"
    )
    
    print("   Running _find_superseding_docs...")
    try:
        # This calls the code with the Nested filter
        finder._find_superseding_docs(result)
        print("   ✅ _find_superseding_docs ran without error")
    except Exception as e:
        print(f"   ❌ _find_superseding_docs failed: {e}")
        
    print("   Running _find_amending_docs...")
    try:
        # This calls the code with the Nested filter
        finder._find_amending_docs(result)
        print("   ✅ _find_amending_docs ran without error")
    except Exception as e:
        print(f"   ❌ _find_amending_docs failed: {e}")

if __name__ == "__main__":
    verify_fix()
