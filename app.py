#!/usr/bin/env python3
"""
Modified Applio app.py with REST API support for Audiobook Converter
 
INSTALLATION INSTRUCTIONS:
1. Download and install Applio normally
2. Backup the original app.py: cp app.py app.py.backup  
3. Replace app.py with this file
4. Run: python app.py
5. API will be available on port 6970, regular UI on 6969

This adds REST API endpoints while preserving all original Applio functionality.
"""

import gradio as gr
import sys
import os
import logging
import asyncio
import threading
from typing import Any
from pathlib import Path
import time

# FastAPI imports for API functionality
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import uuid
import edge_tts
from rvc.infer.infer import VoiceConverter

DEFAULT_SERVER_NAME = "127.0.0.1"
DEFAULT_PORT = 6969
API_PORT = 6970  # API runs on different port
MAX_PORT_ATTEMPTS = 10

# Set up logging
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Add current directory to sys.path
now_dir = os.getcwd()
sys.path.append(now_dir)

# Zluda hijack
import rvc.lib.zluda

# Import Tabs
from tabs.inference.inference import inference_tab
from tabs.train.train import train_tab
from tabs.extra.extra import extra_tab
from tabs.report.report import report_tab
from tabs.download.download import download_tab
from tabs.tts.tts import tts_tab
from tabs.voice_blender.voice_blender import voice_blender_tab
from tabs.plugins.plugins import plugins_tab
from tabs.settings.settings import settings_tab

# Run prerequisites
from core import run_prerequisites_script

run_prerequisites_script(
    pretraineds_hifigan=True,
    models=True,
    exe=True,
)

# Initialize i18n
from assets.i18n.i18n import I18nAuto

i18n = I18nAuto()

# Start Discord presence if enabled
from tabs.settings.sections.presence import load_config_presence

if load_config_presence():
    from assets.discord_presence import RPCManager
    RPCManager.start_presence()

# Check installation
import assets.installation_checker as installation_checker
installation_checker.check_installation()

# Load theme
import assets.themes.loadThemes as loadThemes
my_applio = loadThemes.load_theme() or "ParityError/Interstellar"

# ============================================================================
# AUDIOBOOK CONVERTER API - ADDED FOR AUDIOBOOK FUNCTIONALITY
# ============================================================================

# FastAPI app for API endpoints
api_app = FastAPI(title="Applio Audiobook API", version="1.0.0")

# Request/Response models
class AudiobookRequest(BaseModel):
    text: str
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: int = 0
    rvc_model_path: str
    rvc_index_path: str = ""
    embedder_model: str = "contentvec"
    pitch_shift: int = 0
    filename: str = None

class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: dict = {}
    output_file: str = None
    error: str = None

# Global job tracking
jobs = {}
voice_converter = None

def init_voice_converter():
    """Initialize RVC voice converter"""
    global voice_converter
    if voice_converter is None:
        try:
            voice_converter = VoiceConverter()
            print("✅ RVC VoiceConverter initialized for Audiobook API")
        except Exception as e:
            print(f"⚠️ Failed to initialize RVC for API: {e}")

@api_app.on_event("startup")
async def startup_event():
    """Initialize API components"""
    init_voice_converter()
    # Ensure output directory exists
    Path("api_outputs").mkdir(exist_ok=True)
    print("🚀 Audiobook API endpoints initialized")

@api_app.post("/generate_audiobook")
async def generate_audiobook(request: AudiobookRequest, background_tasks: BackgroundTasks):
    """Generate audiobook from text using TTS + RVC pipeline"""
    job_id = str(uuid.uuid4())
    filename = request.filename or f"audiobook_{job_id}.wav"
    output_path = Path("api_outputs") / filename
    
    # Initialize job
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        output_file=str(output_path)
    )
    
    # Start background processing
    background_tasks.add_task(process_audiobook_job, job_id, request, str(output_path))
    
    return {"job_id": job_id, "status": "pending"}

