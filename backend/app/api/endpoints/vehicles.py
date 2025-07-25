"""
Car Auction Analyzer - Vehicle Analysis API Endpoints

This module defines the API endpoints for vehicle analysis, including:
- Uploading vehicle photos
- Retrieving analysis results
- Downloading analysis reports
- Real-time progress updates via WebSocket

These endpoints handle the core functionality of the Car Auction Analyzer,
allowing dealers to submit vehicles for analysis and receive detailed reports.
"""
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiofiles
from fastapi import (
    APIRouter, 
    BackgroundTasks,
    Depends, 
    File, 
    Form, 
    HTTPException, 
    Path, 
    Query, 
    Request,
    UploadFile, 
    WebSocket, 
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_user_optional,
    get_db_session,
)
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.models import User, Vehicle, VehicleAnalysis
from app.models.schemas import (
    AnalysisReport,
    AnalysisResult,
    AnalysisStatus,
    DamageAssessment,
    MarketPrice,
    PartsEstimate,
    ROICalculation,
    VehicleCreate,
    VehicleDetail,
    VehicleIdentification,
    VehicleResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.file_service import FileService
from app.services.minio_service import MinioService
from app.services.redis_service import RedisService
from app.services.vehicle_service import VehicleService
from app.worker.tasks import (
    analyze_vehicle_photos_task,
    generate_analysis_report_task,
)


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Request and Response Models
class VehicleUploadRequest(BaseModel):
    """Request model for vehicle photo upload."""
    
    auction_id: Optional[str] = Field(
        None, 
        description="Auction identifier if available"
    )
    vin: Optional[str] = Field(
        None, 
        description="Vehicle Identification Number if available",
        min_length=17,
        max_length=17,
        regex="^[A-HJ-NPR-Z0-9]{17}$",
    )
    make: Optional[str] = Field(
        None, 
        description="Vehicle make if known"
    )
    model: Optional[str] = Field(
        None, 
        description="Vehicle model if known"
    )
    year: Optional[int] = Field(
        None, 
        description="Vehicle year if known",
        ge=1900,
        le=datetime.now().year + 1,
    )
    auction_url: Optional[HttpUrl] = Field(
        None, 
        description="URL to the auction listing if available"
    )
    asking_price: Optional[float] = Field(
        None, 
        description="Current asking price or auction starting bid",
        ge=0,
    )
    notes: Optional[str] = Field(
        None, 
        description="Additional notes about the vehicle"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "auction_id": "AUC12345",
                "vin": "1HGCM82633A004352",
                "make": "Honda",
                "model": "Accord",
                "year": 2022,
                "auction_url": "https://example-auction.com/listing/12345",
                "asking_price": 15000.00,
                "notes": "Minor visible damage on rear bumper"
            }
        }


