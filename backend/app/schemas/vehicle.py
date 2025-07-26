"""
Vehicle Analysis Schemas

This module defines Pydantic models for the vehicle analysis system, including:
- Vehicle identification
- Damage assessment
- Repair costs
- Market prices
- ROI analysis
"""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class VehicleIdentification(BaseModel):
    """Vehicle make, model, year and trim identification."""
    make: str = Field(..., description="Vehicle manufacturer (e.g., Toyota, Honda)")
    model: str = Field(..., description="Vehicle model (e.g., Camry, Accord)")
    year: int = Field(..., description="Model year of the vehicle")
    trim: Optional[str] = Field(None, description="Trim level (e.g., LX, EX, Limited)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of identification (0-1)")
    source: str = Field(..., description="Source of identification (e.g., 'google_vision', 'user_provided')")
    year_estimated: Optional[bool] = Field(False, description="Whether the year was estimated rather than detected")
    
    @validator('year')
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < 1900 or v > current_year + 1:
            raise ValueError(f'Year must be between 1900 and {current_year + 1}')
        return v


class DamageAssessment(BaseModel):
    """Assessment of vehicle damage for a specific area."""
    area: str = Field(..., description="Area of the vehicle with damage (e.g., 'Front Bumper')")
    severity: str = Field(..., description="Severity of damage (None, Minor, Moderate, Severe)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of assessment (0-1)")
    description: str = Field(..., description="Detailed description of the damage")
    repair_recommendation: str = Field(..., description="Recommended repair action")
    estimated_cost: float = Field(..., ge=0.0, description="Estimated cost to repair in USD")
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ['None', 'Minor', 'Moderate', 'Severe']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of: {", ".join(valid_severities)}')
        return v


class PartDetail(BaseModel):
    """Details about a specific part needing repair."""
    part: str = Field(..., description="Name of the part")
    action: str = Field(..., description="Action required (Repair, Replace, Paint)")
    cost: float = Field(..., ge=0.0, description="Cost of the part in USD")


class RepairCost(BaseModel):
    """Breakdown of estimated repair costs."""
    parts_cost: float = Field(..., ge=0.0, description="Total cost of parts in USD")
    labor_cost: float = Field(..., ge=0.0, description="Total cost of labor in USD")
    paint_cost: float = Field(..., ge=0.0, description="Total cost of paint and materials in USD")
    total_cost: float = Field(..., ge=0.0, description="Total repair cost in USD")
    parts_details: List[Dict[str, Any]] = Field([], description="Detailed breakdown of parts and costs")
    labor_hours: float = Field(..., ge=0.0, description="Estimated labor hours required")


class MarketPrice(BaseModel):
    """Market price information for the vehicle."""
    retail_price: float = Field(..., ge=0.0, description="Average retail price in USD")
    trade_in_price: float = Field(..., ge=0.0, description="Average trade-in value in USD")
    private_party_price: float = Field(..., ge=0.0, description="Average private party sale price in USD")
    source: str = Field(..., description="Source of pricing data (e.g., 'kbb', 'edmunds', 'estimated')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of price estimates (0-1)")


class ROIAnalysis(BaseModel):
    """Return on investment analysis for the vehicle purchase."""
    asking_price: float = Field(..., ge=0.0, description="Asking price at auction in USD")
    total_investment: float = Field(..., ge=0.0, description="Total investment including purchase and repairs in USD")
    potential_profit: float = Field(..., description="Potential profit after repairs in USD")
    roi_percentage: float = Field(..., description="ROI as a percentage")
    recommendation: str = Field(..., description="Purchase recommendation (Pass, Consider, Buy, Strong Buy)")
    additional_factors: List[str] = Field([], description="Additional factors affecting the decision")
    
    @validator('recommendation')
    def validate_recommendation(cls, v):
        valid_recommendations = ['Pass', 'Consider', 'Buy', 'Strong Buy']
        if v not in valid_recommendations:
            raise ValueError(f'Recommendation must be one of: {", ".join(valid_recommendations)}')
        return v


class VehicleAnalysis(BaseModel):
    """Complete vehicle analysis including identification, damage, costs, and ROI."""
    identification: Dict[str, Any] = Field(..., description="Vehicle identification details")
    damage_assessment: List[DamageAssessment] = Field(..., description="Damage assessments by area")
    market_prices: MarketPrice = Field(..., description="Market price information")
    repair_costs: RepairCost = Field(..., description="Repair cost estimates")
    roi_analysis: ROIAnalysis = Field(..., description="ROI analysis and recommendation")
    analysis_date: datetime = Field(default_factory=datetime.now, description="Date and time of analysis")


class VehicleAnalysisRequest(BaseModel):
    """Request model for vehicle analysis."""
    vehicle_info: Optional[Dict[str, Any]] = Field(None, description="Optional user-provided vehicle information")
    photo_ids: List[str] = Field(..., min_items=1, description="List of uploaded photo IDs to analyze")


class VehicleAnalysisResponse(BaseModel):
    """Response model for vehicle analysis."""
    analysis_id: str = Field(..., description="Unique ID for this analysis")
    analysis: VehicleAnalysis = Field(..., description="Complete vehicle analysis")
    processing_time: float = Field(..., description="Processing time in seconds")
