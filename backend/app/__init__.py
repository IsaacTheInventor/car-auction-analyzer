"""
Car Auction Analyzer - Backend Application Package

This package contains the backend API and services for the Car Auction Analyzer,
an AI-powered platform that helps car dealers make data-driven decisions at auctions.
"""

__version__ = "0.1.0"
__author__ = "Car Auction Analyzer Team"

# Package-level constants
APP_NAME = "car-auction-analyzer"
API_PREFIX = "/api/v1"

# Make key components available at package level
from app.core.config import settings  # noqa
