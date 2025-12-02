import sys
import threading
import logging
import os
from typing import Optional, List

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Slot, Signal, QUrl

# Import backend modules
from app.engine import T2IEngine
from app.server import start_server_thread
from app.utils import get_file_list
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

    def __init__(self, engine: T2IEngine):
        super().__init__()
        self.engine = engine

    @Slot(result=list)
    def get_models(self):
        """Returns a list of available checkpoint models found in models/checkpoints."""
        checkpoints_dir = "models/checkpoints"
        models = get_file_list(checkpoints_dir)
        # Prepend the default HuggingFace ID
        return ["stabilityai/stable-diffusion-xl-base-1.0"] + models

    @Slot(result=list)
    def get_loras(self):
        """Returns a list of available LoRA models found in models/loras."""
        loras_dir = "models/loras"
        loras = get_file_list(loras_dir)
        return ["None"] + loras

    @Slot(str, str, int, float, str, bool, str, str, float)
    def generate(self, prompt: str, neg_prompt: str, steps: int, cfg: float, seed_str: str, 
                 use_refiner: bool, model_name: str, lora_name: str, lora_scale: float):
        """
        Main generation slot called from QML.
        Accepts all standard parameters including model and LoRA selection.
        """
        logger.info(f"UI requested generation: '{prompt[:30]}...'")
        logger.info(f"Params: Model='{model_name}', LoRA='{lora_name}' ({lora_scale}), Refiner={use_refiner}")
        
        self.statusUpdated.emit("Starting generation...")
        
        # 1. Resolve Model Path
        # If it's the default ID, keep it. Otherwise, assume it's a filename in models/checkpoints.
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
        
        def run_job():
            try:
                # Handle Model Switching
                # If the requested model is different from the currently loaded ID, force a reload
                if self.engine.base_model_id != real_model_path:
                    logger.info(f"Switching model from '{self.engine.base_model_id}' to '{real_model_path}'")
                    self.engine.base_model_id = real_model_path
                    # Setting pipeline to None forces engine.load_base_model() to re-initialize it
                    self.engine.base_pipeline = None 
                
                path = self.engine.generate(
                    prompt=prompt,
                    negative_prompt=neg_prompt,
                    steps=steps,
                    guidance_scale=cfg,
                    seed=seed,
                    use_refiner=use_refiner,
                    lora_path=real_lora_path,
                    lora_scale=lora_scale
                )
                self.generationFinished.emit(path)
                self.statusUpdated.emit("Ready")
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                self.errorOccurred.emit(str(e))
                self.statusUpdated.emit("Error occurred")

        # Start the worker thread
        threading.Thread(target=run_job, daemon=True).start()

def main():
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("RootLogic")
    app.setOrganizationDomain("kami.local")
    app.setApplicationName("Kami")

    # 1. Initialize the AI Engine
    logger.info("Initializing T2I Engine...")
    engine = T2IEngine()
    
    # 2. Share engine with the API Server
    server_module.shared_engine = engine
    server_module.shared_config = None 

    # 3. Start API Server in background thread
    logger.info("Starting API Server...")
    server_thread = threading.Thread(
        target=start_server_thread, 
        kwargs={'host': '0.0.0.0', 'port': 8000},
        daemon=True
    )
    server_thread.start()

    # 4. Setup QML Engine
    qml_engine = QQmlApplicationEngine()
    
    bridge = KamiBridge(engine)
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
