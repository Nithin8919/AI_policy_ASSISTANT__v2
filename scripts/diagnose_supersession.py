import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

retrieval_path = os.path.join(project_root, 'retrieval')
if os.path.exists(retrieval_path) and retrieval_path not in sys.path:
    sys.path.insert(0, retrieval_path)

from retrieval.retrieval_core.qdrant_client import get_qdrant_client

def diagnose_supersession():
    print("🔍 Diagnosing Supersession Map...\n")
    
    try:
        client = get_qdrant_client().client
        
        # Check if 'go' collection exists
        collections = client.get_collections()
        go_exists = any(c.name == 'go' for c in collections.collections)
        
        if not go_exists:
            print("❌ Collection 'go' does not exist!")
            print("   Available collections:", [c.name for c in collections.collections])
            return
        
        print("✅ Collection 'go' found\n")
        
        # Sample documents with relations
        print("📄 Sampling documents with 'supersedes' relations...\n")
        
        offset = None
        supersedes_count = 0
        sample_relations = []
        sample_go_numbers = []
        
        for i in range(5):  # Check first 5 batches
            points, offset = client.scroll(
                collection_name="go",
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            for point in points:
                doc_id = point.payload.get("doc_id")
                go_number = point.payload.get("go_number")
                relations = point.payload.get("relations", [])
                
                # Collect sample GO numbers
                if go_number and len(sample_go_numbers) < 5:
                    sample_go_numbers.append({
                        'doc_id': doc_id,
                        'go_number': go_number,
                        'go_number_type': type(go_number).__name__
                    })
                
                # Check for supersedes relations
                for rel in relations:
                    rel_type = rel.get("relation_type") or rel.get("type")
                    if rel_type == "supersedes":
                        supersedes_count += 1
                        if len(sample_relations) < 5:
                            sample_relations.append({
                                'doc_id': doc_id,
                                'go_number': go_number,
                                'target': rel.get('target'),
                                'relation': rel
                            })
            
            if offset is None:
                break
        
        # Report findings
        print(f"📊 Found {supersedes_count} 'supersedes' relations\n")
        
        if sample_go_numbers:
            print("📋 Sample GO Numbers (format analysis):")
            for sample in sample_go_numbers:
                print(f"   - doc_id: {sample['doc_id']}")
                print(f"     go_number: {sample['go_number']} ({sample['go_number_type']})")
            print()
        
        if sample_relations:
            print("🔗 Sample Supersession Relations:")
            for i, sample in enumerate(sample_relations, 1):
                print(f"\n   {i}. Document: {sample['doc_id']}")
                print(f"      GO Number: {sample['go_number']}")
                print(f"      Supersedes Target: {sample['target']}")
                
                # Try to extract number from target
                import re
                match = re.search(r'(\d+)', sample['target'])
                if match:
                    extracted_num = match.group(1)
                    print(f"      Extracted Number: {extracted_num}")
                    print(f"      Match Check: '{extracted_num}' == '{sample['go_number']}' ? {str(extracted_num) == str(sample['go_number'])}")
        else:
            print("⚠️ No supersession relations found in sample!")
            print("   This could mean:")
            print("   1. Your data doesn't contain supersession info")
            print("   2. The relation_type field uses different naming")
            print("   3. Relations aren't being ingested correctly")
        
        # Check relation types that DO exist
        print("\n📊 Checking what relation types are present...")
        offset = None
        relation_types = set()
        
        for i in range(3):
            points, offset = client.scroll(
                collection_name="go",
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            for point in points:
                relations = point.payload.get("relations", [])
                for rel in relations:
                    rel_type = rel.get("relation_type") or rel.get("type")
                    if rel_type:
                        relation_types.add(rel_type)
            
            if offset is None:
                break
        
        if relation_types:
            print(f"   Found relation types: {sorted(relation_types)}")
        else:
            print("   ⚠️ No relation_type fields found in any document!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_supersession()
