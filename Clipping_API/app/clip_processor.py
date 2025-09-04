import asyncio
import os
import json
import yaml
import logging
import subprocess
import sys
from datetime import datetime
from typing import Tuple, List, Dict, Any
from pathlib import Path
from app.models import ClipResponse
from app.mediamtx_client import MediaMTXClient
from app.metrics import metrics_collector

logger = logging.getLogger(__name__)

class ClipProcessor:
    def __init__(self, mediamtx_clips_dir: str = "mediamtx_clips"):
        self.mediamtx_client = MediaMTXClient(mediamtx_clips_dir)
        self.videos_dir = "videos"
        self.annotations_dir = "annotations"
        
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.annotations_dir, exist_ok=True)
    
    async def process_clip(self, job: ClipResponse) -> Tuple[bool, str]:
        try:
            # Calculate time range from timestamp 
            start_time = job.start_time if hasattr(job, 'start_time') else job.timestamp - timedelta(seconds=15)
            end_time = job.end_time if hasattr(job, 'end_time') else job.timestamp + timedelta(seconds=5)
            clips = self.mediamtx_client.find_clips(
                job.camera_id, start_time, end_time
            )
            
            if not clips:
                return False, f"No clips found for camera {job.camera_id} in time range"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{job.camera_id}_{timestamp}_{job.clip_id}.mp4"
            output_path = os.path.join(self.videos_dir, output_filename)
            
            success = await self._process_mediamtx_clips(clips, output_path, start_time, end_time)
            
            if not success:
                return False, "FFmpeg processing failed"
            
            # Use actual start/end times from the clips
            actual_start = min(clip['start_time'] for clip in clips)
            actual_end = max(clip['end_time'] for clip in clips)
            
            await self._generate_annotations(job, clips, actual_start, actual_end, timestamp)
            
            download_url = f"/videos/{output_filename}"
            return True, download_url
            
        except Exception as e:
            logger.error(f"Error processing clip {job.clip_id}: {e}")
            metrics_collector.record_error("processing_exception")
            return False, str(e)
    
    async def _process_mediamtx_clips(self, clips: List[Dict[str, Any]], output_path: str, 
                                     start_time: datetime, end_time: datetime) -> bool:
        try:
            if len(clips) == 1:
                clip = clips[0]
                start_offset = max(0, (start_time - clip['start_time']).total_seconds())
                duration = (end_time - max(start_time, clip['start_time'])).total_seconds()
                
                # Convert to absolute path
                input_file = os.path.abspath(clip['file_path'])
                output_file = os.path.abspath(output_path)
                
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_offset),
                    "-i", input_file,
                    "-t", str(duration),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    output_file
                ]
            else:
                # Use pathlib for cross-platform path handling
                concat_file = f"concat_{Path(clips[0]['file_path']).name}.txt"
                concat_path = os.path.abspath(concat_file)
                
                with open(concat_path, 'w') as f:
                    for clip in clips:
                        abs_clip_path = os.path.abspath(clip['file_path'])
                        # Use forward slashes for concat file format (FFmpeg requirement)
                        file_line = f"file '{abs_clip_path.replace(os.sep, '/')}'\n"
                        f.write(file_line)
                
                output_file = os.path.abspath(output_path)
                
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_path,
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    output_file
                ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Use synchronous subprocess to avoid Windows asyncio issues
            try:
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                stdout = process.stdout.encode() if isinstance(process.stdout, str) else b''
                stderr = process.stderr.encode() if isinstance(process.stderr, str) else b''
                returncode = process.returncode
            except subprocess.TimeoutExpired as e:
                logger.error(f"FFmpeg command timed out after 300 seconds")
                metrics_collector.record_error("ffmpeg_timeout")
                return False
            except Exception as sync_e:
                logger.error(f"Subprocess execution failed: {sync_e}")
                metrics_collector.record_error("subprocess_failed")
                return False
            
            if len(clips) > 1:
                concat_path = f"concat_{Path(clips[0]['file_path']).name}.txt" 
                abs_concat_path = os.path.abspath(concat_path)
                if os.path.exists(abs_concat_path):
                    os.remove(abs_concat_path)
            
            if returncode == 0:
                logger.info(f"Successfully created clip: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg failed with return code {returncode}")
                logger.error(f"FFmpeg command was: {' '.join(cmd)}")
                logger.error(f"FFmpeg stderr: {stderr.decode()}")
                logger.error(f"FFmpeg stdout: {stdout.decode()}")
                metrics_collector.record_error("ffmpeg_failed")
                return False
                
        except Exception as e:
            logger.error(f"Error in FFmpeg processing: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"FFmpeg command that failed: {' '.join(cmd) if 'cmd' in locals() else 'Command not built'}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            metrics_collector.record_error("ffmpeg_exception")
            return False
    
    async def _generate_annotations(self, job: ClipResponse, clips_info: List[Dict], 
                                  actual_start: datetime, actual_end: datetime, 
                                  timestamp: str):
        base_filename = f"{job.camera_id}_{timestamp}_{job.clip_id}"
        
        annotation_data = {
            "clip_id": job.clip_id,
            "camera_id": job.camera_id,
            "requested_start": job.start_time.isoformat(),
            "requested_end": job.end_time.isoformat(),
            "actual_start": actual_start.isoformat(),
            "actual_end": actual_end.isoformat(),
            "duration_seconds": (job.end_time - job.start_time).total_seconds(),
            "source_clips": [
                {
                    "file_path": clip["file_path"],
                    "filename": clip["filename"],
                    "start_time": clip["start_time"].isoformat(),
                    "end_time": clip["end_time"].isoformat(),
                    "file_size": clip["file_size"]
                } for clip in clips_info
            ],
            "created_at": datetime.now().isoformat(),
            "source": "MediaMTX"
        }
        
        json_path = os.path.join(self.annotations_dir, f"{base_filename}.json")
        with open(json_path, 'w') as f:
            json.dump(annotation_data, f, indent=2)
        
        yaml_path = os.path.join(self.annotations_dir, f"{base_filename}.yaml")
        with open(yaml_path, 'w') as f:
            yaml.dump(annotation_data, f, default_flow_style=False)
        
        txt_path = os.path.join(self.annotations_dir, f"{base_filename}.txt")
        with open(txt_path, 'w') as f:
            f.write(f"Clip ID: {job.clip_id}\n")
            f.write(f"Camera: {job.camera_id}\n")
            f.write(f"Source: MediaMTX\n")
            f.write(f"Requested Time Range: {job.start_time} to {job.end_time}\n")
            f.write(f"Actual Time Range: {actual_start} to {actual_end}\n")
            f.write(f"Duration: {annotation_data['duration_seconds']} seconds\n")
            f.write(f"Source Clips Used: {len(clips_info)}\n")
            for i, clip in enumerate(clips_info):
                f.write(f"  {i+1}. {clip['filename']} ({clip['start_time'].isoformat()} to {clip['end_time'].isoformat()})\n")

clip_processor = ClipProcessor()

async def process_clip(job: ClipResponse) -> Tuple[bool, str]:
    return await clip_processor.process_clip(job)