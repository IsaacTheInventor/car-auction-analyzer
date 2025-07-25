"""
Car Auction Analyzer - Configuration Module

This module defines the application settings and configuration using Pydantic.
It loads environment variables, validates them, and provides typed access to all
configuration settings throughout the application.
"""
import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import (
    AnyHttpUrl,
    BaseSettings,
    EmailStr,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    validator,
)
from pydantic.env_settings import SettingsSourceCallable


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with validation.
    
    Settings are organized by category and include detailed documentation.
    Default values are provided where appropriate, but critical settings
    should be explicitly set in production environments.
    """
    
    #-----------------------------------------------
    # APPLICATION SETTINGS
    #-----------------------------------------------
    # Application environment: development, staging, production
    ENVIRONMENT: str = Field(
        "development",
        description="Application environment (development, staging, production)"
    )
    
    # API and server configuration
    API_HOST: str = Field(
        "http://localhost:8000",
        description="Base URL where the API is hosted"
    )
    PORT: int = Field(
        8000,
        description="Port to run the application on"
    )
    DEBUG: bool = Field(
        True,
        description="Enable debug mode (disable in production)"
    )
    LOG_LEVEL: str = Field(
        "debug",
        description="Logging level (debug, info, warning, error, critical)"
    )
    
    # Secret key for encryption and signing
    SECRET_KEY: str = Field(
        secrets.token_urlsafe(32),
        description="Secret key for encryption and signing (auto-generated if not provided)"
    )
    
    # API version prefix
    API_VERSION: str = Field(
        "v1",
        description="API version prefix"
    )
    
    # CORS configuration
    CORS_ORIGINS: str = Field(
        "http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Allowed hosts for production environments
    ALLOWED_HOSTS: str = Field(
        "localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts (used in production)"
    )
    
    # Upload directory for temporary file storage
    UPLOAD_DIR: str = Field(
        "./uploads",
        description="Directory for temporary file uploads"
    )
    
    # Project root directory
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    
    #-----------------------------------------------
    # DATABASE CONFIGURATION
    #-----------------------------------------------
    # PostgreSQL connection string
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string"
    )
    
    # Database connection pool settings
    DB_POOL_SIZE: int = Field(
        5,
        description="Database connection pool size"
    )
    DB_MAX_OVERFLOW: int = Field(
        10,
        description="Maximum number of connections to overflow from the pool"
    )
    DB_POOL_TIMEOUT: int = Field(
        30,
        description="Timeout for acquiring a connection from the pool (seconds)"
    )
    
    # Enable SQL query logging (development only)
    SQL_ECHO: bool = Field(
        True,
        description="Enable SQL query logging (development only)"
    )
    
    @validator("SQL_ECHO", pre=True)
    def set_sql_echo_based_on_environment(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Disable SQL echo in production environments."""
        if values.get("ENVIRONMENT") == "production":
            return False
        return v
    
    #-----------------------------------------------
    # REDIS CONFIGURATION
    #-----------------------------------------------
    # Redis connection string
    REDIS_URL: RedisDsn = Field(
        ...,
        description="Redis connection string"
    )
    
    # Redis password (if applicable)
    REDIS_PASSWORD: Optional[SecretStr] = Field(
        None,
        description="Redis password (if applicable)"
    )
    
    # Redis connection pool size
    REDIS_POOL_SIZE: int = Field(
        10,
        description="Redis connection pool size"
    )
    
    # Redis cache TTL in seconds
    REDIS_CACHE_TTL: int = Field(
        3600,
        description="Redis cache TTL in seconds (default: 1 hour)"
    )
    
    #-----------------------------------------------
    # MINIO / S3 CONFIGURATION
    #-----------------------------------------------
    # MinIO endpoint
    MINIO_ENDPOINT: str = Field(
        ...,
        description="MinIO server endpoint"
    )
    
    # MinIO access credentials
    MINIO_ACCESS_KEY: str = Field(
        ...,
        description="MinIO access key"
    )
    MINIO_SECRET_KEY: SecretStr = Field(
        ...,
        description="MinIO secret key"
    )
    
    # Use SSL for MinIO connection
    MINIO_SECURE: bool = Field(
        False,
        description="Use SSL for MinIO connection"
    )
    
    # Bucket names
    MINIO_BUCKET_IMAGES: str = Field(
        "car-images",
        description="Bucket name for car images"
    )
    MINIO_BUCKET_MODELS: str = Field(
        "model-artifacts",
        description="Bucket name for ML model artifacts"
    )
    
    # AWS S3 configuration (alternative to MinIO)
    AWS_ACCESS_KEY_ID: Optional[str] = Field(
        None,
        description="AWS access key ID (for S3)"
    )
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = Field(
        None,
        description="AWS secret access key (for S3)"
    )
    AWS_REGION: Optional[str] = Field(
        "us-east-1",
        description="AWS region (for S3)"
    )
    AWS_BUCKET_NAME: Optional[str] = Field(
        None,
        description="AWS S3 bucket name"
    )
    
    @validator("MINIO_ENDPOINT", pre=True)
    def validate_minio_endpoint(cls, v: Optional[str]) -> str:
        """Ensure MinIO endpoint does not have protocol prefix."""
        if v and (v.startswith("http://") or v.startswith("https://")):
            # Strip protocol prefix
            return v.split("://", 1)[1]
        return v
    
    #-----------------------------------------------
    # EXTERNAL API KEYS
    #-----------------------------------------------
    # Vehicle data APIs
    VIN_DECODER_API_KEY: Optional[SecretStr] = Field(
        None,
        description="API key for VIN decoder service"
    )
    EDMUNDS_API_KEY: Optional[SecretStr] = Field(
        None,
        description="API key for Edmunds vehicle data"
    )
    KBB_API_KEY: Optional[SecretStr] = Field(
        None,
        description="API key for Kelley Blue Book"
    )
    
    # Free fallback APIs
    FREE_VIN_API_ENABLED: bool = Field(
        True,
        description="Use free VIN API as fallback"
    )
    
    # Parts pricing APIs
    ROCK_AUTO_API_KEY: Optional[SecretStr] = Field(
        None,
        description="API key for RockAuto parts"
    )
    EBAY_PARTS_API_KEY: Optional[SecretStr] = Field(
        None,
        description="API key for eBay parts API"
    )
    EBAY_CLIENT_ID: Optional[str] = Field(
        None,
        description="eBay OAuth client ID"
    )
    EBAY_CLIENT_SECRET: Optional[SecretStr] = Field(
        None,
        description="eBay OAuth client secret"
    )
    
    # AI/ML Services (if using cloud providers)
    GOOGLE_VISION_API_KEY: Optional[SecretStr] = Field(
        None,
        description="Google Cloud Vision API key"
    )
    AZURE_COMPUTER_VISION_KEY: Optional[SecretStr] = Field(
        None,
        description="Azure Computer Vision API key"
    )
    AZURE_COMPUTER_VISION_ENDPOINT: Optional[AnyHttpUrl] = Field(
        None,
        description="Azure Computer Vision API endpoint"
    )
    
    #-----------------------------------------------
    # WEB SCRAPING CONFIGURATION
    #-----------------------------------------------
    # Proxy settings for web scraping
    PROXY_LIST: str = Field(
        "",
        description="Comma-separated list of proxies for web scraping"
    )
    
    # Proxy authentication
    PROXY_USERNAME: Optional[str] = Field(
        None,
        description="Username for proxy authentication"
    )
    PROXY_PASSWORD: Optional[SecretStr] = Field(
        None,
        description="Password for proxy authentication"
    )
    
    # Proxy rotation settings
    PROXY_ROTATION_ENABLED: bool = Field(
        True,
        description="Enable proxy rotation for web scraping"
    )
    PROXY_ROTATION_INTERVAL: int = Field(
        30,
        description="Proxy rotation interval in seconds"
    )
    
    # User agent rotation
    USER_AGENT_ROTATION_ENABLED: bool = Field(
        True,
        description="Enable user agent rotation for web scraping"
    )
    
    # Scraping rate limits
    SCRAPE_RATE_LIMIT: int = Field(
        10,
        description="Maximum requests per minute for scraping"
    )
    
    # Scraping timeouts
    SCRAPE_REQUEST_TIMEOUT: int = Field(
        30,
        description="HTTP request timeout for scraping in seconds"
    )
    SCRAPE_PAGE_LOAD_TIMEOUT: int = Field(
        60,
        description="Page load timeout for browser-based scraping in seconds"
    )
    
    # Allowed scraping domains
    ALLOWED_SCRAPE_DOMAINS: str = Field(
        "autotrader.com,cars.com,craigslist.org,facebook.com/marketplace",
        description="Comma-separated list of domains allowed for scraping"
    )
    
    @validator("PROXY_LIST", pre=True)
    def parse_proxy_list(cls, v: Optional[str]) -> str:
        """Return empty string if proxy list is None."""
        return v or ""
    
    #-----------------------------------------------
    # SECURITY SETTINGS
    #-----------------------------------------------
    # JWT settings
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = Field(
        "HS256",
        description="Algorithm used for JWT signing"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30,
        description="JWT access token expiration in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        7,
        description="JWT refresh token expiration in days"
    )
    
    # Password hashing
    PASSWORD_HASH_ALGORITHM: str = Field(
        "bcrypt",
        description="Algorithm used for password hashing"
    )
    
    # API rate limiting
    RATE_LIMIT_ENABLED: bool = Field(
        True,
        description="Enable API rate limiting"
    )
    RATE_LIMIT_DEFAULT: int = Field(
        100,
        description="Default rate limit per hour"
    )
    RATE_LIMIT_SIGNUP: int = Field(
        5,
        description="Rate limit for signup endpoint per hour"
    )
    RATE_LIMIT_LOGIN: int = Field(
        10,
        description="Rate limit for login endpoint per hour"
    )
    
    # CSRF protection
    CSRF_ENABLED: bool = Field(
        True,
        description="Enable CSRF protection"
    )
    
    # Security headers
    SECURITY_HEADERS_ENABLED: bool = Field(
        True,
        description="Enable security headers"
    )
    
    @validator("JWT_SECRET_KEY", pre=True)
    def set_jwt_secret_key(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """Use the main SECRET_KEY if JWT_SECRET_KEY is not provided."""
        if v is None:
            return values.get("SECRET_KEY", "")
        return v
    
    #-----------------------------------------------
    # CELERY / ASYNC TASK SETTINGS
    #-----------------------------------------------
    # Celery broker URL (same as REDIS_URL by default)
    CELERY_BROKER_URL: Optional[str] = None
    
    # Celery result backend
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Task queue settings
    TASK_QUEUE_DEFAULT: str = Field(
        "default",
        description="Default task queue name"
    )
    TASK_QUEUE_ML: str = Field(
        "ml_tasks",
        description="Queue for ML processing tasks"
    )
    TASK_QUEUE_SCRAPING: str = Field(
        "scraping_tasks",
        description="Queue for web scraping tasks"
    )
    
    # Task timeouts
    TASK_TIMEOUT_DEFAULT: int = Field(
        300,
        description="Default task timeout in seconds (5 minutes)"
    )
    TASK_TIMEOUT_ML: int = Field(
        1800,
        description="ML task timeout in seconds (30 minutes)"
    )
    TASK_TIMEOUT_SCRAPING: int = Field(
        600,
        description="Scraping task timeout in seconds (10 minutes)"
    )
    
    # Concurrency settings
    WORKER_CONCURRENCY: int = Field(
        4,
        description="Number of concurrent worker processes"
    )
    
    @validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", pre=True)
    def set_celery_urls(cls, v: Optional[str], values: Dict[str, Any], **kwargs) -> str:
        """Use REDIS_URL if Celery URLs are not provided."""
        if v is None:
            redis_url = values.get("REDIS_URL")
            if isinstance(redis_url, str):
                return redis_url
        return v
    
    #-----------------------------------------------
    # ML MODEL SETTINGS
    #-----------------------------------------------
    # Model paths
    MODEL_PATH_VEHICLE_DETECTION: str = Field(
        "./models/vehicle_detection.pt",
        description="Path to vehicle detection model"
    )
    MODEL_PATH_DAMAGE_DETECTION: str = Field(
        "./models/damage_detection.pt",
        description="Path to damage detection model"
    )
    MODEL_PATH_MAKE_MODEL: str = Field(
        "./models/make_model_classifier.pt",
        description="Path to make/model classifier model"
    )
    
    # Model confidence thresholds
    MODEL_CONFIDENCE_THRESHOLD: float = Field(
        0.5,
        description="Confidence threshold for model predictions"
    )
    
    # Custom model training
    ENABLE_CUSTOM_TRAINING: bool = Field(
        True,
        description="Enable custom model training"
    )
    TRAINING_BATCH_SIZE: int = Field(
        16,
        description="Batch size for model training"
    )
    TRAINING_EPOCHS: int = Field(
        10,
        description="Number of epochs for model training"
    )
    
    #-----------------------------------------------
    # NOTIFICATION SETTINGS
    #-----------------------------------------------
    # Email settings
    SMTP_SERVER: Optional[str] = Field(
        None,
        description="SMTP server for sending emails"
    )
    SMTP_PORT: Optional[int] = Field(
        587,
        description="SMTP port"
    )
    SMTP_USERNAME: Optional[str] = Field(
        None,
        description="SMTP username"
    )
    SMTP_PASSWORD: Optional[SecretStr] = Field(
        None,
        description="SMTP password"
    )
    EMAIL_FROM: Optional[EmailStr] = Field(
        None,
        description="From email address for notifications"
    )
    
    # SMS notifications
    SMS_ENABLED: bool = Field(
        False,
        description="Enable SMS notifications"
    )
    SMS_PROVIDER: Optional[str] = Field(
        "twilio",
        description="SMS provider (twilio, aws_sns, etc.)"
    )
    TWILIO_ACCOUNT_SID: Optional[str] = Field(
        None,
        description="Twilio account SID"
    )
    TWILIO_AUTH_TOKEN: Optional[SecretStr] = Field(
        None,
        description="Twilio auth token"
    )
    TWILIO_PHONE_NUMBER: Optional[str] = Field(
        None,
        description="Twilio phone number"
    )
    
    #-----------------------------------------------
    # FRONTEND SETTINGS
    #-----------------------------------------------
    # Frontend URL (for redirects and links)
    FRONTEND_URL: AnyHttpUrl = Field(
        "http://localhost:3000",
        description="URL of the frontend application"
    )
    
    # Analytics
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(
        None,
        description="Google Analytics ID"
    )
    
    # Feature flags
    FEATURE_MOBILE_CAPTURE: bool = Field(
        True,
        description="Enable mobile photo capture feature"
    )
    FEATURE_CUSTOM_TRAINING: bool = Field(
        True,
        description="Enable custom model training feature"
    )
    FEATURE_AUCTION_INTEGRATION: bool = Field(
        False,
        description="Enable direct auction site integration"
    )
    
    class Config:
        """Pydantic configuration for the Settings class."""
        
        # Environment variable prefix
        env_prefix = ""
        
        # Case sensitivity for environment variables
        case_sensitive = True
        
        # Allow environment variables to be loaded from .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        # Validate all fields even if some fail
        validate_all = True
        
        # Extra configuration for handling environment variables
        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            """Customize the sources for settings, prioritizing environment variables."""
            return env_settings, file_secret_settings, init_settings


# Create a global settings instance
settings = Settings()
