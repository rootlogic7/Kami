import sys
import os
import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QSlider, QCheckBox, 
    QFileDialog, QScrollArea, QGridLayout, QTabWidget, QSplitter,
    QProgressBar, QMessageBox, QComboBox, QListWidget, QGroupBox,
    QMenu, QInputDialog, QLineEdit, QSpinBox, QDoubleSpinBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.engine import T2IEngine
from app.config import SessionConfig, STYLES
from app.utils import get_file_list
# Import Database stuff
from app.database import get_filtered_images, get_all_models, scan_and_import_folder

CHECKPOINTS_DIR = "models/checkpoints"
LORAS_DIR = "models/loras"

# --- Catppuccin Colors ---
CAT_BASE = "#1e1e2e"; CAT_MANTLE = "#181825"; CAT_SURFACE0 = "#313244"
CAT_SURFACE1 = "#45475a"; CAT_TEXT = "#cdd6f4"; CAT_SUBTEXT0 = "#a6adc8"
CAT_GREEN = "#a6e3a1"; CAT_RED = "#f38ba8"; CAT_OVERLAY0 = "#6c7086"

# --- Workers ---
class GeneratorWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, engine, params, mode="T2I", input_image=None):
        super().__init__()
        self.engine, self.params, self.mode, self.input_image = engine, params, mode, input_image

    def run(self):
        try:
            if self.engine.base_model_id != self.params.get("model_path"):
                self.engine.base_model_id = self.params.get("model_path")
                self.engine.base_pipeline = None 
            
            gen_args = {k: v for k, v in self.params.items() if k not in ["model_path", "strength"]}
            if self.mode == "T2I":
                path = self.engine.generate(**gen_args)
            else:
                if not self.input_image: raise ValueError("No input image")
                gen_args["strength"] = self.params["strength"]
                path = self.engine.generate_i2i(input_image=self.input_image, **gen_args)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))

