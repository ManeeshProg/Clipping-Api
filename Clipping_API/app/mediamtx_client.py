import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import glob
import re

logger = logging.getLogger(__name__)

class MediaMTXClient:
    def __init__(self, clips_base_dir: str = "mediamtx_clips"):
        """
        Initialize MediaMTX client for fetching recorded clips
        
        Args:
            clips_base_dir: Base directory where MediaMTX stores recorded clips
        """
        self.clips_base_dir = os.path.abspath(clips_base_dir)
        self.supported_formats = ['.mp4', '.mkv', '.avi']
        
    def find_clips(self, camera_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Find recorded clips for a camera within the specified time range
        
        Args:
            camera_id: Camera identifier
            start_time: Start timestamp for clip search
            end_time: End timestamp for clip search
            
        Returns:
            List of clip metadata dictionaries
        """
        camera_dir = os.path.join(self.clips_base_dir, camera_id)
        
        if not os.path.exists(camera_dir):
            logger.warning(f"Camera directory not found: {camera_dir}")
            return []
        
        clips = []
        
        # Search for video files with timestamp patterns
        for ext in self.supported_formats:
            pattern = os.path.join(camera_dir, f"*{ext}")
            for file_path in glob.glob(pattern):
                clip_info = self._extract_clip_info(file_path, start_time, end_time)
                if clip_info:
                    clips.append(clip_info)
        
        # Sort by recording start time
        clips.sort(key=lambda x: x['start_time'])
        return clips
    
    def _extract_clip_info(self, file_path: str, start_time: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Extract clip information from file path and check if it overlaps with requested time range
        
        Args:
            file_path: Path to the video clip file
            start_time: Requested start time
            end_time: Requested end time
            
        Returns:
            Clip info dictionary if the clip overlaps with the time range, None otherwise
        """
        filename = os.path.basename(file_path)
        
        # Try different timestamp formats that MediaMTX might use
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})',  # YYYY-MM-DD_HH-MM-SS
            r'(\d{4}\d{2}\d{2})_(\d{6})',                  # YYYYMMDD_HHMMSS
            r'(\d{14})',                                   # YYYYMMDDHHMMSS
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',    # ISO format in filename
        ]
        
        clip_start_time = None
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    if len(match.groups()) == 2:
                        # Date and time separate
                        date_str = match.group(1).replace('-', '')
                        time_str = match.group(2).replace('-', '')
                        timestamp_str = date_str + time_str
                        clip_start_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    elif len(match.groups()) == 1:
                        timestamp_str = match.group(1)
                        if 'T' in timestamp_str:
                            # ISO format
                            clip_start_time = datetime.fromisoformat(timestamp_str.replace(':', ''))
                        else:
                            # Numeric format
                            clip_start_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    break
                except ValueError:
                    continue
        
        if not clip_start_time:
            # Fallback to file modification time
            try:
                stat = os.stat(file_path)
                clip_start_time = datetime.fromtimestamp(stat.st_mtime)
                logger.info(f"Using file mtime for {filename}: {clip_start_time}")
            except Exception as e:
                logger.error(f"Could not determine timestamp for {filename}: {e}")
                return None
        
        # Estimate clip duration (MediaMTX typically creates fixed-duration segments)
        # This could be configurable or determined by analyzing the actual file
        estimated_duration = timedelta(seconds=20)  # Default 20-second segments
        
        try:
            # Try to get actual file duration using os.stat as a rough estimate
            # In a real implementation, you might want to use ffprobe for accurate duration
            stat = os.stat(file_path)
            file_size_mb = stat.st_size / (1024 * 1024)
            
            # Rough estimate: 1MB per 5 seconds for standard quality
            # Adjust this based on your MediaMTX recording settings
            if file_size_mb > 0:
                estimated_duration = timedelta(seconds=max(5, int(file_size_mb * 5)))
        except Exception as e:
            logger.debug(f"Could not estimate duration for {filename}: {e}")
        
        clip_end_time = clip_start_time + estimated_duration
        
        # Check if clip overlaps with requested time range
        if clip_end_time >= start_time and clip_start_time <= end_time:
            return {
                'file_path': os.path.abspath(file_path),
                'filename': filename,
                'start_time': clip_start_time,
                'end_time': clip_end_time,
                'duration_seconds': estimated_duration.total_seconds(),
                'file_size': os.path.getsize(file_path)
            }
        
        return None
    
    def get_camera_list(self) -> List[str]:
        """
        Get list of available cameras based on subdirectories in clips base directory
        
        Returns:
            List of camera IDs
        """
        if not os.path.exists(self.clips_base_dir):
            return []
        
        cameras = []
        try:
            for item in os.listdir(self.clips_base_dir):
                item_path = os.path.join(self.clips_base_dir, item)
                if os.path.isdir(item_path):
                    cameras.append(item)
        except Exception as e:
            logger.error(f"Error listing cameras: {e}")
        
        return sorted(cameras)
    
    def validate_clips_directory(self) -> bool:
        """
        Validate that the MediaMTX clips directory exists and is accessible
        
        Returns:
            True if directory is valid, False otherwise
        """
        try:
            return os.path.exists(self.clips_base_dir) and os.path.isdir(self.clips_base_dir)
        except Exception as e:
            logger.error(f"Error validating clips directory: {e}")
            return False