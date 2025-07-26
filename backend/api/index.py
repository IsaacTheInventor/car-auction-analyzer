from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main FastAPI application
from app.main import app as fastapi_app

# Configure CORS specifically for Vercel environment
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://car-auction-analyzer-isaac.netlify.app").split(",")
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Vercel-specific middleware for request handling
@fastapi_app.middleware("http")
async def add_vercel_headers(request: Request, call_next):
    response = await call_next(request)
    # Add security headers for Vercel deployment
    response.headers["X-Vercel-Deployment"] = "1"
    return response

# Health check endpoint for Vercel
@fastapi_app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "ok", "environment": os.getenv("ENVIRONMENT", "production")})

# Export the app for Vercel
app = fastapi_app

# Handler for Vercel serverless function
def handler(request, response):
    # Process the request through the ASGI app
    return app(request, response)
