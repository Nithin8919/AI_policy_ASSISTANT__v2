#!/bin/bash

# AP Policy Assistant Frontend Startup Script
# ==========================================

echo "🎨 Starting AP Policy Assistant Frontend..."

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Set environment variable for API connection
export NEXT_PUBLIC_API_URL=http://localhost:8000

echo "🌐 Starting Next.js development server..."
echo "   Frontend will be available at http://localhost:3000"
echo "   Connecting to API at http://localhost:8000"
echo ""

npm run dev