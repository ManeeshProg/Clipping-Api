import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional
from app.models import ClipRequest, ClipResponse, ClipStatus
from app.metrics import metrics_collector

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, ClipResponse] = {}
        self.processing_queue = asyncio.Queue()
        self.max_concurrent_jobs = 3
        self._workers_started = False
        self._lock = asyncio.Lock()
    
    async def submit_job(self, request: ClipRequest) -> str:
        clip_id = str(uuid.uuid4())
        
        # Calculate time range: 15s before timestamp + 5s after timestamp
        from datetime import timedelta
        start_time = request.timestamp - timedelta(seconds=15)
        end_time = request.timestamp + timedelta(seconds=5)
        
        job = ClipResponse(
            clip_id=clip_id,
            status=ClipStatus.PENDING,
            camera_id=request.camera_id,
            start_time=start_time,
            end_time=end_time,
            created_at=datetime.now()
        )
        
        async with self._lock:
            self.jobs[clip_id] = job
        
        await self.processing_queue.put(clip_id)
        metrics_collector.update_queue_depth(self.processing_queue.qsize())
        metrics_collector.record_request_start(clip_id, request.camera_id)
        
        if not self._workers_started:
            await self._start_workers()
        
        logger.info(f"Job {clip_id} submitted for camera {request.camera_id}")
        return clip_id
    
    async def get_job(self, clip_id: str) -> Optional[ClipResponse]:
        async with self._lock:
            return self.jobs.get(clip_id)
    
    async def update_job_status(self, clip_id: str, status: ClipStatus, 
                              download_url: Optional[str] = None, 
                              error_message: Optional[str] = None):
        async with self._lock:
            if clip_id in self.jobs:
                self.jobs[clip_id].status = status
                if download_url:
                    self.jobs[clip_id].download_url = download_url
                if error_message:
                    self.jobs[clip_id].error_message = error_message
                if status in [ClipStatus.DONE, ClipStatus.FAILED]:
                    self.jobs[clip_id].completed_at = datetime.now()
                    success = status == ClipStatus.DONE
                    metrics_collector.record_request_complete(
                        clip_id, self.jobs[clip_id].camera_id, success
                    )
    
    async def _start_workers(self):
        if self._workers_started:
            return
        
        self._workers_started = True
        for i in range(self.max_concurrent_jobs):
            asyncio.create_task(self._worker(f"worker-{i}"))
        logger.info(f"Started {self.max_concurrent_jobs} worker tasks")
    
    async def _worker(self, worker_name: str):
        logger.info(f"Worker {worker_name} started")
        
        while True:
            try:
                clip_id = await self.processing_queue.get()
                metrics_collector.update_queue_depth(self.processing_queue.qsize())
                
                job = await self.get_job(clip_id)
                if not job:
                    continue
                
                logger.info(f"Worker {worker_name} processing job {clip_id}")
                await self.update_job_status(clip_id, ClipStatus.PROCESSING)
                
                from app.clip_processor import process_clip
                success, result = await process_clip(job)
                
                if success:
                    await self.update_job_status(
                        clip_id, ClipStatus.DONE, download_url=result
                    )
                    logger.info(f"Job {clip_id} completed successfully")
                else:
                    await self.update_job_status(
                        clip_id, ClipStatus.FAILED, error_message=result
                    )
                    logger.error(f"Job {clip_id} failed: {result}")
                    metrics_collector.record_error("processing_failed")
                
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                if 'clip_id' in locals():
                    await self.update_job_status(
                        clip_id, ClipStatus.FAILED, 
                        error_message=f"Worker error: {str(e)}"
                    )
                    metrics_collector.record_error("worker_exception")
    
    def get_queue_depth(self) -> int:
        return self.processing_queue.qsize()
    
    def get_job_count(self) -> int:
        return len(self.jobs)

job_manager = JobManager()