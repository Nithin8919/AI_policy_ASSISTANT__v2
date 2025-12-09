#!/bin/bash

# Install PDF Viewer Dependencies
# This script installs react-pdf and its required dependencies

set -e

echo "📦 Installing PDF Viewer Dependencies..."
echo "========================================"
echo ""

cd "$(dirname "$0")"

echo "Installing react-pdf and pdfjs-dist..."
npm install react-pdf pdfjs-dist

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "Installed packages:"
echo "  - react-pdf: React component for PDF rendering"
echo "  - pdfjs-dist: PDF.js library for PDF parsing"
echo ""
echo "Next steps:"
echo "  1. The PdfViewer component is ready to use"
echo "  2. Configure NEXT_PUBLIC_API_URL in .env.local if needed"
echo "  3. Test the PDF viewer in your application"
