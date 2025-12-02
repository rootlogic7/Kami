import os
import json
import logging
from typing import List, Dict, Any, Optional

# Constants for file paths
FAV_FILE = "favorites.json"
SESSION_FILE = "session_config.json"
STYLES_FILE = "styles.json"

logger = logging.getLogger(__name__)

def load_styles() -> Dict[str, Dict[str, str]]:
    """
    Loads style presets from the JSON file.
    Returns a default dictionary if the file is missing or corrupt.
    
    Returns:
        Dict[str, Dict[str, str]]: A dictionary containing style prompts.
    """
    defaults = {
        "None": {"name": "No Style", "pos": "", "neg": ""}
    }
    
    if os.path.exists(STYLES_FILE):
        try:
            with open(STYLES_FILE, 'r', encoding='utf-8') as f:
                user_styles = json.load(f)
                # Merge defaults with user styles; user styles take precedence
                return {**defaults, **user_styles}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {STYLES_FILE}: {e}")
            return defaults
        except Exception as e:
            logger.error(f"Unexpected error loading styles: {e}")
            return defaults
            
    return defaults

# Global variable to be imported by other modules
STYLES = load_styles()

class SessionConfig:
    """
    Manages the application session state, including configuration persistence 
    and favorite prompts list.
    """
    def __init__(self):
        # Default generation parameters
        self.prompt: str = ""
        self.neg_prompt: str = "ugly, blurry, low quality, distortion, grid"
        self.steps: int = 30
        self.guidance: float = 7.0
        self.seed: Optional[int] = None
        self.width: int = 1024
        self.height: int = 1024
        
        # Model configuration
        self.model_path: str = "stabilityai/stable-diffusion-xl-base-1.0"
        self.use_refiner: bool = False
        self.lora_path: Optional[str] = None
        self.lora_scale: float = 0.8
        
        # Style configuration
        self.current_style: str = "None"
        
        # Advanced settings (FreeU, Pony)
        self.use_freeu: bool = False
        self.freeu_args: Dict[str, float] = {"s1": 0.9, "s2": 0.2, "b1": 1.3, "b2": 1.4}
        
        self.pony_mode: bool = False 
        self.pony_prefix: str = "score_9, score_8_up, score_7_up, score_6_up, source_anime, "
        self.pony_neg: str = "score_4, score_5, score_6, source_pony, source_furry, "
        
        # Data persistence
        self.favourites: List[Dict[str, str]] = self._load_favorites()
        self._load_session_state()

    def _load_favorites(self) -> List[Dict[str, str]]:
        """
        Loads favorite prompts from disk. Handles migration from legacy formats (list of strings).
        """
        if not os.path.exists(FAV_FILE):
            return []

        try:
            with open(FAV_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                migrated = []
                
                for item in data:
                    # Migration: Handle legacy string-only favorites
                    if isinstance(item, str):
                        migrated.append({
                            "name": item[:25].strip() + "...", 
                            "prompt": item,
                            "negative_prompt": "" 
                        })
                    # Handle dict format
                    elif isinstance(item, dict) and "prompt" in item:
                        if "name" not in item: 
                            item["name"] = "Untitled"
                        if "negative_prompt" not in item: 
                            item["negative_prompt"] = ""
                        migrated.append(item)
                        
                return migrated
                
        except json.JSONDecodeError:
            logger.error(f"Failed to decode {FAV_FILE}. Returning empty list.")
            return []
        except Exception as e:
            logger.error(f"Error loading favorites: {e}")
            return []

    def save_favorites(self) -> None:
        """Saves the current list of favorites to disk."""
        try:
            with open(FAV_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.favourites, f, indent=4, ensure_ascii=False)
            logger.debug("Favorites saved successfully.")
        except IOError as e:
            logger.error(f"Error saving favorites: {e}")

    def _load_session_state(self) -> None:
        """Loads the last used session configuration from disk."""
        if not os.path.exists(SESSION_FILE):
            return

        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Update attributes if they exist in the loaded data
                self.steps = data.get("steps", self.steps)
                self.guidance = data.get("guidance", self.guidance)
                self.neg_prompt = data.get("neg_prompt", self.neg_prompt)
                self.model_path = data.get("model_path", self.model_path)
                self.lora_path = data.get("lora_path", self.lora_path)
                self.lora_scale = data.get("lora_scale", self.lora_scale)
                self.use_refiner = data.get("use_refiner", self.use_refiner)
                self.pony_mode = data.get("pony_mode", self.pony_mode)
                self.current_style = data.get("current_style", self.current_style)
                self.use_freeu = data.get("use_freeu", self.use_freeu)
                
                if "freeu_args" in data:
                    self.freeu_args = data["freeu_args"]
                    
        except Exception as e:
            logger.warning(f"Could not load session config: {e}")

    def save_session_state(self) -> None:
        """Persists the current session configuration to disk."""
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
