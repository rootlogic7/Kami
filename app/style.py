# app/style.py

CAT_BASE = "#1e1e2e"
CAT_MANTLE = "#181825"
CAT_SURFACE0 = "#313244"
CAT_SURFACE1 = "#45475a"
CAT_TEXT = "#cdd6f4"
CAT_SUBTEXT0 = "#a6adc8"
CAT_GREEN = "#a6e3a1"
CAT_RED = "#f38ba8"
CAT_OVERLAY0 = "#6c7086"
CAT_LAVENDER = "#b4befe"

CAT_COLORS = {
    "BASE": CAT_BASE, "MANTLE": CAT_MANTLE, "SURFACE0": CAT_SURFACE0,
    "SURFACE1": CAT_SURFACE1, "TEXT": CAT_TEXT, "GREEN": CAT_GREEN, "RED": CAT_RED
}

def get_stylesheet():
    return f"""
        /* GLOBAL */
        QMainWindow, QWidget {{ 
            background-color: {CAT_BASE}; color: {CAT_TEXT}; font-family: 'Segoe UI', sans-serif; font-size: 13px; 
        }}
        
        /* TOOLTIPS */
        QToolTip {{ 
            background-color: {CAT_MANTLE}; color: {CAT_TEXT}; border: 1px solid {CAT_LAVENDER}; padding: 5px; 
        }}

        /* GROUPS */
        QGroupBox {{ 
            border: 1px solid {CAT_SURFACE1}; margin-top: 20px; border-radius: 6px; padding-top: 15px; font-weight: bold;
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {CAT_GREEN}; 
        }}

        /* INPUTS */
        QLineEdit, QTextEdit, QListWidget, QComboBox {{ 
            background-color: {CAT_SURFACE0}; border: 1px solid {CAT_SURFACE1}; border-radius: 4px; padding: 6px; color: {CAT_TEXT}; 
            selection-background-color: {CAT_GREEN}; selection-color: {CAT_BASE};
        }}

        /* COMBOBOX & LIST VIEW FIXES */
        QComboBox {{
            padding-right: 20px; /* Platz für Pfeil */
        }}
        QComboBox::drop-down {{ 
            border: 0px; 
        }}
        QComboBox::down-arrow {{
            image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; 
            border-top: 5px solid {CAT_TEXT}; width: 0; height: 0; margin-right: 10px;
        }}
        
        /* Das Popup-Menü selbst */
        QComboBox QAbstractItemView {{
            background-color: {CAT_SURFACE0};
            border: 1px solid {CAT_SURFACE1};
            selection-background-color: {CAT_SURFACE1};
            color: {CAT_TEXT};
            outline: 0px;
            padding: 4px;
        }}
        
        /* Einzelne Items */
        QComboBox::item {{
            height: 25px; 
        }}
        QComboBox::item:selected {{
            background-color: {CAT_SURFACE1};
            color: {CAT_GREEN};
        }}
        
        /* QListView (für Favorites und Combos) */
        QListView {{
            background-color: {CAT_SURFACE0};
            outline: 0;
        }}
        QListView::item {{
            padding: 5px;
        }}
        QListView::item:selected {{
            background-color: {CAT_SURFACE1};
            color: {CAT_GREEN};
            border-radius: 4px;
        }}
        QListView::item:hover {{
            background-color: {CAT_MANTLE};
        }}

        /* SPINBOXES */
        QSpinBox, QDoubleSpinBox {{
            background-color: {CAT_SURFACE0}; border: 1px solid {CAT_SURFACE1}; border-radius: 4px; padding: 4px; padding-right: 15px; 
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border; subcontrol-position: top right; width: 16px; 
            border-left: 1px solid {CAT_SURFACE1}; background: {CAT_SURFACE0};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; 
            border-left: 1px solid {CAT_SURFACE1}; background: {CAT_SURFACE0};
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            width: 0; height: 0; border-left: 3px solid transparent; border-right: 3px solid transparent; border-bottom: 3px solid {CAT_TEXT};
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            width: 0; height: 0; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 3px solid {CAT_TEXT};
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background-color: {CAT_SURFACE1}; }}

        /* BUTTONS */
        QPushButton {{ 
            background-color: {CAT_SURFACE1}; color: {CAT_TEXT}; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; 
        }}
        QPushButton:hover {{ background-color: {CAT_OVERLAY0}; }}
        QPushButton#GenerateBtn {{ background-color: {CAT_GREEN}; color: {CAT_BASE}; font-size: 14px; }}
        QPushButton#GenerateBtn:hover {{ background-color: #94e2d5; }}
        QPushButton#ModeBtn:checked {{ background-color: {CAT_GREEN}; color: {CAT_BASE}; }}
        QPushButton#DeleteBtn {{ background-color: {CAT_RED}; color: {CAT_BASE}; }}
        QPushButton#DeleteBtn:hover {{ background-color: #eba0ac; }}
        QPushButton#LoadBtn {{ background-color: {CAT_LAVENDER}; color: {CAT_BASE}; }}

        /* SLIDERS & TABS */
        QSlider::groove:horizontal {{ border: 1px solid {CAT_SURFACE1}; height: 6px; background: {CAT_MANTLE}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {CAT_GREEN}; border: 1px solid {CAT_BASE}; width: 16px; margin: -5px 0; border-radius: 8px; }}
        
        QTabWidget::pane {{ border: 1px solid {CAT_SURFACE1}; border-radius: 4px; top: -1px; }}
        QTabBar::tab {{ 
            background: {CAT_SURFACE0}; border: 1px solid {CAT_SURFACE1}; padding: 8px 12px; margin-right: 4px; 
            border-top-left-radius: 4px; border-top-right-radius: 4px; color: {CAT_SUBTEXT0}; 
        }}
        QTabBar::tab:selected {{ background: {CAT_GREEN}; color: {CAT_BASE}; font-weight: bold; }}

        /* MISC */
        QProgressBar {{ border: 1px solid {CAT_SURFACE1}; border-radius: 4px; text-align: center; background: {CAT_MANTLE}; }}
        QProgressBar::chunk {{ background-color: {CAT_GREEN}; width: 20px; }}
        QScrollBar:vertical {{ border: none; background: {CAT_MANTLE}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {CAT_SURFACE1}; min-height: 20px; border-radius: 5px; }}
        QLabel#PreviewLabel {{ background-color: {CAT_MANTLE}; border: 2px dashed {CAT_SURFACE1}; border-radius: 8px; }}
    """
