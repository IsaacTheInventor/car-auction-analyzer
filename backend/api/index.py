"""
Vercel Entry Point
------------------
This minimal file exposes a FastAPI `app` object that Vercel’s Python
builder can detect automatically.  We simply import the main application
(`app.main:app`) and apply lightweight CORS configuration based on the
`ALLOWED_ORIGINS` environment variable supplied at deploy-time.
"""

import os
from fastapi.middleware.cors import CORSMiddleware

# Import the full FastAPI application defined in the core package
from app.main import app  # type: ignore

# Vercel-specific CORS (comma-separated string → list)
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://car-auction-analyzer-isaac.netlify.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional lightweight health-check for platform probes
@app.get("/api/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT", "production")}
