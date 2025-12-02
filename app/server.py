import logging
import threading
import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import the core engine and config
from app.engine import T2IEngine
from app.config import SessionConfig
from app.database import get_filtered_images, delete_image_record

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

# --- Pydantic Models for Request Validation ---
class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    steps: int = 30
    guidance_scale: float = 7.0
    seed: Optional[int] = None
    use_refiner: bool = False
    model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    lora_path: Optional[str] = None
    lora_scale: float = 0.8
    use_freeu: bool = False

# --- Global Engine Instance ---
# This instance will be shared between the API and the local QML GUI.
# We initialize it as None and create it on startup to avoid import side-effects.
shared_engine: Optional[T2IEngine] = None
shared_config: Optional[SessionConfig] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI app.
    Ensures the engine is ready when the server starts.
    """
    global shared_engine, shared_config
    logger.info("Server starting up...")
    
    # In a real hybrid run, shared_engine might already be instantiated by main_hybrid.py.
    # If not (standalone server mode), we create it here.
    if shared_engine is None:
        logger.info("Initializing T2IEngine for standalone server mode.")
        shared_engine = T2IEngine()
    
    if shared_config is None:
        shared_config = SessionConfig()
        
    yield
    
    logger.info("Server shutting down...")
    # Clean up resources if necessary
    if shared_engine:
        shared_engine.cleanup()

# --- API Setup ---
app = FastAPI(title="Kami Backend API", lifespan=lifespan)

# Allow CORS so external Frontends (like a dev server on the laptop) can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact IPs (e.g., Laptop IP)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/api/status")
async def get_status():
    """Returns the server status and currently loaded model."""
    if not shared_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return {
        "status": "online",
        "model": shared_engine.base_model_id,
        "device": shared_engine.device,
        "is_generating": shared_engine.lock.locked()
    }

@app.post("/api/generate")
async def generate_image(req: GenerationRequest):
    """
    Endpoint to trigger image generation.
    """
    if not shared_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Check if engine is busy (optional, as engine has internal lock, 
    # but fast fail here is nicer for HTTP clients)
    if shared_engine.lock.locked():
        raise HTTPException(status_code=429, detail="Engine is busy processing another request.")

    try:
        # Prepare FreeU args if enabled
        freeu_args = shared_config.freeu_args if req.use_freeu and shared_config else None

        # Run generation (blocking call, so we ideally run it in a threadpool)
        # For simplicity in this step, we call it directly, which blocks the event loop briefly.
        # In production, we should use fastapi.concurrency.run_in_threadpool
        
        output_path = await app.router.dependency_overrides.get(
            "generate_func", 
            lambda: shared_engine.generate(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt,
                steps=req.steps,
                guidance_scale=req.guidance_scale,
                seed=req.seed,
                use_refiner=req.use_refiner,
                lora_path=req.lora_path if req.lora_path != "None" else None,
                lora_scale=req.lora_scale,
                freeu_args=freeu_args
            )
        )()

        return {
            "status": "success", 
            "image_path": output_path,
            "url": f"/images/{os.path.basename(output_path)}" # Relative URL for frontend
        }
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gallery")
async def get_gallery(limit: int = 50, offset: int = 0):
    """Returns the latest images from the database."""
    # Note: get_filtered_images currently returns all matches. 
    # Pagination should ideally be moved to SQL level for performance.
    images = get_filtered_images() # Returns sqlite3.Row objects
    
    # Convert rows to dicts
    result = []
    for row in images:
        img_dict = dict(row)
        # Add a web-accessible URL
        filename = os.path.basename(img_dict['path'])
        img_dict['url'] = f"/images/{filename}"
        result.append(img_dict)
        
    return result[:limit] # Simple slicing for now

# --- Static File Serving ---

# 1. Serve generated images
# This allows the frontend to access "output_images/2023.../img.png" via "http://.../images/img.png"
# We need to serve the ROOT output folder, but the paths in DB are absolute or structured.
# A simple approach is to serve the root directory where images are saved.
OUTPUT_ROOT = os.path.join(os.getcwd(), "output_images")
if not os.path.exists(OUTPUT_ROOT):
    os.makedirs(OUTPUT_ROOT)
app.mount("/images", StaticFiles(directory=OUTPUT_ROOT), name="images")

# 2. Serve the React Frontend (Placeholder)
# Later, we will place the 'dist' or 'build' folder of React here.
# app.mount("/", StaticFiles(directory="web_frontend", html=True), name="frontend")

def start_server_thread(host="0.0.0.0", port=8000):
    """Helper to start the server in a separate thread (for GUI integration)."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    # Standalone testing
    start_server_thread()
