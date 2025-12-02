import sqlite3
import os
import sys

# Ensure we can find the DB relative to this script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "library.db")
IMAGES_ROOT = os.path.join(PROJECT_ROOT, "output_images")

def fix_database_paths():
    """
    Scans the database for broken file paths and attempts to fix them
    by locating the files in the current 'output_images' directory.
    Handles duplicate entries by removing the broken records.
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    print(f"🔧 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        # Fetch all images
        c.execute("SELECT id, path FROM images")
        rows = c.fetchall()
        
        updated_count = 0
        deleted_count = 0
        not_found_count = 0
        
        print(f"🔍 Scanning {len(rows)} records...")

        for row in rows:
            img_id = row['id']
            current_path = row['path']

            # 1. Check if file exists at current path (Healthy record)
            if os.path.exists(current_path):
                continue 

            # 2. Path is broken. Let's try to reconstruct it.
            try:
                # We assume structure is: .../output_images/YYYYMMDD/filename.png
                parts = current_path.split(os.sep)
                if len(parts) < 2:
                    continue
                
                filename = parts[-1]
                date_folder = parts[-2]
                
                # Construct new hypothetical path in current project
                new_path = os.path.join(IMAGES_ROOT, date_folder, filename)
                
                if os.path.exists(new_path):
                    # Found the file! Now try to update the DB.
                    try:
                        c.execute("UPDATE images SET path = ? WHERE id = ?", (new_path, img_id))
                        updated_count += 1
                        print(f"   ✅ Fixed: .../{date_folder}/{filename}")
                    except sqlite3.IntegrityError:
                        # UNIQUE constraint failed: The new path is already in the DB.
                        # This means 'img_id' is a duplicate of a healthy record.
                        # We can safely delete the broken duplicate.
                        c.execute("DELETE FROM images WHERE id = ?", (img_id,))
                        deleted_count += 1
                        print(f"   🗑️  Removed duplicate record for: {filename}")
                else:
                    print(f"   ⚠️  Lost: {filename} (Not found in {new_path})")
                    not_found_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error processing {current_path}: {e}")

        conn.commit()
        print("-" * 40)
        print(f"🎉 Done.")
        print(f"   - Fixed paths: {updated_count}")
        print(f"   - Removed duplicates: {deleted_count}")
        if not_found_count > 0:
            print(f"   - Unrecoverable (missing files): {not_found_count}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database_paths()
