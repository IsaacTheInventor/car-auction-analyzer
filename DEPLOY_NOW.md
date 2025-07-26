# 🚀 DEPLOY_NOW.md  
Car Auction Analyzer – **Immediate Manual Deployment Guide**

Use this single page to put the app in production **today**, without relying on any CLI helpers.

---

## 0. What You Need Before You Start
1. **GitHub account** with **1 × personal access token** (repo scope).  
2. **Netlify account** (free).  
3. **Ubuntu 22.04 ×64 VM** (2 vCPU / 4 GB, Docker-ready static IP).  
4. **Domain name** you control (e.g. `cars.example.com`).  
5. Latest **Docker** & **Docker Compose v2** pre-installed on the VM.  
6. The project folder on your laptop: `C:\Users\isaac\car-auction-analyzer`.

---

## 1. Front-End (PWA) — Netlify (≈ 3 min)

1. Sign in to Netlify → https://app.netlify.com  
2. **Sites → Add new site → Deploy manually**.  
3. Drag-and-drop the folder **`docs/`** (or the zip `car-auction-analyzer-frontend.zip`).  
4. Netlify assigns a URL, e.g. `https://car-auction-analyzer.netlify.app`.  
5. Go to **Site settings → Environment variables**  
   • Key: `APP_API_BASE`  
   • Value: `https://api.your-domain.com` (replace later with real API).  
6. Save → Deploy site → You’re done with the PWA.

---

## 2. Back-End — GitHub + Cloud VM

### 2.1 Create GitHub Repository (browser only)
1. Open https://github.com/new  
2. Repository name: **`car-auction-analyzer`**  
3. Set **Private** (or Public) → **Create repository**.  
4. On the next page you’ll see *“…or push an existing repository”*. Keep that page open.

### 2.2 Push Code From Laptop
Open **PowerShell** in the project root:

```powershell
# initialise remote
git remote add origin https://github.com/<YOUR_USERNAME>/car-auction-analyzer.git
# push all branches & tags
git push -u origin master
```

(if prompted, paste your Personal Access Token as password).

### 2.3 Provision the VM
SSH into the server (replace IP):

```bash
ssh ubuntu@YOUR_SERVER_IP
```

Install Docker if missing:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

Install Compose v2 plugin (if not already):

```bash
sudo apt-get install docker-compose-plugin -y
```

### 2.4 Clone the Repo on the Server

```bash
cd /srv
git clone https://github.com/<YOUR_USERNAME>/car-auction-analyzer.git
cd car-auction-analyzer
```

### 2.5 Configure Environment Secrets
Copy the template and edit:

```bash
cp .env.production .env
nano .env
```

Minimum values to change **now**:

```
API_DOMAIN=api.your-domain.com
ACME_EMAIL=you@example.com
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=<strong-db-pass>
REDIS_PASSWORD=<strong-redis-pass>
MINIO_SECRET_KEY=<strong-minio-pass>
GOOGLE_CLOUD_VISION_API_KEY=<key>          # or leave blank for demo
```

(leave unused API keys blank – the app will fall back to mock data).

### 2.6 Start the Production Stack

```bash
docker compose -f docker-compose.prod.yml pull   # downloads base images
docker compose -f docker-compose.prod.yml up -d  # first run builds api image
```

Watch logs:

```bash
docker compose logs -f api worker traefik
```

**After ~60 s** browse:  
`http://YOUR_SERVER_IP` → should redirect to **https**.  
`https://api.your-domain.com/api/docs` → FastAPI swagger.

---

## 3. DNS

| Record | Type | Value |
|--------|------|-------|
| `api.your-domain.com` | A | VM IP |
| (optional) `minio.your-domain.com` | A | VM IP |
| (optional) `flower.your-domain.com` | A | VM IP |

Wait ≤ 5 min for propagation; Traefik auto-fetches Let’s Encrypt certs.

---

## 4. Final Wiring

1. In Netlify **Site settings → Environment variables** change `APP_API_BASE` to  
   `https://api.your-domain.com` (if you used a placeholder).  
2. **Restart Netlify deploy**: *Deploys → Trigger deploy → Clear cache & deploy*.

---

## 5. Smoke Test (Mobile)

1. Visit your Netlify URL on iPhone → “Add to Home Screen”.  
2. Take 1–2 exterior photos → **Upload for Analysis**.  
3. In VM logs you should see:

```
POST /api/vehicles 202
celery.worker - Task completed
```

4. Results modal should show vehicle ID, damage list, ROI.

---

## 6. Useful Maintenance Commands

```bash
# Stop services
docker compose -f docker-compose.prod.yml down

# Update to latest code
cd /srv/car-auction-analyzer
git pull origin master
docker compose -f docker-compose.prod.yml up -d --build

# Database shell
docker compose exec db psql -U caa_user -d car_auction
```

---

## 7. Done 🎉

Your Car Auction Analyzer is now live:
- **PWA**: `https://car-auction-analyzer.netlify.app`
- **API**: `https://api.your-domain.com/api/docs`

Happy bidding!
