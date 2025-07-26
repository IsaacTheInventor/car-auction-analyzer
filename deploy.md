# Car Auction Analyzer – Deployment Guide

This guide shows how to put the application into production quickly and safely.  
Two main surfaces must be deployed:

1. **Frontend Progressive Web App (PWA)** – static files (`docs/` folder).  
2. **Backend API & async workers** – FastAPI, PostgreSQL, Redis, MinIO, Celery.

---

## 1. Prerequisites

| Tool | Notes |
|------|-------|
| Git & GitHub account | Required for GitHub Pages or CI/CD |
| Docker Desktop / Docker Engine 20+ | Runs containers locally & in the cloud |
| Docker Compose v2 | Simplifies multi-service orchestration |
| Netlify (free) account | Simplest push-to-deploy for static front-end |
| Cloud provider (AWS/GCP/Azure/DigitalOcean) | For long-running backend |
| Domain name (optional) | For custom URL & SSL cert |

---

## 2. Environment Variables

Create a `.env` file (never commit to Git):

```
# ───── Core Services ────────────────────────────────
DATABASE_URL=postgresql+asyncpg://caa_user:STRONG_PASS@db:5432/car_auction
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=caa_minio
MINIO_SECRET_KEY=SUPER_SECRET_MINIO
MINIO_BUCKET_IMAGES=vehicle-images

# ───── External APIs ────────────────────────────────
GOOGLE_CLOUD_VISION_API_KEY=
AZURE_COMPUTER_VISION_KEY=
AZURE_COMPUTER_VISION_ENDPOINT=
IMAGGA_API_KEY=
IMAGGA_API_SECRET=
KBB_API_KEY=
EDMUNDS_API_KEY=
MITCHELL_API_KEY=

# ───── Security & App Config ────────────────────────
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=https://your-frontend-url.com
```

---

## 3. Backend Deployment

### 3.1 Local (Developer) Deployment

```
# clone repo & cd
docker compose -f docker-compose.dev.yml up --build
```

Services available:

| URL | Service |
|-----|---------|
| `http://localhost:8000/api/docs` | FastAPI OpenAPI UI |
| `http://localhost:9001/` | MinIO console |
| `http://localhost:5555/` | Flower – Celery monitoring |

### 3.2 Production with Docker Compose

1. **Copy** `docker-compose.prod.yml` to your VM.
2. **Add** `.env` with production values.
3. Launch:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

The file enables:

* Traefik reverse-proxy (Let's Encrypt TLS)
* FastAPI (gunicorn + uvicorn workers)
* Celery workers & beat scheduler
* PostgreSQL with daily backups (`/var/backups/car_auction`)
* Redis, MinIO

### 3.3 Kubernetes / Cloud-native (optional)

Helm chart is provided in `deploy/helm/` (create if not yet):

```
helm install caa ./deploy/helm \
  --set image.tag=v1.0.0 \
  --set envSecrets.GOOGLE_CLOUD_VISION_API_KEY=<secret> \
  --set ingress.host=api.caa.yourdomain.com
```

Autoscaling & rolling updates handled by K8s.

---

## 4. Frontend Deployment (Static/PWA)

### 4.1 Netlify (fastest)

1. Log in → **Sites → Add new → Deploy manually**  
2. Drag-and-drop the `docs/` folder.  
3. Netlify assigns an HTTPS URL e.g. `https://car-auction-analyzer.netlify.app`.

Optional: connect to Git for continuous deploy.

### 4.2 GitHub Pages

1. Commit `docs/` directory to the `main` branch.  
2. **Settings → Pages → Build & deployment**  
   * Source: `Deploy from a folder`  
   * Folder: `/docs`  
3. GitHub provides `https://<username>.github.io/car-auction-analyzer/`.

#### Configure API base URL

Add to `docs/index.html` **before** main script:

```html
<script>
  window.APP_API_BASE = "https://api.caa.yourdomain.com";
</script>
```

Netlify: set **Environment Variables → APP_API_BASE** in Site > Settings.

---

## 5. CI/CD (optional but recommended)

* **GitHub Actions** workflow (`.github/workflows/deploy.yml`)  
  * Build & push backend Docker image to GHCR  
  * Run unit tests  
  * Deploy to prod server via SSH & `docker compose pull && up -d`  
* **Netlify build hook** triggers frontend redeploy on every push to `main`.

---

## 6. Production Hardening Checklist

- [ ] Use strong random `SECRET_KEY` & rotate annually.  
- [ ] **PostgreSQL** backups → S3 or managed snapshots.  
- [ ] **MinIO**: enable versioning & replicate to off-site bucket.  
- [ ] Enable HTTPS on both API & static site (Traefik/Netlify do this).  
- [ ] Configure CORS (`ALLOWED_ORIGINS`) correctly.  
- [ ] Add Web Application Firewall (WAF) if hosting API publicly.  
- [ ] Enable Cloud logging & alerting (Grafana/Prometheus/Loki or cloud-native).  
- [ ] Periodic CVE scanning (Dependabot, Trivy).  
- [ ] Autoscale Celery workers for heavy image workloads.  
- [ ] GDPR/CCPA compliance if storing user images.

---

## 7. Verifying Deployment

1. Open `https://<your-static-site>` on mobile.  
2. Install as PWA (“Add to Home Screen”).  
3. Take sample photos, **check network tab** → requests reach `https://api.caa.yourdomain.com`.  
4. In backend logs, verify `POST /api/vehicles` and Celery tasks complete.  
5. Confirm analysis results returned and stored in PostgreSQL.

---

## 8. Frequently Asked Questions

| Question | Answer |
|----------|--------|
| **Why Netlify _and_ GitHub Pages?** | Netlify is fastest to start; GitHub Pages is free & integrated with repo. Use either. |
| **Do I need all external AI keys?** | No, app gracefully degrades. Provide at least one (Google Vision) for best accuracy. |
| **Can I use AWS S3 instead of MinIO?** | Yes. Set `MINIO_ENDPOINT=s3.amazonaws.com`, keys = AWS Access/Secret, and enable `MINIO_SECURE=true`. |
| **How to scale?** | Run multiple FastAPI & Celery replicas behind Traefik/Nginx Ingress; use RDS/Aurora for DB. |

---

Congratulations! 🚀  
You now have a fully deployable, AI-powered Car Auction Analyzer ready for production use.
