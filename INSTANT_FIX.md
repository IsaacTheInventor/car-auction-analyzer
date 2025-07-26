# INSTANT_FIX.md
## 🚀 5-Minute Backend Launch via **GitHub Codespaces** (Free Tier)

Follow these steps to get the FastAPI + Celery backend live **without installing anything locally**. Codespaces gives you a cloud VM with Docker pre-installed and a public HTTPS URL.

---

### 1 · Open the Repository in a Codespace
1. Go to **https://github.com/IsaacTheInventor/car-auction-analyzer**  
2. Click the green **“Code”** button → **Codespaces** tab → **“Create codespace on `master`”**  
   • Choose the free template; GitHub spins up a VM (~1-2 min).

### 2 · Prepare Environment Variables
Inside the Codespace terminal (at `/workspaces/car-auction-analyzer`):

```bash
cp .env.production .env
# Open the file in editor tab (or use `nano .env`)
# ── Minimum to run ──
ALLOWED_ORIGINS=https://car-auction-analyzer-isaac.netlify.app
SECRET_KEY=$(openssl rand -hex 32)
```

*(Optional)* add your AI API keys now for real analysis.

### 3 · Start the Full Stack (Docker Compose)
```bash
docker compose -f docker-compose.prod.yml pull      # first run ~1-2 min
docker compose -f docker-compose.prod.yml up -d
```
Codespaces automatically maps ports; wait until logs show  
`Uvicorn running on http://0.0.0.0:8000`.

### 4 · Expose the Public API URL
1. In the Codespace toolbar click **“Ports”**.  
2. Find port **8000** → click **“Make Public”**.  
3. Copy the generated HTTPS URL (e.g.  
   `https://8000-<hash>.app.github.dev`).

### 5 · Wire Front-End to the API
Back on your laptop terminal (or Netlify UI):

```bash
netlify env:set APP_API_BASE <YOUR-NEW-API-URL>
netlify deploy --prod           # instantaneous redeploy
```

### 6 · Smoke Test
1. Open **https://car-auction-analyzer-isaac.netlify.app** on your phone.  
2. Install PWA → take a few vehicle photos → **Upload for Analysis**.  
3. Watch Codespace logs (`docker compose logs -f api worker`) – you should see real AI processing.

### 7 · Persistence Notes
Codespace containers sleep after 30 min idle.  
For continuous uptime, later migrate to Railway/Render/AWS using the same `.env` & `docker-compose.prod.yml`.

---

🎉 **Done!** You now have the backend running in the cloud and connected to your live PWA — all within GitHub Codespaces and under 5 minutes.
