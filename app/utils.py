import os
import sys
import base64
import glob
from PIL import Image
from typing import Dict, List, Optional

def is_kitty_compatible() -> bool:
    """
    Checks if the current terminal supports the Kitty graphics protocol
    (e.g., Kitty, Ghostty).
    """
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return "kitty" in term or "ghostty" in term_program

def print_image_preview(image_path: str):
    """
    Renders an image directly in the terminal using the Kitty graphics protocol.
    
    Args:
        image_path (str): The local path to the image file.
    """
    if not is_kitty_compatible():
        print(f"[Info] Terminal not Kitty-compatible. Image: {image_path}")
        return

    try:
        # Get absolute path and encode it to base64
        abs_path = os.path.abspath(image_path)
        
        # Check if file exists to prevent errors
        if not os.path.exists(abs_path):
            return

        with open(abs_path, "rb") as f:
            image_data = f.read()
            b64_data = base64.b64encode(image_data).decode('ascii')
        
        # Kitty escape sequence:
        # a=T (Transmit and Display), t=d (Direct), f=100 (PNG)
        # We send the data directly (t=d) instead of path to avoid permission issues in some envs
        sys.stdout.write(f"\x1b_Gf=100,a=T,t=d;{b64_data}\x1b\\")
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"[Warning] Image preview failed: {e}")

def get_image_metadata(image_path: str) -> Dict[str, str]:
    """
    Extracts metadata (PNG Info) from the generated image.
    Specifically looks for the 'parameters' key used by SD WebUI / Diffusers.
    """
    info = {}
    try:
        with Image.open(image_path) as img:
            img.load()  # Ensure image is loaded
            if img.info and 'parameters' in img.info:
                info['parameters'] = img.info['parameters']
            else:
                info['parameters'] = "No metadata found."
    except Exception as e:
        info['parameters'] = f"Error reading metadata: {e}"
    return info

def get_all_generated_images(base_dir: str = "output_images") -> List[str]:
    """
    Recursively finds all PNG images in the output directory, sorted by modification time (newest first).
    """
    if not os.path.exists(base_dir):
        return []
    
    # Use glob to find .png files recursively
    pattern = os.path.join(base_dir, "**", "*.png")
    files = glob.glob(pattern, recursive=True)
    
    # Sort by modification time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)
    return files

def find_images_by_prompt_content(search_text: str, base_dir: str = "output_images") -> List[str]:
    """
    Searches for images where the metadata parameters contain the search_text.
    Useful for finding images associated with a favorite prompt.
    """
    matches = []
    all_images = get_all_generated_images(base_dir)
    
    # Normalize search text slightly to improve hit rate
    search_clean = search_text.strip().lower()[:50] # Check first 50 chars for speed
    
    for img_path in all_images:
        meta = get_image_metadata(img_path)
        params = meta.get('parameters', '').lower()
        if search_clean in params:
            matches.append(img_path)
            
    return matches

def get_clean_path(path_input: str) -> str:
    """Removes quotes and whitespace from path strings."""
    return path_input.strip().strip('"').strip("'")

def get_file_list(directory: str, file_exts=('.safetensors', '.ckpt')) -> list:
    """
    Returns a sorted list of model files in a directory.
    """
    if not os.path.exists(directory):
        return []
    
    files = [f for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) 
             and not f.startswith('.')
             and f.lower().endswith(file_exts)]
    return sorted(files)
