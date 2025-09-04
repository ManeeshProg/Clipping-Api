# 🎬 Clipping API Microservice

A **timestamp-based** FastAPI microservice that creates video clips from recorded camera footage using 5-second segment processing.

## ✨ Features

- 🕒 **Timestamp-Based Requests** - Request clips using a single timestamp (15s before + 5s after)
- 📹 **5-Second Segment Processing** - Optimized for MediaMTX 5-second video segments
- ⚡ **Stream-Copy FFmpeg** - Fast, lossless video concatenation
- 🔄 **Async Job Queue** - Concurrent clip processing
- 📊 **Prometheus Metrics** - Built-in observability
- 📝 **Multi-Format Annotations** - JSON, YAML, and TXT metadata files

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/clips` | Submit a clip request |
| GET | `/clips/{clip_id}` | Get clip status and download link |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/cameras` | List available cameras |

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg
- Docker (optional)

### Local Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start the service:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

3. **Access the API:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Docker Setup

1. **Start with Docker Compose:**
```bash
docker-compose up -d
```

This starts:
- Clipping API on port 8000
- Prometheus on port 9090
- Grafana on port 3000 (admin/admin)

## 🎯 Video File Setup

### 📂 Directory Structure

Place your video files in the MediaMTX clips directory:

```
D:\BirlaPOC\Clipping_API\mediamtx_clips\
├── camera1\
│   ├── camera1_20250829_143010.mp4    # 14:30:10 segment
│   ├── camera1_20250829_143015.mp4    # 14:30:15 segment  
│   ├── camera1_20250829_143020.mp4    # 14:30:20 segment
│   └── camera1_20250829_143025.mp4    # 14:30:25 segment
├── camera2\
│   └── camera2_20250829_143030.mp4
└── camera3\
    └── camera3_20250829_143045.mp4
```

### 📝 File Naming Convention

- **Format**: `{camera_id}_{YYYYMMDD}_{HHMMSS}.mp4`
- **Examples**:
  - `camera1_20250829_143010.mp4` → 2025-08-29 at 14:30:10
  - `camera2_20250830_091545.mp4` → 2025-08-30 at 09:15:45

### 🎥 Video Requirements

- **Duration**: 5-second segments (recommended)
- **Formats**: `.mp4`, `.mkv`, `.avi`
- **Content**: Any valid video content (H.264, etc.)
- **Size**: Any size (API handles automatically)

## 🚀 Usage Examples

### ✅ NEW: Timestamp-Based Request

```bash
curl -X POST "http://localhost:8000/clips" \
-H "Content-Type: application/json" \
-d '{
  "camera_id": "camera1",
  "timestamp": "2025-08-29T14:30:15",
  "duration": 20
}'
```

**What this does:**
- 🕒 **Timestamp**: `14:30:15` (reference point)
- ⏮️ **Gets 15s before**: `14:30:00` to `14:30:15`
- ⏭️ **Gets 5s after**: `14:30:15` to `14:30:20`
- 🎬 **Total clip**: 20 seconds (4 segments combined)

**Response:**
```json
{
  "clip_id": "e9096580-1612-4190-a3d2-2bd47661d9eb",
  "status": "pending", 
  "message": "Clip request submitted successfully"
}
```

### 📊 Check Clip Status

```bash
curl "http://localhost:8000/clips/e9096580-1612-4190-a3d2-2bd47661d9eb"
```

**Response:**
```json
{
  "clip_id": "e9096580-1612-4190-a3d2-2bd47661d9eb",
  "status": "done",
  "camera_id": "camera1",
  "start_time": "2025-08-29T14:30:00",
  "end_time": "2025-08-29T14:30:20",
  "download_url": "/videos/camera1_20250829_144643_e9096580-1612-4190-a3d2-2bd47661d9eb.mp4",
  "created_at": "2025-08-29T14:46:43.924982",
  "completed_at": "2025-08-29T14:46:44.008043"
}
```

### 📥 Download the Clip

```bash
# Direct download
wget http://localhost:8000/videos/camera1_20250829_144643_e9096580-1612-4190-a3d2-2bd47661d9eb.mp4

# Or with curl
curl -O http://localhost:8000/videos/camera1_20250829_144643_e9096580-1612-4190-a3d2-2bd47661d9eb.mp4
```

### 🎯 Real-World Example

**Scenario**: Security incident at 2:30:15 PM, need 15 seconds before + 5 seconds after

1. **Place video files**:
   ```
   mediamtx_clips/camera1/
   ├── camera1_20250829_143000.mp4  # 14:30:00-14:30:05
   ├── camera1_20250829_143005.mp4  # 14:30:05-14:30:10
   ├── camera1_20250829_143010.mp4  # 14:30:10-14:30:15
   ├── camera1_20250829_143015.mp4  # 14:30:15-14:30:20
   └── camera1_20250829_143020.mp4  # 14:30:20-14:30:25
   ```

2. **Make request**:
   ```bash
   curl -X POST "http://localhost:8000/clips" \
   -H "Content-Type: application/json" \
   -d '{
     "camera_id": "camera1",
     "timestamp": "2025-08-29T14:30:15",
     "duration": 20
   }'
   ```

3. **Result**: Combined 20-second clip from 14:30:00 to 14:30:20 ✅

## Configuration

Edit `config.yaml` to customize:

