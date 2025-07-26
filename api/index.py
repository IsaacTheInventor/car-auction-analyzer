"""
Vercel Serverless FastAPI Backend for Car Auction Analyzer
Optimized for deployment as a Vercel serverless function
"""

import os
import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI(
    title="Car Auction Analyzer API",
    description="Simple API for analyzing vehicle photos at auctions",
    version="1.0.0",
)

# Configure CORS
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "https://car-auction-analyzer-isaac.netlify.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class VehiclePhoto(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    category: str = Field(..., description="Photo category (exterior, interior, etc.)")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


class VehicleAnalysisRequest(BaseModel):
    photos: List[VehiclePhoto] = Field(..., description="List of vehicle photos")
    notes: Optional[str] = Field(None, description="Additional notes")


class DamageAssessment(BaseModel):
    location: str
    severity: str
    repair_cost: float
    description: str


class VehicleAnalysisResult(BaseModel):
    id: str = Field(..., description="Unique analysis ID")
    make: str
    model: str
    year: int
    estimated_value: float
    damages: List[DamageAssessment]
    total_repair_cost: float
    auction_price_estimate: float
    roi_potential: float
    confidence_score: float
    analysis_date: datetime = Field(default_factory=datetime.now)


# Mock data for realistic responses
VEHICLE_MAKES = ["Toyota", "Honda", "Ford", "Chevrolet", "BMW", "Mercedes", "Audi", "Lexus"]
VEHICLE_MODELS = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Highlander", "Tacoma"],
    "Honda": ["Civic", "Accord", "CR-V", "Pilot", "Odyssey"],
    "Ford": ["F-150", "Escape", "Explorer", "Mustang", "Edge"],
    "Chevrolet": ["Silverado", "Equinox", "Malibu", "Traverse", "Tahoe"],
    "BMW": ["3 Series", "5 Series", "X3", "X5", "7 Series"],
    "Mercedes": ["C-Class", "E-Class", "GLC", "GLE", "S-Class"],
    "Audi": ["A4", "A6", "Q5", "Q7", "A8"],
    "Lexus": ["ES", "RX", "NX", "IS", "GX"],
}
DAMAGE_LOCATIONS = ["Front bumper", "Rear bumper", "Driver door", "Passenger door", "Hood", "Trunk", "Fender", "Roof"]
DAMAGE_SEVERITIES = ["Minor", "Moderate", "Severe"]


# Root route for Vercel
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint to verify API is running"""
    return {
        "message": "Car Auction Analyzer API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }


# Routes
@app.get("/api/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/vehicles/analyze", response_model=VehicleAnalysisResult, tags=["Analysis"])
async def analyze_vehicle(request: VehicleAnalysisRequest) -> VehicleAnalysisResult:
    """
    Analyze vehicle photos and return assessment
    In a real implementation, this would call AI services
    """
    # Generate realistic mock data
    make = random.choice(VEHICLE_MAKES)
    model = random.choice(VEHICLE_MODELS[make])
    year = random.randint(2015, 2023)
    base_value = random.uniform(15000, 45000)
    
    # Generate 1-3 random damages
    num_damages = random.randint(1, 3)
    damages = []
    total_repair = 0
    
    for _ in range(num_damages):
        severity = random.choice(DAMAGE_SEVERITIES)
        severity_multiplier = 1.0
        if severity == "Minor":
            repair_cost = random.uniform(200, 800)
            severity_multiplier = 0.98
        elif severity == "Moderate":
            repair_cost = random.uniform(800, 2500)
            severity_multiplier = 0.9
        else:  # Severe
            repair_cost = random.uniform(2500, 6000)
            severity_multiplier = 0.75
            
        damages.append(
            DamageAssessment(
                location=random.choice(DAMAGE_LOCATIONS),
                severity=severity,
                repair_cost=round(repair_cost, 2),
                description=f"{severity} damage requiring repair"
            )
        )
        total_repair += repair_cost
    
    # Calculate financial estimates
    total_repair = round(total_repair, 2)
    estimated_value = round(base_value * 0.98, 2)  # Slight reduction for auction vehicles
    auction_estimate = round(estimated_value - (total_repair * 1.2), 2)  # Auction price factors in repairs plus margin
    roi_potential = round((estimated_value - auction_estimate - total_repair) / auction_estimate * 100, 1)
    
    return VehicleAnalysisResult(
        id=str(uuid.uuid4()),
        make=make,
        model=model,
        year=year,
        estimated_value=estimated_value,
        damages=damages,
        total_repair_cost=total_repair,
        auction_price_estimate=auction_estimate,
        roi_potential=roi_potential,
        confidence_score=random.uniform(0.85, 0.98),
    )


@app.post("/api/vehicles", status_code=202, tags=["Vehicles"])
async def upload_vehicle_photos(request: VehicleAnalysisRequest) -> Dict[str, str]:
    """
    Upload vehicle photos for analysis
    Returns a task ID that would normally be used to check status
    """
    return {
        "task_id": str(uuid.uuid4()),
        "status": "processing",
        "message": "Photos received and processing started",
        "estimated_completion_seconds": random.randint(5, 15)
    }


@app.get("/api/vehicles/{task_id}", tags=["Vehicles"])
async def get_analysis_result(task_id: str) -> Union[VehicleAnalysisResult, Dict[str, str]]:
    """
    Get analysis results for a specific task
    In a real implementation, this would check a database or task queue
    """
    # Simulate a small chance of still processing
    if random.random() < 0.1:
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Analysis in progress",
            "estimated_completion_seconds": random.randint(1, 5)
        }
    
    # Otherwise return completed analysis
    return await analyze_vehicle(
        VehicleAnalysisRequest(
            photos=[
                VehiclePhoto(
                    image_data="base64_placeholder",
                    category="exterior"
                )
            ]
        )
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all routes"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
        },
    )


# Vercel serverless handler
def handler(request: Dict[str, Any]) -> Callable:
    """
    Vercel serverless function handler
    This is the entry point for the Vercel serverless function
    """
    return app
