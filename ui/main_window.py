import os
import qtawesome as qta
from PIL import Image

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QSlider, QCheckBox, 
    QFileDialog, QScrollArea, QGridLayout, QSplitter,
    QProgressBar, QMessageBox, QComboBox, QListWidget, QGroupBox,
    QInputDialog, QLineEdit, QSpinBox, QDoubleSpinBox, QStackedWidget,
    QButtonGroup, QFrame
)
from PyQt6.QtCore import Qt, QThread, QThreadPool, QSize
from PyQt6.QtGui import QPixmap, QIcon

from app.engine import T2IEngine
from app.config import SessionConfig, STYLES
from app.utils import get_file_list, generate_random_prompt
from app.style import get_stylesheet, CAT_COLORS
# NEU: Import von delete_image_record
from app.database import get_filtered_images, get_all_models, delete_image_record

from ui.workers import GeneratorWorker, DBScannerWorker, ThumbnailLoader
from ui.widgets import ClickableLabel, setup_combo_view, ImageViewerDialog

CHECKPOINTS_DIR = "models/checkpoints"
LORAS_DIR = "models/loras"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kami - SDXL Station")
        self.resize(1600, 950)
        
        self.engine = T2IEngine()
        self.config = SessionConfig()
        self.history = []
        # self.input_img_pil = None # Entfernt
        self.threadpool = QThreadPool()
        
        self.gallery_results = []       
        self.gallery_page_size = 50     
        self.gallery_current_page = 0 
        self.selected_gallery_item = None
        
        os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
        os.makedirs(LORAS_DIR, exist_ok=True)
        
        self.init_ui()
        self.apply_theme()
        self.load_settings_from_config()
        self.start_db_scan()

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet())

    def create_nav_btn(self, text, icon_name):
        btn = QPushButton(f" {text}")
        btn.setIcon(qta.icon(icon_name, color=CAT_COLORS['SUBTEXT0']))
        btn.setIconSize(QSize(18, 18))
        btn.setObjectName("NavBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def init_ui(self):
        # === MAIN LAYOUT ===
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. TOP NAVIGATION BAR
        self.navbar = QWidget()
        self.navbar.setObjectName("NavBar")
        self.navbar.setFixedHeight(60)
        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(10)

        self.btn_nav_gen = self.create_nav_btn("Generate", "fa5s.magic")
        self.btn_nav_models = self.create_nav_btn("Models", "fa5s.sliders-h")
        self.btn_nav_favs = self.create_nav_btn("Favorites", "fa5s.star")
        self.btn_nav_gallery = self.create_nav_btn("Gallery", "fa5s.images")

        self.nav_group = QButtonGroup(self)
        self.nav_group.addButton(self.btn_nav_gen, 0)
        self.nav_group.addButton(self.btn_nav_models, 1)
        self.nav_group.addButton(self.btn_nav_favs, 2)
        self.nav_group.addButton(self.btn_nav_gallery, 3)
        self.nav_group.idClicked.connect(self.switch_view)

        nav_layout.addWidget(self.btn_nav_gen)
        nav_layout.addWidget(self.btn_nav_models)
        nav_layout.addWidget(self.btn_nav_favs)
        nav_layout.addWidget(self.btn_nav_gallery)

        btn_iotd = QPushButton()
        btn_iotd.setIcon(qta.icon('fa5s.dice', color=CAT_COLORS['LAVENDER']))
        btn_iotd.setIconSize(QSize(22, 22))
        btn_iotd.setToolTip("Generate 'Image of the Day' (Random)")
        btn_iotd.setFixedSize(40, 40) # Quadratischer Button
        btn_iotd.setStyleSheet(f"""
            QPushButton {{ background-color: {CAT_COLORS['SURFACE0']}; border-radius: 20px; }}
            QPushButton:hover {{ background-color: {CAT_COLORS['SURFACE1']}; }}
        """)
        btn_iotd.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_iotd.clicked.connect(self.start_iotd_workflow)
        nav_layout.addWidget(btn_iotd)

        nav_layout.addStretch() 

        main_layout.addWidget(self.navbar)

        # 2. CONTENT STACK
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.init_page_gen()
        self.init_page_models()
        self.init_page_favs()
        self.init_page_gallery()

        self.btn_nav_gen.setChecked(True)
        self.stack.setCurrentIndex(0)

    def switch_view(self, id):
        self.stack.setCurrentIndex(id)
        if id == 3: self.refresh_gallery_view()
        if id == 2: self.refresh_favorites_list()

    # --- PAGE 1: GENERATE ---
    def init_page_gen(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        controls_container = QWidget()
        controls_container.setMinimumWidth(400)
        controls_container.setMaximumWidth(500)
        c_layout = QVBoxLayout(controls_container)
        c_layout.setContentsMargins(15, 15, 15, 15)
        c_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        
        # Modus-Auswahl entfernt
        sc_layout.addWidget(QLabel("<h3>Text-to-Image Mode</h3>"))

        # I2I-Gruppe entfernt
        # self.i2i_group.setVisible(False) entfernt

        sc_layout.addWidget(QLabel("Positive Prompt"))
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText("A majestic lion in the sunset...")
        self.txt_prompt.setMaximumHeight(100)
        sc_layout.addWidget(self.txt_prompt)
        sc_layout.addWidget(QLabel("Negative Prompt"))
        self.txt_neg = QTextEdit()
        self.txt_neg.setPlaceholderText("blur, ugly, low quality...")
        self.txt_neg.setMaximumHeight(60)
        sc_layout.addWidget(self.txt_neg)

        p_group = QGroupBox("Parameters")
        p_layout = QGridLayout(p_group)
        p_layout.addWidget(QLabel("Steps:"), 0, 0)
        self.slider_steps = QSlider(Qt.Orientation.Horizontal)
        self.slider_steps.setRange(1, 100)
        self.spin_steps = QSpinBox()
        self.spin_steps.setRange(1, 100)
        self.spin_steps.setValue(30)
        self.sync_slider_spinbox(self.slider_steps, self.spin_steps, 1.0)
        p_layout.addWidget(self.slider_steps, 0, 1)
        p_layout.addWidget(self.spin_steps, 0, 2)
        p_layout.addWidget(QLabel("CFG:"), 1, 0)
        self.slider_cfg = QSlider(Qt.Orientation.Horizontal)
        self.slider_cfg.setRange(10, 200)
        self.spin_cfg = QDoubleSpinBox()
        self.spin_cfg.setRange(1.0, 20.0)
        self.spin_cfg.setSingleStep(0.5)
        self.spin_cfg.setValue(7.0)
        self.sync_slider_spinbox(self.slider_cfg, self.spin_cfg, 10.0)
        p_layout.addWidget(self.slider_cfg, 1, 1)
        p_layout.addWidget(self.spin_cfg, 1, 2)
        p_layout.addWidget(QLabel("Seed:"), 2, 0)
        self.txt_seed = QLineEdit()
        self.txt_seed.setPlaceholderText("Empty = Random")
        p_layout.addWidget(self.txt_seed, 2, 1, 1, 2)
        sc_layout.addWidget(p_group)
        sc_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        c_layout.addWidget(scroll)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        c_layout.addWidget(self.progress_bar)
        
        self.btn_generate = QPushButton(" GENERATE")
        self.btn_generate.setIcon(qta.icon('fa5s.rocket', color=CAT_COLORS['BASE']))
        self.btn_generate.setIconSize(QSize(20, 20))
        self.btn_generate.setObjectName("GenerateBtn")
        self.btn_generate.setMinimumHeight(55)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self.start_generation)
        c_layout.addWidget(self.btn_generate)

        preview_container = QWidget()
        pc_layout = QVBoxLayout(preview_container)
        pc_layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_main_preview = QLabel()
        self.lbl_main_preview.setObjectName("PreviewLabel")
        self.lbl_main_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_main_preview.setSizePolicy(self.lbl_main_preview.sizePolicy().horizontalPolicy(), self.lbl_main_preview.sizePolicy().verticalPolicy())
        placeholder = qta.icon('fa5s.image', color=CAT_COLORS['SURFACE1']).pixmap(QSize(128, 128))
        self.lbl_main_preview.setPixmap(placeholder)
        pc_layout.addWidget(self.lbl_main_preview, 1)
        
        pc_layout.addWidget(QLabel("Session History"))
        h_scroll = QScrollArea()
        h_scroll.setWidgetResizable(True)
        h_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        h_scroll.setFixedHeight(180)
        self.history_grid = QWidget()
        self.history_layout = QGridLayout(self.history_grid)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.history_layout.setContentsMargins(0,0,0,0)
        h_scroll.setWidget(self.history_grid)
        pc_layout.addWidget(h_scroll)

        splitter.addWidget(controls_container)
        splitter.addWidget(preview_container)
        splitter.setSizes([450, 1150])
        
        layout.addWidget(splitter)
        self.stack.addWidget(page)

    # --- PAGE 2: MODELS ---
    def init_page_models(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.addWidget(QLabel("<h2>Model Configuration</h2>"))
        
        m_group = QGroupBox("Base Model & Refiner")
        m_grid = QGridLayout(m_group)
        self.combo_model = setup_combo_view(QComboBox())
        self.combo_model.addItem("stabilityai/stable-diffusion-xl-base-1.0")
        for f in get_file_list(CHECKPOINTS_DIR):
            self.combo_model.addItem(os.path.join(CHECKPOINTS_DIR, f))
        m_grid.addWidget(QLabel("Checkpoint:"), 0, 0)
        m_grid.addWidget(self.combo_model, 0, 1)
        self.chk_refiner = QCheckBox("Use SDXL Refiner")
        m_grid.addWidget(self.chk_refiner, 1, 0, 1, 2)
        layout.addWidget(m_group)
        
        l_group = QGroupBox("LoRA Configuration")
        l_grid = QGridLayout(l_group)
        self.combo_lora = setup_combo_view(QComboBox())
        self.combo_lora.addItem("None")
        for f in get_file_list(LORAS_DIR):
            self.combo_lora.addItem(os.path.join(LORAS_DIR, f))
        l_grid.addWidget(QLabel("LoRA File:"), 0, 0)
        l_grid.addWidget(self.combo_lora, 0, 1)
        l_grid.addWidget(QLabel("Scale:"), 1, 0)
        ls_layout = QHBoxLayout()
        self.slider_lora = QSlider(Qt.Orientation.Horizontal)
        self.slider_lora.setRange(0, 200)
        self.spin_lora = QDoubleSpinBox()
        self.spin_lora.setRange(0.0, 2.0)
        self.spin_lora.setSingleStep(0.1)
        self.spin_lora.setValue(1.0)
        self.sync_slider_spinbox(self.slider_lora, self.spin_lora, 100.0)
        ls_layout.addWidget(self.slider_lora)
        ls_layout.addWidget(self.spin_lora)
        l_grid.addLayout(ls_layout, 1, 1)
        layout.addWidget(l_group)
        
        s_group = QGroupBox("Styles & Advanced")
        s_grid = QGridLayout(s_group)
        self.combo_style = setup_combo_view(QComboBox())
        for k in STYLES.keys():
            self.combo_style.addItem(k)
        self.combo_style.currentTextChanged.connect(lambda t: setattr(self.config, 'current_style', t))
        s_grid.addWidget(QLabel("Preset:"), 0, 0)
        s_grid.addWidget(self.combo_style, 0, 1)
        self.chk_pony = QCheckBox("Pony Mode (Score Tags)")
        s_grid.addWidget(self.chk_pony, 1, 0)
        self.chk_freeu = QCheckBox("FreeU (Quality Boost)")
        s_grid.addWidget(self.chk_freeu, 1, 1)
        layout.addWidget(s_group)
        layout.addStretch()
        self.stack.addWidget(page)

    # --- PAGE 3: FAVORITES ---
    def init_page_favs(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        
        left_f = QWidget()
        left_fl = QVBoxLayout(left_f)
        left_fl.addWidget(QLabel("Saved Favorites"))
        self.list_favs = QListWidget()
        self.list_favs.itemClicked.connect(self.on_favorite_selected)
        left_fl.addWidget(self.list_favs)
        
        right_f = QWidget()
        right_fl = QVBoxLayout(right_f)
        right_fl.addWidget(QLabel("Edit Prompt"))
        self.fav_txt_prompt = QTextEdit()
        self.fav_txt_prompt.setPlaceholderText("Positive Prompt...")
        right_fl.addWidget(self.fav_txt_prompt)
        right_fl.addWidget(QLabel("Edit Negative Prompt (Optional)"))
        self.fav_txt_neg = QTextEdit()
        self.fav_txt_neg.setMaximumHeight(80)
        right_fl.addWidget(self.fav_txt_neg)
        
        f_btn_layout = QHBoxLayout()
        btn_load_fav = QPushButton(" Load")
        btn_load_fav.setIcon(qta.icon('fa5s.upload', color=CAT_COLORS['TEXT']))
        btn_load_fav.setObjectName("LoadBtn")
        btn_load_fav.clicked.connect(self.load_favorite_to_gen)
        
        btn_update_fav = QPushButton(" Update")
        btn_update_fav.setIcon(qta.icon('fa5s.save', color=CAT_COLORS['TEXT']))
        btn_update_fav.clicked.connect(self.update_favorite)
        
        btn_new_fav = QPushButton(" New")
        btn_new_fav.setIcon(qta.icon('fa5s.plus', color=CAT_COLORS['TEXT']))
        btn_new_fav.clicked.connect(self.save_new_favorite)
        
        btn_del_fav = QPushButton(" Delete")
        btn_del_fav.setIcon(qta.icon('fa5s.trash', color=CAT_COLORS['BASE']))
        btn_del_fav.setObjectName("DeleteBtn")
        btn_del_fav.clicked.connect(self.delete_favorite)
        
        f_btn_layout.addWidget(btn_load_fav)
        f_btn_layout.addWidget(btn_update_fav)
        f_btn_layout.addWidget(btn_new_fav)
        f_btn_layout.addWidget(btn_del_fav)
        right_fl.addLayout(f_btn_layout)
        
        layout.addWidget(left_f, 1)
        layout.addWidget(right_f, 2)
        self.stack.addWidget(page)

    # --- PAGE 4: GALLERY ---
    def init_page_gallery(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # HEADER
        header_container = QWidget()
        header_container.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; border-bottom: 1px solid {CAT_COLORS['SURFACE0']};")
        header_container.setFixedHeight(70)
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(15)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Suche nach Prompts, Seeds oder Modellen...")
        self.txt_search.setMinimumHeight(40)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{ 
                font-size: 14px; padding-left: 10px; border-radius: 20px; 
                border: 1px solid {CAT_COLORS['SURFACE1']}; background-color: {CAT_COLORS['BASE']};
            }}
            QLineEdit:focus {{ border: 1px solid {CAT_COLORS['BLUE']}; }}
        """)
        self.txt_search.textChanged.connect(self.on_gallery_search_changed)
        
        self.combo_filter_model = setup_combo_view(QComboBox())
        self.combo_filter_model.setFixedWidth(200)
        self.combo_filter_model.setMinimumHeight(35)
        self.combo_filter_model.addItem("All Models")
        self.combo_filter_model.currentIndexChanged.connect(self.on_gallery_search_changed)
        
        self.combo_sort = setup_combo_view(QComboBox())
        self.combo_sort.setFixedWidth(150)
        self.combo_sort.setMinimumHeight(35)
        self.combo_sort.addItems(["Newest First", "Oldest First", "Steps (High-Low)"])
        self.combo_sort.currentIndexChanged.connect(self.on_gallery_search_changed)
        
        btn_scan = QPushButton(" Rescan")
        btn_scan.setIcon(qta.icon('fa5s.sync-alt', color=CAT_COLORS['TEXT']))
        btn_scan.setFixedSize(90, 35)
        btn_scan.clicked.connect(self.start_db_scan)

        header_layout.addWidget(self.txt_search, 1)
        header_layout.addWidget(self.combo_filter_model)
        header_layout.addWidget(self.combo_sort)
        header_layout.addWidget(btn_scan)
        layout.addWidget(header_container)

        # BODY
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.gal_scroll = QScrollArea()
        self.gal_scroll.setWidgetResizable(True)
        self.gal_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.gal_scroll.setStyleSheet(f"background-color: {CAT_COLORS['BASE']};")
        
        self.db_grid = QWidget()
        self.db_layout = QGridLayout(self.db_grid)
        self.db_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.db_layout.setContentsMargins(15, 15, 15, 15)
        self.db_layout.setSpacing(10)
        self.gal_scroll.setWidget(self.db_grid)
        left_layout.addWidget(self.gal_scroll)
        
        pag_container = QWidget()
        pag_container.setFixedHeight(50)
        pag_container.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; border-top: 1px solid {CAT_COLORS['SURFACE0']};")
        self.pag_layout = QHBoxLayout(pag_container)
        self.pag_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(pag_container)
        
        right_widget = QWidget()
        right_widget.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; border-left: 1px solid {CAT_COLORS['SURFACE0']};")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        right_layout.addWidget(QLabel("<h3>Image Details</h3>"))
        
        self.gal_detail_img = ClickableLabel("")
        self.gal_detail_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gal_detail_img.setMinimumHeight(300)
        self.gal_detail_img.setStyleSheet(f"background-color: {CAT_COLORS['CRUST']}; border: 1px solid {CAT_COLORS['SURFACE0']}; border-radius: 8px;")
        self.gal_detail_img.setText("Select an image...")
        right_layout.addWidget(self.gal_detail_img)
        
        self.gal_detail_txt = QTextEdit()
        self.gal_detail_txt.setReadOnly(True)
        self.gal_detail_txt.setPlaceholderText("Metadata will appear here...")
        right_layout.addWidget(self.gal_detail_txt)
        
        btn_use_params = QPushButton(" Use Parameters")
        btn_use_params.setIcon(qta.icon('fa5s.magic', color=CAT_COLORS['TEXT']))
        btn_use_params.clicked.connect(self.use_gallery_params)
        
        # Button "Use as Input (I2I)" entfernt
        # btn_use_img = QPushButton(" Use as Input (I2I)")
        # btn_use_img.setIcon(qta.icon('fa5s.image', color=CAT_COLORS['TEXT']))
        # btn_use_img.clicked.connect(self.use_gallery_image_i2i) # entfernt
        
        # NEU: Delete Button im rechten Panel
        btn_del_img = QPushButton(" Delete Image")
        btn_del_img.setIcon(qta.icon('fa5s.trash', color=CAT_COLORS['BASE']))
        btn_del_img.setStyleSheet(f"background-color: {CAT_COLORS['RED']}; color: {CAT_COLORS['BASE']}; margin-top: 10px;")
        btn_del_img.clicked.connect(self.delete_gallery_image)
        
        right_layout.addWidget(btn_use_params)
        # right_layout.addWidget(btn_use_img) # entfernt
        right_layout.addWidget(btn_del_img)
        right_layout.addStretch()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([1100, 500])
        
        layout.addWidget(splitter)
        self.stack.addWidget(page)

    # --- LOGIC ---
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

    def on_gallery_search_changed(self):
        self.gallery_current_page = 0
        self.refresh_gallery_view()

    def refresh_gallery_view(self):
        current_models = [self.combo_filter_model.itemText(i) for i in range(self.combo_filter_model.count())]
        for m in get_all_models():
            if m not in current_models: self.combo_filter_model.addItem(m)
        
        self.gallery_results = get_filtered_images(
            self.txt_search.text(), 
            self.combo_sort.currentText(), 
            "All" if self.combo_filter_model.currentText() == "All Models" else self.combo_filter_model.currentText()
        )
        self.render_gallery_page()

    def render_gallery_page(self):
        for i in reversed(range(self.db_layout.count())): 
            w = self.db_layout.itemAt(i).widget()
            if w: w.setParent(None)

        total_items = len(self.gallery_results)
        start_idx = self.gallery_current_page * self.gallery_page_size
        end_idx = start_idx + self.gallery_page_size
        visible_items = self.gallery_results[start_idx:end_idx]
        
        for i, row in enumerate(visible_items):
            loader = ThumbnailLoader(row['path'], row['prompt'][:300], dict(row))
            loader.signals.loaded.connect(self.add_thumbnail_to_grid)
            self.threadpool.start(loader)
            
        self.update_pagination_controls(total_items)

    def add_thumbnail_to_grid(self, path, pixmap, tooltip, row_data):
        if self.db_layout.count() >= self.gallery_page_size: return

        count = self.db_layout.count()
        cols = 5
        lbl = ClickableLabel(path)
        lbl.setPixmap(pixmap)
        lbl.setFixedSize(200, 200) 
        lbl.setScaledContents(True) 
        lbl.setStyleSheet(f"""
            QLabel {{ border: 1px solid {CAT_COLORS['SURFACE1']}; border-radius: 6px; background-color: {CAT_COLORS['MANTLE']}; }}
            QLabel:hover {{ border: 2px solid {CAT_COLORS['BLUE']}; }}
        """)
        lbl.setToolTip(tooltip)
        lbl.clicked.connect(lambda: self.show_gallery_details(row_data, pixmap))
        # lbl.double_clicked.connect(lambda: self.set_input_image(path)) # entfernt
        self.db_layout.addWidget(lbl, count // cols, count % cols)

    def update_pagination_controls(self, total_items):
        for i in reversed(range(self.pag_layout.count())): 
            w = self.pag_layout.itemAt(i).widget()
            if w: w.setParent(None)

        total_pages = (total_items + self.gallery_page_size - 1) // self.gallery_page_size
        if total_pages <= 1: return

        btn_prev = QPushButton("<")
        btn_prev.setFixedSize(30, 30)
        btn_prev.setEnabled(self.gallery_current_page > 0)
        btn_prev.clicked.connect(lambda: self.change_gallery_page(self.gallery_current_page - 1))
        self.pag_layout.addWidget(btn_prev)

        start_p = max(0, self.gallery_current_page - 4)
        end_p = min(total_pages, start_p + 10)
        for p in range(start_p, end_p):
            btn = QPushButton(str(p + 1))
            btn.setFixedSize(30, 30); btn.setCheckable(True)
            btn.setChecked(p == self.gallery_current_page)
            if p == self.gallery_current_page: btn.setStyleSheet(f"background-color: {CAT_COLORS['BLUE']}; color: {CAT_COLORS['BASE']}; border: none;")
            else: btn.setStyleSheet("background-color: transparent;")
            btn.clicked.connect(lambda _, page=p: self.change_gallery_page(page))
            self.pag_layout.addWidget(btn)

        btn_next = QPushButton(">")
        btn_next.setFixedSize(30, 30)
        btn_next.setEnabled(self.gallery_current_page < total_pages - 1)
        btn_next.clicked.connect(lambda: self.change_gallery_page(self.gallery_current_page + 1))
        self.pag_layout.addWidget(btn_next)
        
        lbl_info = QLabel(f" Page {self.gallery_current_page + 1} of {total_pages} ({total_items} items)")
        lbl_info.setStyleSheet(f"color: {CAT_COLORS['SUBTEXT0']}; margin-left: 10px;")
        self.pag_layout.addWidget(lbl_info)

    def change_gallery_page(self, new_page):
        self.gallery_current_page = new_page
        self.render_gallery_page()
        self.gal_scroll.verticalScrollBar().setValue(0)

    def show_gallery_details(self, row, pixmap):
        self.selected_gallery_item = row
        w = self.gal_detail_img.width()
        if not pixmap.isNull():
            self.gal_detail_img.setPixmap(pixmap.scaled(w, w, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        try: self.gal_detail_img.clicked.disconnect()
        except: pass
        
        self.gal_detail_img.clicked.connect(lambda: self.open_fullscreen_viewer(row['path']))

        meta = (
            f"<b>Prompt:</b><br>{row['prompt']}<br><br>"
            f"<b>Negative:</b><br>{row['negative_prompt']}<br><br>"
            f"<b>Model:</b> {row['model']}<br>"
            f"<b>Seed:</b> {row['seed']}<br>"
            f"<b>Steps:</b> {row['steps']} | <b>CFG:</b> {row['cfg']}<br>"
            f"<b>Date:</b> {row['timestamp']}"
        )
        self.gal_detail_txt.setHtml(meta)

    def open_fullscreen_viewer(self, path):
        viewer = ImageViewerDialog(path, self)
        # NEU: Signal für Löschung verbinden
        viewer.delete_confirmed.connect(self.handle_viewer_delete)
        viewer.exec()

    # NEU: Handler für Löschung aus Viewer
    def handle_viewer_delete(self, path):
        # Viewer hat schon bestätigt, also direkt löschen
        try:
            os.remove(path)
            delete_image_record(path)
            self.refresh_gallery_view()
            self.gal_detail_img.clear()
            self.gal_detail_img.setText("Deleted")
            self.gal_detail_txt.clear()
            self.selected_gallery_item = None
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete: {e}")

    # NEU: Handler für Löschung aus Galerie-Panel
    def delete_gallery_image(self):
        if not self.selected_gallery_item: return
        path = self.selected_gallery_item['path']
        
        res = QMessageBox.question(self, "Delete Image", "Permanently delete this image?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                delete_image_record(path)
                self.refresh_gallery_view()
                self.gal_detail_img.clear()
                self.gal_detail_img.setText("Deleted")
                self.gal_detail_txt.clear()
                self.selected_gallery_item = None
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete: {e}")

    def use_gallery_params(self):
        if not self.selected_gallery_item: return
        row = self.selected_gallery_item
        self.txt_prompt.setText(row['prompt'])
        self.txt_neg.setText(row['negative_prompt'])
        self.spin_steps.setValue(int(row['steps']))
        self.spin_cfg.setValue(float(row['cfg']))
        try:
            seed = int(row['seed'])
            self.txt_seed.setText(str(seed))
        except: self.txt_seed.setText("")
        self.btn_nav_gen.setChecked(True)
        self.switch_view(0)
        QMessageBox.information(self, "Loaded", "Parameters loaded from image!")

    # use_gallery_image_i2i entfernt
    # toggle_mode entfernt
    # load_input_image_dialog entfernt
    # set_input_image entfernt

    # RESTORED: Load settings (essential for startup)
    def load_settings_from_config(self):
        self.txt_neg.setText(self.config.neg_prompt); self.spin_steps.setValue(self.config.steps); self.spin_cfg.setValue(self.config.guidance)
        self.chk_refiner.setChecked(self.config.use_refiner); self.chk_pony.setChecked(self.config.pony_mode); self.chk_freeu.setChecked(self.config.use_freeu)
        idx = self.combo_style.findText(self.config.current_style)
        if idx >= 0: self.combo_style.setCurrentIndex(idx)

    # RESTORED: Refresh favorites list
    def refresh_favorites_list(self):
        self.list_favs.clear()
        for fav in self.config.favourites: self.list_favs.addItem(f"{fav['name']}")

    # RESTORED: On favorite selected (CRASH FIX) - Logic improved to handle negative prompt
    def on_favorite_selected(self, item):
        idx = self.list_favs.row(item)
        if 0 <= idx < len(self.config.favourites):
            fav = self.config.favourites[idx]
            self.fav_txt_prompt.setText(fav.get('prompt', ''))
            self.fav_txt_neg.setText(fav.get('negative_prompt', ''))

    # RESTORED: Load favorite to generate - Logic improved to load negative prompt
    def load_favorite_to_gen(self):
        self.txt_prompt.setText(self.fav_txt_prompt.toPlainText())
        self.txt_neg.setText(self.fav_txt_neg.toPlainText()) # Lade Neg. Prompt
        self.btn_nav_gen.setChecked(True); self.switch_view(0)

    # RESTORED: Save new favorite - Logic improved to save negative prompt
    def save_new_favorite(self):
        text, ok = QInputDialog.getText(self, "Save New", "Name:")
        if ok and text:
            self.config.favourites.append({
                "name": text, 
                "prompt": self.fav_txt_prompt.toPlainText(),
                "negative_prompt": self.fav_txt_neg.toPlainText() # Speichere Neg. Prompt
            })
            self.config.save_favorites(); self.refresh_favorites_list()

    # RESTORED: Update favorite - Logic improved to update negative prompt
    def update_favorite(self):
        row = self.list_favs.currentRow()
        if row >= 0:
            self.config.favourites[row]['prompt'] = self.fav_txt_prompt.toPlainText()
            self.config.favourites[row]['negative_prompt'] = self.fav_txt_neg.toPlainText() # Update Neg. Prompt
            self.config.save_favorites(); QMessageBox.information(self, "Info", "Favorite updated!")

    # RESTORED: Delete favorite - Logic improved to clear text fields
    def delete_favorite(self):
        row = self.list_favs.currentRow()
        if row >= 0:
            del self.config.favourites[row]
            self.config.save_favorites(); self.refresh_favorites_list(); self.fav_txt_prompt.clear(); self.fav_txt_neg.clear()

    def start_generation(self):
        self.btn_generate.setEnabled(False); self.btn_generate.setText(" GENERATING...")
        self.progress_bar.setVisible(True); self.progress_bar.setRange(0, 0)
        
        prompt_raw = self.txt_prompt.toPlainText(); neg_raw = self.txt_neg.toPlainText()
        style_name = self.combo_style.currentText()
        if style_name in STYLES and style_name != "None":
            prompt_final = STYLES[style_name]["pos"] + prompt_raw; neg_final = STYLES[style_name]["neg"] + neg_raw
        else: prompt_final, neg_final = prompt_raw, neg_raw
            
        if self.chk_pony.isChecked():
            prompt_final = self.config.pony_prefix + prompt_final
            if "score_4" not in neg_final: neg_final = self.config.pony_neg + neg_raw
                
        seed_val = int(self.txt_seed.text().strip()) if self.txt_seed.text().strip().isdigit() else None
        lora_p = self.combo_lora.currentText() if self.combo_lora.currentText() != "None" else None
        
        params = {
            "model_path": self.combo_model.currentText(), "prompt": prompt_final, "negative_prompt": neg_final,
            "steps": self.spin_steps.value(), "guidance_scale": self.spin_cfg.value(), "seed": seed_val,
            "use_refiner": self.chk_refiner.isChecked(), "lora_path": lora_p, "lora_scale": self.spin_lora.value(),
            # strength entfernt
            "freeu_args": {"s1":0.9, "s2":0.2, "b1":1.3, "b2":1.4} if self.chk_freeu.isChecked() else None
        }
        # mode und input_img_pil entfernt
        self.thread = QThread()
        self.worker = GeneratorWorker(self.engine, params)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_generation_finished(self, path):
        self.btn_generate.setEnabled(True); self.btn_generate.setText(" GENERATE")
        self.progress_bar.setVisible(False)
        pixmap = QPixmap(path)
        if not pixmap.isNull():
             self.lbl_main_preview.setPixmap(pixmap.scaled(self.lbl_main_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.add_to_history(path); self.config.prompt = self.txt_prompt.toPlainText(); self.config.save_session_state(); self.start_db_scan()

    def on_generation_error(self, err):
        self.btn_generate.setEnabled(True); self.btn_generate.setText(" GENERATE")
        self.progress_bar.setVisible(False); QMessageBox.critical(self, "Error", err)

    def add_to_history(self, path):
        row = len(self.history) // 4; col = len(self.history) % 4
        lbl = ClickableLabel(path)
        pix = QPixmap(path); lbl.setPixmap(pix.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        lbl.setFixedSize(150, 150); lbl.setStyleSheet(f"border: 1px solid {CAT_COLORS['SURFACE1']}; border-radius: 4px;")
        # lbl.double_clicked.connect(lambda: self.set_input_image(path)) # entfernt
        self.history_layout.addWidget(lbl, row, col); self.history.append(path)

    # --- IOTD WORKFLOW ---
    def start_iotd_workflow(self):
        # 1. Prompt generieren
        prompt = generate_random_prompt()
        
        # 2. User fragen (Bestätigung)
        msg = QMessageBox(self)
        msg.setWindowTitle("Image of the Day")
        msg.setText("Generate a random image with this prompt?")
        msg.setInformativeText(prompt)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        # Styling für die Messagebox (optional, damit es zum Theme passt)
        msg.setStyleSheet(f"background-color: {CAT_COLORS['MANTLE']}; color: {CAT_COLORS['TEXT']};")
        
        ret = msg.exec()
        
        if ret == QMessageBox.StandardButton.Yes:
            # 3. Generierung starten
            self.btn_generate.setEnabled(False) # Hauptbutton sperren
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            # Gute Standard-Parameter für SDXL
            params = {
                "model_path": self.config.model_path, # Nutzt das zuletzt eingestellte Modell
                "prompt": prompt,
                "negative_prompt": "ugly, deformed, noisy, blurry, low contrast, text, watermark",
                "steps": 40, # Etwas mehr Qualität
                "guidance_scale": 7.5,
                "seed": None, # Zufall
                "use_refiner": self.config.use_refiner,
                "lora_path": None,
                "lora_scale": 0.8,
                # strength entfernt
                "freeu_args": None
            }
            
            self.thread = QThread()
            self.worker = GeneratorWorker(self.engine, params) # ohne mode und input_image
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            
            # WICHTIG: Wir verbinden es mit einer SPEZIELLEN on_finished Methode
            self.worker.finished.connect(self.on_iotd_finished)
            
            self.worker.error.connect(self.on_generation_error) # Standard Error Handler nutzen
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

    def on_iotd_finished(self, path):
        # UI zurücksetzen
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # In DB und History aufnehmen (wie bei normaler Generierung)
        self.add_to_history(path)
        self.start_db_scan()
        
        # SPEZIAL-EFFEKT: Direkt im großen Viewer öffnen
        # Wir nutzen den neuen ImageViewerDialog, den wir vorhin erstellt haben
        viewer = ImageViewerDialog(path, self)
        viewer.delete_confirmed.connect(self.handle_viewer_delete) # Löschen erlauben
        viewer.setWindowTitle("Image of the Day - Result")
        viewer.exec()
