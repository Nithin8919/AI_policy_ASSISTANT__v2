
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    import pdfplumber
    print("✅ pdfplumber is installed")
except ImportError:
    print("❌ pdfplumber is NOT installed")

try:
    import PyPDF2
    print("✅ PyPDF2 is installed")
except ImportError:
    print("❌ PyPDF2 is NOT installed")

try:
    from ingestion_v2.extraction.extract_text import TextExtractor
    print("✅ ingestion_v2.extraction.extract_text imported successfully")
    
    extractor = TextExtractor()
    print(f"Extractor initialized. Strategies: pdfplumber={extractor.use_pdfplumber}, pypdf={extractor.fallback_to_pypdf}")
    
except Exception as e:
    print(f"❌ Failed to import/init TextExtractor: {e}")

# Check if we can extract from a dummy PDF
# We don't have a real PDF, but we can check if the libraries are loaded
