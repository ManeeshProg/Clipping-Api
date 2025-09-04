import logging
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.models import ClipRequest, ClipResponse, HealthResponse
from app.job_manager import job_manager
from app.metrics import metrics_collector
from app.mediamtx_client import MediaMTXClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clipping API Microservice",
    description="Video clip retrieval service with MediaMTX integration",
    version="1.0.0"
)

if os.path.exists("videos"):
    app.mount("/videos", StaticFiles(directory="videos"), name="videos")

mediamtx_client = MediaMTXClient()

@app.post("/clips", response_model=dict)
async def create_clip(request: ClipRequest):
    try:
        logger.info(f"Received clip request for camera {request.camera_id}")
        
        # Calculate time range: 15s before timestamp + 5s after timestamp
        start_time = request.timestamp - timedelta(seconds=15)
        end_time = request.timestamp + timedelta(seconds=5)
        
        clips = mediamtx_client.find_clips(
            request.camera_id, start_time, end_time
        )
        
        if not clips:
            raise HTTPException(
                status_code=404, 
                detail=f"No video clips found for camera {request.camera_id} in specified time range"
            )
        
        clip_id = await job_manager.submit_job(request)
        
        return {
            "clip_id": clip_id,
            "status": "pending",
            "message": "Clip request submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating clip request: {e}")
        metrics_collector.record_error("api_error")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip_status(clip_id: str):
    try:
        job = await job_manager.get_job(clip_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clip status: {e}")
        metrics_collector.record_error("api_error")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.get("/metrics")
async def get_metrics():
    metrics_data = metrics_collector.get_metrics()
    return Response(
        content=metrics_data,
        media_type=metrics_collector.get_content_type()
    )

@app.get("/cameras")
async def list_cameras():
    try:
        cameras = mediamtx_client.get_camera_list()
        return {"cameras": cameras}
    except Exception as e:
        logger.error(f"Error listing cameras: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {
        "service": "Clipping API Microservice",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "create_clip": "POST /clips",
            "get_clip_status": "GET /clips/{clip_id}",
            "health": "GET /health",
            "metrics": "GET /metrics",
            "cameras": "GET /cameras"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)