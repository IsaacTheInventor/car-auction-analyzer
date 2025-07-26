# 🚀 QUICK_DEPLOY.md
Car Auction Analyzer – 5-Minute Production Launch

---  
This is the **absolute fastest** path to ship the app live. For deeper docs see `deploy.md`.

## 1 · Prerequisites
| Tool | Version | Purpose |
|------|---------|---------|
| Docker & Docker Compose v2 | latest | Run backend stack |
| Netlify account (free) | — | Host static PWA |
| Domain (optional) | e.g. `cars.example.com` | Point API + PWA |
| AI Service Keys | Google Vision, Azure CV, Imagga | Real analysis |

> All commands assume a Linux/Unix VM. On Windows use WSL or adapt accordingly.

---

## 2 · Clone the Repo on Your Laptop
```bash
git clone https://github.com/yourname/car-auction-analyzer.git
cd car-auction-analyzer
```

---

## 3 · Frontend – Netlify in 60 Seconds
1. Log into Netlify → **Add new site → Deploy manually**.  
2. Drag-and-drop the **`docs/`** folder.  
3. Netlify gives you an HTTPS URL, e.g. `https://caa.netlify.app`.

Inject API base URL:
*Netlify UI → Site settings → Environment variables*  
```
Key: APP_API_BASE
Value: https://api.yourdomain.com   # see backend section
```

(Alternate: add `<script>window.APP_API_BASE="…";</script>` before the main script tag in `docs/index.html`.)

---

## 4 · Backend – Docker Compose (≈ 3 mins)
### 4.1 Spin up a small VM
Ubuntu 22.04, 2 vCPU, 4 GB RAM, static IP. Open ports **80/443**.

### 4.2 Copy project to the VM
```bash
scp -r ./car-auction-analyzer ubuntu@VM_IP:~/
ssh ubuntu@VM_IP
cd car-auction-analyzer
```

### 4.3 Create `.env.production`
```bash
cp .env.production .env              # or nano .env and paste
```
Fill in:
* API_DOMAIN=api.yourdomain.com  
* ACME_EMAIL=you@example.com  
* Database/Redis/MinIO passwords  
* SECRET_KEY=`openssl rand -hex 32`  
* AI keys (next section)  

### 4.4 Run the stack
```bash
docker compose -f docker-compose.prod.yml pull    # first time builds will build
docker compose -f docker-compose.prod.yml up -d
```
Traefik auto-fetches Let’s Encrypt certs. API is live at `https://api.yourdomain.com/api/docs`.

---

## 5 · Get AI Service Keys (free tiers)
1. **Google Cloud Vision**  
   • Create project → *APIs & Services* → enable Vision API → *Credentials* → API key.  
   • Put into `GOOGLE_CLOUD_VISION_API_KEY`.

2. **Azure Computer Vision**  
   • Azure portal → *Create resource* → AI Services → Computer Vision.  
   • Copy `KEY1` and `ENDPOINT` into `AZURE_COMPUTER_VISION_KEY` / `..._ENDPOINT`.

3. **Imagga**  
   • Sign up at imagga.com → *API Keys* → copy key & secret.

4. **(Optional) Market Data**  
   • KBB Developer Portal → get `KBB_API_KEY`  
   • Edmunds → get `EDMUNDS_API_KEY`.

Add each key to `.env` and `docker compose up -d` (or `docker compose restart api worker`).

---

## 6 · Wire PWA → API
Make sure Netlify `APP_API_BASE` points to `https://api.yourdomain.com`.  
Open the PWA link on iPhone → “Add to Home Screen”.

---

## 7 · Smoke Test
1. Visit `https://caa.netlify.app` on mobile.  
2. Take 1–2 car photos → **Upload for Analysis**.  
3. Watch logs:  
```bash
docker compose logs -f api worker
```
4. Expected: 200 OK on `POST /api/vehicles`, Celery task processed, analysis results shown.

🎉 Done! You’ve deployed Car Auction Analyzer to production.
