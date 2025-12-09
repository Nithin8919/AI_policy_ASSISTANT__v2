#!/bin/bash

# Setup GCS CORS Configuration for PDF Viewer
# This script configures CORS on the GCS bucket to allow PDF access from the frontend

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 GCS CORS Configuration Setup${NC}"
echo "=================================="
echo ""

# Check if bucket name is provided
if [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${RED}❌ Error: GCS_BUCKET_NAME environment variable not set${NC}"
    echo ""
    echo "Usage:"
    echo "  export GCS_BUCKET_NAME=your-bucket-name"
    echo "  ./setup_gcs_cors.sh"
    echo ""
    echo "Or:"
    echo "  GCS_BUCKET_NAME=your-bucket-name ./setup_gcs_cors.sh"
    exit 1
fi

BUCKET_NAME="$GCS_BUCKET_NAME"
CORS_CONFIG="$(dirname "$0")/gcs_cors_config.json"

echo -e "${YELLOW}📦 Bucket: ${BUCKET_NAME}${NC}"
echo -e "${YELLOW}📄 CORS Config: ${CORS_CONFIG}${NC}"
echo ""

# Check if CORS config file exists
if [ ! -f "$CORS_CONFIG" ]; then
    echo -e "${RED}❌ Error: CORS config file not found: ${CORS_CONFIG}${NC}"
    exit 1
fi

# Display CORS configuration
echo -e "${GREEN}📋 CORS Configuration:${NC}"
cat "$CORS_CONFIG"
echo ""

# Confirm before applying
read -p "Apply this CORS configuration to gs://${BUCKET_NAME}? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Cancelled by user${NC}"
    exit 0
fi

# Apply CORS configuration
echo -e "${GREEN}🚀 Applying CORS configuration...${NC}"

if gsutil cors set "$CORS_CONFIG" "gs://${BUCKET_NAME}"; then
    echo ""
    echo -e "${GREEN}✅ CORS configuration applied successfully!${NC}"
    echo ""
    
    # Verify CORS configuration
    echo -e "${GREEN}🔍 Verifying CORS configuration:${NC}"
    gsutil cors get "gs://${BUCKET_NAME}"
    echo ""
    
    echo -e "${GREEN}✨ Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Update frontend origins in gcs_cors_config.json for production"
    echo "  2. Run verify_gcs_setup.py to test authentication and access"
    echo "  3. Test PDF viewer in the frontend"
else
    echo ""
    echo -e "${RED}❌ Failed to apply CORS configuration${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if you have permission to modify the bucket"
    echo "  2. Verify the bucket name is correct"
    echo "  3. Ensure you're authenticated: gcloud auth login"
    exit 1
fi
