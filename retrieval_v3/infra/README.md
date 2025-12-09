# GCS Infrastructure Setup for PDF Viewer

This directory contains infrastructure configuration and setup scripts for the PDF viewer feature's Google Cloud Storage integration.

## 📁 Files

### `gcs_cors_config.json`
CORS configuration for the GCS bucket. This allows the frontend to access PDFs directly from GCS.

**Current Configuration:**
- **Origins**: `http://localhost:3000`, `http://localhost:8000` (development)
- **Methods**: `GET`, `HEAD`, `OPTIONS`
- **Headers**: Required headers for PDF.js range requests
- **Max Age**: 3600 seconds (1 hour)

**For Production:**
Update the `origin` array to include your production domain:
```json
"origin": [
  "https://your-production-domain.com",
  "http://localhost:3000"
]
```

### `setup_gcs_cors.sh`
Shell script to apply CORS configuration to your GCS bucket.

**Usage:**
```bash
export GCS_BUCKET_NAME=your-bucket-name
./setup_gcs_cors.sh
```

Or in one line:
```bash
GCS_BUCKET_NAME=your-bucket-name ./setup_gcs_cors.sh
```

**What it does:**
1. Validates environment variables
2. Shows the CORS configuration
3. Asks for confirmation
4. Applies CORS to the bucket
5. Verifies the configuration

### `verify_gcs_setup.py`
Comprehensive verification script that checks your entire GCS setup.

**Usage:**
```bash
export GCS_BUCKET_NAME=your-bucket-name
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json  # Optional
python verify_gcs_setup.py
```

**What it checks:**
1. ✅ Environment variables are set
2. ✅ GCS authentication is working
3. ✅ Bucket exists and is accessible
4. ✅ CORS configuration is correct
5. ✅ PDF files are present
6. ✅ Signed URL generation works

---

## 🚀 Quick Start

### Step 1: Set Environment Variables

Add to your `.env` file:
```bash
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Step 2: Verify Setup

Run the verification script to check everything:
```bash
cd retrieval_v3/infra
python verify_gcs_setup.py
```

### Step 3: Configure CORS

If CORS is not configured (verification script will tell you):
```bash
./setup_gcs_cors.sh
```

### Step 4: Test the API

Test the PDF viewer endpoints:
```bash
# Get signed URL
curl "http://localhost:8000/api/pdf-url?doc_id=2018se_ms70"

# Locate snippet
curl -X POST "http://localhost:8000/api/locate-snippet" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "2018se_ms70",
    "snippet": "your text snippet here"
  }'
```

---

## 🔐 Authentication Setup

### Option 1: Service Account (Recommended for Production)

1. Create a service account in Google Cloud Console
2. Grant it these permissions:
   - `storage.buckets.get`
   - `storage.objects.get`
   - `storage.objects.list`
3. Download the JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the file path

### Option 2: Application Default Credentials (Development)

```bash
gcloud auth application-default login
```

This uses your personal Google Cloud credentials.

---

## 🛠️ Troubleshooting

### "GCS_BUCKET_NAME not set"
Set the environment variable:
```bash
export GCS_BUCKET_NAME=your-bucket-name
```

### "Access denied to bucket"
Ensure your service account has the required permissions:
- `storage.buckets.get`
- `storage.objects.get`
- `storage.objects.list`

### "CORS configuration not found"
Run the CORS setup script:
```bash
./setup_gcs_cors.sh
```

### "PDF not found"
Check that:
1. The PDF file exists in your bucket
2. The filename matches the expected format (e.g., `2018SE_MS70.PDF`)
3. The `doc_id_to_pdf_filename()` function correctly converts doc_id to filename

---

## 📋 CORS Configuration Details

The CORS configuration allows:

1. **Range Requests**: Required for PDF.js to load large PDFs efficiently
2. **Content-Type Headers**: Ensures PDFs are served with correct MIME type
3. **Cache Control**: Allows browsers to cache PDF responses
4. **ETag Support**: Enables conditional requests

**Why these headers matter:**
- `Content-Range`: PDF.js uses range requests to load only visible pages
- `Accept-Ranges`: Tells the browser that range requests are supported
- `ETag`: Enables efficient caching and revalidation

---

## 🔄 Updating CORS for Production

1. Edit `gcs_cors_config.json`
2. Add your production domain to the `origin` array
3. Run `./setup_gcs_cors.sh` again
4. Verify with `python verify_gcs_setup.py`

Example production config:
```json
{
  "origin": [
    "https://policy-assistant.example.com",
    "https://staging.policy-assistant.example.com",
    "http://localhost:3000"
  ],
  "method": ["GET", "HEAD", "OPTIONS"],
  "responseHeader": [
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Cache-Control",
    "ETag"
  ],
  "maxAgeSeconds": 3600
}
```

---

## 📊 Monitoring

After setup, monitor:

1. **Signed URL Generation**: Check backend logs for URL generation
2. **CORS Errors**: Check browser console for CORS-related errors
3. **PDF Load Times**: Monitor PDF.js loading performance
4. **GCS Costs**: Monitor GCS egress and storage costs

---

## 🔗 Related Documentation

- [Google Cloud Storage CORS](https://cloud.google.com/storage/docs/cross-origin)
- [PDF.js Documentation](https://mozilla.github.io/pdf.js/)
- [Signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls)

---

## ✅ Checklist

Before deploying to production:

- [ ] Service account created with minimal permissions
- [ ] CORS configured with production domain
- [ ] Environment variables set in production
- [ ] Verification script passes all checks
- [ ] PDF viewer tested in frontend
- [ ] Signed URLs expire appropriately (60 minutes default)
- [ ] Error handling tested (missing PDFs, invalid doc_ids)
- [ ] Monitoring and logging configured
