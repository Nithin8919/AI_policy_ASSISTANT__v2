yes# P1 Quick Wins - Implementation Guide

## Overview
5 high-impact changes for -50% latency and +15% recall improvement.

---

## Quick Win #1: Section Type Boost (Item 26)

**File**: `retrieval_v3/pipeline/retrieval_engine.py`
**Location**: Line ~418, after RRF fusion in `_single_hybrid_search()`
**Impact**: Prioritize "orders" sections over "annexure" and "preamble"

**Add before `return fused_results`**:
```python
# P1 Quick Win #1: Apply section type boost
try:
    from retrieval_v3.retrieval_core.scoring import section_type_boost
    for result in fused_results:
        section_type = result.metadata.get('section_type')
        if section_type:
            boost = section_type_boost(section_type)
            if boost > 1.0:
                result.score *= boost
                result.metadata['section_boost'] = boost
except Exception as e:
    logger.warning(f"Section boost failed: {e}")
```

---

## Quick Win #2: Surgical Neighbor Expansion (Item 21)

**File**: `retrieval_v3/retrieval/relation_reranker.py`
**Location**: Line ~276, `_expand_with_neighbors()` method
**Impact**: Reduce from 30+ scrolls to 1-2 lookups

**Replace entire method**:
```python
def _expand_with_neighbors(
    self,
    results: List[RelationResult],
    max_neighbors: int = 5
) -> List[RelationResult]:
    """
    P1 Quick Win #2: Surgical neighbor expansion
    - ONLY expand from top-20
    - ONLY along amends/supersedes relations
    - Skip if recent docs already present
    """
    # ONLY expand from top-20
    top_results = results[:20]
    
    # ONLY expand along amends/supersedes
    valid_rel_types = {'amends', 'supersedes'}
    
    # Skip if we already have recent docs for this GO family
    recent_go_numbers = {
        r.metadata.get('go_number')
        for r in top_results
        if r.metadata.get('year') and int(r.metadata.get('year', 0)) >= 2024
    }
    
    neighbors = []
    for result in top_results:
        relations = result.metadata.get('relations', [])
        
        for rel in relations[:max_neighbors]:
            rel_type = rel.get('relation_type')
            if rel_type not in valid_rel_types:
                continue
            
            target = rel.get('target')
            if not target:
                continue
            
            # Skip if we already have recent version
            if any(go_num and go_num in target for go_num in recent_go_numbers if go_num):
                continue
            
            # Fetch neighbor (single lookup, not scroll)
            try:
                # Use points/get instead of scroll
                points = self._client.retrieve(
                    collection_name="ap_government_orders",
                    ids=[target],
                    with_payload=True,
                    with_vectors=False
                )
                if points:
                    # Convert to RelationResult format
                    neighbor = self._point_to_result(points[0])
                    neighbors.append(neighbor)
            except Exception as e:
                logger.warning(f"Failed to fetch neighbor {target}: {e}")
                continue
    
    logger.info(f"   ✅ Fetched {len(neighbors)} neighbors (surgical expansion)")
    return results + neighbors
```

---

## Quick Win #3: Auto-Pin Filters for "Recent GOs" (Item 24)

**File**: `retrieval_v3/pipeline/retrieval_engine.py`
**Location**: Line ~200, start of `retrieve()` method
**Impact**: Force correct filters for "recent" queries

**Add after query normalization**:
```python
# P1 Quick Win #3: Auto-pin filters for "recent GOs" queries
force_filter = None
if "recent" in normalized_query.lower() and "go" in normalized_query.lower():
    import time
    now_ts = int(time.time())
    eighteen_months_ago = now_ts - (18 * 30 * 86400)
    
    force_filter = {
        "must": [
            {"key": "vertical", "match": {"value": "go"}},
            {"key": "date_issued_ts", "range": {"gte": eighteen_months_ago}}
        ]
    }
    
    # Extract department if mentioned
    if "school education" in normalized_query.lower():
        force_filter["must"].append({
            "key": "department",
            "match": {"value": "School Education"}
        })
    
    logger.info(f"🎯 Auto-pinned filters for recent GOs query")

# Pass force_filter to search methods
if force_filter:
    # Apply to all collection searches
    plan.force_filter = force_filter
```

---

## Quick Win #4: Replace Scroll Storm with Filter Query (Item 13)

**File**: `retrieval_v3/retrieval/relation_reranker.py`
**Location**: `EntityExpander` class, wherever scroll is used
**Impact**: Replace 30+ scroll calls with 1 filter query

