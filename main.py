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
import app.server as server_module  # Access to the global shared_engine variable

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

    def __init__(self, engine: T2IEngine):
        super().__init__()
        self.engine = engine

    @Slot(str)
    def generate_test(self, prompt: str):
        """
        Simple test slot called from QML. 
        Runs generation in a separate thread to keep UI responsive.
        """
        logger.info(f"UI requested generation: {prompt}")
        
        def run_job():
            try:
                # We use a simplified call for this 'Hello World' test
                path = self.engine.generate(
                    prompt=prompt,
                    steps=20, # Low steps for quick test
                    guidance_scale=7.0
                )
                # Emit signal back to main thread/UI
                self.generationFinished.emit(path)
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                self.errorOccurred.emit(str(e))

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
    # This ensures both the QML UI and the FastAPI server use the exact same model instance
    server_module.shared_engine = engine
    server_module.shared_config = None # Config loading can be added later if needed

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
    
    # Create the bridge and expose it to QML as "backend"
    bridge = KamiBridge(engine)
    qml_engine.rootContext().setContextProperty("backend", bridge)

    # Load the main QML file
    qml_path = "resources/qml/main.qml"
    qml_engine.load(QUrl.fromLocalFile(qml_path))

    if not qml_engine.rootObjects():
        logger.error("Failed to load QML.")
        sys.exit(-1)

    logger.info("Kami Hybrid started. GUI is ready.")
    
    # Execute Qt Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
