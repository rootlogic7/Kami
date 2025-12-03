import sqlite3
import os
import sys

# Path setup
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "library.db")

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    print(f"🔧 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # Check existing columns in 'characters' table
        c.execute("PRAGMA table_info(characters)")
        columns = [row[1] for row in c.fetchall()]
        
        # 1. Add default_lora column
        if "default_lora" not in columns:
            print("   ➕ Adding column: default_lora")
            c.execute("ALTER TABLE characters ADD COLUMN default_lora TEXT DEFAULT 'None'")
        else:
            print("   ✅ Column 'default_lora' already exists.")

        # 2. Add lora_scale column
        if "lora_scale" not in columns:
            print("   ➕ Adding column: lora_scale")
            c.execute("ALTER TABLE characters ADD COLUMN lora_scale REAL DEFAULT 0.8")
        else:
            print("   ✅ Column 'lora_scale' already exists.")

        conn.commit()
        print("🎉 Migration complete.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
