"""
Supersession Manager
====================
Manages document validity by tracking supersession relationships.
Loads 'supersedes' relations from Qdrant and maintains a set of invalid document IDs.
"""

import logging
from typing import Set, Dict, List, Optional
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

class SupersessionManager:
    """
    Tracks superseded documents to filter them out or downrank them.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client
        self.superseded_ids: Set[str] = set()
        self.supersession_map: Dict[str, str] = {} # superseded_id -> superseding_id
        
        # Load relations on init
        self._load_supersession_data()
        
    def _load_supersession_data(self):
        """
        Fetch all 'supersedes' relations from Qdrant.
        We scan the 'go' collection as that's where most supersessions happen.
        """
        try:
            logger.info("🔄 Loading supersession data from Qdrant...")
            
            # We need to find chunks that HAVE relations of type 'supersedes'
            # Since we can't easily query deep JSON in Qdrant without a payload index on specific fields,
            # and 'relations' is a list of objects, we might need to scroll and check.
            # Optimization: If we have a 'has_relations' boolean, we filter by that first.
            
            offset = None
            count = 0
            
            offset = None
            count = 0
            
            # Check if we have a wrapper or real client
            client_instance = self.client.client if hasattr(self.client, 'client') else self.client
            
            while True:
                points, offset = client_instance.scroll(
                    collection_name="ap_government_orders",  # FIXED: was 'go' (empty collection)
                    scroll_filter=None, # Ideally filter by has_relations=True if available
                    limit=1000,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                for point in points:
                    relations = point.payload.get("relations", [])
                    if not relations:
                        continue
                        
                    for rel in relations:
                        if rel.get("relation_type") == "supersedes":
                            target = rel.get("target")
                            # We need to resolve 'target' (e.g. "G.O.Ms.No.123") to a doc_id if possible.
                            # This is hard without a reverse lookup map.
                            # BUT, often the relation metadata might contain the target_id if we were smart.
                            # If not, we might only be able to warn about the *text* target.
                            
                            # However, if we look at the OTHER side:
                            # A document might say "This order supersedes G.O.Ms.No.X".
                            # So the CURRENT document is the NEW one. The TARGET is the OLD one.
                            # We want to mark the TARGET as superseded.
                            
                            # For now, let's store the raw target string.
                            # Realistically, to be effective, we need to map "G.O.Ms.No.123" -> Doc ID.
                            # We can build a lookup map of "GO Number" -> "Doc ID" while we scroll.
                            pass

                if offset is None:
                    break
            
            # Since resolving text targets to IDs is complex at runtime without a pre-built map,
            # we will implement a simpler approach:
            # 1. Build a map of GO Number -> Doc ID from all docs.
            # 2. Build a list of (New Doc ID, Superseded GO Number).
            # 3. Map Superseded GO Number -> Superseded Doc ID.
            
            self._build_supersession_map()
            
        except Exception as e:
            logger.error(f"Failed to load supersession data: {e}")

    def _build_supersession_map(self):
        """
        Builds the map of superseded documents.
        OPTIMIZED: Only scans documents with relations to avoid full collection scan
        """
        go_number_to_id = {}
        supersession_claims = [] # List of (new_doc_id, superseded_go_number_str)
        
        try:
            import time
            start_time = time.time()
            
            # Check if we have a wrapper or real client
            client_instance = self.client.client if hasattr(self.client, 'client') else self.client
            
            # OPTIMIZATION: Only fetch documents that have relations
            # This reduces scan from 5495 to ~few hundred documents
            scroll_filter = {
                "must": [
                    {"key": "has_relations", "match": {"value": True}}
                ]
            }
            
            offset = None
            docs_scanned = 0
            relations_found = 0
            
            while True:
                points, offset = client_instance.scroll(
                    collection_name="ap_government_orders",
                    scroll_filter=scroll_filter,  # OPTIMIZED: Filter to docs with relations only
                    limit=1000,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                docs_scanned += len(points)
                
                for point in points:
                    doc_id = point.payload.get("doc_id")
                    go_number = point.payload.get("go_number")
                    
                    # Map GO number to Doc ID
                    if go_number and doc_id:
                        # Normalize GO number (keep as-is for now)
                        clean_go = str(go_number).strip()
                        go_number_to_id[clean_go] = doc_id
                        
                    # Check for supersession claims
                    relations = point.payload.get("relations", [])
                    for rel in relations:
                        rel_type = rel.get("relation_type") or rel.get("type")
                        if rel_type == "supersedes":
                            relations_found += 1
                            target = rel.get("target", "")
                            # Extract number from target string "G.O.Ms.No.123"
                            import re
                            match = re.search(r'(\d+)', target)
                            if match:
                                superseded_num = match.group(1)
                                supersession_claims.append((doc_id, superseded_num))
                
                if offset is None:
                    break
            
            # Now resolve claims
            for new_id, old_num in supersession_claims:
                if old_num in go_number_to_id:
                    old_id = go_number_to_id[old_num]
                    # Avoid self-supersession loops or errors
                    if old_id != new_id:
                        self.superseded_ids.add(old_id)
                        self.supersession_map[old_id] = new_id
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Supersession map built in {elapsed:.2f}s")
            logger.info(f"   Scanned {docs_scanned} docs with relations, found {relations_found} 'supersedes' relations")
            logger.info(f"   Result: {len(self.superseded_ids)} superseded documents")
            
        except Exception as e:
            logger.error(f"Error building supersession map: {e}")

    def is_superseded(self, doc_id: str) -> bool:
        """Check if a document is superseded"""
        return doc_id in self.superseded_ids
        
    def get_superseding_doc_id(self, doc_id: str) -> Optional[str]:
        """Get the ID of the document that superseded this one"""
        return self.supersession_map.get(doc_id)
