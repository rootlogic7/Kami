# app/style.py

# --- KONFIGURATION ---
APP_FONT = "DepartureMono Nerd Font Propo" 

# --- CATPPUCCIN MOCHA PALETTE ---
CAT_BASE = "#1e1e2e"
CAT_MANTLE = "#181825"
CAT_CRUST = "#11111b"
CAT_SURFACE0 = "#313244"
CAT_SURFACE1 = "#45475a"
CAT_TEXT = "#cdd6f4"
CAT_SUBTEXT0 = "#a6adc8"
CAT_SUBTEXT1 = "#bac2de"
CAT_OVERLAY0 = "#6c7086"

# Akzentfarben
CAT_BLUE = "#89b4fa"
CAT_LAVENDER = "#b4befe"
CAT_SAPPHIRE = "#74c7ec"
CAT_SKY = "#89dceb"
CAT_TEAL = "#94e2d5"
CAT_GREEN = "#a6e3a1"
CAT_YELLOW = "#f9e2af"
CAT_PEACH = "#fab387"
CAT_MAROON = "#eba0ac"
CAT_RED = "#f38ba8"
CAT_MAUVE = "#cba6f7"
CAT_PINK = "#f5c2e7"
CAT_FLAMINGO = "#f2cdcd"
CAT_ROSEWATER = "#f5e0dc"

CAT_COLORS = {
    "BASE": CAT_BASE, "MANTLE": CAT_MANTLE, "CRUST": CAT_CRUST,
    "SURFACE0": CAT_SURFACE0, "SURFACE1": CAT_SURFACE1, 
    "TEXT": CAT_TEXT, "SUBTEXT0": CAT_SUBTEXT0,
    "BLUE": CAT_BLUE, "LAVENDER": CAT_LAVENDER, "RED": CAT_RED, 
    "GREEN": CAT_GREEN, "ROSEWATER": CAT_ROSEWATER, "OVERLAY0": CAT_OVERLAY0
}

