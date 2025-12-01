# Infrastructure Issues - Requires User Action

## 1. Gemini API Model Name Issue

**Error:** `404 models/gemini-1.5-flash-002 is not found`

**Status:** Updated all code to use `gemini-1.5-flash-latest` alias

**Possible Causes:**
- API key might be invalid or expired
- API endpoint configuration issue  
- Need to check if using correct Google AI SDK vs Vertex AI

**Action Required:**
1. Verify `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable is set correctly
2. Check if API key has access to Gemini models
3. Try testing with a simple script:
```python
import google.generativeai as genai
genai.configure(api_key="YOUR_KEY")
model = genai.GenerativeModel('gemini-1.5-flash-latest')
response = model.generate_content("Hello")
print(response.text)
```

---

## 2. Missing Qdrant Collection

**Error:** `Not found: Collection 'go' doesn't exist`

**Impact:** Supersession tracking for Government Orders will not work

**Action Required:**
- Create the `go` collection in Qdrant OR
- Update code to use correct collection name (likely `ap_government_orders`)

**Fix Location:** Check `SupersessionManager` initialization

---

## 3. Empty BM25 Index

**Error:** `BM25 index with 0 documents`, `BM25 index is None after ensure_ready`

**Impact:** Only vector search works, no sparse retrieval → weaker results

**Action Required:**
1. Build BM25 index from your documents
2. Run indexing script to populate BM25
3. Verify BM25 index file exists and is loaded correctly

---

## 4. Missing Qdrant Indexes for Entity Fields

**Warning:** `Skipping unindexed entity type: years`

**Impact:** Entity expansion limited to indexed fields only

**Currently Indexed:**
- ✅ `entities.departments`
- ✅ `entities.acts`
- ✅ `entities.schemes`
- ✅ `entities.go_numbers`
- ✅ `entities.sections`

**NOT Indexed (being skipped):**
- ❌ `entities.years`
- ❌ `entities.keywords`
- ❌ `entities.dates`

**Action Required:**
Create Qdrant payload indexes for these fields:
```python
client.create_payload_index(
    collection_name="ap_government_orders",
    field_name="entities.years",
    field_schema="keyword"
)
```

---

## Summary

**Code fixes completed:**
- ✅ Qdrant Nested filter syntax
- ✅ Gemini model names updated to `-latest` alias
- ✅ Entity expansion defensive checks

**Infrastructure issues (require user action):**
- ⚠️ Gemini API key/configuration
- ⚠️ Missing 'go' collection
- ⚠️ Empty BM25 index
- ⚠️ Missing entity field indexes