- Storage paths
- Processing workers
- Retention policies
- Logging levels

## Monitoring

### Prometheus Metrics

Available at `/metrics`:

- `clip_requests_total` - Total requests by camera and status
- `clip_latency_seconds` - Processing latency histogram
- `clip_queue_depth` - Current queue depth
- `clip_errors_total` - Error counts by type

### Grafana Dashboard

Pre-configured dashboards for:
- Request rates and latency
- Error rates
- Queue depth monitoring
- Success rates by camera

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   REST API      │    │ Job Manager  │    │ Clip Processor  │
│   (FastAPI)     │───▶│ (AsyncQueue) │───▶│ (FFmpeg)        │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                     │
         ▼                       ▼                     ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Buffer Index    │    │   Metrics    │    │   Storage       │
│ (Mock Data)     │    │ (Prometheus) │    │ (Videos/Annot.) │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## 📁 Output Files

### 🎬 Video Files
Generated in `/videos/` directory:
- **Format**: `{camera_id}_{timestamp}_{clip_id}.mp4`
- **Example**: `camera1_20250829_144643_e9096580-1612-4190-a3d2-2bd47661d9eb.mp4`

### 📋 Annotation Files
Generated in `/annotations/` directory with detailed metadata:
- 📄 **JSON**: `camera1_20250829_144643_<clip_id>.json`
- 📋 **YAML**: `camera1_20250829_144643_<clip_id>.yaml`  
- 📝 **TXT**: `camera1_20250829_144643_<clip_id>.txt`

### 📊 Example Annotation Content

```json
{
  "clip_id": "e9096580-1612-4190-a3d2-2bd47661d9eb",
  "camera_id": "camera1",
  "requested_start": "2025-08-29T14:30:00",
  "requested_end": "2025-08-29T14:30:20", 
  "actual_start": "2025-08-29T14:30:00",
  "actual_end": "2025-08-29T14:30:20",
  "duration_seconds": 20.0,
  "source_clips": [
    {
      "file_path": "D:\\mediamtx_clips\\camera1\\camera1_20250829_143000.mp4",
      "filename": "camera1_20250829_143000.mp4",
      "start_time": "2025-08-29T14:30:00",
      "end_time": "2025-08-29T14:30:05",
      "file_size": 10998961
    },
    {
      "file_path": "D:\\mediamtx_clips\\camera1\\camera1_20250829_143005.mp4", 
      "filename": "camera1_20250829_143005.mp4",
      "start_time": "2025-08-29T14:30:05",
      "end_time": "2025-08-29T14:30:10",
      "file_size": 10998961
    }
  ],
  "created_at": "2025-08-29T14:46:44.008043",
  "source": "MediaMTX"
}
```

### 🎯 Key Benefits

- ✅ **Exact Timing**: 15 seconds before + 5 seconds after timestamp
- ✅ **Segment Combination**: Automatically merges multiple 5-second clips
- ✅ **Complete Segments**: Uses full segments even if partially overlapping
- ✅ **Fast Processing**: Stream-copy for lossless, high-speed concatenation
- ✅ **Rich Metadata**: Detailed information about source segments used

## Development

### 📁 Project Structure
```
clipping-api/
├── 🔧 app/
│   ├── __init__.py
│   ├── main.py           # 🌐 FastAPI app & timestamp processing
│   ├── models.py         # 📝 Pydantic models (NEW timestamp format)
│   ├── mediamtx_client.py # 📹 5-second segment detection
│   ├── job_manager.py    # 🔄 Async job queue
│   ├── clip_processor.py # ⚡ FFmpeg integration
│   └── metrics.py        # 📊 Prometheus metrics
├── 📂 mediamtx_clips/    # 🎬 INPUT: Your camera videos here!
│   ├── camera1/          #     └── camera1_YYYYMMDD_HHMMSS.mp4
│   ├── camera2/          #     └── camera2_YYYYMMDD_HHMMSS.mp4
│   └── camera3/          #     └── camera3_YYYYMMDD_HHMMSS.mp4
├── 🎞️ videos/           # 📤 OUTPUT: Generated clips
├── 📋 annotations/       # 📄 OUTPUT: Metadata files
├── ⚙️ config.yaml       # 🔧 Configuration
├── 📦 requirements.txt   # 🐍 Python dependencies
└── 📖 README.md         # 📚 This file
```

### 🔧 Setup Checklist

Before running the API:

- ✅ **Create directories**:
  ```bash
  mkdir -p mediamtx_clips/camera1 videos annotations
  ```

- ✅ **Place video files** in `mediamtx_clips/camera1/`:
  ```bash
  # Example: Copy your video with proper naming
  cp your_video.mp4 mediamtx_clips/camera1/camera1_20250829_143010.mp4
  ```

- ✅ **Install dependencies**:
  ```bash
  pip install fastapi uvicorn prometheus_client
  ```

- ✅ **Start API**:
  ```bash
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

### Testing

```bash
# Run with test configuration
python -m pytest tests/

# Load test with sample requests
python scripts/load_test.py
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

2. **Permission denied on video files**
   ```bash
   chmod 644 mock_cameras/*.mp4
   ```

3. **Port already in use**
   ```bash
   # Change port in config.yaml or use environment variable
   export PORT=8001
   python -m uvicorn app.main:app --port $PORT
   ```

## License

MIT License - see LICENSE file for details.