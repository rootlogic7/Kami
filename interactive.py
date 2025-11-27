import os
import sys
import shlex
import json

from app.engine import T2IEngine

CHECKPOINTS_DIR = "models/checkpoints"
LORAS_DIR = "models/loras"
FAV_FILE = "favorites.json"

class SessionConfig:
    """Hält den aktuellen Status der Sitzung."""
    def __init__(self):
        self.prompt = ""
        self.neg_prompt = "ugly, blurry, low quality, distortion, grid"
        self.steps = 30
        self.guidance = 7.0
        self.seed = None  # None = Random
        self.width = 1024
        self.height = 1024
        self.model_path = "stabilityai/stable-diffusion-xl-base-1.0"
        self.use_refiner = False
        self.lora_path = None
        self.lora_scale = 0.8
        self.favourites = load_favorites()
        
        # Pony/Illustrious
        self.pony_mode = False 
        self.pony_prefix = "score_9, score_8_up, score_7_up, score_6_up, source_anime, "
        self.pony_neg = "score_4, score_5, score_6, source_pony, source_furry, "

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(config):
    clear_screen()
    print("================================================================")
    print("       🚀 PYTHON SDXL GENERATOR - INTERACTIVE SESSION")
    print("================================================================")

    current_path = config.model_path
    
    if current_path.lower().endswith((".safetensors", ".ckpt")):
        model_name = os.path.basename(current_path)
    else:
        model_name = current_path
        
    if len(model_name) > 60:
        model_name = model_name[:27] + "..." + model_name[-27:]


    lora_name = os.path.basename(config.lora_path) if config.lora_path else 'None'
    
    print(f" [M] Model:     {model_name}")
    print(f" [L] LoRA:      {lora_name} (Scale: {config.lora_scale})")
    print(f" [R] Refiner:   {'ON' if config.use_refiner else 'OFF'}")
    print(f" [P] Pony Mode: {'🦄 ON' if config.pony_mode else 'OFF'} (Auto-Prefixes)")

    print("----------------------------------------------------------------")
    print(f" [1] Steps:     {config.steps}")
    print(f" [2] Guidance:  {config.guidance}")
    print(f" [3] Neg:       {config.neg_prompt[:50]}...")
    print("================================================================")
    print(" [ENTER] Prompt eingeben & Generieren")
    print(f" [F] Favoriten ({len(config.favourites)}) | [S] Einstellungen ändern | [Q] Beenden")
    print("================================================================")

def get_clean_path(path_input):
    return path_input.strip().strip('"').strip("'")


def get_file_list(directory, file_exts=('.safetensors', '.ckpt')):
    if not os.path.exists(directory):
        return []
    
    files = [f for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) 
             and not f.startswith('.')
             and f.lower().endswith(file_exts)]
    return sorted(files)

def select_file_from_list(file_type, current_path, directory, hf_allowed=False):
    print(f"\n--- {file_type} Auswahl ---")
    file_list = get_file_list(directory)
    
    current_name = os.path.basename(current_path) if current_path else 'None'
    print(f"[0] Aktuell Beibehalten: {current_name}")
    if hf_allowed:
        print(f"[ID] HuggingFace ID verwenden")
    
    if file_list:
        print(f"\nLokale Dateien in './{directory}':")
        for i, filename in enumerate(file_list, 1):
            print(f"[{i}] {filename}")
    else:
        print(f"\nKeine lokalen Dateien im Verzeichnis './{directory}' gefunden.")
    
    print("\n[A] Manuellen Pfad/Text eingeben")
    if file_type == "LoRA":
         print("[X] LoRA deaktivieren")
         
    choice = input(f"Wahl (Nummer, A, X, ID oder [ENTER] für Beibehalten): ").strip()
    
    if not choice:
        return current_path

    choice_lower = choice.lower()

    if choice_lower == 'x' and file_type == "LoRA":
        return None

def load_favorites():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warnung: {FAV_FILE} ist beschädigt. Starte mit leerer Liste.")
            return []
    return []