class AnalysisProgressUpdate(BaseModel):
    """Model for WebSocket progress updates."""
    
    vehicle_id: str = Field(..., description="Vehicle ID")
    status: AnalysisStatus = Field(..., description="Current analysis status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Current processing step")
    message: Optional[str] = Field(None, description="Status message")
    estimated_time_remaining: Optional[int] = Field(
        None, 
        description="Estimated time remaining in seconds"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReportFormat(str):
    """Enumeration of supported report formats."""
    
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, vehicle_id: str):
        """Connect a WebSocket client for a specific vehicle."""
        await websocket.accept()
        if vehicle_id not in self.active_connections:
            self.active_connections[vehicle_id] = []
        self.active_connections[vehicle_id].append(websocket)
        logger.info(f"WebSocket client connected for vehicle {vehicle_id}")
    
    def disconnect(self, websocket: WebSocket, vehicle_id: str):
        """Disconnect a WebSocket client."""
        if vehicle_id in self.active_connections:
            if websocket in self.active_connections[vehicle_id]:
                self.active_connections[vehicle_id].remove(websocket)
            if not self.active_connections[vehicle_id]:
                del self.active_connections[vehicle_id]
        logger.info(f"WebSocket client disconnected from vehicle {vehicle_id}")
    
    async def broadcast_to_vehicle(self, vehicle_id: str, message: Dict[str, Any]):
        """Broadcast a message to all clients connected to a specific vehicle."""
        if vehicle_id in self.active_connections:
            disconnected_websockets = []
            for websocket in self.active_connections[vehicle_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {str(e)}")
                    disconnected_websockets.append(websocket)
            
            # Clean up any disconnected websockets
            for websocket in disconnected_websockets:
                self.disconnect(websocket, vehicle_id)


# Create a connection manager instance
manager = ConnectionManager()


# Dependency for getting services
async def get_services(
    db: AsyncSession = Depends(get_db_session),
    request: Request = None,
):
    """Dependency to get all required services."""
    file_service = FileService(upload_dir=settings.UPLOAD_DIR)
    
    # Get MinIO service from app state
    minio_service = request.app.state.minio_service if request else MinioService(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY.get_secret_value(),
        secure=settings.MINIO_SECURE,
    )
    
    # Get Redis service from app state
    redis_service = request.app.state.redis_service if request else None
    
    vehicle_service = VehicleService(db=db, minio_service=minio_service)
    analysis_service = AnalysisService(
        db=db, 
        minio_service=minio_service,
        redis_service=redis_service,
    )
    
    return {
        "file_service": file_service,
        "minio_service": minio_service,
        "vehicle_service": vehicle_service,
        "analysis_service": analysis_service,
        "redis_service": redis_service,
    }


@router.post(
    "/",
    response_model=VehicleResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload vehicle photos and start analysis",
    description="Upload photos of a vehicle to analyze its condition, estimate repair costs, "
                "and calculate potential ROI. The analysis will be performed asynchronously.",
)
async def upload_vehicle_photos(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(
        ..., 
        description="Vehicle photos (exterior, interior, damage areas)",
    ),
    data: str = Form(
        ..., 
        description="Vehicle metadata in JSON format",
    ),
    user: User = Depends(get_current_active_user),
    services: Dict[str, Any] = Depends(get_services),
    request: Request = None,
):
    """
    Upload vehicle photos and start analysis.
    
    This endpoint accepts multiple photos of a vehicle along with metadata,
    and initiates an asynchronous analysis process. It returns immediately
    with a job ID that can be used to check the status of the analysis.
    
    The analysis includes:
    - Vehicle identification (make, model, year, trim)
    - Damage detection and assessment
    - Parts cost estimation
    - Market price analysis
    - ROI calculation
    
    The progress of the analysis can be monitored via WebSocket.
    """
    # Parse the JSON data
    try:
        vehicle_data = json.loads(data)
        vehicle_request = VehicleUploadRequest(**vehicle_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON data",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid vehicle data: {str(e)}",
        )
    
    # Validate files
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )
    
    # Check file types
    valid_mime_types = [
        "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"
    ]
    for file in files:
        content_type = file.content_type
        if content_type not in valid_mime_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {content_type}. "
                       f"Supported types: {', '.join(valid_mime_types)}",
            )
    
    # Generate a unique ID for the vehicle
    vehicle_id = str(uuid.uuid4())
    
    try:
        # Save files to temporary storage
        file_service = services["file_service"]
        minio_service = services["minio_service"]
        vehicle_service = services["vehicle_service"]
        
        # Create upload directory if it doesn't exist
        await file_service.ensure_upload_dir_exists()
        
        # Save files temporarily and get their paths
        temp_file_paths = []
        for file in files:
            file_path = await file_service.save_upload_file(file, vehicle_id)
            temp_file_paths.append(file_path)
        
        # Create vehicle record in database
        vehicle = await vehicle_service.create_vehicle(
            user_id=user.id,
            vehicle_id=vehicle_id,
            make=vehicle_request.make,
            model=vehicle_request.model,
            year=vehicle_request.year,
            vin=vehicle_request.vin,
            auction_id=vehicle_request.auction_id,
            auction_url=str(vehicle_request.auction_url) if vehicle_request.auction_url else None,
            asking_price=vehicle_request.asking_price,
            notes=vehicle_request.notes,
        )
        
        # Upload files to MinIO
        for file_path in temp_file_paths:
            await minio_service.upload_file(
                bucket_name=settings.MINIO_BUCKET_IMAGES,
                object_name=f"{vehicle_id}/{file_path.name}",
                file_path=file_path,
                content_type=files[temp_file_paths.index(file_path)].content_type,
            )
        
        # Start analysis task asynchronously
        task = analyze_vehicle_photos_task.delay(
            vehicle_id=vehicle_id,
            user_id=str(user.id),
            file_paths=[f"{vehicle_id}/{path.name}" for path in temp_file_paths],
            metadata=vehicle_request.dict(),
        )
        
        # Update vehicle record with task ID
        await vehicle_service.update_vehicle(
            vehicle_id=vehicle_id,
            task_id=task.id,
        )
        
        # Clean up temporary files in the background
        background_tasks.add_task(
            file_service.cleanup_temp_files,
            temp_file_paths,
        )
        
        # Return response with vehicle ID and task ID
        return {
            "vehicle_id": vehicle_id,
            "task_id": task.id,
            "status": AnalysisStatus.QUEUED,
            "message": "Vehicle photos uploaded successfully. Analysis started.",
            "created_at": vehicle.created_at,
            "estimated_completion_time": datetime.utcnow().timestamp() + 300,  # Estimate 5 minutes
        }
        
    except Exception as e:
        logger.exception(f"Error processing vehicle upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing vehicle upload: {str(e)}",
        )


