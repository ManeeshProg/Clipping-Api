import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from app.models import BufferSegment

class BufferIndex:
    def __init__(self, buffer_file: str = "buffer_index.json"):
        # Use absolute path to ensure we're reading the right file
        self.buffer_file = os.path.abspath(buffer_file)
        self.buffer_data = self._load_buffer_index()
    
    def _load_buffer_index(self) -> Dict[str, List[BufferSegment]]:
        if os.path.exists(self.buffer_file):
            with open(self.buffer_file, 'r') as f:
                data = json.load(f)
                buffer_data = {}
                for camera_id, segments in data.items():
                    buffer_data[camera_id] = [
                        BufferSegment(
                            file=seg["file"],
                            start=datetime.fromisoformat(seg["start"]),
                            end=datetime.fromisoformat(seg["end"]),
                            keyframes=seg["keyframes"]
                        ) for seg in segments
                    ]
                return buffer_data
        return self._create_default_buffer()
    
    def _create_default_buffer(self) -> Dict[str, List[BufferSegment]]:
        base_time = datetime(2025, 8, 25, 18, 0, 0)
        
        default_data = {
            "camera1": [
                BufferSegment(
                    file="mock_cameras/test.mp4",
                    start=base_time,
                    end=base_time + timedelta(seconds=30),
                    keyframes=[0, 5, 10, 15, 20, 25, 30]
                ),
                BufferSegment(
                    file="mock_cameras/test2.mp4",
                    start=base_time + timedelta(seconds=30),
                    end=base_time + timedelta(seconds=60),
                    keyframes=[0, 5, 10, 15, 20, 25, 30]
                )
            ],
            "camera2": [
                BufferSegment(
                    file="mock_cameras/test2.mp4",
                    start=base_time,
                    end=base_time + timedelta(seconds=30),
                    keyframes=[0, 4, 8, 12, 16, 20, 24, 28, 30]
                ),
                BufferSegment(
                    file="mock_cameras/test3.mp4",
                    start=base_time + timedelta(seconds=30),
                    end=base_time + timedelta(seconds=60),
                    keyframes=[0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
                )
            ],
            "camera3": [
                BufferSegment(
                    file="mock_cameras/test3.mp4",
                    start=base_time,
                    end=base_time + timedelta(seconds=45),
                    keyframes=[0, 6, 12, 18, 24, 30, 36, 42, 45]
                )
            ]
        }
        
        self._save_buffer_index(default_data)
        return default_data
    
    def _save_buffer_index(self, data: Dict[str, List[BufferSegment]]):
        json_data = {}
        for camera_id, segments in data.items():
            json_data[camera_id] = [
                {
                    "file": seg.file,
                    "start": seg.start.isoformat(),
                    "end": seg.end.isoformat(),
                    "keyframes": seg.keyframes
                } for seg in segments
            ]
        
        with open(self.buffer_file, 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def find_segments(self, camera_id: str, start_time: datetime, end_time: datetime) -> List[BufferSegment]:
        if camera_id not in self.buffer_data:
            return []
        
        relevant_segments = []
        for segment in self.buffer_data[camera_id]:
            if (segment.start <= end_time and segment.end >= start_time):
                relevant_segments.append(segment)
        
        return sorted(relevant_segments, key=lambda s: s.start)
    
    def snap_to_keyframe(self, segment: BufferSegment, timestamp: datetime, prefer_earlier: bool = True) -> Tuple[datetime, float]:
        segment_duration = (segment.end - segment.start).total_seconds()
        relative_time = (timestamp - segment.start).total_seconds()
        
        if relative_time < 0:
            return segment.start, 0.0
        if relative_time > segment_duration:
            return segment.end, segment.keyframes[-1]
        
        closest_keyframe = min(segment.keyframes, key=lambda kf: abs(kf - relative_time))
        
        if prefer_earlier and closest_keyframe > relative_time:
            earlier_keyframes = [kf for kf in segment.keyframes if kf <= relative_time]
            if earlier_keyframes:
                closest_keyframe = max(earlier_keyframes)
        elif not prefer_earlier and closest_keyframe < relative_time:
            later_keyframes = [kf for kf in segment.keyframes if kf >= relative_time]
            if later_keyframes:
                closest_keyframe = min(later_keyframes)
        
        snapped_time = segment.start + timedelta(seconds=closest_keyframe)
        return snapped_time, closest_keyframe
    
    def get_camera_list(self) -> List[str]:
        return list(self.buffer_data.keys())