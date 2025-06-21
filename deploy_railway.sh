#!/bin/bash
set -e

echo "🚀 Deploying S_AI-V1 to Railway..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "📝 Found uncommitted changes. Committing them..."
    git add .
    read -p "Enter commit message: " commit_msg
    git commit -m "$commit_msg"
fi

# Push to remote
echo "📤 Pushing to remote repository..."
git push

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Error: Railway CLI not found. Please install it first:"
    echo "npm install -g @railway/cli"
    exit 1
fi

# Check environment variables
echo "🔍 Checking Railway environment variables..."
railway variables

# Deploy to Railway
echo "🚂 Starting Railway deployment..."
railway up

echo "✅ Deployment script completed!"
echo "📊 Check the Railway dashboard for deployment status"
