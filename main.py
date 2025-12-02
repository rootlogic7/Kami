import sys
import threading
import logging
import os
from typing import Optional, List, Dict, Any

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Slot, Signal, QUrl

# Import backend modules
from app.engine import T2IEngine
from app.server import start_server_thread
from app.utils import get_file_list
from app.database import get_filtered_images, delete_image_record, get_all_models
from app.config import SessionConfig
import app.server as server_module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

class KamiBridge(QObject):
    """
    Bridge class to expose Python logic to QML.
    Inherits from QObject to allow Signal/Slot communication.
    """
    
    # Signals to update the UI asynchronously
    generationFinished = Signal(str, arguments=['path'])
    errorOccurred = Signal(str, arguments=['message'])
    statusUpdated = Signal(str, arguments=['message'])

    def __init__(self, engine: T2IEngine, config: SessionConfig):
        super().__init__()
        self.engine = engine
        self.config = config

    # --- Configuration Management ---

    @Slot(result="QVariantMap")
    def get_config(self):
        """Returns the current configuration as a dictionary for QML."""
        return {
            "steps": self.config.steps,
            "guidance": self.config.guidance,
            "neg_prompt": self.config.neg_prompt,
            "model_path": self.config.model_path,
            "lora_path": self.config.lora_path,
            "lora_scale": self.config.lora_scale,
            "use_refiner": self.config.use_refiner,
            "pony_mode": self.config.pony_mode,
            "use_freeu": self.config.use_freeu,
            # We can add more fields here as needed
        }

    @Slot(str, "QVariant")
    def set_config_value(self, key: str, value):
        """Updates a single configuration value and persists it to disk."""
        if hasattr(self.config, key):
            # Logging specific changes for debugging
            logger.info(f"Updating config: {key} = {value}")
            setattr(self.config, key, value)
            self.config.save_session_state()
        else:
            logger.warning(f"Attempted to set invalid config key: {key}")

    # --- Resources (Models/LoRAs) ---

    @Slot(result=list)
    def get_models(self):
        """Returns a list of available checkpoint models found in models/checkpoints."""
        checkpoints_dir = "models/checkpoints"
        models = get_file_list(checkpoints_dir)
        return ["stabilityai/stable-diffusion-xl-base-1.0"] + models

    @Slot(result=list)
    def get_loras(self):
        """Returns a list of available LoRA models found in models/loras."""
        loras_dir = "models/loras"
        loras = get_file_list(loras_dir)
        return ["None"] + loras
    
    # --- Gallery Management ---

    @Slot(str, str, str, int, int, result=list)
    def get_gallery_images(self, search_text: str, sort_by: str, model_filter: str, limit: int, offset: int):
        """
        Retrieves a paginated list of images from the DB based on filters.
        Returns a list of dictionaries (compatible with QML ListModel).
        """
        try:
            rows = get_filtered_images(search_text, sort_by, model_filter)
            
            # Slicing for pagination
            start = offset
            end = offset + limit
            sliced = rows[start:end]
            
            results = []
            for row in sliced:
                data = dict(row)
                if not os.path.isabs(data['path']):
                    data['path'] = os.path.abspath(data['path'])
                results.append(data)
                
            return results
        except Exception as e:
            logger.error(f"Error fetching gallery images: {e}")
            return []

    @Slot(result=list)
    def get_db_models(self):
        """Returns a list of unique models used in the database history."""
        return ["All Models"] + get_all_models()

    @Slot(str, result=bool)
    def delete_image(self, path: str):
        """Deletes an image from disk and database."""
        try:
            if os.path.exists(path):
                os.remove(path)
            else:
                logger.warning(f"File not found on disk: {path}")
            return delete_image_record(path)
        except Exception as e:
            logger.error(f"Failed to delete image {path}: {e}")
            return False

    # --- Generation ---

    @Slot(str, str, int, float, str, bool, str, str, float)
    def generate(self, prompt: str, neg_prompt: str, steps: int, cfg: float, seed_str: str, 
                 use_refiner: bool, model_name: str, lora_name: str, lora_scale: float):
        """
        Main generation slot called from QML.
        """
        logger.info(f"UI requested generation: '{prompt[:30]}...'")
        
        self.statusUpdated.emit("Starting generation...")
        
        # 1. Resolve Model Path
        real_model_path = model_name
        if model_name != "stabilityai/stable-diffusion-xl-base-1.0":
             real_model_path = os.path.join("models/checkpoints", model_name)

        # 2. Resolve LoRA Path
        real_lora_path = None
        if lora_name and lora_name != "None":
             real_lora_path = os.path.join("models/loras", lora_name)

        # 3. Parse Seed
        seed: Optional[int] = None
        if seed_str.strip():
            try:
                seed = int(seed_str)
            except ValueError:
                logger.warning(f"Invalid seed '{seed_str}', using random.")
        
        # 4. Check for Pony Mode (Inject prefixes if enabled)
        final_prompt = prompt
        final_neg = neg_prompt
        
        if self.config.pony_mode:
            logger.info("Applying Pony Diffusion prefixes...")
            final_prompt = self.config.pony_prefix + prompt
            if "score_4" not in neg_prompt:
                final_neg = self.config.pony_neg + neg_prompt

        # 5. Prepare FreeU Args
        freeu_args = self.config.freeu_args if self.config.use_freeu else None
        
        def run_job():
            try:
                if self.engine.base_model_id != real_model_path:
                    logger.info(f"Switching model from '{self.engine.base_model_id}' to '{real_model_path}'")
                    self.engine.base_model_id = real_model_path
                    self.engine.base_pipeline = None 
                
                path = self.engine.generate(
                    prompt=final_prompt,
                    negative_prompt=final_neg,
                    steps=steps,
                    guidance_scale=cfg,
                    seed=seed,
                    use_refiner=use_refiner,
                    lora_path=real_lora_path,
                    lora_scale=lora_scale,
                    freeu_args=freeu_args
                )
                self.generationFinished.emit(path)
                self.statusUpdated.emit("Ready")
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                self.errorOccurred.emit(str(e))
                self.statusUpdated.emit("Error occurred")

        threading.Thread(target=run_job, daemon=True).start()

def main():
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("RootLogic")
    app.setOrganizationDomain("kami.local")
    app.setApplicationName("Kami")

    # 1. Initialize Configuration
    logger.info("Loading Session Config...")
    config = SessionConfig()

    # 2. Initialize the AI Engine
    logger.info("Initializing T2I Engine...")
    engine = T2IEngine()
    
    # 3. Share engine and config with the API Server
    server_module.shared_engine = engine
    server_module.shared_config = config 

    # 4. Start API Server in background thread
    logger.info("Starting API Server...")
    server_thread = threading.Thread(
        target=start_server_thread, 
        kwargs={'host': '0.0.0.0', 'port': 8000},
        daemon=True
    )
    server_thread.start()

    # 5. Setup QML Engine
    qml_engine = QQmlApplicationEngine()
    
    # Pass config to bridge
    bridge = KamiBridge(engine, config)
    qml_engine.rootContext().setContextProperty("backend", bridge)

    qml_path = "resources/qml/main.qml"
    qml_engine.load(QUrl.fromLocalFile(qml_path))

    if not qml_engine.rootObjects():
        logger.error("Failed to load QML.")
        sys.exit(-1)

    logger.info("Kami Hybrid started. GUI is ready.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
