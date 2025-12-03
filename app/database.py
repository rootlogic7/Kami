import sqlite3
import os
import glob
import logging
from datetime import datetime
from typing import List, Optional, Any, Tuple, Dict
from PIL import Image

# Initialize logger
logger = logging.getLogger(__name__)

DB_FILE = "library.db"

def init_db() -> None:
    """
    Initializes the SQLite database tables if they do not exist.
    Creates tables for: images (gallery), characters, and presets.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            
            # 1. Gallery Table
            c.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    prompt TEXT,
                    negative_prompt TEXT,
                    model TEXT,
                    steps INTEGER,
                    cfg REAL,
                    seed TEXT,
                    timestamp DATETIME,
                    favorite INTEGER DEFAULT 0
                )
            ''')

            # 2. Characters Table
            c.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    trigger_words TEXT,
                    preview_path TEXT,
                    notes TEXT
                )
            ''')

            # 3. Presets Table
            c.execute('''
                CREATE TABLE IF NOT EXISTS presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    model TEXT,
                    lora TEXT,
                    lora_scale REAL,
                    steps INTEGER,
                    cfg REAL,
                    prompt_template TEXT,
                    negative_prompt TEXT
                )
            ''')
            
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# --- IMAGE OPERATIONS ---

def add_image_record(
    path: str, 
    prompt: str, 
    neg: str, 
    model: str, 
    steps: int, 
    cfg: float, 
    seed: str | int
) -> None:
    """Inserts a new image record into the database."""
    try:
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR IGNORE INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (abs_path, prompt, neg, model, steps, cfg, str(seed), datetime.now()))
        logger.debug(f"Added record for: {abs_path}")
    except sqlite3.Error as e:
        logger.error(f"Could not add record to DB: {e}")
    finally:
        if 'conn' in locals(): conn.close()

def delete_image_record(path: str) -> bool:
    """Deletes an image record from the database based on its file path."""
    try:
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute("DELETE FROM images WHERE path = ?", (abs_path,))
        return True
    except sqlite3.Error as e:
        logger.error(f"Could not delete record: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()

def get_filtered_images(
    search_text: str = "", 
    sort_by: str = "Newest", 
    model_filter: str = "All"
) -> List[sqlite3.Row]:
    """Queries the database with search filters and sorting."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        query = "SELECT * FROM images WHERE 1=1"
        params: List[Any] = []
        
        if search_text:
            query += " AND (prompt LIKE ? OR seed LIKE ? OR model LIKE ?)"
            term = f"%{search_text}%"
            params.extend([term, term, term])
            
        if model_filter and model_filter not in ["All Models", "All"]:
            query += " AND model LIKE ?"
            params.append(f"%{model_filter}%")
            
        if sort_by in ["Newest First", "Newest"]:
            query += " ORDER BY timestamp DESC"
        elif sort_by in ["Oldest First", "Oldest"]:
            query += " ORDER BY timestamp ASC"
        elif sort_by == "Steps (High-Low)":
            query += " ORDER BY steps DESC"
            
        c.execute(query, params)
        return c.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        return []
    finally:
        conn.close()

def get_all_models() -> List[str]:
    """Returns a list of all unique model names currently in the DB."""
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT model FROM images")
        return [r[0] for r in c.fetchall() if r[0]]
    finally:
        conn.close()

# --- CHARACTER OPERATIONS ---

# --- CHARACTER OPERATIONS ---

def add_character(name: str, description: str, trigger_words: str, preview_path: str = "", notes: str = "", default_lora: str = "None", lora_scale: float = 0.8) -> bool:
    """Adds a new character to the registry including LoRA settings."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO characters (name, description, trigger_words, preview_path, notes, default_lora, lora_scale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, trigger_words, preview_path, notes, default_lora, lora_scale))
        logger.info(f"Added character: {name}")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Character '{name}' already exists.")
        return False
    except Exception as e:
        logger.error(f"Error adding character: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()

def get_characters() -> List[Dict[str, Any]]:
    """Returns all characters as a list of dictionaries."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        # Ensure we select all columns, including new ones
        c.execute("SELECT * FROM characters ORDER BY name ASC")
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()

def delete_character(char_id: int) -> bool:
    """Deletes a character by ID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute("DELETE FROM characters WHERE id = ?", (char_id,))
        return True
    finally:
        if 'conn' in locals(): conn.close()

def update_character(char_id: int, name: str, description: str, trigger_words: str, preview_path: str, notes: str, default_lora: str, lora_scale: float) -> bool:
    """Updates an existing character."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute('''
                UPDATE characters 
                SET name=?, description=?, trigger_words=?, preview_path=?, notes=?, default_lora=?, lora_scale=?
                WHERE id=?
            ''', (name, description, trigger_words, preview_path, notes, default_lora, lora_scale, char_id))
        return True
    except Exception as e:
        logger.error(f"Error updating character: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()

# --- PRESET OPERATIONS ---

def add_preset(name: str, model: str, lora: str, lora_scale: float, steps: int, cfg: float, prompt: str, neg: str) -> bool:
    """Adds a new generation preset."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO presets (name, model, lora, lora_scale, steps, cfg, prompt_template, negative_prompt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, model, lora, lora_scale, steps, cfg, prompt, neg))
        logger.info(f"Added preset: {name}")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Preset '{name}' already exists.")
        return False
    finally:
        if 'conn' in locals(): conn.close()

def get_presets() -> List[Dict[str, Any]]:
    """Returns all presets as a list of dictionaries."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM presets ORDER BY name ASC")
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()

def delete_preset(preset_id: int) -> bool:
    """Deletes a preset by ID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
        return True
    finally:
        if 'conn' in locals(): conn.close()

# --- UTILS ---

def scan_and_import_folder(base_dir: str = "output_images") -> int:
    """Scans output folder for new PNGs."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    new_count = 0
    
    try:
        c = conn.cursor()
        c.execute("SELECT path FROM images")
        existing_paths = set(r[0] for r in c.fetchall())
        search_path = os.path.join(base_dir, "**", "*.png")
        found_files = glob.glob(search_path, recursive=True)
        
        with conn:
            for file_path in found_files:
                abs_path = os.path.abspath(file_path)
                if abs_path not in existing_paths:
                    try:
                        prompt = "Unknown"; neg = ""; steps = 0; cfg = 0.0; seed = "Random"; model = "Unknown"
                        with Image.open(abs_path) as img:
                            img.load()
                            params = img.info.get("parameters", "")
                            
                        if params:
                            lines = params.split('\n')
                            if len(lines) > 0: prompt = lines[0]
                            for line in lines:
                                if line.startswith("Negative prompt:"): neg = line.split(":", 1)[1].strip()
                                if "Steps:" in line:
                                    parts = line.split(", ")
                                    for p in parts:
                                        if "Steps:" in p: 
                                            try: steps = int(p.split(":")[1])
                                            except ValueError: pass
                                        if "CFG scale:" in p: 
                                            try: cfg = float(p.split(":")[1])
                                            except ValueError: pass
                                        if "Seed:" in p: seed = p.split(":")[1].strip()
                                        if "Model:" in p: model = p.split(":")[1].strip()

                        ts = datetime.fromtimestamp(os.path.getmtime(abs_path))
                        c.execute('''
                            INSERT INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (abs_path, prompt, neg, model, steps, cfg, seed, ts))
                        new_count += 1
                    except Exception as e:
                        logger.warning(f"Skipping corrupt file {file_path}: {e}")
        return new_count
    finally:
        conn.close()
