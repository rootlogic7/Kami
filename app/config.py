import os
import json
import logging
from typing import List, Dict, Any, Optional

# Constants
FAV_FILE = "favorites.json"
SESSION_FILE = "session_config.json"

logger = logging.getLogger(__name__)

# --- New Styles Preset Library ---
# These styles act as prefixes/suffixes to the user prompt
STYLES = {
    "None": {
        "name": "No Style",
        "pos": "",
        "neg": ""
    },
    "Cinematic": {
        "name": "Cinematic (Movies)",
        "pos": "cinematic shot, dynamic lighting, 70mm, depth of field, color graded, ",
        "neg": "cartoon, illustration, flat, 3d render, "
    },
    "Anime": {
        "name": "Anime (Modern)",
        "pos": "anime style, key visual, vibrant, studio ghibli, makoto shinkai, ",
        "neg": "photo, realistic, 3d, "
    },
    "Photographic": {
        "name": "Photorealistic",
        "pos": "raw photo, 8k uhd, dslr, soft lighting, high quality, film grain, Fujifilm XT3, ",
        "neg": "drawing, painting, illustration, glitch, deformed, "
    },
    "Digital Art": {
        "name": "Digital Art",
        "pos": "concept art, digital painting, mystery, elegant, highly detailed, artstation, ",
        "neg": "photo, realistic, grain, "
    },
    "Pixel Art": {
        "name": "Pixel Art",
        "pos": "pixel art, 16-bit, retro game, dithering, ",
        "neg": "blur, vector, smooth, realistic, "
    }
}

class SessionConfig:
    """
    Manages the session state, configuration persistence, and favorites.
    """
    def __init__(self):
        # Default settings
        self.prompt = ""
        self.neg_prompt = "ugly, blurry, low quality, distortion, grid"
        self.steps = 30
        self.guidance = 7.0
        self.seed = None
        self.width = 1024
        self.height = 1024
        self.model_path = "stabilityai/stable-diffusion-xl-base-1.0"
        self.use_refiner = False
        self.lora_path = None
        self.lora_scale = 0.8
        
        # New Settings
        self.current_style = "None" # Key from STYLES dict
        
        # FreeU Settings (s1, s2, b1, b2) - Default SDXL parameters
        self.use_freeu = False
        self.freeu_args = {"s1": 0.9, "s2": 0.2, "b1": 1.3, "b2": 1.4}
        
        # Pony Diffusion specific settings
        self.pony_mode = False 
        self.pony_prefix = "score_9, score_8_up, score_7_up, score_6_up, source_anime, "
        self.pony_neg = "score_4, score_5, score_6, source_pony, source_furry, "
        
        # Load data
        self.favourites = self._load_favorites()
        self._load_session_state()

    def _load_favorites(self) -> List[Dict[str, str]]:
        """Loads favorites from JSON, migrating old string-only formats if necessary."""
        if os.path.exists(FAV_FILE):
            try:
                with open(FAV_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    migrated = []
                    for item in data:
                        if isinstance(item, str):
                            migrated.append({
                                "name": item[:25].strip() + "...", 
                                "prompt": item
                            })
                        elif isinstance(item, dict) and "prompt" in item:
                            if "name" not in item: item["name"] = "Untitled"
                            migrated.append(item)
                    return migrated
            except json.JSONDecodeError:
                logger.error(f"Failed to decode {FAV_FILE}. Starting with empty favorites.")
                return []
        return []

    def save_favorites(self):
        """Saves current favorites to JSON."""
        try:
            with open(FAV_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.favourites, f, indent=4, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error saving favorites: {e}")

    def _load_session_state(self):
        """Restores the last session configuration."""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.steps = data.get("steps", self.steps)
                    self.guidance = data.get("guidance", self.guidance)
                    self.neg_prompt = data.get("neg_prompt", self.neg_prompt)
                    self.model_path = data.get("model_path", self.model_path)
                    self.lora_path = data.get("lora_path", self.lora_path)
                    self.lora_scale = data.get("lora_scale", self.lora_scale)
                    self.use_refiner = data.get("use_refiner", self.use_refiner)
                    self.pony_mode = data.get("pony_mode", self.pony_mode)
                    
                    # Load new fields
                    self.current_style = data.get("current_style", self.current_style)
                    self.use_freeu = data.get("use_freeu", self.use_freeu)
                    if "freeu_args" in data:
                        self.freeu_args = data["freeu_args"]

            except Exception as e:
                logger.warning(f"Could not load session config: {e}")

    def save_session_state(self):
        """Persists the current configuration to a JSON file."""
        data = {
            "steps": self.steps,
            "guidance": self.guidance,
            "neg_prompt": self.neg_prompt,
            "model_path": self.model_path,
            "lora_path": self.lora_path,
            "lora_scale": self.lora_scale,
            "use_refiner": self.use_refiner,
            "pony_mode": self.pony_mode,
            "current_style": self.current_style,
            "use_freeu": self.use_freeu,
            "freeu_args": self.freeu_args
        }
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logger.error(f"Error saving session state: {e}")