def save_favorites(favorites):
    try:
        with open(FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Fehler beim Speichern der Favoriten: {e}")    


def main():
    config = SessionConfig()
    engine = None
    
    while True:
        print_header(config)
        choice = input("\nBefehl oder [ENTER] für Generierung: ").strip().lower()

        if choice == 'q':
            print("👋 Bis bald!")
            break

        # --- MODEL SETTINGS ---
        elif choice == 'm':
            new_path = select_file_from_list(
                file_type="Model", 
                current_path=config.model_path, 
                directory=CHECKPOINTS_DIR, 
                hf_allowed=True
            )
            
            if new_path and new_path != config.model_path:
                print(f"Modellpfad aktualisiert auf: {new_path}")
                
                if engine is not None:
                    engine.cleanup()
                
                config.model_path = new_path
                engine = None
        
        elif choice == 'l':
            new_lora_path = select_file_from_list(
                file_type="LoRA", 
                current_path=config.lora_path, 
                directory=LORAS_DIR, 
                hf_allowed=False
            )
            
            if new_lora_path != config.lora_path:
                config.lora_path = new_lora_path
                
                if new_lora_path is not None:
                    scale = input(f"LoRA Scale (0.1 - 1.0) [Aktuell {config.lora_scale}]: ")
                    try:
                        config.lora_scale = float(scale) if scale else config.lora_scale
                    except ValueError:
                        print("Ungültige Skala. Behalte aktuellen Wert bei.")

        elif choice == 'r':
            config.use_refiner = not config.use_refiner
        
        elif choice == 'p':
            config.pony_mode = not config.pony_mode
            if config.pony_mode:
                print("🦄 Pony Modus aktiviert! Score-Tags werden automatisch hinzugefügt.")
                if "score_4" not in config.neg_prompt:
                    config.neg_prompt = config.pony_neg + config.neg_prompt
            else:
                 print("🦄 Pony Modus deaktiviert.")

        elif choice == 'f':
            print("\n--- Favoriten Prompts ---")
            if not config.favourites:
                print("Keine Favoriten gespeichert.")
                input("Drücke Enter...")
                continue
            
            for i, fav in enumerate(config.favourites, 1):
                print(f"[{i}] {fav[:80]}{'...' if len(fav) > 80 else ''}")
                
            print("\n[D] Prompt löschen | [ENTER] Abbrechen")
            fav_choice = input("Wähle Nummer zum Laden oder D zum Löschen: ").strip()
            
            if not fav_choice:
                continue

            if fav_choice.lower() == 'd':
                try:
                    del_index = int(input("Nummer des zu löschenden Prompts: ")) - 1
                    if 0 <= del_index < len(config.favourites):
                        deleted_prompt = config.favourites.pop(del_index)
                        save_favorites(config.favourites)
                        print(f"Favorit gelöscht: {deleted_prompt[:40]}...")
                    else:
                        print("Ungültige Nummer.")
                except ValueError:
                    print("Ungültige Eingabe.")
                input("Drücke Enter...")
                continue
                
            try:
                load_index = int(fav_choice) - 1
                if 0 <= load_index < len(config.favourites):
                    config.prompt = config.favourites[load_index]
                    print(f"✅ Favorit geladen. Prompt: {config.prompt[:50]}...")
                else:
                    print("Ungültige Nummer.")
            except ValueError:
                print("Ungültige Eingabe.")
            input("Drücke Enter...")

        elif choice == '1':
            try:
                val = int(input(f"Neue Steps (Aktuell {config.steps}): "))
                config.steps = val
            except ValueError: pass
        
        elif choice == '2':
            try:
                val = float(input(f"Neue Guidance (Aktuell {config.guidance}): "))
                config.guidance = val
            except ValueError: pass
        
        elif choice == '3':
            val = input(f"Neuer Negative Prompt (Aktuell: {config.neg_prompt}): ")
            if val: config.neg_prompt = val

        elif choice == '':
            prompt_input = input("\n✨ PROMPT: ")
            
            if not prompt_input:
                continue

            if engine is None:
                try:
                    engine = T2IEngine(base_model_id=config.model_path)
                except Exception as e:
                    print(f"❌ Fehler beim Laden des Modells: {e}")
                    input("Drücke Enter um fortzufahren...")
                    continue

            final_prompt = prompt_input
            if config.pony_mode:
                final_prompt = config.pony_prefix + prompt_input
            
            print(f"\nGeneriere: {final_prompt[:80]}...")
            
            try:
                saved_path = engine.generate(
                    prompt=final_prompt,
                    negative_prompt=config.neg_prompt,
                    steps=config.steps,
                    guidance_scale=config.guidance,
                    seed=config.seed, 
                    use_refiner=config.use_refiner,
                    lora_path=config.lora_path,
                    lora_scale=config.lora_scale
                )
                
                if os.name == 'nt':
                    os.startfile(saved_path)
                elif sys.platform == 'darwin':
                    os.system(f'open "{saved_path}"')

                save_fav = input("Prompt als Favorit speichern? [y/N]: ").strip().lower()
                if save_fav == 'y':
                    if final_prompt not in config.favourites:
                        config.favourites.append(final_prompt)
                        save_favorites(config.favourites)
                        print("⭐ Prompt gespeichert!")
                    else:
                        print("Prompt ist bereits gespeichert.")
                
                input("\n✅ Fertig! Drücke [ENTER] für das Menü...")

            except Exception as e:
                print(f"\n❌ Fehler bei der Generierung: {e}")
                import traceback
                traceback.print_exc()
                input("Drücke Enter...")
        
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch.")
