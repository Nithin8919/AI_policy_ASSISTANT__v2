# Clause Indexer - Build instant lookup from existing chunks

"""
Clause Indexer - Build instant clause lookup without reprocessing data
Scans existing Qdrant collections to create "Section X" -> chunk_id mappings
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class ClauseMatch:
    """A matched clause in a chunk"""
    clause_text: str
    chunk_id: str
    doc_id: str
    content: str
    confidence: float
    vertical: str


class ClauseIndexer:
    """Build and maintain clause index from existing chunks"""
    
    # Clause patterns to detect
    CLAUSE_PATTERNS = [
        (r'\bsection\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'section'),
        (r'\brule\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'rule'),
        (r'\barticle\s+(\d+\w*)', 'article'),
        (r'\bclause\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'clause'),
        (r'\bsub-rule\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', 'sub-rule'),
        (r'\bamendment\s+(\d+)', 'amendment'),
    ]
    
    # Act/Rule contexts
    ACT_CONTEXTS = [
        'rte', 'right to education', 'cce', 'apsermc', 'education act',
        'continuous comprehensive evaluation', 'sarva shiksha abhiyan'
    ]
    
    def __init__(self, qdrant_client, index_file: str = 'clause_index.json'):
        """
        Args:
            qdrant_client: Qdrant client instance
            index_file: Path to save/load clause index
        """
        self.qdrant_client = qdrant_client
        self.index_file = index_file
        self.clause_index = {}
        self.load_index()
    
    def build_index(self, collections: List[str] = None) -> Dict[str, ClauseMatch]:
        """
        Build clause index from existing collections
        
        Args:
            collections: Collections to scan (default: all legal collections)
            
        Returns:
            Dictionary mapping clause text -> ClauseMatch
        """
        if collections is None:
            collections = ['ap_legal_documents', 'ap_government_orders']
        
        print(f"🔍 Building clause index from {len(collections)} collections...")
        start_time = time.time()
        
        all_matches = {}
        
        for collection in collections:
            print(f"  📄 Scanning collection: {collection}")
            matches = self._scan_collection(collection)
            
            # Merge matches, preferring higher confidence
            for key, match in matches.items():
                if key not in all_matches or match.confidence > all_matches[key].confidence:
                    all_matches[key] = match
        
        self.clause_index = all_matches
        self.save_index()
        
        elapsed = time.time() - start_time
        print(f"✅ Built index with {len(all_matches)} clauses in {elapsed:.1f}s")
        
        # Show sample entries
        print("📋 Sample index entries:")
        for i, (key, match) in enumerate(list(all_matches.items())[:5]):
            print(f"  {key} -> {match.chunk_id[:8]}... ({match.confidence:.2f})")
        
        return all_matches
    
    def _scan_collection(self, collection: str) -> Dict[str, ClauseMatch]:
        """Scan a single collection for clause patterns"""
        matches = {}
        
        try:
            # Scroll through all chunks in collection
            scroll_result = self.qdrant_client.client.scroll if hasattr(self.qdrant_client, "client") else self.qdrant_client.scroll(
                collection_name=collection,
                limit=1000,  # Process in batches
                with_payload=True
            )
            
            points, next_offset = scroll_result
            
            while points:
                for point in points:
                    chunk_matches = self._extract_clauses_from_chunk(point, collection)
                    
                    for clause_key, match in chunk_matches.items():
                        # Keep best match for each clause
                        if clause_key not in matches or match.confidence > matches[clause_key].confidence:
                            matches[clause_key] = match
                
                # Get next batch
                if next_offset:
                    scroll_result = self.qdrant_client.client.scroll if hasattr(self.qdrant_client, "client") else self.qdrant_client.scroll(
                        collection_name=collection,
                        limit=1000,
                        offset=next_offset,
                        with_payload=True
                    )
                    points, next_offset = scroll_result
                else:
                    break
                    
        except Exception as e:
            print(f"⚠️ Error scanning collection {collection}: {e}")
        
        return matches
    
    def _extract_clauses_from_chunk(self, point, collection: str) -> Dict[str, ClauseMatch]:
        """Extract all clause references from a single chunk"""
        matches = {}
        
        content = point.payload.get('content', '')
        if not content:
            return matches
        
        content_lower = content.lower()
        
        # Detect act/rule context
        act_context = self._detect_act_context(content_lower)
        
        # Find all clause patterns
        for pattern, clause_type in self.CLAUSE_PATTERNS:
            for match in re.finditer(pattern, content_lower):
                clause_num = match.group(1)
                clause_text = f"{clause_type} {clause_num}"
                
                # Build contextual key
                if act_context:
                    clause_key = f"{act_context} {clause_text}"
                else:
                    clause_key = clause_text
                
                # Calculate confidence based on context quality
                confidence = self._calculate_confidence(content, match, act_context)
                
                matches[clause_key] = ClauseMatch(
                    clause_text=clause_text,
                    chunk_id=str(point.id),
                    doc_id=point.payload.get('doc_id', 'unknown'),
                    content=content,
                    confidence=confidence,
                    vertical=self._get_vertical_from_collection(collection)
                )
        
        return matches
    
    def _detect_act_context(self, content_lower: str) -> Optional[str]:
        """Detect which act/rule context this content belongs to"""
        for context in self.ACT_CONTEXTS:
            if context in content_lower:
                if context in ['rte', 'right to education']:
                    return 'rte'
                elif context == 'cce':
                    return 'cce'
                elif context == 'apsermc':
                    return 'apsermc'
                elif 'education act' in context:
                    return 'education'
        return None
    
    def _calculate_confidence(self, content: str, match, act_context: str) -> float:
        """Calculate confidence score for clause match"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we have act context
        if act_context:
            confidence += 0.3
        
        # Higher confidence if clause appears near start
        match_position = match.start() / len(content)
        if match_position < 0.1:  # First 10% of content
            confidence += 0.2
        elif match_position < 0.3:  # First 30%
            confidence += 0.1
        
        # Higher confidence if surrounded by legal language
        context_window = content[max(0, match.start()-100):match.end()+100].lower()
        legal_terms = ['shall', 'provided', 'whereas', 'hereby', 'therefore', 'act', 'rule']
        legal_count = sum(1 for term in legal_terms if term in context_window)
        confidence += min(0.2, legal_count * 0.03)
        
        return min(1.0, confidence)
    
    def _get_vertical_from_collection(self, collection: str) -> str:
        """Map collection name to vertical"""
        if 'legal' in collection.lower():
            return 'legal'
        elif 'government' in collection.lower() or 'go' in collection.lower():
            return 'go'
        elif 'judicial' in collection.lower():
            return 'judicial'
        elif 'data' in collection.lower():
            return 'data'
        elif 'scheme' in collection.lower():
            return 'schemes'
        else:
            return 'unknown'
    
    def lookup_clause(self, query: str) -> List[ClauseMatch]:
        """
        Look up clause matches for a query
        
        Args:
            query: User query like "RTE Section 12"
            
        Returns:
            List of matching ClauseMatch objects
        """
        query_lower = query.lower()
        matches = []
        
        # Try exact matches first
        for clause_key, match in self.clause_index.items():
            if clause_key in query_lower:
                matches.append(match)
        
        # Try partial matches
        if not matches:
            # Extract clause patterns from query
            for pattern, clause_type in self.CLAUSE_PATTERNS:
                for match in re.finditer(pattern, query_lower):
                    clause_num = match.group(1)
                    clause_text = f"{clause_type} {clause_num}"
                    
                    # Look for this clause in index
                    for clause_key, clause_match in self.clause_index.items():
                        if clause_text in clause_key:
                            matches.append(clause_match)
        
        # Remove duplicates and sort by confidence
        unique_matches = {}
        for match in matches:
            key = f"{match.chunk_id}_{match.clause_text}"
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        sorted_matches = sorted(unique_matches.values(), key=lambda x: x.confidence, reverse=True)
        return sorted_matches[:5]  # Top 5 matches
    
    def save_index(self):
        """Save clause index to file"""
        try:
            # Convert ClauseMatch objects to dicts for JSON serialization
            serializable_index = {}
            for key, match in self.clause_index.items():
                serializable_index[key] = {
                    'clause_text': match.clause_text,
                    'chunk_id': match.chunk_id,
                    'doc_id': match.doc_id,
                    'content': match.content[:500],  # Truncate content for size
                    'confidence': match.confidence,
                    'vertical': match.vertical
                }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_index, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved clause index to {self.index_file}")
            
        except Exception as e:
            print(f"⚠️ Failed to save index: {e}")
    
    def load_index(self):
        """Load clause index from file"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                serializable_index = json.load(f)
            
            # Convert dicts back to ClauseMatch objects
            self.clause_index = {}
            for key, data in serializable_index.items():
                self.clause_index[key] = ClauseMatch(
                    clause_text=data['clause_text'],
                    chunk_id=data['chunk_id'],
                    doc_id=data['doc_id'],
                    content=data['content'],
                    confidence=data['confidence'],
                    vertical=data['vertical']
                )
            
            print(f"📂 Loaded {len(self.clause_index)} clauses from {self.index_file}")
            
        except FileNotFoundError:
            print(f"📝 No existing index found at {self.index_file}")
            self.clause_index = {}
        except Exception as e:
            print(f"⚠️ Failed to load index: {e}")
            self.clause_index = {}
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        if not self.clause_index:
            return {"total_clauses": 0}
        
        stats = {
            "total_clauses": len(self.clause_index),
            "by_type": {},
            "by_act": {},
            "by_vertical": {},
            "avg_confidence": 0.0
        }
        
        confidences = []
        
        for clause_match in self.clause_index.values():
            # By type
            clause_type = clause_match.clause_text.split()[0]
            stats["by_type"][clause_type] = stats["by_type"].get(clause_type, 0) + 1
            
            # By vertical
            vertical = clause_match.vertical
            stats["by_vertical"][vertical] = stats["by_vertical"].get(vertical, 0) + 1
            
            # Confidence
            confidences.append(clause_match.confidence)
        
        if confidences:
            stats["avg_confidence"] = sum(confidences) / len(confidences)
        
        return stats


# Convenience functions
def build_clause_index(qdrant_client, collections: List[str] = None) -> ClauseIndexer:
    """Quick function to build clause index"""
    indexer = ClauseIndexer(qdrant_client)
    indexer.build_index(collections)
    return indexer


def lookup_clause(query: str, qdrant_client, index_file: str = 'clause_index.json') -> List[ClauseMatch]:
    """Quick function to lookup clauses"""
    indexer = ClauseIndexer(qdrant_client, index_file)
    return indexer.lookup_clause(query)


# Example usage and tests
if __name__ == "__main__":
    import os
    from qdrant_client import QdrantClient
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    QDRANT_URL = os.getenv('QDRANT_URL')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    
    # Initialize client
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    print("🚀 Building Clause Index from Existing Data")
    print("=" * 60)
    
    # Build index
    indexer = ClauseIndexer(qdrant)
    indexer.build_index(['ap_legal_documents', 'ap_government_orders'])
    
    # Show stats
    stats = indexer.get_stats()
    print(f"\n📊 Index Statistics:")
    print(f"  Total clauses: {stats['total_clauses']}")
    print(f"  Average confidence: {stats['avg_confidence']:.2f}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By vertical: {stats['by_vertical']}")
    
    # Test lookups
    test_queries = [
        "What is RTE Act Section 12?",
        "Article 21A Constitution",
        "CCE Rule 7",
        "Section 4 APSERMC",
    ]
    
    print(f"\n🔍 Testing Clause Lookups:")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        matches = indexer.lookup_clause(query)
        
        if matches:
            for i, match in enumerate(matches[:2], 1):
                print(f"  {i}. {match.clause_text} (confidence: {match.confidence:.2f})")
                print(f"     {match.content[:100]}...")
        else:
            print("  No matches found")