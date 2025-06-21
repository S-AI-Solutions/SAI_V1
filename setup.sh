#!/bin/bash

# Document AI MVP Setup Script

echo "🚀 Setting up Document AI MVP..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found"

# Navigate to backend directory
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads logs

echo "✅ Setup complete!"
echo ""
echo "🎯 To start the server:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "🌐 Then open http://localhost:8000 in your browser"
