from PyQt6.QtWidgets import (
    QLabel, QListView, QComboBox, QDialog, QScrollArea, 
    QVBoxLayout, QPushButton, QHBoxLayout, QSizePolicy, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QAction
from app.style import CAT_COLORS

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

def setup_combo_view(combo: QComboBox):
    """
    Zwingt Comboboxen zur Nutzung von QListView.
    Dies ist notwendig, damit CSS-Styling (Padding, Colors) korrekt angewendet wird.
    """
    combo.setView(QListView())
    return combo

class ImageViewerDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.resize(1200, 900) 
        self.setStyleSheet(f"background-color: {CAT_COLORS['BASE']}; color: {CAT_COLORS['TEXT']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area für das Bild
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        
        # Bild laden
        self.pixmap = QPixmap(image_path)
        self.image_label.setPixmap(self.pixmap)
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Toolbar (Unten)
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; border-top: 1px solid {CAT_COLORS['SURFACE0']};")
        toolbar.setFixedHeight(60)
        tb_layout = QHBoxLayout(toolbar)
        
        btn_fit = QPushButton(" Fit to Window")
        btn_fit.clicked.connect(self.fit_to_window)
        
        btn_100 = QPushButton(" Original Size (1:1)")
        btn_100.clicked.connect(self.show_original_size)
        
        btn_close = QPushButton(" Close")
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(f"background-color: {CAT_COLORS['RED']}; color: {CAT_COLORS['BASE']}; border: none;")

        tb_layout.addStretch()
        tb_layout.addWidget(btn_fit)
        tb_layout.addWidget(btn_100)
        tb_layout.addWidget(btn_close)
        tb_layout.addStretch()
        
        layout.addWidget(toolbar)
        
        # Standard: Fit to Window
        self.fit_to_window()

    def fit_to_window(self):
        if not self.pixmap.isNull():
            # Wir ziehen etwas von der Höhe ab für die Toolbar
            avail_size = self.scroll_area.size()
            scaled = self.pixmap.scaled(avail_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.adjustSize()

    def show_original_size(self):
        self.image_label.setPixmap(self.pixmap)
        self.image_label.adjustSize()

    def resizeEvent(self, event):
        # Einfaches Verhalten: Beim Resizen wieder einpassen, falls man nicht 1:1 wollte
        # (Kann man verfeinern, aber reicht für den Anfang)
        self.fit_to_window()
        super().resizeEvent(event)
