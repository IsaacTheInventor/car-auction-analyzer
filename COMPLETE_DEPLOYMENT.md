# Car Auction Analyzer – **Complete Deployment Guide**

This document shows **every supported path** to get the backend + frontend of Car Auction Analyzer into production.  
Choose the platform that best fits your needs, copy the commands, and you’re live.

---

## 0. Prerequisites (all options)

| Requirement | Minimum Version | Notes |
|-------------|-----------------|-------|
| Git         | 2.30+           | Push / clone repo |
| Node & npm  | 18+             | Needed for Netlify / Vercel CLI |
| Docker & Compose v2 | 20.10+ | Only for Docker / Render / Railway local builds |
| GitHub repo | [`IsaacTheInventor/car-auction-analyzer`](https://github.com/IsaacTheInventor/car-auction-analyzer) | Already created |
| API keys    | (optional) Google Vision, Azure CV, Imagga | Leave blank for demo mode |

---

## 1. Front-End (PWA) – **Netlify** ✅ *LIVE*

*Status: already deployed*

```
Live URL: https://car-auction-analyzer-isaac.netlify.app
```

### 1.1  Update / Redeploy
```bash
# run inside project root
netlify deploy --dir=docs              # preview
netlify deploy --dir=docs --prod       # production
```

### 1.2  Set API Endpoint
```bash
netlify env:set APP_API_BASE https://api.<your-domain>.com
netlify deploy --prod
```

**Pros**  
+ Free HTTPS, instant deploys, drag-and-drop.  
+ Built-in CDN + PWA works out of the box.

**Cons**  
− Static only (backend hosted elsewhere).  

---

## 2. Back-End Options

| Platform | Ease | Cost | Autoscale | Notes |
|----------|------|------|-----------|-------|
| Railway  | ★★★★☆ | Free tier | Yes | Easiest one-click deployment |
| Render   | ★★★☆☆ | Free tier | Yes | Multi-service YAML blueprint |
| Vercel   | ★★☆☆☆ | Free tier | Limited | Serverless FastAPI functions |
| Docker VM| ★★☆☆☆ | Depends | Manual | Full control on any VPS |

---

### 2.1  **Railway** (Container)

1. **One-click import**  
   • Go to `https://railway.app/new` → “Deploy from GitHub”  
   • Select `IsaacTheInventor/car-auction-analyzer`  
   • Railway auto-detects `railway.json` – accept defaults.

2. **CLI alternative**
   ```bash
   railway login                # browser auth
   railway init                 # inside repo
   railway up                   # builds & deploys
   ```

3. **Add env vars**
   Railway UI → Variables → paste AI keys.

4. **API URL** (after deploy)  
   `https://car-auction-api.up.railway.app` (copy from “Domains”)  
   Update Netlify `APP_API_BASE`.

**Pros**  
+ Fastest end-to-end hosting (DB, Redis, MinIO plugin).  
+ Zero-downtime deploys, logs, metrics.

**Cons**  
− Free tier sleeps after inactivity.  

---

### 2.2  **Render.com** (Blueprint)

1. **Create Database & Redis** (Render will auto-provision via `render.yaml`).  
2. **Click**: ➡️  “New + Blueprint” → Paste repo URL → **Apply**.  
3. Render builds Docker image and spins up:  
   * `car-auction-api` (web)  
   * `car-auction-worker` (Celery)  
   * `car-auction-beat`  
   * `car-auction-flower`  
   * Postgres & Redis managed services
4. **Domain**: e.g. `https://car-auction-api.onrender.com`  
   Set `APP_API_BASE` in Netlify.

**Pros**  
+ Automatic HTTPS, background workers, free PostgreSQL.  
+ Auto-deploy on `git push`.

**Cons**  
− First cold start ≈ 30 s on free plan.  

---

### 2.3  **Vercel** (Serverless)

> Good for demos or lightweight traffic; heavy ML tasks will shift to background workers on Railway/Render.

1. `npm i -g vercel`
2. ```bash
   vercel login
   vercel --prod           # first run asks config questions
   ```
3. Vercel deploys `/api/*` routes to serverless functions.  
4. Copy HTTPS URL (e.g. `https://car-auction-analyzer.vercel.app`)  
   Update Netlify `APP_API_BASE`.

**Pros**  
+ No infrastructure to manage.  
+ Automatic scaling to zero.

**Cons**  
− 60 s execution limit, 1024 MB RAM.  
− Long-running Celery workers not supported (needs external queue).

---

### 2.4  **Local / VPS Docker Compose**

Best for full control on any Linux VM (AWS EC2, DigitalOcean, bare metal).

```bash
ssh ubuntu@<VM_IP>
sudo apt update && sudo apt install docker.io docker-compose-plugin -y
git clone https://github.com/IsaacTheInventor/car-auction-analyzer.git
cd car-auction-analyzer
cp .env.production .env          # edit secrets & domain
docker compose -f docker-compose.prod.yml up -d
```

*Reverse-proxy & HTTPS*  
Point DNS `api.<your-domain>.com` → VM IP.  
Traefik in the stack auto-generates Let’s Encrypt certificates.

**Pros**  
+ Full power, no cloud vendor lock-in.  
+ Background workers, MinIO, Traefik included.

**Cons**  
− You manage OS, updates, backups.  

---

## 3.  Environment Variables Cheat-Sheet

Key | Purpose
----|---------
`DATABASE_URL` | PostgreSQL connection string
`REDIS_URL` | Redis broker for Celery
`MINIO_*` | Object storage (or S3) creds
`GOOGLE_CLOUD_VISION_API_KEY` | Vehicle detection
`AZURE_COMPUTER_VISION_*` | Damage assessment
`IMAGGA_*` | Image tagging fallback
`SECRET_KEY` | FastAPI & JWT security
`ALLOWED_ORIGINS` | CORS (set to Netlify URL)
`APP_API_BASE` | Front-end → API URL (Netlify)

---

## 4.  Smoke-Test After Deploy

1. Open **Netlify URL** on mobile.  
2. Take ≥1 photo → *Upload for Analysis*.  
3. Check API logs (Railway / Render / VM):  
   ```
   POST /api/vehicles 202
   celery.worker → Task completed
   ```
4. Verify results modal shows real AI output.

---

## 5.  Troubleshooting

| Symptom | Fix |
|---------|-----|
| `CORS` error in browser | Ensure `ALLOWED_ORIGINS` env matches Netlify URL |
| 502 / 504 on first call | Render/Railway free tier cold start – retry |
| Images not saving | Check MinIO / S3 creds; bucket exists |
| AI results all “Simulated” | Provide API keys & restart worker |

---

### 🎉 You’re done!

Pick **one** backend option, follow the copy-paste commands, and your Car Auction Analyzer will be fully operational with real AI analysis. Need help? Open an issue in the [GitHub repo](https://github.com/IsaacTheInventor/car-auction-analyzer/issues) and we’ll sort it out!
