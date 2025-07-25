"""
Car Auction Analyzer - API Routes

This module defines the main API router that includes all sub-routers for different
API endpoints. It organizes the API into logical groups with proper tags for documentation.
"""
from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    vehicles,
    market,
    parts,
    analysis,
    users,
    uploads,
    webhooks,
)

# Create the main API router
api_router = APIRouter()

# Include sub-routers with appropriate tags and prefixes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
    responses={401: {"description": "Unauthorized"}},
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
    responses={401: {"description": "Unauthorized"}},
)

api_router.include_router(
    vehicles.router,
    prefix="/vehicles",
    tags=["Vehicles"],
    responses={404: {"description": "Vehicle not found"}},
)

api_router.include_router(
    market.router,
    prefix="/market",
    tags=["Market Data"],
    responses={404: {"description": "Market data not found"}},
)

api_router.include_router(
    parts.router,
    prefix="/parts",
    tags=["Parts & Repairs"],
    responses={404: {"description": "Parts data not found"}},
)

api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis & Reports"],
    responses={404: {"description": "Analysis not found"}},
)

api_router.include_router(
    uploads.router,
    prefix="/uploads",
    tags=["File Uploads"],
    responses={413: {"description": "Request entity too large"}},
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"],
    responses={400: {"description": "Invalid webhook payload"}},
)
