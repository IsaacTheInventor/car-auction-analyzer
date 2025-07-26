"""
Ultra-Simple FastAPI App for Vercel Deployment
Car Auction Analyzer API - Minimal Version
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import uuid
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Car Auction Analyzer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://car-auction-analyzer-isaac.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Car Auction Analyzer API is running",
        "version": "1.0.0",
        "endpoints": ["/api/health", "/api/vehicles/analyze", "/api/vehicles"]
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# Mock vehicle analysis endpoint
@app.post("/api/vehicles/analyze")
async def analyze_vehicle(request: Request):
    # Simple mock data
    return {
        "id": str(uuid.uuid4()),
        "make": "Toyota",
        "model": "Camry",
        "year": 2020,
        "estimated_value": 22500.00,
        "damages": [
            {
                "location": "Front bumper",
                "severity": "Minor",
                "repair_cost": 450.00,
                "description": "Minor scratches requiring paint"
            }
        ],
        "total_repair_cost": 450.00,
        "auction_price_estimate": 19500.00,
        "roi_potential": 13.1,
        "confidence_score": 0.92,
        "analysis_date": datetime.now().isoformat()
    }

# Vehicle upload endpoint
@app.post("/api/vehicles")
async def upload_vehicle(request: Request):
    return {
        "task_id": str(uuid.uuid4()),
        "status": "processing",
        "message": "Photos received and processing started",
        "estimated_completion_seconds": 10
    }

# Get analysis result by task ID
@app.get("/api/vehicles/{task_id}")
async def get_analysis_result(task_id: str):
    return {
        "id": task_id,
        "make": "Honda",
        "model": "Accord",
        "year": 2019,
        "estimated_value": 20000.00,
        "damages": [
            {
                "location": "Rear bumper",
                "severity": "Moderate",
                "repair_cost": 1200.00,
                "description": "Dent requiring replacement"
            }
        ],
        "total_repair_cost": 1200.00,
        "auction_price_estimate": 17000.00,
        "roi_potential": 10.6,
        "confidence_score": 0.89,
        "analysis_date": datetime.now().isoformat()
    }
