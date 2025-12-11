# OAuth/Vertex AI Permission Fix Instructions

## Problem Summary
Your service account `pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com` lacks the required permission to use Vertex AI models. This causes 403 PERMISSION_DENIED errors when trying to use Gemini models for:
- Internet search (google_search_client.py)
- Query rewriting (query_rewriter.py)
- Answer generation (answer_builder.py)

## Current Status
✅ **OAuth Configuration**: Properly configured
- Service Account: `pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com`
- Project: `tech-bharath`
- Location: `asia-south1`
- Credentials File: `/Users/nitin/pdf-viewer-key.json`
- Scopes: `cloud-platform`, `generative-language.retriever`

❌ **Missing Permission**: `aiplatform.endpoints.predict`

## Solution: Grant Vertex AI Permissions

### Option 1: Using gcloud CLI (Recommended)
You need someone with **Project IAM Admin** or **Owner** role to run:

```bash
gcloud projects add-iam-policy-binding tech-bharath \
    --member='serviceAccount:pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com' \
    --role='roles/aiplatform.user'
```

### Option 2: Using Google Cloud Console
1. Go to [Google Cloud Console IAM](https://console.cloud.google.com/iam-admin/iam?project=tech-bharath)
2. Find the service account: `pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com`
3. Click "Edit Principal" (pencil icon)
4. Click "Add Another Role"
5. Search for and select: **Vertex AI User** (`roles/aiplatform.user`)
6. Click "Save"

### Option 3: Custom Role with Minimal Permissions
If you want minimal permissions instead of the full `aiplatform.user` role:

```bash
# Create custom role
gcloud iam roles create vertexAIPredict \
    --project=tech-bharath \
    --title="Vertex AI Predict Only" \
    --description="Minimal permission for Vertex AI model prediction" \
    --permissions=aiplatform.endpoints.predict

# Assign to service account
gcloud projects add-iam-policy-binding tech-bharath \
    --member='serviceAccount:pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com' \
    --role='projects/tech-bharath/roles/vertexAIPredict'
```

## Verification

After granting permissions, verify the fix:

```bash
# Run the OAuth diagnostic script
python3 scripts/check_oauth_setup.py
```

Expected output:
```
✅ All checks passed! Your OAuth/Vertex AI setup is working correctly.
```

## Code Changes Made

### 1. Removed API Key Fallback from Internet Search
**File**: `retrieval_v3/internet/google_search_client.py`
- **Change**: Removed automatic fallback to AI Studio when Vertex AI returns 403
- **Reason**: Enforce OAuth-only authentication, making permission issues visible
- **Impact**: System will fail fast with clear error messages instead of silently falling back

### 2. Query Rewriter Already OAuth-Only
**File**: `retrieval_v3/query_understanding/query_rewriter.py`
- **Status**: Already configured for OAuth-only (no API key fallback)
- **Behavior**: Falls back to rule-based rewrites on permission errors

## What Happens Now

### Before Permission Grant:
```
⚠️ Vertex AI permission denied (403) for gemini-2.5-flash
💡 Service account needs 'roles/aiplatform.user' role. Contact your GCP admin.
ERROR: Internet search failed for all tried models
```

### After Permission Grant:
```
✅ Initialized GoogleSearchClient with Vertex AI (ADC/gcloud)
✅ Internet search succeeded with model: gemini-2.5-flash
✅ Found 5 web results
```

## Important Notes

1. **No API Key Fallback**: The system now strictly uses OAuth/service account credentials
2. **Clear Error Messages**: Permission issues are immediately visible in logs
3. **All Services Affected**: This fix enables:
   - Internet search functionality
   - LLM-based query rewriting
   - Advanced answer generation
4. **No Code Changes Needed After Permission Grant**: Once permissions are granted, everything will work automatically

## Contact Your Admin

If you don't have permission to modify IAM policies, send this to your GCP admin:

---

**Subject**: Grant Vertex AI Permissions to Service Account

Hi,

Please grant the **Vertex AI User** role to our service account for the AI Policy Assistant application:

- **Service Account**: `pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com`
- **Project**: `tech-bharath`
- **Role Needed**: `roles/aiplatform.user`

**Command to run**:
```bash
gcloud projects add-iam-policy-binding tech-bharath \
    --member='serviceAccount:pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com' \
    --role='roles/aiplatform.user'
```

This will enable the application to use Gemini models via Vertex AI for internet search and query processing.

Thanks!

---

## Troubleshooting

### Still getting 403 errors after granting permissions?
1. Wait 1-2 minutes for IAM changes to propagate
2. Restart your application
3. Run the diagnostic script again: `python3 scripts/check_oauth_setup.py`

### Need to verify current permissions?
```bash
gcloud projects get-iam-policy tech-bharath \
    --flatten="bindings[].members" \
    --filter="bindings.members:pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com"
```

### Want to test with a different service account?
Update the `.env` file:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/new-service-account-key.json
```
