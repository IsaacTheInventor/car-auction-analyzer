"""
Enhanced FastAPI App for Vercel Deployment
Car Auction Analyzer API - With File Upload Support
"""

from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import os
import json
import uuid
import random
import base64
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Car Auction Analyzer API")

# Configure CORS
origins = os.getenv("ALLOWED_ORIGINS", "https://car-auction-analyzer-isaac.netlify.app").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define models
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

# Generate realistic vehicle analysis based on photos
def generate_vehicle_analysis(photos: List[VehiclePhoto]) -> VehicleAnalysisResult:
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

# Vehicle analysis endpoint - supports both JSON and form data
@app.post("/api/vehicles/analyze", response_model=VehicleAnalysisResult)
async def analyze_vehicle(request: Request):
    try:
        content_type = request.headers.get("Content-Type", "")
        
        # Handle JSON request
        if "application/json" in content_type:
            data = await request.json()
            analysis_request = VehicleAnalysisRequest(**data)
            return generate_vehicle_analysis(analysis_request.photos)
        
        # Handle form data request
        elif "multipart/form-data" in content_type:
            form_data = await request.form()
            photos = []
            
            for key, value in form_data.items():
                if key.startswith("photo_"):
                    if isinstance(value, UploadFile):
                        # Handle file upload
                        contents = await value.read()
                        base64_image = base64.b64encode(contents).decode("utf-8")
                        category = form_data.get(f"category_{key[6:]}", "Exterior")
                        
                        photos.append(VehiclePhoto(
                            image_data=base64_image,
                            category=category
                        ))
                    else:
                        # Handle base64 string
                        category = form_data.get(f"category_{key[6:]}", "Exterior")
                        photos.append(VehiclePhoto(
                            image_data=value,
                            category=category
                        ))
            
            if not photos:
                # Try to get photos from a JSON string in the form
                photos_json = form_data.get("photos")
                if photos_json:
                    if isinstance(photos_json, str):
                        try:
                            photos_data = json.loads(photos_json)
                            photos = [VehiclePhoto(**photo) for photo in photos_data]
                        except json.JSONDecodeError:
                            pass
            
            if not photos:
                raise HTTPException(status_code=400, detail="No photos provided")
            
            return generate_vehicle_analysis(photos)
        
        else:
            # Handle raw body with JSON
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    analysis_request = VehicleAnalysisRequest(**data)
                    return generate_vehicle_analysis(analysis_request.photos)
            except:
                pass
            
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Please use application/json or multipart/form-data"
            )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

# Vehicle upload endpoint
@app.post("/api/vehicles")
async def upload_vehicle(request: Request):
    try:
        content_type = request.headers.get("Content-Type", "")
        
        # Process the request based on content type
        if "application/json" in content_type:
            try:
                data = await request.json()
                # Validate the data structure
                if "photos" not in data or not isinstance(data["photos"], list):
                    raise HTTPException(status_code=400, detail="Invalid request: 'photos' field is required and must be an array")
                
                # In a real implementation, this would store the photos and start a background task
                return {
                    "task_id": str(uuid.uuid4()),
                    "status": "processing",
                    "message": f"Processing {len(data['photos'])} photos",
                    "estimated_completion_seconds": min(len(data['photos']) * 2, 30)
                }
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON")
        
        elif "multipart/form-data" in content_type:
            form = await request.form()
            photo_count = 0
            
            # Count the number of photos in the form
            for key in form.keys():
                if key.startswith("photo_") or key == "photos":
                    photo_count += 1
            
            if photo_count == 0:
                raise HTTPException(status_code=400, detail="No photos provided")
            
            return {
                "task_id": str(uuid.uuid4()),
                "status": "processing",
                "message": f"Processing {photo_count} photos",
                "estimated_completion_seconds": min(photo_count * 2, 30)
            }
        
        else:
            # Try to parse as JSON anyway
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    if "photos" in data and isinstance(data["photos"], list):
                        return {
                            "task_id": str(uuid.uuid4()),
                            "status": "processing",
                            "message": f"Processing {len(data['photos'])} photos",
                            "estimated_completion_seconds": min(len(data['photos']) * 2, 30)
                        }
            except:
                pass
            
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Please use application/json or multipart/form-data"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# Get analysis result by task ID
@app.get("/api/vehicles/{task_id}")
async def get_analysis_result(task_id: str):
    try:
        # In a real implementation, this would check a database for the task status
        # For demo purposes, we'll generate a random result
        
        # Simulate a small chance of still processing
        if random.random() < 0.1:
            return {
                "task_id": task_id,
                "status": "processing",
                "message": "Analysis in progress",
                "estimated_completion_seconds": random.randint(1, 5)
            }
        
        # Generate a realistic vehicle analysis
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
            if severity == "Minor":
                repair_cost = random.uniform(200, 800)
            elif severity == "Moderate":
                repair_cost = random.uniform(800, 2500)
            else:  # Severe
                repair_cost = random.uniform(2500, 6000)
                
            damages.append({
                "location": random.choice(DAMAGE_LOCATIONS),
                "severity": severity,
                "repair_cost": round(repair_cost, 2),
                "description": f"{severity} damage requiring repair"
            })
            total_repair += repair_cost
        
        # Calculate financial estimates
        total_repair = round(total_repair, 2)
        estimated_value = round(base_value * 0.98, 2)
        auction_estimate = round(estimated_value - (total_repair * 1.2), 2)
        roi_potential = round((estimated_value - auction_estimate - total_repair) / auction_estimate * 100, 1)
        
        return {
            "id": task_id,
            "make": make,
            "model": model,
            "year": year,
            "estimated_value": estimated_value,
            "damages": damages,
            "total_repair_cost": total_repair,
            "auction_price_estimate": auction_estimate,
            "roi_potential": roi_potential,
            "confidence_score": random.uniform(0.85, 0.98),
            "analysis_date": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"}
    )
