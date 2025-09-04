import time
from typing import Dict, List
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from threading import Lock

class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        
        self.clip_requests_total = Counter(
            'clip_requests_total', 
            'Total number of clip requests',
            ['camera_id', 'status']
        )
        
        self.clip_latency_seconds = Histogram(
            'clip_latency_seconds',
            'Time taken to process clip requests',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        
        self.clip_queue_depth = Gauge(
            'clip_queue_depth',
            'Number of clips in processing queue'
        )
        
        self.clip_errors_total = Counter(
            'clip_errors_total',
            'Total number of clip processing errors',
            ['error_type']
        )
        
        self._active_requests: Dict[str, float] = {}
    
    def record_request_start(self, clip_id: str, camera_id: str):
        with self._lock:
            self._active_requests[clip_id] = time.time()
            self.clip_requests_total.labels(camera_id=camera_id, status='started').inc()
    
    def record_request_complete(self, clip_id: str, camera_id: str, success: bool):
        with self._lock:
            if clip_id in self._active_requests:
                duration = time.time() - self._active_requests[clip_id]
                self.clip_latency_seconds.observe(duration)
                del self._active_requests[clip_id]
            
            status = 'success' if success else 'failed'
            self.clip_requests_total.labels(camera_id=camera_id, status=status).inc()
    
    def record_error(self, error_type: str):
        self.clip_errors_total.labels(error_type=error_type).inc()
    
    def update_queue_depth(self, depth: int):
        self.clip_queue_depth.set(depth)
    
    def get_metrics(self) -> str:
        return generate_latest()
    
    def get_content_type(self) -> str:
        return CONTENT_TYPE_LATEST

metrics_collector = MetricsCollector()