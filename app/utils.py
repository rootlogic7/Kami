import os
import sys
import base64

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
        return

    try:
        # Get absolute path and encode it to base64
        abs_path = os.path.abspath(image_path)
        b64_path = base64.b64encode(abs_path.encode('utf-8')).decode('ascii')
        
        # Kitty escape sequence:
        # a=T (Transmit and Display), t=f (Type=File), f=100 (PNG/Auto detection)
        sys.stdout.write(f"\x1b_Gf=100,a=T,t=f;{b64_path}\x1b\\")
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        # We use standard print here to avoid circular dependency with rich console
        print(f"[Warning] Image preview failed: {e}")

def get_clean_path(path_input: str) -> str:
    """Removes quotes and whitespace from path strings."""
    return path_input.strip().strip('"').strip("'")

def get_file_list(directory: str, file_exts=('.safetensors', '.ckpt')) -> list:
    """
    Returns a sorted list of model files in a directory.
    
    Args:
        directory (str): Path to the directory.
        file_exts (tuple): Allowed file extensions.
    """
    if not os.path.exists(directory):
        return []
    
    files = [f for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) 
             and not f.startswith('.')
             and f.lower().endswith(file_exts)]
    return sorted(files)
