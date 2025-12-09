# GCS Service Account Setup for Signed URLs

## ⚠️ Important: Application Default Credentials Cannot Generate Signed URLs

You've successfully authenticated with `gcloud auth application-default login`, but **user credentials cannot generate signed URLs**. You need a **service account** with a private key.

## 🔑 Quick Fix: Create a Service Account

### Option 1: Using gcloud CLI (Recommended - Fastest)

```bash
# 1. Set your project
export PROJECT_ID="tech-bharath"
export SERVICE_ACCOUNT_NAME="pdf-viewer-sa"

# 2. Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="PDF Viewer Service Account" \
    --project=$PROJECT_ID

# 3. Grant Storage Object Admin role (needed for signed URLs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# 4. Create and download JSON key
gcloud iam service-accounts keys create ~/pdf-viewer-key.json \
    --iam-account="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 5. Update .env file
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/pdf-viewer-key.json" >> .env

echo "✅ Service account created and configured!"
echo "Key saved to: ~/pdf-viewer-key.json"
```

### Option 2: Using Google Cloud Console (Manual)

1. **Go to Service Accounts page:**
   - https://console.cloud.google.com/iam-admin/serviceaccounts?project=tech-bharath

2. **Create Service Account:**
   - Click "Create Service Account"
   - Name: `pdf-viewer-sa`
   - Description: "Service account for PDF viewer signed URLs"
   - Click "Create and Continue"

3. **Grant Permissions:**
   - Role: `Storage Object Admin`
   - Click "Continue" → "Done"

4. **Create JSON Key:**
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Click "Create"
   - **Save the downloaded JSON file**

5. **Update .env:**
   ```bash
   # Add this line to your .env file
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/downloaded-key.json
   ```

## 🚀 After Setup

1. **Restart the backend:**
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart:
   python main_v3.py
   ```

2. **Test again:**
   ```bash
   python test_pdf_endpoints.py "Documents/Data Reports (Metrics & Statistics)/ASER_Reports/Tools validating_the_aser_testing_tools__oct_2012__2.pdf" "education"
   ```

## 🔍 Why Service Account is Needed

| Credential Type | Can Read GCS? | Can Generate Signed URLs? |
|----------------|---------------|---------------------------|
| User Credentials (ADC) | ✅ Yes | ❌ No (no private key) |
| Service Account | ✅ Yes | ✅ Yes (has private key) |

**Signed URLs require:**
- Private key to cryptographically sign the URL
- Service accounts have private keys
- User credentials only have OAuth tokens

## 📝 What Happens Next

Once you set up the service account:
1. ✅ PDF URL generation will work
2. ✅ Snippet location will work
3. ✅ Frontend PDF viewer will work
4. ✅ CORS can be configured (optional for browser access)

## 🐛 Troubleshooting

### "Permission denied"
```bash
# Grant yourself permission to create service accounts
gcloud projects add-iam-policy-binding tech-bharath \
    --member="user:your-email@gmail.com" \
    --role="roles/iam.serviceAccountAdmin"
```

### "Service account already exists"
```bash
# List existing service accounts
gcloud iam service-accounts list --project=tech-bharath

# Use existing one or delete and recreate
gcloud iam service-accounts delete pdf-viewer-sa@tech-bharath.iam.gserviceaccount.com
```

### "Cannot find credentials file"
```bash
# Check the path in .env
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS

# Verify file exists
ls -la ~/pdf-viewer-key.json
```

---

**Ready to proceed?** Run the Option 1 commands above to set up the service account in ~2 minutes!
