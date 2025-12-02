import sys
import os
from PyQt6.QtWidgets import QApplication

# Sicherstellen, dass das Root-Verzeichnis im Pfad ist, um "app" und "ui" zu finden
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("kami")
    app.setApplicationName("Kami")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
