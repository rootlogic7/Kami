from PyQt6.QtWidgets import (
    QLabel, QListView, QComboBox, QDialog, QScrollArea, 
    QVBoxLayout, QPushButton, QHBoxLayout, QSizePolicy, QWidget, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QAction
import qtawesome as qta
from app.style import CAT_COLORS

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

def setup_combo_view(combo: QComboBox):
    combo.setView(QListView())
    return combo

class ImageViewerDialog(QDialog):
    # Neues Signal, das den Pfad des zu löschenden Bildes sendet
    delete_confirmed = pyqtSignal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle("Image Viewer")
        self.resize(1200, 900) 
        self.setStyleSheet(f"background-color: {CAT_COLORS['BASE']}; color: {CAT_COLORS['TEXT']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        
        self.pixmap = QPixmap(image_path)
        self.image_label.setPixmap(self.pixmap)
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; border-top: 1px solid {CAT_COLORS['SURFACE0']};")
        toolbar.setFixedHeight(60)
        tb_layout = QHBoxLayout(toolbar)
        
        btn_fit = QPushButton(" Fit")
        btn_fit.clicked.connect(self.fit_to_window)
        
        btn_100 = QPushButton(" 1:1")
        btn_100.clicked.connect(self.show_original_size)
        
        # NEU: Delete Button
        btn_del = QPushButton(" Delete")
        btn_del.setIcon(qta.icon('fa5s.trash', color=CAT_COLORS['BASE']))
        btn_del.clicked.connect(self.ask_delete)
        btn_del.setStyleSheet(f"background-color: {CAT_COLORS['RED']}; color: {CAT_COLORS['BASE']}; border: none;")
        
        btn_close = QPushButton(" Close")
        btn_close.clicked.connect(self.close)

        tb_layout.addWidget(btn_del) # Delete links
        tb_layout.addStretch()
        tb_layout.addWidget(btn_fit)
        tb_layout.addWidget(btn_100)
        tb_layout.addWidget(btn_close)
        
        layout.addWidget(toolbar)
        self.fit_to_window()

    def ask_delete(self):
        # Sicherheitsabfrage direkt im Viewer
        res = QMessageBox.question(self, "Delete Image", "Permanently delete this image from disk?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.delete_confirmed.emit(self.image_path)
            self.close()

    def fit_to_window(self):
        if not self.pixmap.isNull():
            avail_size = self.scroll_area.size()
            scaled = self.pixmap.scaled(avail_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.adjustSize()

    def show_original_size(self):
        self.image_label.setPixmap(self.pixmap)
        self.image_label.adjustSize()

    def resizeEvent(self, event):
        self.fit_to_window()
        super().resizeEvent(event)