async def process_audiobook_job(job_id: str, request: AudiobookRequest, output_path: str):
    """Background task to process audiobook"""
    try:
        jobs[job_id].status = "processing"
        
        # Step 1: Generate TTS
        temp_tts_path = f"temp_tts_{job_id}.wav"
        
        # Format TTS rate
        rate_str = f"+{request.tts_rate}%" if request.tts_rate >= 0 else f"{request.tts_rate}%"
        
        # Generate TTS
        communicate = edge_tts.Communicate(request.text, request.tts_voice, rate=rate_str)
        await communicate.save(temp_tts_path)
        
        if not Path(temp_tts_path).exists():
            raise RuntimeError("TTS generation failed")
        
        # Step 2: Apply RVC conversion
        if voice_converter and Path(request.rvc_model_path).exists():
            voice_converter.convert_audio(
                audio_input_path=temp_tts_path,
                audio_output_path=output_path,
                model_path=request.rvc_model_path,
                index_path=request.rvc_index_path,
                embedder_model=request.embedder_model,
                sid=0,
                f0_up_key=request.pitch_shift,
                f0_method="rmvpe",
                filter_radius=3,
                resample_sr=0,
                rms_mix_rate=0.25,
                protect=0.33
            )
        else:
            # No RVC - just copy TTS output
            import shutil
            shutil.copy2(temp_tts_path, output_path)
        
        # Cleanup temp file
        if Path(temp_tts_path).exists():
            Path(temp_tts_path).unlink()
        
        # Update job status
        jobs[job_id].status = "completed"
        jobs[job_id].progress = {
            "text_length": len(request.text),
            "output_file": output_path
        }
        
    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)
        
        # Cleanup on error
        for temp_file in [f"temp_tts_{job_id}.wav", output_path]:
            if Path(temp_file).exists():
                Path(temp_file).unlink()

