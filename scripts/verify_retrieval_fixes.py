
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Verify retrieval path exists
retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval_v3.retrieval.relation_reranker import EntityExpander, RelationReranker, RelationResult

def verify_retrieval_logic():
    print("🧪 Verifying Retrieval Logic Fixes...")
    
    # 1. Initialize Components
    try:
        client = get_qdrant_client().client
        expander = EntityExpander(client)
        reranker = RelationReranker(client)
        print("✅ Components initialized")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # 2. Test Entity Expansion with 'years' (New Feature)
    print("\n🔍 Testing Entity Expansion (Years)...")
    try:
        # Mock entities with a year that definitely exists (e.g. 2023 or 2024)
        entities = {
            'years': ['2023'],
            'departments': ['School Education']  # Usually a safe bet
        }
        
        results = expander._find_by_entities(entities, max_results=5)
        print(f"   Found {len(results)} results for entities: {entities}")
        
        if results:
            print(f"   ✅ First result: {results[0].doc_id}")
            if results[0].metadata.get('found_via_entity'):
                 print("   ✅ 'found_via_entity' flag present")
        else:
             print("   ⚠️ No results found (might be lack of data, but code didn't crash)")

    except Exception as e:
        print(f"❌ Entity Expansion failed: {e}")

    # 3. Test Surgical Expansion with String ID (New Feature)
    print("\n🔍 Testing Surgical Expansion (String ID)...")
    try:
        # Mock a result that triggers expansion
        mock_result = RelationResult(
            chunk_id='dummy_id',
            doc_id='dummy_doc',
            content='dummy content',
            score=1.0,
            vertical='go',
            metadata={
                'relations': [
                    {'type': 'supersedes', 'target': 'G.O.Ms.No. 1'} # String ID
                ]
            }
        )
        
        # This will internally call _fetch_by_identifier for the string target
        # We perform a real search, so "G.O.Ms.No. 1" might not exist, but we check if code runs
        neighbors = reranker._expand_with_neighbors([mock_result], max_neighbors=1)
        print(f"   Execution successful. Neighbors found: {len(neighbors)}")
        print("   ✅ Surgical expansion logic handled String ID without crash")
        
    except Exception as e:
        print(f"❌ Surgical Expansion failed: {e}")

if __name__ == "__main__":
    verify_retrieval_logic()
