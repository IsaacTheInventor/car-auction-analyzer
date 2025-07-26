# 🚀 INSTANT_BACKEND_DEPLOY.md
Car Auction Analyzer – **One-Click Backend Deployment**

This page lets you spin-up the complete FastAPI + Celery backend **now**, without touching the command line.

---

## 1 · Pick a Platform & Click

| Platform | One-Click Button | Free Tier Notes |
|----------|-----------------|-----------------|
| Railway (containers) | [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/yp2XnU?referrer=isaac-backend&repository-url=https://github.com/IsaacTheInventor/car-auction-analyzer&plugins[]=postgresql&plugins[]=redis) | Sleeps after 30 min idle |
| Render (Docker blueprint) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/IsaacTheInventor/car-auction-analyzer) | Cold-start ≈ 30 s on free |
| Vercel (Serverless) | [![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/import?s=https://github.com/IsaacTheInventor/car-auction-analyzer&project-name=car-auction-analyzer-api&env=ALLOWED_ORIGINS,GOOGLE_CLOUD_VISION_API_KEY,AZURE_COMPUTER_VISION_KEY,AZURE_COMPUTER_VISION_ENDPOINT,IMAGGA_API_KEY,IMAGGA_API_SECRET&build-env=PYTHON_VERSION=3.12) | 60 s execution limit |

*Buttons open the provider with repo pre-selected and Docker/Vercel config auto-detected.*

---

## 2 · Add Required Environment Variables

| Key | Value |
|-----|-------|
| `ALLOWED_ORIGINS` | `https://car-auction-analyzer-isaac.netlify.app` |
| `SECRET_KEY` | Click “Generate” / “Add Random Value” |
| (optional) AI keys | `GOOGLE_CLOUD_VISION_API_KEY`, `AZURE_COMPUTER_VISION_KEY`, `AZURE_COMPUTER_VISION_ENDPOINT`, `IMAGGA_API_KEY`, `IMAGGA_API_SECRET` |

> You can leave AI keys blank to test; app will fall back to mock analysis.

*Railway & Render also auto-inject `DATABASE_URL`, `REDIS_URL`, and MinIO/S3 credentials.*

---

## 3 · Wait for Build & Copy API URL

1. Build logs will show **“Application started on :8000”**  
2. Copy the public URL, e.g.  
   *Railway*: `https://car-auction-api.up.railway.app`  
   *Render*:  `https://car-auction-api.onrender.com`  
   *Vercel*:  `https://car-auction-analyzer-api.vercel.app`

---

## 4 · Hook Front-End to Backend

On **Netlify**:

```bash
netlify env:set APP_API_BASE <your-api-url>
netlify deploy --prod       # triggers quick redeploy
```

(or via Netlify → Site Settings → Environment Variables → Add/Update `APP_API_BASE`)

---

## 5 · Smoke Test

1. Open the PWA:  
   https://car-auction-analyzer-isaac.netlify.app  
2. Take 1–2 car photos → **Upload for Analysis**  
3. Watch provider logs (Railway/Render/Vercel) – you should see `POST /api/vehicles 202` and Celery task logging.  
4. Results modal now displays **real** AI output.

---

### Need Help?

* Repository Issues: <https://github.com/IsaacTheInventor/car-auction-analyzer/issues>  
* Quick Chat (Railway): open the project → “Support” tab  

Enjoy your fully-serverless **Car Auction Analyzer**! 🏎️📸🤖
