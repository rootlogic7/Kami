from PyQt6.QtWidgets import QLabel, QListView, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt
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
