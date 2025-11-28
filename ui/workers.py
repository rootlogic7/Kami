import os
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, Qt
from PyQt6.QtGui import QImageReader, QPixmap
from app.database import scan_and_import_folder

class GeneratorWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    # mode und input_image entfernt
    def __init__(self, engine, params):
        super().__init__()
        self.engine = engine
        self.params = params

    def run(self):
        try:
            # Check model switching
            if self.engine.base_model_id != self.params.get("model_path"):
                self.engine.base_model_id = self.params.get("model_path")
                self.engine.base_pipeline = None 
            
            # strength entfernt, da es nur für I2I relevant war
            gen_args = {k: v for k, v in self.params.items() if k not in ["model_path", "strength"]}
            
            # Nur T2I-Generierung
            path = self.engine.generate(**gen_args)
            
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))

class DBScannerWorker(QObject):
    finished = pyqtSignal(int)
    def run(self):
        # Scannt den Ordner und gibt Anzahl neuer Bilder zurück
        self.finished.emit(scan_and_import_folder())

class ThumbnailLoaderSignals(QObject):
    # WICHTIG: Das Signal sendet jetzt 4 Werte: Pfad, Bild, Tooltip-Text, Daten-Dict
    loaded = pyqtSignal(str, QPixmap, str, dict)

class ThumbnailLoader(QRunnable):
    def __init__(self, path, prompt, data, size=200):
        super().__init__()
        self.path = path
        self.prompt = prompt
        self.data = data  # Wir speichern die kompletten Zeilen-Daten
        self.size = size
        self.signals = ThumbnailLoaderSignals()

    def run(self):
        if not os.path.exists(self.path):
            return
            
        reader = QImageReader(self.path)
        # Performance: Bild direkt beim Laden skalieren (spart RAM)
        orig = reader.size()
        if orig.isValid():
            reader.setScaledSize(orig.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatio))
            
        img = reader.read()
        if not img.isNull():
            # Wir senden die Daten (self.data) wieder zurück an die GUI
            self.signals.loaded.emit(self.path, QPixmap.fromImage(img), self.prompt, self.data)