class DBScannerWorker(QObject):
    finished = pyqtSignal(int)
    
    def run(self):
        count = scan_and_import_folder()
        self.finished.emit(count)

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDXL Local Station (Wayland Edition)")
        self.resize(1600, 950)
        
        self.engine = T2IEngine()
        self.config = SessionConfig()
        self.history = []
        self.input_img_pil = None
        
        os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
        os.makedirs(LORAS_DIR, exist_ok=True)
        
        self.init_ui()
        self.apply_theme()
        self.load_settings_from_config()
        
        # Start DB Scan on load
        self.start_db_scan()

    def apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {CAT_BASE}; color: {CAT_TEXT}; font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
            QGroupBox {{ border: 1px solid {CAT_SURFACE1}; margin-top: 1.5em; border-radius: 5px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px; color: {CAT_GREEN}; font-weight: bold; }}
            QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {{ 
                background-color: {CAT_SURFACE0}; border: 1px solid {CAT_SURFACE1}; border-radius: 4px; padding: 5px; color: {CAT_TEXT};
                selection-background-color: {CAT_GREEN}; selection-color: {CAT_BASE};
            }}
            QPushButton {{ background-color: {CAT_SURFACE1}; color: {CAT_TEXT}; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {CAT_OVERLAY0}; }}
            QPushButton#GenerateBtn {{ background-color: {CAT_GREEN}; color: {CAT_BASE}; }}
            QPushButton#GenerateBtn:hover {{ background-color: #94e2d5; }}
            QPushButton#ModeBtn:checked {{ background-color: {CAT_GREEN}; color: {CAT_BASE}; }}
            QSlider::groove:horizontal {{ border: 1px solid {CAT_SURFACE1}; height: 6px; background: {CAT_MANTLE}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {CAT_GREEN}; border: 1px solid {CAT_BASE}; width: 16px; margin: -5px 0; border-radius: 8px; }}
            QTabWidget::pane {{ border: 1px solid {CAT_SURFACE1}; border-radius: 4px; }}
            QTabBar::tab {{ background: {CAT_SURFACE0}; border: 1px solid {CAT_SURFACE1}; padding: 8px 12px; margin-right: 2px; border-top-left-radius: 4px; color: {CAT_SUBTEXT0}; }}
            QTabBar::tab:selected {{ background: {CAT_GREEN}; color: {CAT_BASE}; font-weight: bold; }}
            QLabel#PreviewLabel {{ background-color: {CAT_MANTLE}; border: 2px dashed {CAT_SURFACE1}; border-radius: 8px; }}
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ==================== SIDEBAR ====================
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar.setMinimumWidth(400); sidebar.setMaximumWidth(500)
        
        self.side_tabs = QTabWidget()
        # FIX: Signal connection removed here, moved to end of function!
        
        # Tabs
        self.tab_gen = QWidget(); self.tab_models = QWidget(); self.tab_favs = QWidget(); self.tab_gallery = QWidget()
        self.side_tabs.addTab(self.tab_gen, "Generate")
        self.side_tabs.addTab(self.tab_models, "Models & Styles")
        self.side_tabs.addTab(self.tab_favs, "Favorites")
        self.side_tabs.addTab(self.tab_gallery, "Gallery")
        sidebar_layout.addWidget(self.side_tabs)

        # --- TAB 1: GENERATE ---
        gen_layout = QVBoxLayout(self.tab_gen)
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout(mode_group)
        self.btn_mode_t2i = QPushButton("Text to Image"); self.btn_mode_t2i.setObjectName("ModeBtn"); self.btn_mode_t2i.setCheckable(True); self.btn_mode_t2i.setChecked(True)
        self.btn_mode_t2i.clicked.connect(lambda: self.toggle_mode("T2I"))
        self.btn_mode_i2i = QPushButton("Image to Image"); self.btn_mode_i2i.setObjectName("ModeBtn"); self.btn_mode_i2i.setCheckable(True)
        self.btn_mode_i2i.clicked.connect(lambda: self.toggle_mode("I2I"))
        mode_layout.addWidget(self.btn_mode_t2i); mode_layout.addWidget(self.btn_mode_i2i)
        gen_layout.addWidget(mode_group)

        self.i2i_group = QGroupBox("Input Image")
        i2i_layout = QVBoxLayout(self.i2i_group)
        self.lbl_input_preview = QLabel("Drop/Load Image")
        self.lbl_input_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_input_preview.setStyleSheet(f"border: 2px dashed {CAT_SURFACE1}; min-height: 120px;")
        i2i_layout.addWidget(self.lbl_input_preview)
        btn_load = QPushButton("Load"); btn_load.clicked.connect(self.load_input_image_dialog)
        i2i_layout.addWidget(btn_load)
        i2i_layout.addWidget(QLabel("Denoising Strength"))
        s_layout = QHBoxLayout()
        self.slider_strength = QSlider(Qt.Orientation.Horizontal); self.slider_strength.setRange(0, 100)
        self.spin_strength = QDoubleSpinBox(); self.spin_strength.setRange(0.0, 1.0); self.spin_strength.setSingleStep(0.05); self.spin_strength.setValue(0.75)
        self.sync_slider_spinbox(self.slider_strength, self.spin_strength, 100.0)
        s_layout.addWidget(self.slider_strength); s_layout.addWidget(self.spin_strength)
        i2i_layout.addLayout(s_layout)
        gen_layout.addWidget(self.i2i_group); self.i2i_group.setVisible(False)

        gen_layout.addWidget(QLabel("Positive Prompt"))
        self.txt_prompt = QTextEdit(); self.txt_prompt.setMaximumHeight(100)
        gen_layout.addWidget(self.txt_prompt)
        gen_layout.addWidget(QLabel("Negative Prompt"))
        self.txt_neg = QTextEdit(); self.txt_neg.setMaximumHeight(60)
        gen_layout.addWidget(self.txt_neg)

        p_group = QGroupBox("Parameters")
        p_layout = QGridLayout(p_group)
        p_layout.addWidget(QLabel("Steps:"), 0, 0)
        self.slider_steps = QSlider(Qt.Orientation.Horizontal); self.slider_steps.setRange(1, 100)
        self.spin_steps = QSpinBox(); self.spin_steps.setRange(1, 100); self.spin_steps.setValue(30)
        self.sync_slider_spinbox(self.slider_steps, self.spin_steps, 1.0)
        p_layout.addWidget(self.slider_steps, 0, 1); p_layout.addWidget(self.spin_steps, 0, 2)
        
        p_layout.addWidget(QLabel("CFG:"), 1, 0)
        self.slider_cfg = QSlider(Qt.Orientation.Horizontal); self.slider_cfg.setRange(10, 200)
        self.spin_cfg = QDoubleSpinBox(); self.spin_cfg.setRange(1.0, 20.0); self.spin_cfg.setSingleStep(0.5); self.spin_cfg.setValue(7.0)
        self.sync_slider_spinbox(self.slider_cfg, self.spin_cfg, 10.0)
        p_layout.addWidget(self.slider_cfg, 1, 1); p_layout.addWidget(self.spin_cfg, 1, 2)
        
        p_layout.addWidget(QLabel("Seed:"), 2, 0)
        self.txt_seed = QLineEdit(); self.txt_seed.setPlaceholderText("Random")
        p_layout.addWidget(self.txt_seed, 2, 1, 1, 2)
        gen_layout.addWidget(p_group); gen_layout.addStretch()

        # --- TAB 2: MODELS ---
        m_layout = QVBoxLayout(self.tab_models)
        self.combo_model = QComboBox(); self.combo_model.addItem("stabilityai/stable-diffusion-xl-base-1.0")
        for f in get_file_list(CHECKPOINTS_DIR): self.combo_model.addItem(os.path.join(CHECKPOINTS_DIR, f))
        m_layout.addWidget(QLabel("Base Model")); m_layout.addWidget(self.combo_model)
        self.chk_refiner = QCheckBox("Use SDXL Refiner"); m_layout.addWidget(self.chk_refiner)
        
        m_layout.addWidget(QLabel("LoRA")); self.combo_lora = QComboBox(); self.combo_lora.addItem("None")
        for f in get_file_list(LORAS_DIR): self.combo_lora.addItem(os.path.join(LORAS_DIR, f))
        m_layout.addWidget(self.combo_lora)
        l_scale_l = QHBoxLayout()
        self.slider_lora = QSlider(Qt.Orientation.Horizontal); self.slider_lora.setRange(0, 200)
        self.spin_lora = QDoubleSpinBox(); self.spin_lora.setRange(0.0, 2.0); self.spin_lora.setSingleStep(0.1); self.spin_lora.setValue(1.0)
        self.sync_slider_spinbox(self.slider_lora, self.spin_lora, 100.0)
        l_scale_l.addWidget(self.slider_lora); l_scale_l.addWidget(self.spin_lora)
        m_layout.addLayout(l_scale_l)
        
        self.combo_style = QComboBox()
        for k in STYLES.keys(): self.combo_style.addItem(k)
        self.combo_style.currentTextChanged.connect(lambda t: setattr(self.config, 'current_style', t))
        m_layout.addWidget(QLabel("Style")); m_layout.addWidget(self.combo_style)
        self.chk_pony = QCheckBox("Pony Mode"); m_layout.addWidget(self.chk_pony)
        self.chk_freeu = QCheckBox("FreeU"); m_layout.addWidget(self.chk_freeu)
        m_layout.addStretch()

        # --- TAB 3: FAVORITES ---
        f_layout = QVBoxLayout(self.tab_favs)
        self.list_favs = QListWidget(); self.list_favs.itemDoubleClicked.connect(self.load_favorite)
        f_layout.addWidget(self.list_favs)
        bf_layout = QHBoxLayout()
        btn_sf = QPushButton("Save"); btn_sf.clicked.connect(self.save_favorite)
        btn_df = QPushButton("Delete"); btn_df.clicked.connect(self.delete_favorite)
        bf_layout.addWidget(btn_sf); bf_layout.addWidget(btn_df)
        f_layout.addLayout(bf_layout)
        self.refresh_favorites_list()

        # --- TAB 4: GALLERY FILTER (NEW) ---
        gal_layout = QVBoxLayout(self.tab_gallery)
        gal_layout.addWidget(QLabel("Search Prompts"))
        self.txt_search = QLineEdit(); self.txt_search.textChanged.connect(self.refresh_gallery_view)
        gal_layout.addWidget(self.txt_search)
        
        gal_layout.addWidget(QLabel("Filter by Model"))
        self.combo_filter_model = QComboBox(); self.combo_filter_model.addItem("All")
        self.combo_filter_model.currentIndexChanged.connect(self.refresh_gallery_view)
        gal_layout.addWidget(self.combo_filter_model)
        
        gal_layout.addWidget(QLabel("Sort By"))
        self.combo_sort = QComboBox(); self.combo_sort.addItems(["Newest", "Oldest", "Steps (High-Low)"])
        self.combo_sort.currentIndexChanged.connect(self.refresh_gallery_view)
        gal_layout.addWidget(self.combo_sort)
        
        btn_scan = QPushButton("Rescan Folder"); btn_scan.clicked.connect(self.start_db_scan)
        gal_layout.addWidget(btn_scan)
        gal_layout.addStretch()

        # GENERATE BUTTON
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        sidebar_layout.addWidget(self.progress_bar)
        self.btn_generate = QPushButton("GENERATE IMAGE"); self.btn_generate.setObjectName("GenerateBtn"); self.btn_generate.setMinimumHeight(60)
        self.btn_generate.clicked.connect(self.start_generation)
        sidebar_layout.addWidget(self.btn_generate)

        # ==================== RIGHT AREA (STACKED) ====================
        self.right_stack = QStackedWidget()
        
        # --- Page 0: Generator View ---
        gen_view = QWidget(); gv_layout = QVBoxLayout(gen_view)
        self.lbl_main_preview = QLabel("Ready to dream..."); self.lbl_main_preview.setObjectName("PreviewLabel"); self.lbl_main_preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl_main_preview.setMinimumHeight(500)
        gv_layout.addWidget(self.lbl_main_preview)
        gv_layout.addWidget(QLabel("Session History"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.history_grid = QWidget(); self.history_layout = QGridLayout(self.history_grid); self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.history_grid); gv_layout.addWidget(scroll)
        self.right_stack.addWidget(gen_view)
        
        # --- Page 1: Gallery View ---
        gal_view = QWidget(); gal_v_layout = QVBoxLayout(gal_view)
        gal_scroll = QScrollArea(); gal_scroll.setWidgetResizable(True)
        self.db_grid = QWidget(); self.db_layout = QGridLayout(self.db_grid); self.db_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        gal_scroll.setWidget(self.db_grid); gal_v_layout.addWidget(gal_scroll)
        self.right_stack.addWidget(gal_view)

        splitter.addWidget(sidebar); splitter.addWidget(self.right_stack)
        splitter.setSizes([450, 1150])
        
        # FIX: Connect Signal AFTER everything is initialized
        self.side_tabs.currentChanged.connect(self.on_tab_changed)

    # --- Logic ---
    def on_tab_changed(self, index):
        # Switch Right Stack based on Tab
        if index == 3: # Gallery Tab
            self.right_stack.setCurrentIndex(1)
            self.refresh_gallery_view()
        else:
            self.right_stack.setCurrentIndex(0)

    def sync_slider_spinbox(self, slider, spinbox, factor):
        is_float = isinstance(spinbox, QDoubleSpinBox)
        if is_float: slider.valueChanged.connect(lambda v: spinbox.setValue(v / factor))
        else: slider.valueChanged.connect(lambda v: spinbox.setValue(int(v / factor)))
        spinbox.valueChanged.connect(lambda v: slider.setValue(int(v * factor)))

    def start_db_scan(self):
        self.scan_thread = QThread()
        self.scan_worker = DBScannerWorker()
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(lambda c: print(f"Scanned {c} new images"))
        self.scan_worker.finished.connect(self.refresh_gallery_view)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.start()

    def refresh_gallery_view(self):
        # Populate Model Filter
        current_models = [self.combo_filter_model.itemText(i) for i in range(self.combo_filter_model.count())]
        db_models = get_all_models()
        for m in db_models:
            if m not in current_models: self.combo_filter_model.addItem(m)
            
        # Get Images
        rows = get_filtered_images(
            search_text=self.txt_search.text(),
            sort_by=self.combo_sort.currentText(),
            model_filter=self.combo_filter_model.currentText()
        )
        
        # Clear Grid
        for i in reversed(range(self.db_layout.count())): 
            w = self.db_layout.itemAt(i).widget(); 
            if w: w.setParent(None)
            
        # Fill Grid (Limit 50 for perfo, implement pagination later if needed)
        cols = 5
        for i, row in enumerate(rows[:50]): 
            path = row['path']
            if not os.path.exists(path): continue
            
            lbl = ClickableLabel(path)
            pix = QPixmap(path)
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                lbl.setFixedSize(200, 200)
                lbl.setStyleSheet(f"border: 1px solid {CAT_SURFACE1}; border-radius: 4px;")
                lbl.setToolTip(f"{row['prompt'][:100]}...")
                lbl.double_clicked.connect(lambda p=path: self.set_input_image(p))
                lbl.clicked.connect(lambda p=path: self.preview_image_gallery(p))
                
                self.db_layout.addWidget(lbl, i // cols, i % cols)

    def preview_image_gallery(self, path):
        # Could show full size preview later
        pass 

    def toggle_mode(self, mode):
        if mode == "T2I":
            self.btn_mode_t2i.setChecked(True); self.btn_mode_i2i.setChecked(False); self.i2i_group.setVisible(False)
        else:
            self.btn_mode_t2i.setChecked(False); self.btn_mode_i2i.setChecked(True); self.i2i_group.setVisible(True)

    def load_input_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if path: self.set_input_image(path)

    def set_input_image(self, path):
        try:
            self.input_img_pil = Image.open(path).convert("RGB")
            pixmap = QPixmap(path)
            self.lbl_input_preview.setPixmap(pixmap.scaled(self.lbl_input_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.toggle_mode("I2I")
            self.side_tabs.setCurrentIndex(0) # Go to Generate
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    def load_settings_from_config(self):
        self.txt_neg.setText(self.config.neg_prompt)
        self.spin_steps.setValue(self.config.steps)
        self.spin_cfg.setValue(self.config.guidance)
        self.chk_refiner.setChecked(self.config.use_refiner)
        self.chk_pony.setChecked(self.config.pony_mode)
        self.chk_freeu.setChecked(self.config.use_freeu)
        idx = self.combo_style.findText(self.config.current_style)
        if idx >= 0: self.combo_style.setCurrentIndex(idx)

    def refresh_favorites_list(self):
        self.list_favs.clear()
        for fav in self.config.favourites: self.list_favs.addItem(f"{fav['name']}")

    def load_favorite(self, item):
        idx = self.list_favs.row(item)
        if 0 <= idx < len(self.config.favourites):
            fav = self.config.favourites[idx]
            self.txt_prompt.setText(fav['prompt'])
            self.side_tabs.setCurrentIndex(0)

    def save_favorite(self):
        text, ok = QInputDialog.getText(self, "Save Favorite", "Name:")
        if ok and text:
            self.config.favourites.append({"name": text, "prompt": self.txt_prompt.toPlainText()})
            self.config.save_favorites(); self.refresh_favorites_list()

    def delete_favorite(self):
        row = self.list_favs.currentRow()
        if row >= 0:
            del self.config.favourites[row]
            self.config.save_favorites(); self.refresh_favorites_list()

    def start_generation(self):
        self.btn_generate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        prompt_raw = self.txt_prompt.toPlainText()
        neg_raw = self.txt_neg.toPlainText()
        style_name = self.combo_style.currentText()
        if style_name in STYLES and style_name != "None":
            prompt_final = STYLES[style_name]["pos"] + prompt_raw
            neg_final = STYLES[style_name]["neg"] + neg_raw
        else:
            prompt_final, neg_final = prompt_raw, neg_raw
            
        if self.chk_pony.isChecked():
            prompt_final = self.config.pony_prefix + prompt_final
            if "score_4" not in neg_final: neg_final = self.config.pony_neg + neg_final

        seed_val = int(self.txt_seed.text().strip()) if self.txt_seed.text().strip().isdigit() else None
        lora_p = self.combo_lora.currentText() if self.combo_lora.currentText() != "None" else None

        params = {
            "model_path": self.combo_model.currentText(),
            "prompt": prompt_final,
            "negative_prompt": neg_final,
            "steps": self.spin_steps.value(),
            "guidance_scale": self.spin_cfg.value(),
            "seed": seed_val,
            "use_refiner": self.chk_refiner.isChecked(),
            "lora_path": lora_p,
            "lora_scale": self.spin_lora.value(),
            "strength": self.spin_strength.value(),
            "freeu_args": {"s1":0.9, "s2":0.2, "b1":1.3, "b2":1.4} if self.chk_freeu.isChecked() else None
        }
        
        mode = "T2I" if self.btn_mode_t2i.isChecked() else "I2I"
        
        self.thread = QThread()
        self.worker = GeneratorWorker(self.engine, params, mode, self.input_img_pil)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_generation_finished(self, path):
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        pixmap = QPixmap(path)
        w, h = self.lbl_main_preview.width(), self.lbl_main_preview.height()
        self.lbl_main_preview.setPixmap(pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.add_to_history(path)
        self.config.prompt = self.txt_prompt.toPlainText()
        self.config.save_session_state()
        # Trigger scan to add new image to DB immediately
        self.start_db_scan()

    def on_generation_error(self, err):
        self.btn_generate.setEnabled(True); self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", err)

    def add_to_history(self, path):
        row = len(self.history) // 4; col = len(self.history) % 4
        lbl = ClickableLabel(path)
        pix = QPixmap(path)
        lbl.setPixmap(pix.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        lbl.setFixedSize(150, 150)
        lbl.setStyleSheet(f"border: 1px solid {CAT_SURFACE1}; border-radius: 4px;")
        lbl.double_clicked.connect(lambda: self.set_input_image(path))
        self.history_layout.addWidget(lbl, row, col)
        self.history.append(path)

class ClickableLabel(QLabel):
    clicked = pyqtSignal(); double_clicked = pyqtSignal()
    def mousePressEvent(self, event): self.clicked.emit()
    def mouseDoubleClickEvent(self, event): self.double_clicked.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
