# app/style.py

CAT_BASE = "#1e1e2e"
CAT_MANTLE = "#181825"
CAT_CRUST = "#11111b"
CAT_SURFACE0 = "#313244"
CAT_SURFACE1 = "#45475a"
CAT_TEXT = "#cdd6f4"
CAT_SUBTEXT0 = "#a6adc8"
CAT_GREEN = "#a6e3a1"
CAT_RED = "#f38ba8"
CAT_BLUE = "#89b4fa"
CAT_LAVENDER = "#b4befe"
CAT_OVERLAY0 = "#6c7086"

CAT_COLORS = {
    "BASE": CAT_BASE, "MANTLE": CAT_MANTLE, "CRUST": CAT_CRUST,
    "SURFACE0": CAT_SURFACE0, "SURFACE1": CAT_SURFACE1, 
    "TEXT": CAT_TEXT, "SUBTEXT0": CAT_SUBTEXT0,
    "GREEN": CAT_GREEN, "RED": CAT_RED, "BLUE": CAT_BLUE,
    "LAVENDER": CAT_LAVENDER, "OVERLAY0": CAT_OVERLAY0
}

def get_stylesheet():
    return f"""
        /* --- GLOBAL --- */
        QMainWindow, QWidget {{ 
            background-color: {CAT_BASE}; color: {CAT_TEXT}; 
            font-family: 'Segoe UI', sans-serif; font-size: 13px; 
        }}
        
        QToolTip {{ 
            background-color: {CAT_CRUST}; color: {CAT_TEXT}; 
            border: 1px solid {CAT_SURFACE1}; padding: 5px; border-radius: 4px;
        }}

        /* --- NAVIGATION BAR --- */
        QWidget#NavBar {{
            background-color: {CAT_MANTLE};
            border-bottom: 1px solid {CAT_CRUST};
        }}
        
        QPushButton#NavBtn {{
            background-color: transparent; border: none; border-radius: 6px;
            color: {CAT_SUBTEXT0}; font-size: 14px; padding: 10px 15px; text-align: left;
        }}
        QPushButton#NavBtn:hover {{
            background-color: {CAT_SURFACE0}; color: {CAT_TEXT};
        }}
        QPushButton#NavBtn:checked {{
            background-color: {CAT_SURFACE0}; color: {CAT_LAVENDER}; 
            border-bottom: 3px solid {CAT_LAVENDER}; border-radius: 0px; /* Flat look */
        }}

        /* --- INPUTS --- */
        QLineEdit, QTextEdit, QPlainTextEdit {{ 
            background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE0}; 
            border-radius: 6px; padding: 8px; color: {CAT_TEXT}; 
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {CAT_LAVENDER}; background-color: {CAT_CRUST};
        }}

        /* --- COMBOBOX --- */
        QComboBox {{
            background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE0};
            border-radius: 6px; padding: 6px 10px; color: {CAT_TEXT};
        }}
        QComboBox::drop-down {{ border: 0px; }}
        QComboBox::down-arrow {{
            image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; 
            border-top: 5px solid {CAT_TEXT}; margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE1};
            selection-background-color: {CAT_SURFACE1}; color: {CAT_TEXT}; outline: 0; padding: 4px;
        }}

        /* --- BUTTONS --- */
        QPushButton {{ 
            background-color: {CAT_SURFACE0}; color: {CAT_TEXT}; border: 1px solid {CAT_SURFACE1};
            padding: 8px 16px; border-radius: 6px; font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {CAT_SURFACE1}; border-color: {CAT_LAVENDER}; }}
        QPushButton:pressed {{ background-color: {CAT_MANTLE}; }}
        
        QPushButton#GenerateBtn {{ 
            background-color: {CAT_GREEN}; color: {CAT_BASE}; border: none; font-size: 15px; 
        }}
        QPushButton#GenerateBtn:hover {{ background-color: #94e2d5; }}
        QPushButton#GenerateBtn:disabled {{ background-color: {CAT_SURFACE1}; color: {CAT_OVERLAY0}; }}

        QPushButton#DeleteBtn:hover {{ background-color: {CAT_RED}; color: {CAT_BASE}; border-color: {CAT_RED}; }}

        QPushButton#ModeBtn {{ background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE1}; }}
        QPushButton#ModeBtn:checked {{ background-color: {CAT_BLUE}; color: {CAT_BASE}; border-color: {CAT_BLUE}; }}

        /* --- SLIDERS --- */
        QSlider::groove:horizontal {{ height: 6px; background: {CAT_MANTLE}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ 
            background: {CAT_BLUE}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; 
        }}
        QSlider::sub-page:horizontal {{ background: {CAT_SURFACE1}; border-radius: 3px; }}

        /* --- SCROLLBARS --- */
        QScrollBar:vertical {{
            border: none; background: {CAT_BASE}; width: 8px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {CAT_SURFACE1}; min-height: 20px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {CAT_OVERLAY0}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

        /* --- GROUP BOX --- */
        QGroupBox {{ 
            border: 1px solid {CAT_SURFACE0}; margin-top: 24px; border-radius: 8px; padding-top: 16px;
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin; left: 12px; padding: 0 8px; color: {CAT_LAVENDER}; font-weight: bold;
        }}
        
        /* --- LIST WIDGET --- */
        QListWidget {{ background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE0}; border-radius: 6px; }}
        QListWidget::item {{ padding: 8px; border-radius: 4px; margin: 2px; }}
        QListWidget::item:selected {{ background-color: {CAT_SURFACE1}; color: {CAT_BLUE}; border: 1px solid {CAT_BLUE}; }}

        QLabel#PreviewLabel {{ 
            background-color: {CAT_CRUST}; border: 2px dashed {CAT_SURFACE0}; border-radius: 8px; 
        }}
    """
