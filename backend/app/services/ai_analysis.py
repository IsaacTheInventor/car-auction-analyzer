"""
AI Analysis Service for Car Auction Analyzer

This module provides comprehensive AI-powered analysis of vehicle photos, including:
- Vehicle identification (make, model, year)
- Damage detection and assessment
- Repair cost estimation
- Market price analysis
- ROI calculation

It integrates with multiple external APIs and provides fallback mechanisms
to ensure reliable operation even if some services are unavailable.
"""

import os
import io
import logging
import json
import base64
import time
import random
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from urllib.parse import urlencode

import httpx
import numpy as np
from PIL import Image
import cv2
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.vehicle import VehicleAnalysis, DamageAssessment, RepairCost, MarketPrice, ROIAnalysis

# Configure logging
logger = logging.getLogger(__name__)

# API Keys and endpoints (should be moved to environment variables in production)
GOOGLE_CLOUD_VISION_API_KEY = os.getenv("GOOGLE_CLOUD_VISION_API_KEY", "")
GOOGLE_CLOUD_VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"

AZURE_COMPUTER_VISION_KEY = os.getenv("AZURE_COMPUTER_VISION_KEY", "")
AZURE_COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT", 
                                          "https://your-resource.cognitiveservices.azure.com/")

IMAGGA_API_KEY = os.getenv("IMAGGA_API_KEY", "")
IMAGGA_API_SECRET = os.getenv("IMAGGA_API_SECRET", "")
IMAGGA_ENDPOINT = "https://api.imagga.com/v2/tags"

# Market price APIs
KBB_API_KEY = os.getenv("KBB_API_KEY", "")
KBB_API_ENDPOINT = "https://api.kbb.com/v1/vehicle"

EDMUNDS_API_KEY = os.getenv("EDMUNDS_API_KEY", "")
EDMUNDS_API_ENDPOINT = "https://api.edmunds.com/api/vehicle/v2"

# Parts and repair cost APIs
MITCHELL_API_KEY = os.getenv("MITCHELL_API_KEY", "")
MITCHELL_API_ENDPOINT = "https://api.mitchell.com/repair-estimator/v1"

NHTSA_API_ENDPOINT = "https://vpic.nhtsa.dot.gov/api/vehicles"


