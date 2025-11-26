#!/bin/bash

# AP Policy Assistant API Startup Script
# =====================================

echo "🚀 Starting AP Policy Assistant API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
echo "📋 Installing requirements..."
pip install -r api_requirements.txt

# Check for required environment variables
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  WARNING: GEMINI_API_KEY or GOOGLE_API_KEY not set!"
    echo "   Please set one of these environment variables:"
    echo "   export GEMINI_API_KEY=your_api_key_here"
    echo ""
fi

# Start the API server
echo "🌐 Starting FastAPI server on 0.0.0.0:8000..."
echo "   Frontend should connect to http://localhost:8000"
echo "   API docs available at http://localhost:8000/docs"
echo ""

python main.py