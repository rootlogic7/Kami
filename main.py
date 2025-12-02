import sys
import threading
import logging
from typing import Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Slot, Signal, QUrl

# Import backend modules
from app.engine import T2IEngine
from app.server import start_server_thread
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

    @Slot(str, str, int, float, str, bool)
    def generate(self, prompt: str, neg_prompt: str, steps: int, cfg: float, seed_str: str, use_refiner: bool):
        """
        Main generation slot called from QML.
        Accepts all standard parameters for T2I generation.
        """
        logger.info(f"UI requested generation: '{prompt[:30]}...' (Steps: {steps}, CFG: {cfg})")
        self.statusUpdated.emit("Starting generation...")
        
        # Parse seed (QML sends string to allow empty value)
        seed: Optional[int] = None
        if seed_str.strip():
            try:
                seed = int(seed_str)
            except ValueError:
                logger.warning(f"Invalid seed '{seed_str}', using random.")
        
        def run_job():
            try:
                path = self.engine.generate(
                    prompt=prompt,
                    negative_prompt=neg_prompt,
                    steps=steps,
                    guidance_scale=cfg,
                    seed=seed,
                    use_refiner=use_refiner
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