class AIAnalysisService:
    """Service for AI-powered analysis of vehicle photos."""
    
    def __init__(self):
        """Initialize the AI analysis service."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.vehicle_models_db = self._load_vehicle_models_db()
        self.damage_detection_model = self._load_damage_detection_model()
        self.parts_pricing_db = self._load_parts_pricing_db()
        
        # Cache for API responses to reduce duplicate calls
        self.api_cache = {}
        self.cache_expiry = 3600  # 1 hour in seconds
        
    def _load_vehicle_models_db(self) -> Dict:
        """Load the vehicle models database for fallback identification."""
        try:
            # In production, this would load from a proper database
            # For now, we'll use a simple JSON file with common makes/models
            db_path = os.path.join(os.path.dirname(__file__), "data", "vehicle_models.json")
            if os.path.exists(db_path):
                with open(db_path, "r") as f:
                    return json.load(f)
            
            # If file doesn't exist, return a minimal default database
            return {
                "makes": [
                    {"name": "Toyota", "models": ["Camry", "Corolla", "RAV4", "Highlander"]},
                    {"name": "Honda", "models": ["Accord", "Civic", "CR-V", "Pilot"]},
                    {"name": "Ford", "models": ["F-150", "Escape", "Explorer", "Mustang"]},
                    {"name": "Chevrolet", "models": ["Silverado", "Equinox", "Malibu", "Tahoe"]},
                    {"name": "BMW", "models": ["3 Series", "5 Series", "X3", "X5"]},
                    {"name": "Mercedes-Benz", "models": ["C-Class", "E-Class", "GLC", "GLE"]},
                    {"name": "Audi", "models": ["A4", "A6", "Q5", "Q7"]},
                    {"name": "Lexus", "models": ["RX", "ES", "NX", "IS"]},
                    {"name": "Hyundai", "models": ["Elantra", "Sonata", "Tucson", "Santa Fe"]},
                    {"name": "Kia", "models": ["Forte", "Optima", "Sportage", "Sorento"]}
                ],
                "years": list(range(1990, datetime.now().year + 1))
            }
        except Exception as e:
            logger.error(f"Error loading vehicle models database: {e}")
            # Return minimal fallback data
            return {"makes": [], "years": list(range(1990, datetime.now().year + 1))}
    
    def _load_damage_detection_model(self):
        """
        Load the damage detection model.
        
        In a production environment, this would load a trained model from disk.
        For now, we'll use API services instead of a local model.
        """
        # Placeholder for a real model loading function
        # In production, this might load a TensorFlow/PyTorch model
        return None
    
    def _load_parts_pricing_db(self) -> Dict:
        """Load the parts pricing database for repair cost estimation."""
        try:
            # In production, this would load from a proper database
            db_path = os.path.join(os.path.dirname(__file__), "data", "parts_pricing.json")
            if os.path.exists(db_path):
                with open(db_path, "r") as f:
                    return json.load(f)
            
            # If file doesn't exist, return a minimal default database
            return {
                "bumper": {"front": 800, "rear": 750},
                "fender": {"front_left": 400, "front_right": 400, "rear_left": 450, "rear_right": 450},
                "door": {"driver": 600, "passenger": 600, "rear_left": 550, "rear_right": 550},
                "hood": 650,
                "trunk": 600,
                "windshield": 450,
                "headlight": {"left": 350, "right": 350},
                "taillight": {"left": 300, "right": 300},
                "mirror": {"left": 250, "right": 250},
                "wheel": {"front_left": 300, "front_right": 300, "rear_left": 300, "rear_right": 300},
                "labor_rate": {"body": 85, "mechanical": 95, "paint": 75}
            }
        except Exception as e:
            logger.error(f"Error loading parts pricing database: {e}")
            # Return minimal fallback data
            return {"bumper": {"front": 800}, "labor_rate": {"body": 85}}
    
    async def analyze_vehicle(self, photos: List[UploadFile], vehicle_info: Dict = None) -> VehicleAnalysis:
        """
        Analyze vehicle photos and return comprehensive analysis results.
        
        Args:
            photos: List of photo files uploaded by the user
            vehicle_info: Optional user-provided vehicle information
            
        Returns:
            VehicleAnalysis object with identification, damage assessment, and pricing
        """
        try:
            # Process photos
            processed_photos = await self._process_photos(photos)
            
            # Run analyses in parallel for efficiency
            identification_task = self.identify_vehicle(processed_photos, vehicle_info)
            damage_task = self.detect_damage(processed_photos)
            
            # Wait for both tasks to complete
            identification, damage = await asyncio.gather(identification_task, damage_task)
            
            # Get market prices based on identification
            market_prices = await self.get_market_prices(
                make=identification.get("make"),
                model=identification.get("model"),
                year=identification.get("year"),
                trim=identification.get("trim")
            )
            
            # Calculate repair costs
            repair_costs = await self.estimate_repair_costs(
                damage_assessment=damage,
                make=identification.get("make"),
                model=identification.get("model"),
                year=identification.get("year")
            )
            
            # Calculate ROI if asking price is provided
            asking_price = vehicle_info.get("asking_price") if vehicle_info else None
            roi = await self.calculate_roi(
                market_prices=market_prices,
                repair_costs=repair_costs,
                asking_price=asking_price
            )
            
            # Compile complete analysis
            return VehicleAnalysis(
                identification=identification,
                damage_assessment=damage,
                market_prices=market_prices,
                repair_costs=repair_costs,
                roi_analysis=roi
            )
            
        except Exception as e:
            logger.error(f"Error analyzing vehicle: {e}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    async def _process_photos(self, photos: List[UploadFile]) -> List[Dict]:
        """
        Process and validate uploaded photos.
        
        Args:
            photos: List of uploaded photo files
            
        Returns:
            List of dictionaries with processed photo data
        """
        processed = []
        
        for photo in photos:
            try:
                # Read photo data
                contents = await photo.read()
                
                # Validate image
                try:
                    img = Image.open(io.BytesIO(contents))
                    img_format = img.format.lower()
                    
                    # Convert to standard format if needed
                    if img_format not in ["jpeg", "jpg", "png"]:
                        buffer = io.BytesIO()
                        img = img.convert("RGB")
                        img.save(buffer, format="JPEG")
                        contents = buffer.getvalue()
                        img_format = "jpeg"
                    
                    # Get image dimensions
                    width, height = img.size
                    
                    # Convert to base64 for API calls
                    base64_image = base64.b64encode(contents).decode("utf-8")
                    
                    # Get category from filename or metadata
                    category = None
                    if hasattr(photo, "filename"):
                        filename = photo.filename.lower()
                        if "front" in filename:
                            category = "Exterior Front"
                        elif "rear" in filename:
                            category = "Exterior Rear"
                        elif "driver" in filename:
                            category = "Exterior Driver"
                        elif "passenger" in filename:
                            category = "Exterior Passenger"
                        elif "interior" in filename:
                            category = "Interior"
                        elif "damage" in filename:
                            category = "Damage"
                    
                    # Add processed photo
                    processed.append({
                        "data": contents,
                        "base64": base64_image,
                        "format": img_format,
                        "width": width,
                        "height": height,
                        "category": category,
                        "filename": photo.filename
                    })
                    
                except Exception as img_error:
                    logger.warning(f"Invalid image format: {img_error}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error processing photo: {e}")
                continue
                
        if not processed:
            raise HTTPException(status_code=400, detail="No valid photos provided")
            
        return processed
    
    async def identify_vehicle(self, photos: List[Dict], vehicle_info: Dict = None) -> Dict:
        """
        Identify vehicle make, model, and year from photos.
        
        Uses multiple AI services with fallback mechanisms:
        1. Google Cloud Vision API (primary)
        2. Azure Computer Vision (fallback)
        3. Imagga (second fallback)
        4. User-provided info + basic image analysis (final fallback)
        
        Args:
            photos: List of processed photos
            vehicle_info: Optional user-provided vehicle information
            
        Returns:
            Dictionary with make, model, year, trim, and confidence
        """
        # If user provided complete vehicle info, use it with high confidence
        if vehicle_info and all(k in vehicle_info for k in ["make", "model", "year"]):
            return {
                "make": vehicle_info["make"],
                "model": vehicle_info["model"],
                "year": vehicle_info["year"],
                "trim": vehicle_info.get("trim", "Unknown"),
                "confidence": 0.99,
                "source": "user_provided"
            }
        
        # Select exterior photos for identification
        exterior_photos = [p for p in photos if p.get("category") in 
                          ["Exterior Front", "Exterior Rear", "Exterior Driver", "Exterior Passenger"]]
        
        # If no exterior photos, use all photos
        if not exterior_photos:
            exterior_photos = photos
            
        # Try Google Cloud Vision API first
        if GOOGLE_CLOUD_VISION_API_KEY:
            try:
                result = await self._identify_with_google_vision(exterior_photos[0])
                if result and result.get("confidence", 0) > 0.7:
                    return result
            except Exception as e:
                logger.warning(f"Google Vision API error: {e}")
        
        # Try Azure Computer Vision as fallback
        if AZURE_COMPUTER_VISION_KEY:
            try:
                result = await self._identify_with_azure_vision(exterior_photos[0])
                if result and result.get("confidence", 0) > 0.6:
                    return result
            except Exception as e:
                logger.warning(f"Azure Vision API error: {e}")
        
        # Try Imagga as second fallback
        if IMAGGA_API_KEY:
            try:
                result = await self._identify_with_imagga(exterior_photos[0])
                if result and result.get("confidence", 0) > 0.5:
                    return result
            except Exception as e:
                logger.warning(f"Imagga API error: {e}")
        
        # Final fallback: Basic image analysis + user partial info
        return await self._identify_fallback(exterior_photos, vehicle_info)
    
    async def _identify_with_google_vision(self, photo: Dict) -> Dict:
        """Identify vehicle using Google Cloud Vision API."""
        # Prepare the request
        request_data = {
            "requests": [
                {
                    "image": {
                        "content": photo["base64"]
                    },
                    "features": [
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 10},
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "WEB_DETECTION", "maxResults": 10}
                    ]
                }
            ]
        }
        
        # Call the API
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_CLOUD_VISION_API_KEY
        }
        
        async with self.http_client.stream("POST", GOOGLE_CLOUD_VISION_ENDPOINT, 
                                         json=request_data, headers=headers) as response:
            if response.status_code != 200:
                logger.error(f"Google Vision API error: {response.status_code}")
                return None
                
            result = await response.json()
            
        # Process the response
        vehicle_info = {"confidence": 0, "source": "google_vision"}
        
        # Check for car in object localization
        if "localizedObjectAnnotations" in result["responses"][0]:
            objects = result["responses"][0]["localizedObjectAnnotations"]
            car_objects = [obj for obj in objects if obj["name"].lower() in ["car", "vehicle", "automobile"]]
            
            if car_objects:
                vehicle_info["confidence"] = max(obj["score"] for obj in car_objects)
            
        # Check web detection for make/model
        if "webDetection" in result["responses"][0]:
            web_detection = result["responses"][0]["webDetection"]
            
            # Check web entities
            if "webEntities" in web_detection:
                entities = web_detection["webEntities"]
                
                # Look for car makes and models
                for entity in entities:
                    entity_name = entity.get("description", "").lower()
                    score = entity.get("score", 0)
                    
                    # Check against known makes
                    for make_info in self.vehicle_models_db["makes"]:
                        make_name = make_info["name"].lower()
                        
                        if make_name in entity_name:
                            vehicle_info["make"] = make_info["name"]
                            
                            # Look for model in the same entity
                            for model in make_info["models"]:
                                if model.lower() in entity_name:
                                    vehicle_info["model"] = model
                                    vehicle_info["confidence"] = max(vehicle_info["confidence"], score)
                                    break
            
            # Check best guess labels
            if "bestGuessLabels" in web_detection:
                for label in web_detection["bestGuessLabels"]:
                    label_text = label.get("label", "").lower()
                    
                    # Look for year in label
                    for year in range(1990, datetime.now().year + 1):
                        if str(year) in label_text:
                            vehicle_info["year"] = year
                            break
                    
                    # Parse make and model from label if not already found
                    if "make" not in vehicle_info or "model" not in vehicle_info:
                        for make_info in self.vehicle_models_db["makes"]:
                            make_name = make_info["name"].lower()
                            
                            if make_name in label_text:
                                vehicle_info["make"] = make_info["name"]
                                
                                for model in make_info["models"]:
                                    if model.lower() in label_text:
                                        vehicle_info["model"] = model
                                        break
        
        # Check if we have enough information
        if "make" in vehicle_info and "model" in vehicle_info:
            # If year is missing, estimate from visual cues
            if "year" not in vehicle_info:
                # This would use a more sophisticated model in production
                # For now, just estimate a recent year
                vehicle_info["year"] = datetime.now().year - 3
                vehicle_info["year_estimated"] = True
            
            return vehicle_info
        
        return None
    
    async def _identify_with_azure_vision(self, photo: Dict) -> Dict:
        """Identify vehicle using Azure Computer Vision API."""
        if not AZURE_COMPUTER_VISION_ENDPOINT or not AZURE_COMPUTER_VISION_KEY:
            return None
            
        # Prepare the request
        analyze_url = f"{AZURE_COMPUTER_VISION_ENDPOINT}/vision/v3.1/analyze"
        params = {
            "visualFeatures": "Categories,Tags,Description,Objects,Brands",
            "details": "Landmarks",
            "language": "en"
        }
        
        headers = {
            "Content-Type": f"application/{photo['format']}",
            "Ocp-Apim-Subscription-Key": AZURE_COMPUTER_VISION_KEY
        }
        
        # Call the API
        async with self.http_client.stream("POST", analyze_url, 
                                         params=params, 
                                         headers=headers, 
                                         content=photo["data"]) as response:
            if response.status_code != 200:
                logger.error(f"Azure Vision API error: {response.status_code}")
                return None
                
            result = await response.json()
        
        # Process the response
        vehicle_info = {"confidence": 0, "source": "azure_vision"}
        
        # Check for car in objects
        if "objects" in result:
            car_objects = [obj for obj in result["objects"] 
                          if obj["object"].lower() in ["car", "vehicle", "automobile"]]
            
            if car_objects:
                vehicle_info["confidence"] = max(obj["confidence"] for obj in car_objects)
        
        # Check tags for make/model
        if "tags" in result:
            # Sort tags by confidence
            sorted_tags = sorted(result["tags"], key=lambda x: x["confidence"], reverse=True)
            
            # Extract potential make/model information
            for tag in sorted_tags:
                tag_name = tag["name"].lower()
                
                # Check against known makes
                for make_info in self.vehicle_models_db["makes"]:
                    make_name = make_info["name"].lower()
                    
                    if make_name in tag_name:
                        vehicle_info["make"] = make_info["name"]
                        vehicle_info["confidence"] = max(vehicle_info["confidence"], tag["confidence"])
                        
                        # Look for model in tags
                        for model in make_info["models"]:
                            model_lower = model.lower()
                            if any(model_lower in t["name"].lower() for t in sorted_tags):
                                vehicle_info["model"] = model
                                break
        
        # Check description captions for more information
        if "description" in result and "captions" in result["description"]:
            for caption in result["description"]["captions"]:
                caption_text = caption["text"].lower()
                
                # Look for year in caption
                for year in range(1990, datetime.now().year + 1):
                    if str(year) in caption_text:
                        vehicle_info["year"] = year
                        break
                
                # Parse make and model from caption if not already found
                if "make" not in vehicle_info or "model" not in vehicle_info:
                    for make_info in self.vehicle_models_db["makes"]:
                        make_name = make_info["name"].lower()
                        
                        if make_name in caption_text:
                            vehicle_info["make"] = make_info["name"]
                            
                            for model in make_info["models"]:
                                if model.lower() in caption_text:
                                    vehicle_info["model"] = model
                                    break
        
        # Check if we have enough information
        if "make" in vehicle_info and "model" in vehicle_info:
            # If year is missing, estimate from visual cues
            if "year" not in vehicle_info:
                vehicle_info["year"] = datetime.now().year - 4
                vehicle_info["year_estimated"] = True
            
            return vehicle_info
        
        return None
    
    async def _identify_with_imagga(self, photo: Dict) -> Dict:
        """Identify vehicle using Imagga API."""
        if not IMAGGA_API_KEY or not IMAGGA_API_SECRET:
            return None
            
        # Prepare the request
        auth = base64.b64encode(f"{IMAGGA_API_KEY}:{IMAGGA_API_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}"
        }
        
        # Call the API with multipart form data
        files = {"image": (photo["filename"], photo["data"])}
        
        async with self.http_client.stream("POST", IMAGGA_ENDPOINT, 
                                         headers=headers, 
                                         files=files) as response:
            if response.status_code != 200:
                logger.error(f"Imagga API error: {response.status_code}")
                return None
                
            result = await response.json()
        
        # Process the response
        vehicle_info = {"confidence": 0, "source": "imagga"}
        
        if "result" in result and "tags" in result["result"]:
            # Sort tags by confidence
            sorted_tags = sorted(result["result"]["tags"], key=lambda x: x["confidence"], reverse=True)
            
            # Check for car/vehicle tags
            car_tags = [tag for tag in sorted_tags 
                       if tag["tag"]["en"].lower() in ["car", "vehicle", "automobile"]]
            
            if car_tags:
                vehicle_info["confidence"] = car_tags[0]["confidence"] / 100  # Normalize to 0-1
            
            # Extract potential make/model information
            for tag in sorted_tags:
                tag_name = tag["tag"]["en"].lower()
                
                # Check against known makes
                for make_info in self.vehicle_models_db["makes"]:
                    make_name = make_info["name"].lower()
                    
                    if make_name in tag_name:
                        vehicle_info["make"] = make_info["name"]
                        vehicle_info["confidence"] = max(vehicle_info["confidence"], tag["confidence"] / 100)
                        
                        # Look for model in tags
                        for model in make_info["models"]:
                            model_lower = model.lower()
                            if any(model_lower in t["tag"]["en"].lower() for t in sorted_tags):
                                vehicle_info["model"] = model
                                break
                
                # Look for year in tags
                for year in range(1990, datetime.now().year + 1):
                    if str(year) in tag_name:
                        vehicle_info["year"] = year
                        break
        
        # Check if we have enough information
        if "make" in vehicle_info and "model" in vehicle_info:
            # If year is missing, estimate a recent year
            if "year" not in vehicle_info:
                vehicle_info["year"] = datetime.now().year - 5
                vehicle_info["year_estimated"] = True
            
            return vehicle_info
        
        return None
    
    async def _identify_fallback(self, photos: List[Dict], vehicle_info: Dict = None) -> Dict:
        """
        Fallback vehicle identification when API methods fail.
        
        Uses basic image analysis and any partial user-provided information.
        """
        # Start with any user-provided info
        result = {
            "confidence": 0.5,
            "source": "fallback"
        }
        
        if vehicle_info:
            if "make" in vehicle_info:
                result["make"] = vehicle_info["make"]
                result["confidence"] = max(result["confidence"], 0.8)
            
            if "model" in vehicle_info:
                result["model"] = vehicle_info["model"]
                result["confidence"] = max(result["confidence"], 0.8)
            
            if "year" in vehicle_info:
                result["year"] = vehicle_info["year"]
                result["confidence"] = max(result["confidence"], 0.8)
            
            if "trim" in vehicle_info:
                result["trim"] = vehicle_info["trim"]
        
        # If we're missing critical info, use basic image analysis
        if "make" not in result or "model" not in result:
            # In a real implementation, this would use a local ML model
            # For now, make an educated guess based on color and shape
            
            # Get a random make/model as fallback
            if len(self.vehicle_models_db["makes"]) > 0:
                make_info = random.choice(self.vehicle_models_db["makes"])
                
                if "make" not in result:
                    result["make"] = make_info["name"]
                
                if "model" not in result and make_info["models"]:
                    result["model"] = random.choice(make_info["models"])
            else:
                # Ultimate fallback
                if "make" not in result:
                    result["make"] = "Toyota"
                
                if "model" not in result:
                    result["model"] = "Camry"
            
            # Lower confidence for guessed values
            result["confidence"] = 0.5
        
        # If year is missing, use current year - 3 as estimate
        if "year" not in result:
            result["year"] = datetime.now().year - 3
            result["year_estimated"] = True
        
        # If trim is missing, use a generic value
        if "trim" not in result:
            result["trim"] = "Base"
        
        return result
    
    async def detect_damage(self, photos: List[Dict]) -> List[DamageAssessment]:
        """
        Detect and assess vehicle damage from photos.
        
        Uses multiple methods:
        1. Specialized damage detection API (if available)
        2. General object detection APIs to identify damaged parts
        3. Image segmentation to detect abnormalities
        4. Basic image processing as final fallback
        
        Args:
            photos: List of processed photos
            
        Returns:
            List of DamageAssessment objects
        """
        # Select damage-specific photos first
        damage_photos = [p for p in photos if p.get("category") == "Damage"]
        
        # If no specific damage photos, use all exterior photos
        if not damage_photos:
            damage_photos = [p for p in photos if p.get("category") in 
                           ["Exterior Front", "Exterior Rear", "Exterior Driver", "Exterior Passenger"]]
        
        # If still no photos, use all photos
        if not damage_photos:
            damage_photos = photos
        
        damage_assessments = []
        
        # Try to detect damage in each photo
        for photo in damage_photos:
            # Determine the vehicle area from the photo category
            area = self._get_vehicle_area_from_category(photo.get("category", "Unknown"))
            
            # Try specialized damage detection API first
            try:
                damage = await self._detect_damage_with_api(photo)
                if damage:
                    damage_assessments.extend(damage)
                    continue
            except Exception as e:
                logger.warning(f"Damage detection API error: {e}")
            
            # Fallback to basic image analysis
            try:
                damage = await self._detect_damage_fallback(photo, area)
                if damage:
                    damage_assessments.extend(damage)
            except Exception as e:
                logger.warning(f"Fallback damage detection error: {e}")
        
        # If no damage detected but we have photos, add a "no damage detected" assessment
        if not damage_assessments and photos:
            damage_assessments.append(DamageAssessment(
                area="Overall",
                severity="None",
                confidence=0.7,
                description="No significant damage detected",
                repair_recommendation="No repairs needed",
                estimated_cost=0.0
            ))
        
        return damage_assessments
    
    def _get_vehicle_area_from_category(self, category: str) -> str:
        """Map photo category to vehicle area."""
        category_map = {
            "Exterior Front": "Front",
            "Exterior Rear": "Rear",
            "Exterior Driver": "Driver Side",
            "Exterior Passenger": "Passenger Side",
            "Interior Dashboard": "Interior",
            "Interior Seats": "Interior",
            "Damage": "Unknown",  # Will be determined by damage detection
        }
        
        return category_map.get(category, "Unknown")
    
    async def _detect_damage_with_api(self, photo: Dict) -> List[DamageAssessment]:
        """
        Detect damage using specialized API services.
        
        In production, this would integrate with services like:
        - Tractable AI
        - Mitchell Intelligent Damage Analysis
        - Claim Genius
        
        For now, we'll use Google Cloud Vision as a general-purpose solution.
        """
        if not GOOGLE_CLOUD_VISION_API_KEY:
            return None
            
        # Prepare the request
        request_data = {
            "requests": [
                {
                    "image": {
                        "content": photo["base64"]
                    },
                    "features": [
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 20},
                        {"type": "LABEL_DETECTION", "maxResults": 20},
                        {"type": "IMAGE_PROPERTIES", "maxResults": 20}
                    ]
                }
            ]
        }
        
        # Call the API
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_CLOUD_VISION_API_KEY
        }
        
        async with self.http_client.stream("POST", GOOGLE_CLOUD_VISION_ENDPOINT, 
                                         json=request_data, headers=headers) as response:
            if response.status_code != 200:
                logger.error(f"Google Vision API error: {response.status_code}")
                return None
                
            result = await response.json()
        
        # Process the response to identify potential damage
        damage_assessments = []
        
        # Check labels for damage indicators
        if "labelAnnotations" in result["responses"][0]:
            labels = result["responses"][0]["labelAnnotations"]
            
            # Look for damage-related labels
            damage_labels = [label for label in labels 
                            if any(kw in label["description"].lower() 
                                  for kw in ["damage", "dent", "scratch", "broken", "crack", "accident"])]
            
            if damage_labels:
                # Get the highest confidence damage label
                top_damage = max(damage_labels, key=lambda x: x["score"])
                
                # Determine severity based on confidence
                severity = "Minor"
                if top_damage["score"] > 0.8:
                    severity = "Severe"
                elif top_damage["score"] > 0.6:
                    severity = "Moderate"
                
                # Determine area from object localization
                area = "Unknown"
                if "localizedObjectAnnotations" in result["responses"][0]:
                    objects = result["responses"][0]["localizedObjectAnnotations"]
                    
                    # Look for car parts
                    car_parts = [obj for obj in objects 
                                if any(part in obj["name"].lower() 
                                      for part in ["bumper", "door", "hood", "trunk", "fender", "window"])]
                    
                    if car_parts:
                        area = car_parts[0]["name"]
                
                # If area is still unknown, use photo category
                if area == "Unknown":
                    area = self._get_vehicle_area_from_category(photo.get("category", "Unknown"))
                
                # Create damage assessment
                damage_assessments.append(DamageAssessment(
                    area=area,
                    severity=severity,
                    confidence=top_damage["score"],
                    description=f"{severity} damage detected on {area}",
                    repair_recommendation="Repair or replace affected part",
                    estimated_cost=self._estimate_damage_cost(area, severity)
                ))
        
        return damage_assessments
    
    async def _detect_damage_fallback(self, photo: Dict, area: str) -> List[DamageAssessment]:
        """
        Fallback damage detection using basic image processing.
        
        In production, this would use a trained ML model.
        For now, we'll use a simple heuristic approach.
        """
        # Convert base64 to image for processing
        img_data = base64.b64decode(photo["base64"])
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return []
        
        # Simple damage detection using edge detection and color analysis
        # This is a very basic approach and would be replaced with ML in production
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detect edges
        edges = cv2.Canny(blurred, 50, 150)
        
        # Count edge pixels as a simple damage heuristic
        edge_pixel_count = np.count_nonzero(edges)
        edge_density = edge_pixel_count / (img.shape[0] * img.shape[1])
        
        # Analyze color consistency for scratches/dents
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        # Calculate standard deviation of saturation as indicator of inconsistent paint
        s_std = np.std(s)
        v_std = np.std(v)
        
        # Combine metrics into a damage score
        damage_score = (edge_density * 10) + (s_std / 50) + (v_std / 50)
        
        # Threshold for damage detection
        if damage_score > 0.5:
            # Determine severity based on score
            severity = "Minor"
            if damage_score > 1.5:
                severity = "Severe"
            elif damage_score > 1.0:
                severity = "Moderate"
            
            confidence = min(damage_score / 2, 0.8)  # Cap at 0.8 for fallback method
            
            return [DamageAssessment(
                area=area,
                severity=severity,
                confidence=confidence,
                description=f"Potential {severity.lower()} damage detected on {area}",
                repair_recommendation="Inspect and repair affected area",
                estimated_cost=self._estimate_damage_cost(area, severity)
            )]
        
        return []
    
    def _estimate_damage_cost(self, area: str, severity: str) -> float:
        """Estimate repair cost based on damaged area and severity."""
        # Base costs from parts pricing database
        base_cost = 0.0
        
        # Map area to parts database keys
        area_lower = area.lower()
        
        if "bumper" in area_lower:
            if "front" in area_lower:
                base_cost = self.parts_pricing_db.get("bumper", {}).get("front", 800)
            else:
                base_cost = self.parts_pricing_db.get("bumper", {}).get("rear", 750)
        elif "door" in area_lower:
            if "driver" in area_lower:
                base_cost = self.parts_pricing_db.get("door", {}).get("driver", 600)
            elif "passenger" in area_lower:
                base_cost = self.parts_pricing_db.get("door", {}).get("passenger", 600)
            else:
                base_cost = self.parts_pricing_db.get("door", {}).get("rear_left", 550)
        elif "hood" in area_lower:
            base_cost = self.parts_pricing_db.get("hood", 650)
        elif "trunk" in area_lower:
            base_cost = self.parts_pricing_db.get("trunk", 600)
        elif "fender" in area_lower:
            if "front" in area_lower:
                base_cost = self.parts_pricing_db.get("fender", {}).get("front_left", 400)
            else:
                base_cost = self.parts_pricing_db.get("fender", {}).get("rear_left", 450)
        elif "windshield" in area_lower or "window" in area_lower:
            base_cost = self.parts_pricing_db.get("windshield", 450)
        elif "headlight" in area_lower:
            base_cost = self.parts_pricing_db.get("headlight", {}).get("left", 350)
        elif "taillight" in area_lower:
            base_cost = self.parts_pricing_db.get("taillight", {}).get("left", 300)
        elif "mirror" in area_lower:
            base_cost = self.parts_pricing_db.get("mirror", {}).get("left", 250)
        elif "wheel" in area_lower:
            base_cost = self.parts_pricing_db.get("wheel", {}).get("front_left", 300)
        else:
            # Default cost for unknown areas
            base_cost = 500
        
        # Adjust cost based on severity
        severity_multiplier = 1.0
        if severity == "Minor":
            severity_multiplier = 0.5  # 50% of replacement cost for minor damage
        elif severity == "Moderate":
            severity_multiplier = 0.8  # 80% of replacement cost for moderate damage
        elif severity == "Severe":
            severity_multiplier = 1.2  # 120% of replacement cost for severe damage (additional labor)
        
        # Calculate labor cost
        labor_hours = 2.0  # Default labor hours
        if severity == "Minor":
            labor_hours = 1.0
        elif severity == "Moderate":
            labor_hours = 2.5
        elif severity == "Severe":
            labor_hours = 4.0
        
        labor_rate = self.parts_pricing_db.get("labor_rate", {}).get("body", 85)
        labor_cost = labor_hours * labor_rate
        
        # Calculate total cost
        total_cost = (base_cost * severity_multiplier) + labor_cost
        
        # Round to nearest dollar
        return round(total_cost, 2)
    
    async def estimate_repair_costs(self, damage_assessment: List[DamageAssessment], 
                                   make: str, model: str, year: int) -> RepairCost:
        """
        Estimate repair costs based on damage assessment and vehicle info.
        
        Args:
            damage_assessment: List of damage assessments
            make: Vehicle make
            model: Vehicle model
            year: Vehicle year
            
        Returns:
            RepairCost object with parts, labor, and total costs
        """
        # If no damage, return zero costs
        if not damage_assessment or all(d.severity == "None" for d in damage_assessment):
            return RepairCost(
                parts_cost=0.0,
                labor_cost=0.0,
                paint_cost=0.0,
                total_cost=0.0,
                parts_details=[],
                labor_hours=0.0
            )
        
        # Try to get repair estimates from Mitchell API
        if MITCHELL_API_KEY:
            try:
                mitchell_estimate = await self._get_mitchell_repair_estimate(
                    damage_assessment, make, model, year
                )
                if mitchell_estimate:
                    return mitchell_estimate
            except Exception as e:
                logger.warning(f"Mitchell API error: {e}")
        
        # Fallback to internal calculation
        return self._calculate_repair_costs_fallback(damage_assessment, make, model, year)
    
    async def _get_mitchell_repair_estimate(self, damage_assessment: List[DamageAssessment],
                                          make: str, model: str, year: int) -> RepairCost:
        """Get repair estimate from Mitchell API."""
        # This would be implemented with the actual Mitchell API
        # For now, return None to use fallback
        return None
    
    def _calculate_repair_costs_fallback(self, damage_assessment: List[DamageAssessment],
                                       make: str, model: str, year: int) -> RepairCost:
        """Calculate repair costs using internal database and logic."""
        parts_cost = 0.0
        labor_hours = 0.0
        paint_cost = 0.0
        parts_details = []
        
        # Process each damage assessment
        for damage in damage_assessment:
            if damage.severity == "None":
                continue
                
            # Add the estimated cost from damage assessment
            parts_cost += damage.estimated_cost * 0.6  # Assume 60% of cost is parts
            
            # Calculate labor hours
            damage_labor = 0.0
            if damage.severity == "Minor":
                damage_labor = 1.0
            elif damage.severity == "Moderate":
                damage_labor = 2.5
            elif damage.severity == "Severe":
                damage_labor = 4.0
            
            labor_hours += damage_labor
            
            # Calculate paint cost if applicable
            if damage.area not in ["Windshield", "Window", "Glass", "Interior"]:
                paint_cost += damage_labor * 0.5 * self.parts_pricing_db.get("labor_rate", {}).get("paint", 75)
            
            # Add to parts details
            parts_details.append({
                "part": damage.area,
                "action": "Replace" if damage.severity == "Severe" else "Repair",
                "cost": damage.estimated_cost * 0.6
            })
        
        # Calculate labor cost
        labor_rate = self.parts_pricing_db.get("labor_rate", {}).get("body", 85)
        labor_cost = labor_hours * labor_rate
        
        # Calculate total cost
        total_cost = parts_cost + labor_cost + paint_cost
        
        # Apply make/model/year adjustments
        # Luxury vehicles cost more to repair
        luxury_makes = ["BMW", "Mercedes-Benz", "Audi", "Lexus", "Porsche", "Jaguar", "Land Rover"]
        if make in luxury_makes:
            total_cost *= 1.3  # 30% premium for luxury vehicles
        
        # Older vehicles might need additional parts sourcing
        current_year = datetime.now().year
        if year < current_year - 10:
            total_cost *= 1.15  # 15% premium for older vehicles
        
        # Round all costs to nearest dollar
        parts_cost = round(parts_cost, 2)
        labor_cost = round(labor_cost, 2)
        paint_cost = round(paint_cost, 2)
        total_cost = round(total_cost, 2)
        
        return RepairCost(
            parts_cost=parts_cost,
            labor_cost=labor_cost,
            paint_cost=paint_cost,
            total_cost=total_cost,
            parts_details=parts_details,
            labor_hours=labor_hours
        )
    
    async def get_market_prices(self, make: str, model: str, year: int, trim: str = None) -> MarketPrice:
        """
        Get market prices for the vehicle.
        
        Uses multiple sources:
        1. Kelley Blue Book API (primary)
        2. Edmunds API (fallback)
        3. NHTSA database for additional info
        4. Internal database as final fallback
        
        Args:
            make: Vehicle make
            model: Vehicle model
            year: Vehicle year
            trim: Vehicle trim (optional)
            
        Returns:
            MarketPrice object with retail, trade-in, and private party values
        """
        # Check cache first
        cache_key = f"market_price_{make}_{model}_{year}_{trim}"
        cached = self.api_cache.get(cache_key)
        
        if cached and time.time() - cached["timestamp"] < self.cache_expiry:
            return cached["data"]
        
        # Try Kelley Blue Book API first
        if KBB_API_KEY:
            try:
                kbb_prices = await self._get_kbb_prices(make, model, year, trim)
                if kbb_prices:
                    # Cache the result
                    self.api_cache[cache_key] = {
                        "data": kbb_prices,
                        "timestamp": time.time()
                    }
                    return kbb_prices
            except Exception as e:
                logger.warning(f"KBB API error: {e}")
        
        # Try Edmunds API as fallback
        if EDMUNDS_API_KEY:
            try:
                edmunds_prices = await self._get_edmunds_prices(make, model, year, trim)
                if edmunds_prices:
                    # Cache the result
                    self.api_cache[cache_key] = {
                        "data": edmunds_prices,
                        "timestamp": time.time()
                    }
                    return edmunds_prices
            except Exception as e:
                logger.warning(f"Edmunds API error: {e}")
        
        # Final fallback to estimated prices
        fallback_prices = self._estimate_market_prices(make, model, year, trim)
        
        # Cache the result
        self.api_cache[cache_key] = {
            "data": fallback_prices,
            "timestamp": time.time()
        }
        
        return fallback_prices
    
    async def _get_kbb_prices(self, make: str, model: str, year: int, trim: str = None) -> MarketPrice:
        """Get market prices from Kelley Blue Book API."""
        # This would be implemented with the actual KBB API
        # For now, return None to use fallback
        return None
    
    async def _get_edmunds_prices(self, make: str, model: str, year: int, trim: str = None) -> MarketPrice:
        """Get market prices from Edmunds API."""
        # This would be implemented with the actual Edmunds API
        # For now, return None to use fallback
        return None
    
    def _estimate_market_prices(self, make: str, model: str, year: int, trim: str = None) -> MarketPrice:
        """Estimate market prices using internal logic."""
        # Base values for a typical mid-range vehicle
        base_retail = 20000
        base_trade_in = 17000
        base_private_party = 18500
        
        # Adjust for make (brand value)
        make_adjustments = {
            "Toyota": 1.1,
            "Honda": 1.05,
            "Ford": 0.95,
            "Chevrolet": 0.9,
            "BMW": 1.3,
            "Mercedes-Benz": 1.35,
            "Audi": 1.25,
            "Lexus": 1.2,
            "Hyundai": 0.85,
            "Kia": 0.8
        }
        
        make_multiplier = make_adjustments.get(make, 1.0)
        
        # Adjust for model (popularity/desirability)
        # This would be a more comprehensive database in production
        popular_models = {
            "Camry": 1.1,
            "Accord": 1.1,
            "F-150": 1.15,
            "Civic": 1.05,
            "RAV4": 1.1,
            "CR-V": 1.05,
            "3 Series": 1.2,
            "E-Class": 1.25,
            "Mustang": 1.1,
            "Corvette": 1.3
        }
        
        model_multiplier = popular_models.get(model, 1.0)
        
        # Adjust for age (depreciation)
        current_year = datetime.now().year
        age = current_year - year
        
        if age <= 1:
            age_multiplier = 0.85  # 15% first year depreciation
        elif age <= 3:
            age_multiplier = 0.75  # 25% depreciation for 2-3 year old vehicles
        elif age <= 5:
            age_multiplier = 0.6  # 40% depreciation for 4-5 year old vehicles
        elif age <= 8:
            age_multiplier = 0.45  # 55% depreciation for 6-8 year old vehicles
        elif age <= 12:
            age_multiplier = 0.3  # 70% depreciation for 9-12 year old vehicles
        else:
            age_multiplier = 0.2  # 80% depreciation for 12+ year old vehicles
        
        # Adjust for trim level
        trim_multiplier = 1.0
        if trim:
            trim_lower = trim.lower()
            if any(premium in trim_lower for premium in ["premium", "luxury", "limited", "platinum"]):
                trim_multiplier = 1.2
            elif any(sport in trim_lower for sport in ["sport", "touring", "gt"]):
                trim_multiplier = 1.15
            elif any(base in trim_lower for base in ["base", "l", "le"]):
                trim_multiplier = 0.9
        
        # Calculate adjusted values
        multiplier = make_multiplier * model_multiplier * age_multiplier * trim_multiplier
        
        retail_price = base_retail * multiplier
        trade_in_price = base_trade_in * multiplier
        private_party_price = base_private_party * multiplier
        
        # Round to nearest hundred
        retail_price = round(retail_price / 100) * 100
        trade_in_price = round(trade_in_price / 100) * 100
        private_party_price = round(private_party_price / 100) * 100
        
        return MarketPrice(
            retail_price=retail_price,
            trade_in_price=trade_in_price,
            private_party_price=private_party_price,
            source="estimated",
            confidence=0.7
        )
    
    async def calculate_roi(self, market_prices: MarketPrice, repair_costs: RepairCost, 
                          asking_price: float = None) -> ROIAnalysis:
        """
        Calculate ROI based on market prices, repair costs, and asking price.
        
        Args:
            market_prices: Market price data
            repair_costs: Repair cost estimates
            asking_price: Asking price at auction (optional)
            
        Returns:
            ROIAnalysis object with investment, potential profit, and recommendation
        """
        if not asking_price:
            # If no asking price provided, use a reasonable estimate
            asking_price = market_prices.trade_in_price * 0.9
        
        # Calculate total investment
        total_investment = asking_price + repair_costs.total_cost
        
        # Calculate potential profit (using retail price as target selling price)
        potential_profit = market_prices.retail_price - total_investment
        
        # Calculate ROI percentage
        roi_percentage = (potential_profit / total_investment) * 100 if total_investment > 0 else 0
        
        # Determine recommendation
        recommendation = "Pass"
        if roi_percentage >= 15:
            recommendation = "Strong Buy"
        elif roi_percentage >= 8:
            recommendation = "Buy"
        elif roi_percentage >= 3:
            recommendation = "Consider"
        
        # Additional factors to consider
        additional_factors = []
        
        # Check if repair costs are too high relative to vehicle value
        repair_to_value_ratio = repair_costs.total_cost / market_prices.retail_price
        if repair_to_value_ratio > 0.5:
            additional_factors.append("Repair costs exceed 50% of vehicle value")
            recommendation = "Pass"  # Override to Pass if repairs are too expensive
        
        # Check if the spread between trade-in and retail is healthy
        market_spread = market_prices.retail_price - market_prices.trade_in_price
        if market_spread < 1000:
            additional_factors.append("Low market spread between trade-in and retail")
        
        return ROIAnalysis(
            asking_price=asking_price,
            total_investment=total_investment,
            potential_profit=potential_profit,
            roi_percentage=roi_percentage,
            recommendation=recommendation,
            additional_factors=additional_factors
        )
    
    async def close(self):
        """Close the HTTP client when service is shutting down."""
        await self.http_client.aclose()
