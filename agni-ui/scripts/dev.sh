#!/bin/bash

# Development script for Agni UI
# This script sets up and starts the development environment

set -e

echo "🚀 Starting Agni UI development environment..."

# Navigate to the agni-ui directory
cd "$(dirname "$0")/.."

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. You may want to customize it for your setup."
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🔧 Starting development server on port 7999..."
echo ""
echo "🌐 Frontend will be available at: http://localhost:7999"
echo "🔗 Make sure Django backend is running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the development server"
echo ""

# Start the development server
npm run dev