@api_app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@api_app.get("/download/{job_id}")
async def download_audiobook(job_id: str):
    """Download generated audiobook"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {job.status}")
    
    output_file = Path(job.output_file)
    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        path=str(output_file),
        filename=output_file.name,
        media_type="audio/wav"
    )

@api_app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job.status,
                "output_file": job.output_file
            }
            for job_id, job in jobs.items()
        ]
    }

@api_app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job and associated files"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    # Delete output file if it exists
    if job.output_file and Path(job.output_file).exists():
        Path(job.output_file).unlink()
    
    # Remove from jobs
    del jobs[job_id]
    
    return {"message": "Job deleted"}

@api_app.get("/")
async def api_root():
    """API information"""
    return {
        "name": "Applio Audiobook API",
        "version": "1.0.0",
        "description": "REST API for generating audiobooks with custom voices",
        "endpoints": [
            "POST /generate_audiobook - Generate audiobook from text",
            "GET /status/{job_id} - Get job status",
            "GET /download/{job_id} - Download audiobook",
            "GET /jobs - List all jobs",
            "DELETE /jobs/{job_id} - Delete job"
        ],
        "example_usage": {
            "generate": {
                "text": "Your text here",
                "tts_voice": "en-US-AriaNeural",
                "rvc_model_path": "path/to/model.pth",
                "rvc_index_path": "path/to/index.index"
            }
        }
    }

def run_api_server():
    """Run the API server in a separate thread"""
    try:
        print(f"🌐 Starting Audiobook API server on port {API_PORT}...")
        uvicorn.run(
            api_app,
            host="127.0.0.1",
            port=API_PORT,
            log_level="warning"
        )
    except Exception as e:
        print(f"❌ API server failed to start: {e}")

# ============================================================================
# ORIGINAL APPLIO GRADIO INTERFACE (UNCHANGED)
# ============================================================================

# Define Gradio interface
with gr.Blocks(
    theme=my_applio, title="Applio", css="footer{display:none !important}"
) as Applio:
    gr.Markdown("# Applio")
    gr.Markdown(
        i18n(
            "A simple, high-quality voice conversion tool focused on ease of use and performance."
        )
    )
    gr.Markdown(
        i18n(
            "[Support](https://discord.gg/urxFjYmYYh) — [GitHub](https://github.com/IAHispano/Applio)"
        )
    )
    
    # Add API info section
    with gr.Tab("🤖 Audiobook API"):
        gr.Markdown("## Applio Audiobook REST API")
        gr.Markdown(f"**API Server**: http://127.0.0.1:{API_PORT}")
        gr.Markdown("**Status**: ✅ API endpoints enabled for audiobook conversion")
        
        gr.Markdown("### Available Endpoints:")
        gr.Markdown("""
        - `POST /generate_audiobook` - Generate audiobook from text
        - `GET /status/{job_id}` - Check job status  
        - `GET /download/{job_id}` - Download completed audiobook
        - `GET /jobs` - List all jobs
        - `DELETE /jobs/{job_id}` - Delete job and cleanup
        """)
        
        gr.Markdown("### Example Usage:")
        gr.Code('''
# Submit audiobook generation job
curl -X POST "http://127.0.0.1:6970/generate_audiobook" \\
     -H "Content-Type: application/json" \\
     -d '{
       "text": "Your book text here",
       "tts_voice": "en-US-AriaNeural",
       "rvc_model_path": "logs/your_model.pth", 
       "rvc_index_path": "logs/your_index.index",
       "pitch_shift": 0
     }'

# Check job status (returns job_id from above)
curl "http://127.0.0.1:6970/status/{job_id}"

# Download completed audiobook
curl "http://127.0.0.1:6970/download/{job_id}" -o audiobook.wav
        ''', language="shell")
        
        gr.Markdown("### Integration:")
        gr.Markdown("This API is designed to work with the **AI Audiobook Converter** tool. " +
                   "Install the converter and point it to this API endpoint for automated book conversion.")
    
    with gr.Tab(i18n("Inference")):
        inference_tab()

    with gr.Tab(i18n("Training")):
        train_tab()

    with gr.Tab(i18n("TTS")):
        tts_tab()

    with gr.Tab(i18n("Voice Blender")):
        voice_blender_tab()

    with gr.Tab(i18n("Plugins")):
        plugins_tab()

    with gr.Tab(i18n("Download")):
        download_tab()

    with gr.Tab(i18n("Report a Bug")):
        report_tab()

    with gr.Tab(i18n("Extra")):
        extra_tab()

    with gr.Tab(i18n("Settings")):
        settings_tab()

    gr.Markdown(
        """
    <div style="text-align: center; font-size: 0.9em; text-color: a3a3a3;">
    By using Applio, you agree to comply with ethical and legal standards, respect intellectual property and privacy rights, avoid harmful or prohibited uses, and accept full responsibility for any outcomes, while Applio disclaims liability and reserves the right to amend these terms.
    </div>
    """
    )


def launch_gradio(server_name: str, server_port: int) -> None:
    Applio.launch(
        favicon_path="assets/ICON.ico",
        share="--share" in sys.argv,
        inbrowser="--open" in sys.argv,
        server_name=server_name,
        server_port=server_port,
    )


def get_value_from_args(key: str, default: Any = None) -> Any:
    if key in sys.argv:
        index = sys.argv.index(key) + 1
        if index < len(sys.argv):
            return sys.argv[index]
    return default


if __name__ == "__main__":
    port = int(get_value_from_args("--port", DEFAULT_PORT))
    server = get_value_from_args("--server-name", DEFAULT_SERVER_NAME)
    
    # Start API server in background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Small delay to let API server start
    time.sleep(2)
    
    print(f"🎧 Audiobook API available at: http://127.0.0.1:{API_PORT}")
    print(f"🖥️  Starting Applio Gradio interface on port {port}...")

    for _ in range(MAX_PORT_ATTEMPTS):
        try:
            launch_gradio(server, port)
            break
        except OSError:
            print(
                f"Failed to launch on port {port}, trying again on port {port - 1}..."
            )
            port -= 1
        except Exception as error:
            print(f"An error occurred launching Gradio: {error}")
            break
