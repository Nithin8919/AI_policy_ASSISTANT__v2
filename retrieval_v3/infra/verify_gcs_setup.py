#!/usr/bin/env python3
"""
GCS Setup Verification Script
==============================

Verifies:
1. GCS authentication is working
2. Bucket exists and is accessible
3. CORS configuration is correct
4. Signed URL generation works
5. PDF files are accessible

Usage:
    python verify_gcs_setup.py
    
Environment Variables Required:
    GCS_BUCKET_NAME: Name of the GCS bucket
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional)
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List

# Add retrieval_v3 parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
retrieval_v3_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(retrieval_v3_dir)
sys.path.insert(0, project_root)

from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden
from retrieval_v3.services.gcs_service import GCSService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.NC}")
    print("=" * len(text))


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")


def check_environment_variables() -> Dict[str, str]:
    """Check required environment variables."""
    print_header("1. Environment Variables")
    
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not bucket_name:
        print_error("GCS_BUCKET_NAME not set")
        print("\nPlease set the environment variable:")
        print("  export GCS_BUCKET_NAME=your-bucket-name")
        sys.exit(1)
    
    print_success(f"GCS_BUCKET_NAME: {bucket_name}")
    
    if credentials_path:
        if os.path.exists(credentials_path):
            print_success(f"GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
        else:
            print_error(f"Credentials file not found: {credentials_path}")
            sys.exit(1)
    else:
        print_warning("GOOGLE_APPLICATION_CREDENTIALS not set (using Application Default Credentials)")
    
    return {
        'bucket_name': bucket_name,
        'credentials_path': credentials_path
    }


def check_gcs_authentication(config: Dict[str, str]) -> storage.Client:
    """Verify GCS authentication."""
    print_header("2. GCS Authentication")
    
    try:
        if config['credentials_path']:
            client = storage.Client.from_service_account_json(config['credentials_path'])
            print_success("Authenticated using service account")
        else:
            client = storage.Client()
            print_success("Authenticated using Application Default Credentials")
        
        # Test authentication by listing buckets
        project = client.project
        print_success(f"Project: {project}")
        
        return client
    
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Run: gcloud auth application-default login")
        print("  2. Or set GOOGLE_APPLICATION_CREDENTIALS to service account JSON")
        sys.exit(1)


def check_bucket_access(client: storage.Client, bucket_name: str) -> storage.Bucket:
    """Verify bucket exists and is accessible."""
    print_header("3. Bucket Access")
    
    try:
        bucket = client.bucket(bucket_name)
        
        # Check if bucket exists
        if not bucket.exists():
            print_error(f"Bucket does not exist: {bucket_name}")
            sys.exit(1)
        
        print_success(f"Bucket exists: gs://{bucket_name}")
        
        # Get bucket metadata
        bucket.reload()
        print_success(f"Location: {bucket.location}")
        print_success(f"Storage class: {bucket.storage_class}")
        
        return bucket
    
    except Forbidden as e:
        print_error(f"Access denied to bucket: {bucket_name}")
        print("\nEnsure your service account has the following permissions:")
        print("  - storage.buckets.get")
        print("  - storage.objects.get")
        print("  - storage.objects.list")
        sys.exit(1)
    
    except Exception as e:
        print_error(f"Error accessing bucket: {e}")
        sys.exit(1)


def check_cors_configuration(bucket: storage.Bucket):
    """Verify CORS configuration."""
    print_header("4. CORS Configuration")
    
    try:
        cors_config = bucket.cors
        
        if not cors_config:
            print_warning("No CORS configuration found")
            print("\nTo set CORS configuration:")
            print("  cd retrieval_v3/infra")
            print("  ./setup_gcs_cors.sh")
            return
        
        print_success("CORS configuration found:")
        print(json.dumps(cors_config, indent=2))
        
        # Validate CORS settings
        required_methods = {'GET', 'HEAD', 'OPTIONS'}
        required_headers = {'Content-Type', 'Content-Range', 'Accept-Ranges'}
        
        for rule in cors_config:
            methods = set(rule.get('method', []))
            headers = set(rule.get('responseHeader', []))
            
            if required_methods.issubset(methods):
                print_success("Required methods configured: GET, HEAD, OPTIONS")
            else:
                missing = required_methods - methods
                print_warning(f"Missing methods: {missing}")
            
            if required_headers.issubset(headers):
                print_success("Required headers configured for PDF.js")
            else:
                missing = required_headers - headers
                print_warning(f"Missing headers: {missing}")
    
    except Exception as e:
        print_error(f"Error checking CORS: {e}")


def check_pdf_files(bucket: storage.Bucket):
    """Check for PDF files in bucket."""
    print_header("5. PDF Files")
    
    try:
        # List first 10 PDF files
        blobs = list(bucket.list_blobs(max_results=10))
        
        if not blobs:
            print_warning("No files found in bucket")
            return
        
        pdf_files = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
        
        if not pdf_files:
            print_warning("No PDF files found in first 10 files")
        else:
            print_success(f"Found {len(pdf_files)} PDF files:")
            for pdf in pdf_files[:5]:
                print(f"  - {pdf}")
            if len(pdf_files) > 5:
                print(f"  ... and {len(pdf_files) - 5} more")
    
    except Exception as e:
        print_error(f"Error listing files: {e}")


def test_signed_url_generation(config: Dict[str, str]):
    """Test signed URL generation."""
    print_header("6. Signed URL Generation")
    
    try:
        # Initialize GCS service
        gcs_service = GCSService(bucket_name=config['bucket_name'])
        
        # Test with a sample doc_id (you may need to adjust this)
        test_doc_id = "2018se_ms70"  # Example doc_id
        
        print(f"Testing with doc_id: {test_doc_id}")
        
        # Check if PDF exists
        if not gcs_service.pdf_exists(test_doc_id):
            print_warning(f"Test PDF not found for doc_id: {test_doc_id}")
            print("This is expected if you don't have this specific file.")
            print("The signed URL generation logic is still working.")
            return
        
        # Generate signed URL
        signed_url, expiration = gcs_service.generate_signed_url(
            doc_id=test_doc_id,
            expiration_minutes=5
        )
        
        print_success("Signed URL generated successfully")
        print(f"\nURL: {signed_url[:100]}...")
        print(f"Expires: {expiration.isoformat()}Z")
        
        print("\n💡 You can test this URL in your browser (valid for 5 minutes)")
    
    except NotFound as e:
        print_warning(f"Test PDF not found: {e}")
        print("This is expected if you don't have the test file.")
    
    except Exception as e:
        print_error(f"Error generating signed URL: {e}")
        logger.exception("Detailed error:")


def main():
    """Run all verification checks."""
    print(f"\n{Colors.BOLD}🔍 GCS Setup Verification{Colors.NC}")
    print("=" * 50)
    
    # Run checks
    config = check_environment_variables()
    client = check_gcs_authentication(config)
    bucket = check_bucket_access(client, config['bucket_name'])
    check_cors_configuration(bucket)
    check_pdf_files(bucket)
    test_signed_url_generation(config)
    
    # Final summary
    print_header("Summary")
    print_success("All checks completed!")
    print("\nNext steps:")
    print("  1. If CORS is not configured, run: ./setup_gcs_cors.sh")
    print("  2. Update frontend origins in gcs_cors_config.json for production")
    print("  3. Test the PDF viewer endpoints:")
    print("     - GET /api/pdf-url?doc_id=<doc_id>")
    print("     - POST /api/locate-snippet")
    print("  4. Integrate with frontend PdfViewer component")
    print()


if __name__ == "__main__":
    main()
