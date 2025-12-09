#!/bin/bash

# GCS Credentials Setup Helper
# This script helps you configure GCS credentials for the PDF viewer

set -e

echo "🔐 GCS Credentials Setup"
echo "========================"
echo ""

# Check if .env exists
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file..."
    touch "$ENV_FILE"
fi

# Get bucket name
echo "📦 Step 1: GCS Bucket Name"
echo "What is your GCS bucket name?"
echo "(This is where your PDF files are stored)"
read -p "Bucket name: " BUCKET_NAME

if [ -z "$BUCKET_NAME" ]; then
    echo "❌ Error: Bucket name cannot be empty"
    exit 1
fi

# Check if bucket exists
echo ""
echo "Checking if bucket exists..."
if gsutil ls "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "✅ Bucket found: gs://${BUCKET_NAME}"
else
    echo "⚠️  Warning: Could not access bucket gs://${BUCKET_NAME}"
    echo "   Make sure:"
    echo "   1. The bucket name is correct"
    echo "   2. You have permission to access it"
    echo "   3. You're authenticated with gcloud"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get credentials path
echo ""
echo "🔑 Step 2: Service Account Credentials"
echo ""
echo "Choose authentication method:"
echo "  1. Use Application Default Credentials (quick, for development)"
echo "  2. Use Service Account JSON file (recommended for production)"
read -p "Enter choice (1 or 2): " AUTH_CHOICE

if [ "$AUTH_CHOICE" = "1" ]; then
    # Application Default Credentials
    echo ""
    echo "Setting up Application Default Credentials..."
    
    if gcloud auth application-default login; then
        echo "✅ Application Default Credentials configured"
        CREDS_PATH=""
    else
        echo "❌ Failed to configure Application Default Credentials"
        exit 1
    fi
    
elif [ "$AUTH_CHOICE" = "2" ]; then
    # Service Account JSON
    echo ""
    echo "Where is your service account JSON file?"
    echo "(You can drag and drop the file here)"
    read -p "Path to JSON file: " CREDS_PATH
    
    # Remove quotes if present (from drag-and-drop)
    CREDS_PATH="${CREDS_PATH//\'/}"
    CREDS_PATH="${CREDS_PATH//\"/}"
    
    # Expand ~ to home directory
    CREDS_PATH="${CREDS_PATH/#\~/$HOME}"
    
    if [ ! -f "$CREDS_PATH" ]; then
        echo "❌ Error: File not found: $CREDS_PATH"
        exit 1
    fi
    
    # Validate JSON
    if ! python3 -m json.tool "$CREDS_PATH" > /dev/null 2>&1; then
        echo "❌ Error: Invalid JSON file"
        exit 1
    fi
    
    echo "✅ Valid service account JSON found"
    
    # Optionally move to secure location
    echo ""
    read -p "Move credentials to ~/.gcp/ for security? (Y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        mkdir -p ~/.gcp
        chmod 700 ~/.gcp
        
        FILENAME=$(basename "$CREDS_PATH")
        NEW_PATH="$HOME/.gcp/$FILENAME"
        
        cp "$CREDS_PATH" "$NEW_PATH"
        chmod 600 "$NEW_PATH"
        
        echo "✅ Credentials moved to: $NEW_PATH"
        CREDS_PATH="$NEW_PATH"
    fi
else
    echo "❌ Invalid choice"
    exit 1
fi

# Update .env file
echo ""
echo "📝 Step 3: Updating .env file"

# Remove existing GCS config
sed -i.bak '/^GCS_BUCKET_NAME=/d' "$ENV_FILE"
sed -i.bak '/^GOOGLE_APPLICATION_CREDENTIALS=/d' "$ENV_FILE"

# Add new config
echo "" >> "$ENV_FILE"
echo "# GCS Configuration for PDF Viewer" >> "$ENV_FILE"
echo "GCS_BUCKET_NAME=$BUCKET_NAME" >> "$ENV_FILE"

if [ -n "$CREDS_PATH" ]; then
    echo "GOOGLE_APPLICATION_CREDENTIALS=$CREDS_PATH" >> "$ENV_FILE"
fi

echo "✅ .env file updated"

# Verify setup
echo ""
echo "🔍 Step 4: Verifying setup"
echo ""

export GCS_BUCKET_NAME="$BUCKET_NAME"
if [ -n "$CREDS_PATH" ]; then
    export GOOGLE_APPLICATION_CREDENTIALS="$CREDS_PATH"
fi

cd retrieval_v3/infra
python verify_gcs_setup.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. If CORS is not configured, run: ./retrieval_v3/infra/setup_gcs_cors.sh"
echo "  2. Install frontend dependencies: cd frontend && ./install_pdf_deps.sh"
echo "  3. Test the PDF viewer"
