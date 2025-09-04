from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ClipStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

class ClipRequest(BaseModel):
    camera_id: str
    timestamp: datetime
    duration: int = Field(default=20, description="Duration in seconds")

class ClipResponse(BaseModel):
    clip_id: str
    status: ClipStatus
    camera_id: str
    start_time: datetime
    end_time: datetime
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class BufferSegment(BaseModel):
    file: str
    start: datetime
    end: datetime
    keyframes: List[float]

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"

class MetricsResponse(BaseModel):
    clip_requests_total: int
    clip_errors_total: int
    clip_queue_depth: int
    clip_latency_histogram: dict