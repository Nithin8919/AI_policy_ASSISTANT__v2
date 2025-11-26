# Query Processing Analysis: "What is Section 12?"

## Overview

This document analyzes how the query "What is Section 12?" is processed through the retrieval system, focusing on where filters like "section_number" are generated and applied.

## Complete Query Processing Flow

### 1. Query Entry Point
- **File**: `/retrieval/router.py` (lines 49-146)
- **Function**: `RetrievalRouter.query()`
- The main entry point that orchestrates the entire pipeline

### 2. Query Planning Phase
- **File**: `/retrieval/query_processing/query_plan.py` (lines 99-181)
- **Function**: `QueryPlanner.build_plan()`
- Creates a complete retrieval plan by coordinating all query processing components

#### Step-by-step processing for "What is Section 12?":

**2.1 Query Normalization**
- **File**: `/retrieval/query_processing/normalizer.py`
- Basic text cleaning and normalization

**2.2 Entity Extraction**
- **File**: `/retrieval/query_processing/entity_extractor.py` (lines 64-93)
- **Function**: `EntityExtractor.extract()`
- **Key Pattern**: Line 31 - `r'\bsection\s+(\d+[A-Za-z]*(?:\(\d+\))?(?:\([a-z]\))?)'`
- **Result**: Extracts "Section 12" → normalized as "12"

```python
# Pattern matches "Section 12" in the query
entities = {
    'section': [
        ExtractedEntity(
            type='section',
            value='Section 12',
            normalized='12',
            start=8,
            end=18
        )
    ]
}
```

**2.3 Intent Classification**
- **File**: `/retrieval/query_processing/intent_classifier.py` (lines 39-83)
- **Function**: `IntentClassifier.classify()`
- **Key Logic**: 
  - Detects "what is" keyword (QA mode)
  - Detects specific entity pattern "section\s+\d+" (line 96)
  - **Result**: Mode = QA, Confidence = 0.9

**2.4 Query Enhancement**
- **File**: `/retrieval/query_processing/query_enhancer.py` (lines 56-105)
- **Function**: `QueryEnhancer.enhance()`
- Adds synonyms and entity context to improve retrieval

**2.5 Filter Building (CRITICAL)**
- **File**: `/retrieval/query_processing/query_enhancer.py` (lines 121-151)
- **Function**: `QueryEnhancer.build_filter_dict()`
- **KEY LINE 149**: `filters["section_number"] = sections`

```python
# This is where "section_number" filter is created
def build_filter_dict(self, entities: Dict) -> Dict[str, List[str]]:
    filters = {}
    
    # Section filter - LINE 147-149
    sections = self.entity_extractor.get_entity_values(entities, "section")
    if sections:
        filters["section_number"] = sections  # Creates filter: {"section_number": ["12"]}
    
    return filters
```

**2.6 Vertical Routing**
- **File**: `/retrieval/query_processing/query_router.py` (lines 47-85)
- **Function**: `QueryRouter.route()`
- **Result**: Routes to "legal" vertical due to "section" keyword + entity bonus

### 3. Retrieval Execution Phase

**3.1 Query Embedding**
- **File**: `/retrieval/embeddings/embedding_router.py`
- Converts enhanced query to vector representation

**3.2 Vertical Retrieval**
- **File**: `/retrieval/retrieval_core/vertical_retriever.py` (lines 22-74)
- **Function**: `VerticalRetriever.retrieve()`
- **Key Logic**: Lines 55-67 - Applies filters during Qdrant search

**3.3 Qdrant Filter Construction**
- **File**: `/retrieval/retrieval_core/vertical_retriever.py` (lines 76-115)
- **Function**: `_build_qdrant_filter()`
- Converts simple filter dict to Qdrant filter format:

```python
# Input: {"section_number": ["12"]}
# Output: {"section_number": "12"} (for single value)
```

**3.4 Qdrant Search Execution**
- **File**: `/retrieval/retrieval_core/qdrant_client.py` (lines 36-85)
- **Function**: `QdrantClientWrapper.search()`
- **Line 68**: `query_filter=query_filter` - Passes filter to Qdrant

## Filter Application in Qdrant

The final Qdrant search call looks like:
```python
client.query_points(
    collection_name="ap_legal_documents",
    query=query_vector,
    limit=10,
    query_filter={"section_number": "12"},  # This filters for chunks with section_number = "12"
    with_payload=True
)
```

## Data Structure in Qdrant

During ingestion, legal documents are parsed and chunked with metadata:

### Ingestion Side (Where section_number is stored)
- **File**: `/ingestion_v2/structure/legal_structure.py` (lines 140-172)
- **Function**: `_find_sections()`
- Extracts sections using regex pattern: `r'^(?:Section|Sec\.?)\s+(\d+(?:\([a-zA-Z0-9]+\))?)'`

### Legal Structure Enhancement
- **File**: `/retrieval/verticals/legal_retrieval.py` (lines 20-53)
- **Function**: `enhance_filters()`
- Provides additional legal-specific filter enhancement

## Complete Flow Summary

1. **Query**: "What is Section 12?" enters system
2. **Entity Extraction**: Detects section entity, normalizes "12"
3. **Intent Classification**: Determines QA mode (confidence 0.9)
4. **Filter Building**: Creates `{"section_number": ["12"]}` filter
5. **Vertical Routing**: Routes to "legal" vertical
6. **Query Enhancement**: Adds synonyms and context
7. **Embedding**: Converts to vector
8. **Qdrant Search**: Searches `ap_legal_documents` with section_number filter
9. **Results**: Returns chunks where `metadata.section_number = "12"`
10. **Answer Generation**: LLM synthesizes final answer from filtered results

## Key Files for Filter Generation

1. **Entity Extraction**: `/retrieval/query_processing/entity_extractor.py`
   - Line 31: Section regex pattern
   - Lines 64-93: Extract method
   - Lines 95-121: Normalization logic

2. **Filter Building**: `/retrieval/query_processing/query_enhancer.py`
   - Lines 147-149: **Critical section_number filter creation**
   - Lines 121-151: Filter building logic

3. **Filter Application**: `/retrieval/retrieval_core/vertical_retriever.py`
   - Lines 55-67: Filter application
   - Lines 76-115: Qdrant filter construction

4. **Qdrant Integration**: `/retrieval/retrieval_core/qdrant_client.py`
   - Line 68: Filter parameter in search call

## Testing the Flow

The debug script `/debug_section12_query.py` demonstrates the complete processing:

```
Query: 'What is Section 12?'
Mode: QA (confidence: 0.9)
Primary Vertical: legal  
Filters Applied: {'section_number': ['12']}
```

This filter ensures that only legal document chunks containing Section 12 content are retrieved, providing precise and relevant results for the user's query.