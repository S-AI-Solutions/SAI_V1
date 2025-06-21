#!/bin/bash

echo "🚀 Document AI - One-Click Deployment Script"
echo "============================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit - Document AI MVP"
fi

echo "🎯 Choose your deployment platform:"
echo "1. Railway (Recommended - Fastest)"
echo "2. Render"
echo "3. Fly.io"
echo "4. Heroku"
echo "5. DigitalOcean App Platform"

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo "🚂 Deploying to Railway..."
        echo "1. Go to https://railway.app"
        echo "2. Sign up/Login"
        echo "3. Click 'New Project'"
        echo "4. Select 'Deploy from GitHub repo'"
        echo "5. Connect this repository"
        echo "6. Railway will auto-detect and deploy!"
        echo ""
        echo "📋 Environment Variables to set in Railway:"
        echo "   - GEMINI_API_KEY=your_gemini_api_key"
        echo "   - REDIS_URL=redis://railway-redis:6379 (Railway will provide this)"
        echo ""
        ;;
    2)
        echo "🎨 Deploying to Render..."
        echo "1. Go to https://render.com"
        echo "2. Sign up/Login"
        echo "3. Click 'New +' -> 'Web Service'"
        echo "4. Connect this repository"
        echo "5. Use these settings:"
        echo "   - Build Command: pip install -r backend/requirements_enhanced.txt"
        echo "   - Start Command: uvicorn backend.main:app --host 0.0.0.0 --port \$PORT"
        echo ""
        ;;
    3)
        echo "🪂 Deploying to Fly.io..."
        echo "1. Install flyctl: curl -L https://fly.io/install.sh | sh"
        echo "2. Run: fly auth login"
        echo "3. Run: fly launch"
        echo "4. Follow the prompts"
        echo ""
        ;;
    4)
        echo "💜 Deploying to Heroku..."
        echo "1. Install Heroku CLI"
        echo "2. Run: heroku login"
        echo "3. Run: heroku create your-app-name"
        echo "4. Run: git push heroku main"
        echo ""
        ;;
    5)
        echo "🌊 Deploying to DigitalOcean App Platform..."
        echo "1. Go to https://cloud.digitalocean.com/apps"
        echo "2. Click 'Create App'"
        echo "3. Connect this repository"
        echo "4. DigitalOcean will auto-detect and deploy!"
        echo ""
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🔧 Additional Setup Tips:"
echo "- Make sure to set your GEMINI_API_KEY in environment variables"
echo "- The app will be available at the provided URL"
echo "- Check logs if there are any issues"
echo ""
echo "✅ Deployment setup complete!"