def get_stylesheet():
    return f"""
        /* --- GLOBAL --- */
        QMainWindow, QWidget {{ 
            background-color: {CAT_BASE}; color: {CAT_TEXT}; 
            font-family: '{APP_FONT}', sans-serif; font-size: 14px; 
        }}
        
        QToolTip {{ 
            background-color: {CAT_MANTLE}; color: {CAT_TEXT}; 
            border: 1px solid {CAT_MAUVE}; padding: 8px; border-radius: 6px;
        }}

        /* --- NAVIGATION BAR --- */
        QWidget#NavBar {{
            background-color: {CAT_MANTLE};
            border-bottom: 2px solid {CAT_CRUST};
        }}
        
        QPushButton#NavBtn {{
            background-color: transparent; 
            border: none; 
            border-left: 4px solid transparent; /* Platzhalter, damit Text nicht springt */
            border-radius: 8px;
            color: {CAT_SUBTEXT0}; 
            font-size: 15px; 
            padding: 12px 20px; 
            text-align: left;
            font-weight: 600;
            min-width: 140px; /* <--- NEU: Feste Breite für gleichmäßige Optik */
        }}
        QPushButton#NavBtn:hover {{
            background-color: {CAT_SURFACE0}; color: {CAT_TEXT};
        }}
        QPushButton#NavBtn:checked {{
            background-color: {CAT_SURFACE0}; color: {CAT_MAUVE}; 
            border-left: 4px solid {CAT_MAUVE}; 
            border-radius: 4px; 
        }}

        /* --- INPUTS --- */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{ 
            background-color: {CAT_MANTLE}; border: 2px solid {CAT_SURFACE0}; 
            border-radius: 8px; padding: 10px; color: {CAT_TEXT}; font-size: 14px;
            min-height: 20px; 
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {CAT_MAUVE}; background-color: {CAT_CRUST};
        }}
        QLineEdit[text=""], QTextEdit[text=""] {{ color: {CAT_OVERLAY0}; }}

        /* --- COMBOBOX --- */
        QComboBox {{
            background-color: {CAT_MANTLE}; border: 2px solid {CAT_SURFACE0};
            border-radius: 8px; padding: 8px 12px; color: {CAT_TEXT};
            min-height: 20px;
        }}
        QComboBox::drop-down {{ border: 0px; }}
        QComboBox::down-arrow {{
            image: none; border-left: 6px solid transparent; border-right: 6px solid transparent; 
            border-top: 6px solid {CAT_MAUVE}; margin-right: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {CAT_MANTLE}; border: 1px solid {CAT_SURFACE1};
            selection-background-color: {CAT_SURFACE1}; color: {CAT_TEXT}; outline: 0; padding: 5px;
        }}

        /* --- BUTTONS --- */
        QPushButton {{ 
            background-color: {CAT_SURFACE0}; color: {CAT_TEXT}; border: 1px solid {CAT_SURFACE1};
            padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;
            min-height: 20px;
        }}
        QPushButton:hover {{ 
            background-color: {CAT_SURFACE1}; border-color: {CAT_LAVENDER}; color: {CAT_LAVENDER};
        }}
        QPushButton:pressed {{ background-color: {CAT_MANTLE}; border-color: {CAT_SURFACE0}; }}
        
        QPushButton#GenerateBtn {{ 
            background-color: {CAT_GREEN}; color: {CAT_BASE}; border: none; 
            font-size: 18px; border-radius: 12px; font-weight: 800; letter-spacing: 1px;
            padding: 15px; 
        }}
        QPushButton#GenerateBtn:hover {{ background-color: {CAT_TEAL}; margin-top: -2px; margin-bottom: 2px; }}
        QPushButton#GenerateBtn:disabled {{ background-color: {CAT_SURFACE1}; color: {CAT_OVERLAY0}; margin: 0; }}

        QPushButton#DeleteBtn {{ background-color: {CAT_MANTLE}; color: {CAT_RED}; border: 1px solid {CAT_RED}; }}
        QPushButton#DeleteBtn:hover {{ background-color: {CAT_RED}; color: {CAT_BASE}; }}

        QPushButton#IOTDBtn {{
             background-color: {CAT_MAUVE}; border-radius: 22px; border: 2px solid {CAT_BASE};
        }}
        QPushButton#IOTDBtn:hover {{ background-color: {CAT_PINK}; margin-top: -2px; }}

        /* --- CHECKBOX --- */
        QCheckBox {{ spacing: 10px; font-size: 14px; min-height: 24px; }}
        QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 2px solid {CAT_SURFACE1}; background: {CAT_MANTLE}; }}
        QCheckBox::indicator:checked {{ background: {CAT_MAUVE}; border-color: {CAT_MAUVE}; image: url(none); }}
        QCheckBox::indicator:hover {{ border-color: {CAT_LAVENDER}; }}

        /* --- SLIDERS --- */
        QSlider::groove:horizontal {{ height: 8px; background: {CAT_SURFACE0}; border-radius: 4px; }}
        QSlider::handle:horizontal {{ 
            background: {CAT_MAUVE}; width: 22px; height: 22px; margin: -7px 0; border-radius: 11px; 
            border: 3px solid {CAT_BASE};
        }}
        QSlider::handle:horizontal:hover {{ background: {CAT_PINK}; }}
        QSlider::sub-page:horizontal {{ background: {CAT_BLUE}; border-radius: 4px; }}

        /* --- SCROLLBARS --- */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ border: none; background: {CAT_BASE}; width: 12px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {CAT_SURFACE1}; min-height: 20px; border-radius: 6px; }}
        QScrollBar::handle:vertical:hover {{ background: {CAT_OVERLAY0}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

        /* --- GROUP BOX FIX --- */
        QGroupBox {{ 
            border: 2px solid {CAT_SURFACE0}; 
            margin-top: 40px; 
            border-radius: 12px; 
            padding: 35px 20px 25px 20px; 
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin; 
            subcontrol-position: top left; 
            left: 20px; 
            padding: 5px 15px 5px 15px; 
            color: {CAT_MAUVE}; 
            background-color: {CAT_BASE}; 
            font-weight: bold; 
            font-size: 15px; 
        }}

        /* --- LISTS --- */
        QListWidget {{ 
            background-color: {CAT_MANTLE}; border: 2px solid {CAT_SURFACE0}; border-radius: 10px; outline: none;
        }}
        QListWidget::item {{ padding: 10px; border-radius: 6px; margin: 4px; }}
        QListWidget::item:selected {{ 
            background-color: {CAT_SURFACE1}; color: {CAT_MAUVE}; border: 1px solid {CAT_MAUVE};
        }}
        
        QLabel#PreviewLabel {{ 
            background-color: {CAT_CRUST}; border: 3px dashed {CAT_SURFACE0}; border-radius: 12px; 
        }}
    """
