import sys
import threading
import logging
import os
from typing import Optional, List, Dict, Any

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Slot, Signal, QUrl

# Import backend modules
from app.engine import T2IEngine, GenerationCancelled
from app.server import start_server_thread
from app.utils import get_file_list
from app.config import SessionConfig
import app.server as server_module

# Import DB functions
from app.database import (
    get_filtered_images, delete_image_record, get_all_models,
    add_character, get_characters, delete_character, update_character,
    add_preset, get_presets, delete_preset
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

class KamiBridge(QObject):
    
    # Signals
    generationFinished = Signal(str, arguments=['path'])
    errorOccurred = Signal(str, arguments=['message'])
    statusUpdated = Signal(str, arguments=['message'])
    # NEW: Progress signal (current step, total steps)
    progressChanged = Signal(int, int, arguments=['step', 'total'])

    def __init__(self, engine: T2IEngine, config: SessionConfig):
        super().__init__()
        self.engine = engine
        self.config = config

    # --- Config ---
    @Slot(result="QVariantMap")
    def get_config(self):
        return {
            "steps": self.config.steps, "guidance": self.config.guidance, "neg_prompt": self.config.neg_prompt,
            "model_path": self.config.model_path, "lora_path": self.config.lora_path, "lora_scale": self.config.lora_scale,
            "use_refiner": self.config.use_refiner, "pony_mode": self.config.pony_mode, "use_freeu": self.config.use_freeu,
        }

    @Slot(str, "QVariant")
    def set_config_value(self, key: str, value):
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.config.save_session_state()

    # --- Resources ---
    @Slot(result=list)
    def get_models(self):
        return ["stabilityai/stable-diffusion-xl-base-1.0"] + get_file_list("models/checkpoints")

    @Slot(result=list)
    def get_loras(self):
        return ["None"] + get_file_list("models/loras")
    
    # --- Gallery & DB ---
    @Slot(str, str, str, int, int, result=list)
    def get_gallery_images(self, search_text, sort_by, model_filter, limit, offset):
        try:
            rows = get_filtered_images(search_text, sort_by, model_filter)
            start = offset; end = offset + limit; sliced = rows[start:end]
            results = []
            for row in sliced:
                data = dict(row)
                if not os.path.isabs(data['path']): data['path'] = os.path.abspath(data['path'])
                results.append(data)
            return results
        except Exception as e:
            logger.error(f"Error: {e}"); return []

    @Slot(result=list)
    def get_db_models(self): return ["All Models"] + get_all_models()

    @Slot(str, result=bool)
    def delete_image(self, path): 
        if os.path.exists(path): os.remove(path)
        return delete_image_record(path)

    # --- Characters ---
    @Slot(result=list)
    def get_characters(self): return get_characters()
    @Slot(str, str, str, str, str, str, float, result=bool)
    def add_character(self, n, d, t, p, no, l, ls): return add_character(n, d, t, p, no, l, ls)
    @Slot(int, str, str, str, str, str, str, float, result=bool)
    def update_character(self, id, n, d, t, p, no, l, ls): return update_character(id, n, d, t, p, no, l, ls)
    @Slot(int, result=bool)
    def delete_character(self, id): return delete_character(id)

    # --- Presets ---
    @Slot(result=list)
    def get_presets(self): return get_presets()
    @Slot(str, str, str, float, int, float, str, str, result=bool)
    def add_preset(self, n, m, l, ls, s, c, p, ng): return add_preset(n, m, l, ls, s, c, p, ng)
    @Slot(int, result=bool)
    def delete_preset(self, id): return delete_preset(id)

    # --- Generation Control ---

    @Slot()
    def cancel(self):
        """Stops the current generation process."""
        logger.info("UI requested cancellation.")
        self.engine.abort_generation()

    @Slot(str, str, int, float, str, bool, str, str, float)
    def generate(self, prompt: str, neg_prompt: str, steps: int, cfg: float, seed_str: str, 
                 use_refiner: bool, model_name: str, lora_name: str, lora_scale: float):
        
        logger.info(f"UI requested generation: '{prompt[:30]}...'")
        self.statusUpdated.emit("Starting generation...")
        
        real_model_path = model_name if model_name == "stabilityai/stable-diffusion-xl-base-1.0" else os.path.join("models/checkpoints", model_name)
        real_lora_path = os.path.join("models/loras", lora_name) if lora_name and lora_name != "None" else None
        
        seed: Optional[int] = None
        if seed_str.strip():
            try: seed = int(seed_str)
            except: pass
        
        final_prompt = (self.config.pony_prefix + prompt) if self.config.pony_mode else prompt
        final_neg = (self.config.pony_neg + neg_prompt) if (self.config.pony_mode and "score_4" not in neg_prompt) else neg_prompt
        freeu_args = self.config.freeu_args if self.config.use_freeu else None
        
        def run_job():
            try:
                if self.engine.base_model_id != real_model_path:
                    logger.info("Switching model...")
                    self.engine.base_model_id = real_model_path
                    self.engine.base_pipeline = None 
                
                # Helper to emit progress
                def on_progress(step, total):
                    self.progressChanged.emit(step, total)

                path = self.engine.generate(
                    prompt=final_prompt, negative_prompt=final_neg, steps=steps, guidance_scale=cfg,
                    seed=seed, use_refiner=use_refiner, lora_path=real_lora_path, lora_scale=lora_scale,
                    freeu_args=freeu_args, progress_callback=on_progress
                )
                self.generationFinished.emit(path)
                self.statusUpdated.emit("Ready")
            except GenerationCancelled:
                logger.info("Worker: Generation cancelled.")
                self.statusUpdated.emit("Cancelled")
                # We emit finished with empty path to reset UI state if needed, or handle via status
                self.generationFinished.emit("") 
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

    logger.info("Loading Session Config...")
    config = SessionConfig()
    logger.info("Initializing T2I Engine...")
    engine = T2IEngine()
    
    server_module.shared_engine = engine; server_module.shared_config = config 

    logger.info("Starting API Server...")
    threading.Thread(target=start_server_thread, kwargs={'host': '0.0.0.0', 'port': 8000}, daemon=True).start()

    qml_engine = QQmlApplicationEngine()
    bridge = KamiBridge(engine, config)
    qml_engine.rootContext().setContextProperty("backend", bridge)

    qml_engine.load(QUrl.fromLocalFile("resources/qml/main.qml"))
    if not qml_engine.rootObjects(): sys.exit(-1)

    logger.info("Kami Hybrid started. GUI is ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
