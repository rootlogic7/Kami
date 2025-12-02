import sqlite3
import os
import glob
import logging
from datetime import datetime
from typing import List, Optional, Any, Tuple
from PIL import Image

# Initialize logger
logger = logging.getLogger(__name__)

DB_FILE = "library.db"

def init_db() -> None:
    """
    Initializes the SQLite database table if it does not exist.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
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
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def add_image_record(
    path: str, 
    prompt: str, 
    neg: str, 
    model: str, 
    steps: int, 
    cfg: float, 
    seed: str | int
) -> None:
    """
    Inserts a new image record into the database.
    
    Args:
        path: File path of the image.
        prompt: The positive prompt used.
        neg: The negative prompt used.
        model: The model name.
        steps: Number of inference steps.
        cfg: Guidance scale.
        seed: The seed value (stored as string).
    """
    try:
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            # We explicitly use 'negative_prompt' column but keep 'neg' argument 
            # to match current function calls from engine.py
            c.execute('''
                INSERT OR IGNORE INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (abs_path, prompt, neg, model, steps, cfg, str(seed), datetime.now()))
            
        logger.debug(f"Added record for: {abs_path}")
            
    except sqlite3.Error as e:
        logger.error(f"Could not add record to DB: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in add_image_record: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def delete_image_record(path: str) -> bool:
    """
    Deletes an image record from the database based on its file path.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Normalize path to match DB entry
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        with conn:
            c = conn.cursor()
            c.execute("DELETE FROM images WHERE path = ?", (abs_path,))
            
        logger.info(f"Deleted record for: {path}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Could not delete record: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_filtered_images(
    search_text: str = "", 
    sort_by: str = "Newest", 
    model_filter: str = "All"
) -> List[sqlite3.Row]:
    """
    Queries the database with search filters and sorting.
    
    Returns:
        List of sqlite3.Row objects.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        
        query = "SELECT * FROM images WHERE 1=1"
        params: List[Any] = []
        
        # 1. Search Filter (Prompt, Seed, Model)
        if search_text:
            query += " AND (prompt LIKE ? OR seed LIKE ? OR model LIKE ?)"
            term = f"%{search_text}%"
            params.extend([term, term, term])
            
        # 2. Model Filter
        # Handles "All Models" from UI or "All" default
        if model_filter and model_filter not in ["All Models", "All"]:
            query += " AND model LIKE ?"
            params.append(f"%{model_filter}%")
            
        # 3. Sorting logic
        if sort_by in ["Newest First", "Newest"]:
            query += " ORDER BY timestamp DESC"
        elif sort_by in ["Oldest First", "Oldest"]:
            query += " ORDER BY timestamp ASC"
        elif sort_by == "Steps (High-Low)":
            query += " ORDER BY steps DESC"
            
        c.execute(query, params)
        rows = c.fetchall()
        return rows
        
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        return []
    finally:
        conn.close()

def get_all_models() -> List[str]:
    """
    Returns a list of all unique model names currently in the DB.
    """
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT model FROM images")
        rows = c.fetchall()
        return [r[0] for r in rows if r[0]]
    except sqlite3.Error as e:
        logger.error(f"Error fetching models: {e}")
        return []
    finally:
        conn.close()

def scan_and_import_folder(base_dir: str = "output_images") -> int:
    """
    Scans the output folder for PNG files not yet in the DB and imports them.
    Reads generation parameters from PNG metadata.
    
    Returns:
        int: The number of new images imported.
    """
    init_db()
    
    conn = sqlite3.connect(DB_FILE)
    new_count = 0
    
    try:
        c = conn.cursor()
        c.execute("SELECT path FROM images")
        # Use a set for O(1) lookups
        existing_paths = set(r[0] for r in c.fetchall())
        
        # Recursive glob search
        search_path = os.path.join(base_dir, "**", "*.png")
        found_files = glob.glob(search_path, recursive=True)
        
        with conn:
            for file_path in found_files:
                abs_path = os.path.abspath(file_path)
                
                if abs_path not in existing_paths:
                    try:
                        # Extract metadata safely
                        prompt = "Unknown"
                        neg = ""
                        steps = 0
                        cfg = 0.0
                        seed = "Random"
                        model = "Unknown"
                        
                        with Image.open(abs_path) as img:
                            img.load()
                            params = img.info.get("parameters", "")
                            
                        if params:
                            lines = params.split('\n')
                            if len(lines) > 0:
                                prompt = lines[0]
                            
                            for line in lines:
                                if line.startswith("Negative prompt:"):
                                    neg = line.split(":", 1)[1].strip()
                                if "Steps:" in line:
                                    parts = line.split(", ")
                                    for p in parts:
                                        if "Steps:" in p: 
                                            try: steps = int(p.split(":")[1])
                                            except ValueError: pass
                                        if "CFG scale:" in p: 
                                            try: cfg = float(p.split(":")[1])
                                            except ValueError: pass
                                        if "Seed:" in p: 
                                            seed = p.split(":")[1].strip()
                                        if "Model:" in p: 
                                            model = p.split(":")[1].strip()

                        # Get file creation time as fallback timestamp
                        ts = datetime.fromtimestamp(os.path.getmtime(abs_path))

                        c.execute('''
                            INSERT INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (abs_path, prompt, neg, model, steps, cfg, seed, ts))
                        
                        new_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Skipping corrupt or unreadable file {file_path}: {e}")
                        
        if new_count > 0:
            logger.info(f"Imported {new_count} new images.")
            
        return new_count
        
    except sqlite3.Error as e:
        logger.error(f"Error during folder scan: {e}")
        return 0
    finally:
        conn.close()
