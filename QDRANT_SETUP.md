# Qdrant Connection Status

## Current Status: ❌ Not Connected

**Error**: Connection refused on `http://localhost:6333`

This means Qdrant is not running locally.

---

## Options to Fix

### Option 1: Run Qdrant Locally (Docker - Recommended)

**Quick Start:**
```bash
# Run Qdrant in Docker
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Or with persistent storage
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

**Verify it's running:**
```bash
curl http://localhost:6333/health
# Should return: {"status":"ok"}
```

### Option 2: Use Qdrant Cloud (Remote)

If you have a Qdrant Cloud account:

1. Get your cluster URL and API key from Qdrant Cloud dashboard
2. Set environment variables:
   ```bash
   export QDRANT_URL="https://your-cluster-url.qdrant.io"
   export QDRANT_API_KEY="your-api-key"
   ```
3. Test connection:
   ```bash
   python3 test_qdrant_connection.py
   ```

### Option 3: Install Qdrant Locally (macOS)

```bash
# Using Homebrew
brew install qdrant

# Start Qdrant
qdrant
```

---

## Configuration

The system is configured to use:
- **Default URL**: `http://localhost:6333`
- **Timeout**: 30 seconds
- **API Key**: Optional (only needed for cloud)

You can override these with environment variables:
```bash
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-key-if-needed"
```

---

## Test Connection

Once Qdrant is running, test the connection:
```bash
source .venv/bin/activate
python3 test_qdrant_connection.py
```

---

## Expected Collections

Once connected, you should see these collections (after embedding):
- `ap_legal_documents`
- `ap_government_orders`
- `ap_judicial_documents`
- `ap_data_reports`
- `ap_schemes`

---

## Next Steps

1. **Start Qdrant** (choose one option above)
2. **Test connection**: `python3 test_qdrant_connection.py`
3. **Embed your data** (once Qdrant is running)
4. **Start retrieving**!

