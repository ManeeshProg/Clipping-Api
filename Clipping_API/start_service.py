#!/usr/bin/env python3

"""
Clipping API Service Launcher
Easy way to start the service with proper configuration
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import prometheus_client
        print("✅ Python dependencies OK")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    # Check FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg OK")
        else:
            print("❌ FFmpeg not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found")
        print("Install FFmpeg:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  macOS: brew install ffmpeg") 
        print("  Windows: Download from https://ffmpeg.org/download.html")
        return False
    
    return True

def setup_directories():
    """Create required directories"""
    directories = ['videos', 'annotations', 'logs']
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ Directory {dir_name}/ ready")

def check_mock_data():
    """Check if mock camera data exists"""
    mock_dir = Path("mock_cameras")
    if not mock_dir.exists():
        print("❌ mock_cameras/ directory not found")
        return False
    
    video_files = list(mock_dir.glob("*.mp4"))
    if not video_files:
        print("❌ No video files found in mock_cameras/")
        print("Add some .mp4 files to mock_cameras/ directory")
        return False
    
    print(f"✅ Found {len(video_files)} video files in mock_cameras/")
    for video in video_files:
        print(f"   - {video.name}")
    
    return True

def main():
    print("🎬 Clipping API Service Launcher")
    print("=" * 40)
    
    # Check working directory
    if not Path("app/main.py").exists():
        print("❌ app/main.py not found")
        print("Make sure you're in the project root directory")
        sys.exit(1)
    
    print("✅ Project structure OK")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Check mock data
    if not check_mock_data():
        print("⚠️  Warning: Mock data may be incomplete")
    
    print("\n🚀 Starting Clipping API Service...")
    print("=" * 40)
    print("API will be available at:")
    print("  - Main API: http://localhost:8000")
    print("  - Interactive Docs: http://localhost:8000/docs")
    print("  - Health Check: http://localhost:8000/health") 
    print("  - Metrics: http://localhost:8000/metrics")
    print("\nPress Ctrl+C to stop the service")
    print("=" * 40)
    
    try:
        # Add current directory to Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        # Start the service
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], env=env)
        
    except KeyboardInterrupt:
        print("\n👋 Service stopped")
    except Exception as e:
        print(f"❌ Service failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()