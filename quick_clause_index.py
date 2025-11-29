#!/usr/bin/env python3
"""
Quick Clause Index Builder - Standalone script
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')


@dataclass
class ClauseMatch:
    """A matched clause in a chunk"""
    clause_text: str
    chunk_id: str
    doc_id: str
    content: str
    confidence: float
    vertical: str


def build_clause_index():
    """Build clause index from existing Qdrant data"""
    
    print("🚀 Building Clause Index for Legal Clause Queries")
    print("=" * 60)
    
    # Connect to Qdrant Cloud
    try:
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collections = qdrant.get_collections()
        print(f"✅ Connected to Qdrant Cloud. Found {len(collections.collections)} collections.")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        return
    
    # Collections to scan - ALL collections for comprehensive coverage
    collections = [
        'ap_legal_documents',      # Acts, rules, regulations  
        'ap_government_orders',    # Implementation orders
        'ap_judicial_documents',   # Court judgments (cite sections)
        'ap_data_reports',         # UDISE reports (reference policies)
        'ap_schemes'               # Scheme documents (reference acts)
    ]
    
    # Comprehensive clause patterns
    patterns = [
        (r'\bsection\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'section'),
        (r'\brule\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'rule'),
        (r'\barticle\s+(\d+\w*)', 'article'),
        (r'\bclause\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'clause'),
        (r'\bparagraph\s+(\d+(?:\(\d+\))?)', 'paragraph'),
        (r'\bsub-section\s+(\d+(?:\(\d+\))?)', 'sub-section'),
        (r'\bsub-rule\s+(\d+(?:\(\d+\))?)', 'sub-rule'),
        (r'\bchapter\s+(\d+\w*)', 'chapter'),
        (r'\bpart\s+(\d+\w*)', 'part'),
        (r'\bschedule\s+(\d+\w*)', 'schedule'),
    ]
    
    # Extended act/scheme contexts
    act_contexts = [
        'rte', 'right to education', 'cce', 'education act',
        'samagra shiksha', 'nadu nedu', 'amma vodi', 'vidya kanuka',
        'apsermc', 'school education act', 'children act',
        'juvenile justice', 'child protection', 'pwd act',
        'sarva shiksha abhiyan', 'rashtriya madhyamik'
    ]
    
    clause_index = {}
    
    print(f"📄 Scanning {len(collections)} collections...")
    
    for collection in collections:
        print(f"  Scanning {collection}...")
        
        try:
            # Get all points from collection
            scroll_result = qdrant.scroll(
                collection_name=collection,
                limit=1000,
                with_payload=True
            )
            
            points, next_offset = scroll_result
            chunk_count = 0
            
            while points:
                for point in points:
                    chunk_count += 1
                    content = point.payload.get('text', point.payload.get('content', ''))
                    if not content:
                        continue
                    
                    content_lower = content.lower()
                    
                    # Detect act context
                    act_context = None
                    for context in act_contexts:
                        if context in content_lower:
                            if context in ['rte', 'right to education']:
                                act_context = 'rte'
                                break
                            elif context == 'cce':
                                act_context = 'cce'
                                break
                    
                    # Find clause patterns
                    for pattern, clause_type in patterns:
                        for match in re.finditer(pattern, content_lower):
                            clause_num = match.group(1)
                            clause_text = f"{clause_type} {clause_num}"
                            
                            # Build key
                            if act_context:
                                key = f"{act_context} {clause_text}"
                            else:
                                key = clause_text
                            
                            # Calculate confidence
                            confidence = 0.5
                            if act_context:
                                confidence += 0.3
                            
                            match_position = match.start() / len(content)
                            if match_position < 0.1:
                                confidence += 0.2
                            
                            # Store best match
                            if key not in clause_index or confidence > clause_index[key]['confidence']:
                                clause_index[key] = {
                                    'clause_text': clause_text,
                                    'chunk_id': str(point.id),
                                    'doc_id': point.payload.get('doc_id', 'unknown'),
                                    'content': content[:500],  # Truncate
                                    'confidence': confidence,
                                    'vertical': 'legal' if 'legal' in collection else 'go'
                                }
                                print(f"      Found: {key} (confidence: {confidence:.2f})")
                
                # Get next batch
                if next_offset:
                    scroll_result = qdrant.scroll(
                        collection_name=collection,
                        limit=1000,
                        offset=next_offset,
                        with_payload=True
                    )
                    points, next_offset = scroll_result
                else:
                    break
            
            print(f"    Processed {chunk_count} chunks")
            
        except Exception as e:
            print(f"⚠️ Error scanning {collection}: {e}")
    
    # Save index
    try:
        with open('clause_index.json', 'w', encoding='utf-8') as f:
            json.dump(clause_index, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Built index with {len(clause_index)} clauses")
        print(f"💾 Saved to clause_index.json")
        
        # Show sample
        print("\n📋 Sample index entries:")
        for i, (key, data) in enumerate(list(clause_index.items())[:5]):
            print(f"  {key} -> {data['chunk_id'][:8]}... (conf: {data['confidence']:.2f})")
        
        # Test lookups
        print(f"\n🔍 Testing lookups:")
        test_queries = ["rte section 12", "section 12", "article 21a", "cce rule 7"]
        
        for query in test_queries:
            found = False
            for key in clause_index.keys():
                if query.lower() in key.lower():
                    match = clause_index[key]
                    print(f"  '{query}' -> Found: {key} (conf: {match['confidence']:.2f})")
                    found = True
                    break
            if not found:
                print(f"  '{query}' -> Not found")
        
        print(f"\n🎯 Clause index ready! Legal queries should now work reliably.")
        
    except Exception as e:
        print(f"❌ Failed to save index: {e}")


if __name__ == "__main__":
    build_clause_index()