import sqlite3
import os
import glob
from datetime import datetime
from PIL import Image

DB_FILE = "library.db"

def init_db():
    """Initializes the SQLite database table."""
    conn = sqlite3.connect(DB_FILE)
    try:
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
    finally:
        conn.close()

def add_image_record(path, prompt, neg, model, steps, cfg, seed):
    """Inserts a new image record into the database."""
    try:
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        try:
            with conn:
                c = conn.cursor()
                c.execute('''
                    INSERT OR IGNORE INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (abs_path, prompt, neg, model, steps, cfg, str(seed), datetime.now()))
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB Error] Could not add record: {e}")

def delete_image_record(path):
    """Deletes an image record from the database."""
    try:
        # Pfad normalisieren, um sicherzugehen, dass er mit dem DB-Eintrag übereinstimmt
        abs_path = os.path.abspath(path)
        conn = sqlite3.connect(DB_FILE)
        try:
            with conn:
                c = conn.cursor()
                c.execute("DELETE FROM images WHERE path = ?", (abs_path,))
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB Error] Could not delete record: {e}")
        return False

def get_filtered_images(search_text="", sort_by="Newest", model_filter="All"):
    """Queries the database with filters."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        
        query = "SELECT * FROM images WHERE 1=1"
        params = []
        
        # 1. Search Filter (Prompt, Seed, Model)
        if search_text:
            query += " AND (prompt LIKE ? OR seed LIKE ? OR model LIKE ?)"
            term = f"%{search_text}%"
            params.extend([term, term, term])
            
        # 2. Model Filter
        if model_filter and model_filter != "All Models" and model_filter != "All":
            query += " AND model LIKE ?"
            params.append(f"%{model_filter}%")
            
        # 3. Sorting
        if sort_by == "Newest First" or sort_by == "Newest":
            query += " ORDER BY timestamp DESC"
        elif sort_by == "Oldest First" or sort_by == "Oldest":
            query += " ORDER BY timestamp ASC"
        elif sort_by == "Steps (High-Low)":
            query += " ORDER BY steps DESC"
            
        c.execute(query, params)
        rows = c.fetchall()
        return rows
    finally:
        conn.close()

def get_all_models():
    """Returns a list of all unique model names in the DB."""
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT model FROM images")
        rows = c.fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()

def scan_and_import_folder(base_dir="output_images"):
    """
    Scans the output folder for PNGs not yet in the DB and imports them.
    """
    init_db()
    
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT path FROM images")
        existing_paths = set(r[0] for r in c.fetchall())
        
        search_path = os.path.join(base_dir, "**", "*.png")
        found_files = glob.glob(search_path, recursive=True)
        
        new_count = 0
        
        with conn:
            for file_path in found_files:
                abs_path = os.path.abspath(file_path)
                if abs_path not in existing_paths:
                    try:
                        with Image.open(abs_path) as img:
                            img.load()
                            params = img.info.get("parameters", "")
                            
                        prompt = "Unknown"
                        neg = ""
                        steps = 0
                        cfg = 0.0
                        seed = "Random"
                        model = "Unknown"
                        
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
                                            except: pass
                                        if "CFG scale:" in p: 
                                            try: cfg = float(p.split(":")[1])
                                            except: pass
                                        if "Seed:" in p: seed = p.split(":")[1].strip()
                                        if "Model:" in p: model = p.split(":")[1].strip()

                        c.execute('''
                            INSERT INTO images (path, prompt, negative_prompt, model, steps, cfg, seed, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (abs_path, prompt, neg, model, steps, cfg, seed, datetime.fromtimestamp(os.path.getmtime(abs_path))))
                        new_count += 1
                    except Exception as e:
                        print(f"Skipping {file_path}: {e}")
        return new_count
    finally:
        conn.close()
