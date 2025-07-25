"""
Car Auction Analyzer - Main Application Entry Point

This module initializes the FastAPI application with all necessary middleware,
routers, event handlers, and configurations.
"""
import logging
from contextlib import asynccontextmanager
from typing import Callable

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
)
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__, API_PREFIX
from app.api.routes import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.db.session import create_db_and_tables, engine, get_db_session
from app.services.minio_service import MinioService
from app.services.redis_service import RedisService


# Setup logging
logger = logging.getLogger(__name__)
setup_logging()


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Car Auction Analyzer API (v%s)", __version__)
    
    # Initialize database
    logger.info("Initializing database connection")
    create_db_and_tables()
    
    # Initialize Redis connection
    logger.info("Initializing Redis connection")
    app.state.redis = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    app.state.redis_service = RedisService(app.state.redis)
    
    # Initialize MinIO/S3 client
    logger.info("Initializing object storage connection")
    app.state.minio_service = MinioService(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    
    # Ensure buckets exist
    await app.state.minio_service.ensure_bucket_exists(settings.MINIO_BUCKET_IMAGES)
    await app.state.minio_service.ensure_bucket_exists(settings.MINIO_BUCKET_MODELS)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Close database connections
    logger.info("Closing database connections")
    await engine.dispose()
    
    # Close Redis connections
    logger.info("Closing Redis connections")
    await app.state.redis.close()
    
    # Close MinIO connections
    logger.info("Closing object storage connections")
    await app.state.minio_service.close()
    
    logger.info("Application shutdown complete")


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request information."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process the request, log details, and pass to the next middleware."""
        request_id = request.headers.get("X-Request-ID", "")
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Client: {client_ip} - User-Agent: {user_agent} - Request-ID: {request_id}"
        )
        
        try:
            response = await call_next(request)
            logger.info(
                f"Response: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Request-ID: {request_id}"
            )
            return response
        except Exception as e:
            logger.exception(
                f"Error processing request: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Request-ID: {request_id}"
            )
            raise


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to the response."""
        response = await call_next(request)
        
        # Add security headers if enabled
        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # Content Security Policy - adjust as needed for your application
            if settings.ENVIRONMENT == "production":
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "img-src 'self' data:; "
                    "style-src 'self' 'unsafe-inline'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "connect-src 'self';"
                )
        
        return response


# Create FastAPI application
app = FastAPI(
    title="Car Auction Analyzer API",
    description="API for the Car Auction Analyzer - an AI-powered platform for car dealers",
    version=__version__,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    openapi_url=f"{API_PREFIX}/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS.split(",")
    )


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions."""
    return await validation_exception_handler(request, exc)


@app.exception_handler(AppException)
async def custom_app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions."""
    return await app_exception_handler(request, exc)


# Include API router
app.include_router(api_router, prefix=API_PREFIX)


# Custom OpenAPI schema
def custom_openapi():
    """Generate a custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom schema modifications here if needed
    # For example, add security schemes, tags, etc.
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Custom API documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve custom Swagger UI."""
    return get_swagger_ui_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=None,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Serve custom ReDoc."""
    return get_redoc_html(
        openapi_url=f"{API_PREFIX}/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


# Health check endpoint
@app.get(f"{API_PREFIX}/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    # Check database connection
    try:
        # Use a context manager to ensure the session is closed
        async with get_db_session() as session:
            # Execute a simple query
            await session.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    # Check Redis connection
    try:
        await app.state.redis.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_status = "unhealthy"
    
    # Check MinIO connection
    try:
        await app.state.minio_service.check_connection()
        storage_status = "healthy"
    except Exception as e:
        logger.error(f"Storage health check failed: {str(e)}")
        storage_status = "unhealthy"
    
    # Overall status
    overall_status = all(
        status == "healthy" 
        for status in [db_status, redis_status, storage_status]
    )
    
    status_code = status.HTTP_200_OK if overall_status else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content={
            "status": "healthy" if overall_status else "unhealthy",
            "version": __version__,
            "environment": settings.ENVIRONMENT,
            "components": {
                "database": db_status,
                "redis": redis_status,
                "storage": storage_status,
            },
        },
        status_code=status_code,
    )


# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return JSONResponse(
        content={
            "name": "Car Auction Analyzer API",
            "version": __version__,
            "documentation": f"{settings.API_HOST}/docs",
            "health": f"{settings.API_HOST}{API_PREFIX}/health",
        }
    )


if __name__ == "__main__":
    """
    Run the application directly for development.
    In production, use uvicorn with proper server configuration.
    """
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
