# GCS Credentials - Quick Reference Guide

## 📍 Where to Put Credentials

### File Location
```
/Users/nitin/Desktop/AP Policy Assitant Main NO BS/
└── .env                          👈 Add credentials here
```

### What to Add to `.env`

```bash
# GCS Configuration for PDF Viewer
GCS_BUCKET_NAME=your-bucket-name-here
GOOGLE_APPLICATION_CREDENTIALS=/Users/nitin/.gcp/pdf-viewer-credentials.json
```

---

## 🔑 What Credentials You Need

### 1. GCS Bucket Name
**What it is**: The name of your Google Cloud Storage bucket where PDFs are stored

**Example**: `ap-policy-pdfs` or `my-documents-bucket`

**How to find it**:
- Go to: https://console.cloud.google.com/storage/browser
- You'll see a list of buckets
- Copy the bucket name (NOT the full `gs://bucket-name` URL, just the name)

### 2. Service Account JSON File
**What it is**: A JSON file containing authentication credentials

**How to get it**:

#### Quick Method (Recommended):
```bash
# Run the interactive setup script
./setup_gcs_credentials.sh
```

#### Manual Method:

**Step 1**: Go to Google Cloud Console
- URL: https://console.cloud.google.com/iam-admin/serviceaccounts
- Select your project

**Step 2**: Create Service Account
- Click "Create Service Account"
- Name: `pdf-viewer-service`
- Click "Create and Continue"

**Step 3**: Grant Permissions
- Role 1: `Storage Object Viewer`
- Role 2: `Storage Object Admin` (needed for signed URLs)
- Click "Continue" → "Done"

**Step 4**: Create JSON Key
- Click on the service account you just created
- Go to "Keys" tab
- Click "Add Key" → "Create new key"
- Choose "JSON"
- Click "Create"
- **Save the downloaded JSON file**

**Step 5**: Move JSON to Secure Location
```bash
# Create secure directory
mkdir -p ~/.gcp
chmod 700 ~/.gcp

# Move the downloaded file
mv ~/Downloads/your-project-xxxxx.json ~/.gcp/pdf-viewer-credentials.json
chmod 600 ~/.gcp/pdf-viewer-credentials.json
```

---

## ✅ Quick Setup (Easiest Way)

Just run this script and follow the prompts:

```bash
cd /Users/nitin/Desktop/AP\ Policy\ Assitant\ Main\ NO\ BS
./setup_gcs_credentials.sh
```

The script will:
1. ✅ Ask for your bucket name
2. ✅ Verify the bucket exists
3. ✅ Help you set up authentication
4. ✅ Update your `.env` file automatically
5. ✅ Run verification to confirm everything works

---

## 🔍 Verify Setup

After adding credentials, verify they work:

```bash
cd retrieval_v3/infra
python verify_gcs_setup.py
```

**Expected output**:
```
🔍 GCS Setup Verification
==================================================

1. Environment Variables
========================
✅ GCS_BUCKET_NAME: your-bucket-name
✅ GOOGLE_APPLICATION_CREDENTIALS: /path/to/credentials.json

2. GCS Authentication
=====================
✅ Authenticated using service account
✅ Project: your-project-id

... (more checks)
```

---

## 🐛 Troubleshooting

### "GCS_BUCKET_NAME not set"
**Solution**: Add `GCS_BUCKET_NAME=your-bucket-name` to `.env` file

### "Cannot find credentials file"
**Solution**: Check the path in `GOOGLE_APPLICATION_CREDENTIALS` is correct

### "Access denied to bucket"
**Solution**: 
1. Ensure service account has `Storage Object Viewer` role
2. Grant permission:
   ```bash
   gsutil iam ch serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com:objectViewer gs://YOUR_BUCKET
   ```

### "Invalid JSON file"
**Solution**: Re-download the service account key from Google Cloud Console

---

## 📋 Summary

**What you need**:
1. Bucket name (e.g., `ap-policy-pdfs`)
2. Service account JSON file

**Where to put them**:
- Bucket name → `.env` file as `GCS_BUCKET_NAME=...`
- JSON file → Save to `~/.gcp/` and reference in `.env` as `GOOGLE_APPLICATION_CREDENTIALS=...`

**Easiest way**:
```bash
./setup_gcs_credentials.sh
```

**Verify it works**:
```bash
cd retrieval_v3/infra && python verify_gcs_setup.py
```

---

## 🔗 Helpful Links

- **GCS Console**: https://console.cloud.google.com/storage/browser
- **Service Accounts**: https://console.cloud.google.com/iam-admin/serviceaccounts
- **IAM Permissions**: https://console.cloud.google.com/iam-admin/iam

---

**Need help?** Run `./setup_gcs_credentials.sh` - it will guide you through the process!