**Add new method to EntityExpander**:
```python
def _fetch_by_filter(self, filters: dict, limit: int = 50) -> List:
    """
    P1 Quick Win #4: Single filter query instead of scroll storm
    """
    try:
        # Use query_points with filter instead of scroll
        results = self._client.query_points(
            collection_name="ap_government_orders",
            query_filter=filters,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        return results.points if results else []
    except Exception as e:
        logger.warning(f"Filter query failed: {e}")
        return []

# Example usage for recent GOs:
def _fetch_recent_gos(self, department: str, limit: int = 50):
    """Fetch recent GOs using filter query"""
    import time
    now_ts = int(time.time())
    eighteen_months_ago = now_ts - (18 * 30 * 86400)
    
    filters = {
        "must": [
            {"key": "vertical", "match": {"value": "go"}},
            {"key": "department", "match": {"value": department}},
            {"key": "date_issued_ts", "range": {"gte": eighteen_months_ago}}
        ]
    }
    
    return self._fetch_by_filter(filters, limit)
```

---

## Quick Win #5: Parallelize BM25/Dense Calls (Item 31)

**File**: `retrieval_v3/pipeline/retrieval_engine.py`
**Location**: Line ~370, `_single_hybrid_search()` method
**Impact**: Run BM25 and Dense searches concurrently

**Replace sequential calls with parallel**:
```python
# P1 Quick Win #5: Parallelize BM25 and Dense searches
import concurrent.futures
import time

def _single_hybrid_search(search_query: str, hop: int = 1):
    """Hybrid search with parallelized BM25 and Dense"""
    
    vector_res = []
    bm25_res = []
    
    # Define search functions
    def run_vector_search():
        return self._parallel_retrieve_hop(
            [search_query],
            collection_names,
            top_k=plan.top_k_per_vertical,
            hop_number=hop
        )
    
    def run_bm25_search():
        if self.bm25_retriever:
            raw = self.bm25_retriever.search(search_query, top_k=plan.top_k_per_vertical)
            return self._convert_bm25_to_results(raw)
        return []
    
    # Run in parallel with timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_vector = executor.submit(run_vector_search)
        future_bm25 = executor.submit(run_bm25_search)
        
        try:
            vector_res = future_vector.result(timeout=5.0)  # 5s timeout
            bm25_res = future_bm25.result(timeout=2.0)      # 2s timeout
        except concurrent.futures.TimeoutError:
            logger.warning("Search timeout - using partial results")
            vector_res = future_vector.result() if future_vector.done() else []
            bm25_res = future_bm25.result() if future_bm25.done() else []
    
    # Continue with RRF fusion...
```

---

## Implementation Order

1. ✅ **Quick Win #1** - Section boost (5 min) - Easiest, immediate impact
2. ✅ **Quick Win #3** - Auto-pin filters (10 min) - High impact for "recent" queries
3. ✅ **Quick Win #5** - Parallelize (15 min) - Biggest latency win
4. ✅ **Quick Win #4** - Replace scroll (20 min) - Requires careful testing
5. ✅ **Quick Win #2** - Surgical expansion (30 min) - Most complex

**Total Time**: ~1.5 hours
**Expected Impact**: -50% latency, +15% recall for "recent GOs" queries

---

## Testing Commands

After each change:
```bash
# Test scoring
.venv/bin/python -c "
from retrieval_v3.retrieval_core.scoring import section_type_boost
print(f'Orders boost: {section_type_boost(\"orders\")}')
"

# Test retrieval
.venv/bin/python -c "
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
from retrieval.retrieval_core.qdrant_client import get_qdrant_client

client = get_qdrant_client()
engine = RetrievalEngine(qdrant_client=client)

import time
start = time.time()
results = engine.retrieve('What are the recent GOs related to school education in AP?')
elapsed = time.time() - start

print(f'Results: {len(results.results)}')
print(f'Time: {elapsed:.2f}s')
for r in results.results[:5]:
    print(f'  {r.doc_id}: {r.score:.3f}')
"
```

---

## Success Metrics

**Before P1**:
- Latency: ~31s for 10 results
- Entity expansion: 30+ scroll calls
- No section prioritization
- No filter optimization

**After P1** (Target):
- Latency: <15s for 10 results (-50%)
- Entity expansion: 1-2 lookups
- Orders sections prioritized
- Recent queries auto-filtered
- BM25/Dense parallel execution

---

## Rollback Plan

If any Quick Win causes issues:
1. Comment out the specific change
2. System continues with P0 fixes intact
3. All changes are additive and independent