@router.get(
    "/{vehicle_id}",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Get vehicle analysis results",
    description="Retrieve the analysis results for a specific vehicle.",
)
async def get_vehicle_analysis(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    user: User = Depends(get_current_user_optional),
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Get vehicle analysis results.
    
    This endpoint retrieves the analysis results for a specific vehicle,
    including vehicle identification, damage assessment, parts cost estimation,
    market price analysis, and ROI calculation.
    
    If the analysis is still in progress, it returns the current status.
    """
    try:
        vehicle_service = services["vehicle_service"]
        analysis_service = services["analysis_service"]
        
        # Get vehicle from database
        vehicle = await vehicle_service.get_vehicle(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found",
            )
        
        # Check if user has access to this vehicle
        if user and user.id != vehicle.user_id and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this vehicle",
            )
        
        # Get analysis results
        analysis = await analysis_service.get_analysis_results(vehicle_id)
        if not analysis:
            # If analysis doesn't exist but vehicle does, it's still in queue or processing
            task_status = await analysis_service.get_task_status(vehicle.task_id)
            return {
                "vehicle_id": vehicle_id,
                "status": task_status.get("status", AnalysisStatus.QUEUED),
                "progress": task_status.get("progress", 0.0),
                "message": task_status.get("message", "Analysis in progress"),
                "created_at": vehicle.created_at,
                "completed_at": None,
                "vehicle_identification": None,
                "damage_assessment": None,
                "parts_estimate": None,
                "market_price": None,
                "roi_calculation": None,
            }
        
        # Return complete analysis results
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving vehicle analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving vehicle analysis: {str(e)}",
        )


@router.get(
    "/{vehicle_id}/report",
    response_class=StreamingResponse,
    summary="Download vehicle analysis report",
    description="Generate and download a report of the vehicle analysis in the requested format.",
)
async def download_analysis_report(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    format: str = Query(
        ReportFormat.PDF, 
        description="Report format (pdf, csv, json, xlsx)"
    ),
    user: User = Depends(get_current_active_user),
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Download vehicle analysis report.
    
    This endpoint generates and downloads a report of the vehicle analysis
    in the requested format (PDF, CSV, JSON, or Excel).
    
    The report includes all analysis results, including vehicle identification,
    damage assessment, parts cost estimation, market price analysis, and ROI calculation.
    """
    try:
        vehicle_service = services["vehicle_service"]
        analysis_service = services["analysis_service"]
        
        # Get vehicle from database
        vehicle = await vehicle_service.get_vehicle(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found",
            )
        
        # Check if user has access to this vehicle
        if user.id != vehicle.user_id and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this vehicle",
            )
        
        # Check if analysis is complete
        analysis = await analysis_service.get_analysis_results(vehicle_id)
        if not analysis or analysis["status"] != AnalysisStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is not yet complete. Cannot generate report.",
            )
        
        # Generate report
        report_task = generate_analysis_report_task.delay(
            vehicle_id=vehicle_id,
            format=format,
        )
        
        # Wait for report generation to complete
        report_result = report_task.get(timeout=60)  # Wait up to 60 seconds
        
        if not report_result or "error" in report_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating report: {report_result.get('error', 'Unknown error')}",
            )
        
        # Get report from storage
        report_path = report_result.get("report_path")
        if not report_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Report path not found in task result",
            )
        
        # Stream the report file
        minio_service = services["minio_service"]
        report_stream = await minio_service.get_file_stream(
            bucket_name=settings.MINIO_BUCKET_IMAGES,
            object_name=report_path,
        )
        
        # Set content type based on format
        content_types = {
            ReportFormat.PDF: "application/pdf",
            ReportFormat.CSV: "text/csv",
            ReportFormat.JSON: "application/json",
            ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        
        # Set filename based on vehicle and format
        make_model = f"{vehicle.make}_{vehicle.model}" if vehicle.make and vehicle.model else "vehicle"
        year = f"{vehicle.year}_" if vehicle.year else ""
        filename = f"{year}{make_model}_analysis_report.{format}"
        
        # Return streaming response
        return StreamingResponse(
            report_stream,
            media_type=content_types.get(format, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating analysis report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analysis report: {str(e)}",
        )


@router.websocket("/ws/{vehicle_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    vehicle_id: str,
    services: Dict[str, Any] = Depends(get_services),
):
    """
    WebSocket endpoint for real-time analysis progress updates.
    
    This endpoint allows clients to receive real-time updates about the
    progress of a vehicle analysis. It broadcasts updates to all connected
    clients for a specific vehicle.
    """
    try:
        # Accept the WebSocket connection
        await manager.connect(websocket, vehicle_id)
        
        # Get vehicle service
        vehicle_service = services["vehicle_service"]
        analysis_service = services["analysis_service"]
        redis_service = services["redis_service"]
        
        # Verify vehicle exists
        vehicle = await vehicle_service.get_vehicle(vehicle_id)
        if not vehicle:
            await websocket.send_json({
                "error": f"Vehicle with ID {vehicle_id} not found",
            })
            await websocket.close(code=1008)  # Policy violation
            return
        
        # Send initial status
        task_status = await analysis_service.get_task_status(vehicle.task_id)
        await websocket.send_json({
            "vehicle_id": vehicle_id,
            "status": task_status.get("status", AnalysisStatus.QUEUED),
            "progress": task_status.get("progress", 0.0),
            "current_step": task_status.get("current_step", "Waiting in queue"),
            "message": task_status.get("message", "Analysis in progress"),
            "estimated_time_remaining": task_status.get("estimated_time_remaining", None),
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Subscribe to Redis pubsub for this vehicle
        pubsub = redis_service.get_pubsub()
        await pubsub.subscribe(f"vehicle:{vehicle_id}:progress")
        
        # Listen for messages until client disconnects
        try:
            while True:
                message = await pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                
                # Check if client is still connected
                try:
                    data = await websocket.receive_text()
                    # Handle any client messages (e.g., ping)
                    if data == "ping":
                        await websocket.send_json({"pong": True})
                except WebSocketDisconnect:
                    break
                
        except WebSocketDisconnect:
            # Client disconnected
            pass
        finally:
            # Unsubscribe and disconnect
            await pubsub.unsubscribe(f"vehicle:{vehicle_id}:progress")
            manager.disconnect(websocket, vehicle_id)
            
    except Exception as e:
        logger.exception(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "error": f"WebSocket error: {str(e)}",
            })
            await websocket.close(code=1011)  # Internal error
        except:
            pass


@router.get(
    "/",
    response_model=List[VehicleDetail],
    status_code=status.HTTP_200_OK,
    summary="List user's vehicles",
    description="Retrieve a list of vehicles submitted by the current user.",
)
async def list_user_vehicles(
    skip: int = Query(0, ge=0, description="Skip N records"),
    limit: int = Query(100, ge=1, le=1000, description="Limit to N records"),
    status: Optional[str] = Query(None, description="Filter by analysis status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    user: User = Depends(get_current_active_user),
    services: Dict[str, Any] = Depends(get_services),
):
    """
    List user's vehicles.
    
    This endpoint retrieves a list of vehicles submitted by the current user,
    with optional filtering and sorting.
    """
    try:
        vehicle_service = services["vehicle_service"]
        
        # Get vehicles from database
        vehicles = await vehicle_service.list_user_vehicles(
            user_id=user.id,
            skip=skip,
            limit=limit,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return vehicles
        
    except Exception as e:
        logger.exception(f"Error listing user vehicles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing user vehicles: {str(e)}",
        )


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vehicle",
    description="Delete a vehicle and all associated data.",
)
async def delete_vehicle(
    vehicle_id: str = Path(..., description="Vehicle ID"),
    user: User = Depends(get_current_active_user),
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Delete a vehicle.
    
    This endpoint deletes a vehicle and all associated data, including
    analysis results, reports, and uploaded photos.
    """
    try:
        vehicle_service = services["vehicle_service"]
        
        # Get vehicle from database
        vehicle = await vehicle_service.get_vehicle(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with ID {vehicle_id} not found",
            )
        
        # Check if user has access to this vehicle
        if user.id != vehicle.user_id and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this vehicle",
            )
        
        # Delete vehicle and associated data
        await vehicle_service.delete_vehicle(vehicle_id)
        
        # Return no content
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting vehicle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting vehicle: {str(e)}",
        )
