# 🚀 Document AI - Instant Deployment Guide

## ⚡ Railway (Deploy in 30 seconds) - RECOMMENDED

**Steps:**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select this repository
5. Railway auto-detects everything and deploys!

**Environment Variables to set:**
- `GEMINI_API_KEY` = your_gemini_api_key
- `REDIS_URL` = redis://redis:6379 (Railway provides this automatically)

---

## 🎨 Render (Deploy in 60 seconds)

**Steps:**
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Connect this repository
5. Use these settings:
   - **Build Command**: `pip install -r backend/requirements_enhanced.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: `Python 3`

---

## 🪂 Fly.io (Deploy in 2 minutes)

**Steps:**
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
fly auth login
fly launch
```

---

## 💜 Heroku (Deploy in 3 minutes)

**Steps:**
```bash
# Install Heroku CLI, then:
heroku login
heroku create your-app-name
git push heroku main
```

---

## 🌊 Vercel (For frontend-only deployment)

**Steps:**
```bash
npm install -g vercel
vercel --prod
```

---

## 🔧 Quick Setup Script

Run this for automated setup:
```bash
./deploy.sh
```

## 📋 Environment Variables Needed

For any platform, set these environment variables:
- `GEMINI_API_KEY` - Your Google Gemini API key
- `PORT` - Will be set automatically by most platforms
- `REDIS_URL` - For platforms that don't provide Redis automatically

## ✅ Verification

After deployment, visit:
- `https://your-app-url.com/health` - Should return `{"status": "healthy"}`
- `https://your-app-url.com/` - Main application interface
- `https://your-app-url.com/docs` - API documentation

## 🚨 Troubleshooting

1. **Build fails**: Check that all requirements are in `requirements_enhanced.txt`
2. **App crashes**: Check environment variables are set correctly
3. **Redis errors**: Ensure Redis service is running (most platforms provide this)

## 🎯 Recommended: Railway

Railway is the fastest option - it automatically:
- Detects your app type
- Sets up Redis
- Provides SSL certificates
- Handles scaling
- Gives you a beautiful dashboard

**Total deployment time: ~30 seconds**
