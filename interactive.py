import os
import sys
import json
import base64
from app.engine import T2IEngine

# Rich Imports für das UI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm

console = Console()

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

def is_kitty_compatible():
    """Prüft auf Kitty oder Ghostty Terminal."""
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return "kitty" in term or "ghostty" in term_program

def print_image_preview(image_path):
    """Zeigt das Bild direkt im Terminal an (Kitty Protocol)."""
    if not is_kitty_compatible():
        return

    try:
        # Wir nutzen das 'Local File' Feature des Kitty Protokolls (t=f)
        # Pfad muss base64 codiert werden
        abs_path = os.path.abspath(image_path)
        b64_path = base64.b64encode(abs_path.encode('utf-8')).decode('ascii')
        
        # Escape Code: 
        # a=T (Transmit and Display), t=f (Type=File), f=100 (PNG/Auto detection)
        sys.stdout.write(f"\x1b_Gf=100,a=T,t=f;{b64_path}\x1b\\")
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        console.print(f"[yellow]Vorschau fehlgeschlagen: {e}[/yellow]")

def print_header(config):
    clear_screen()
    
    # Header Panel
    console.print(Panel("[bold magenta]🚀 PYTHON SDXL GENERATOR[/bold magenta] - [dim]Interactive Session[/dim]", box=box.DOUBLE))

    # Info Table erstellen
    table = Table(show_header=False, box=box.ROUNDED, expand=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="bold white")
    table.add_column("Key", style="dim green", justify="right")

    # Modell Name kürzen
    current_path = config.model_path
    if current_path.lower().endswith((".safetensors", ".ckpt")):
        model_name = os.path.basename(current_path)
    else:
        model_name = current_path
    if len(model_name) > 40: model_name = model_name[:17] + "..." + model_name[-20:]

    lora_name = os.path.basename(config.lora_path) if config.lora_path else 'None'

    # Zeilen hinzufügen
    table.add_row("Model", model_name, "[M]")
    table.add_row("LoRA", f"{lora_name} (Scale: {config.lora_scale})", "[L]")
    table.add_row("Refiner", "ON" if config.use_refiner else "OFF", "[R]")
    table.add_row("Pony Mode", "🦄 ON" if config.pony_mode else "OFF", "[P]")
    table.add_section()
    table.add_row("Steps", str(config.steps), "[1]")
    table.add_row("Guidance", str(config.guidance), "[2]")
    table.add_row("Neg Prompt", f"{config.neg_prompt[:60]}...", "[3]")
    
    console.print(table)
    
    # Aktueller Prompt Indikator (Falls geladen)
    if config.prompt:
        console.print(f"[dim]Aktueller Prompt: {config.prompt[:90]}...[/dim]", style="italic grey50")

    # Footer Actions
    actions = "[bold white][ENTER][/bold white] Generate | [bold white][F][/bold white] Favorites | [bold white][Q][/bold white] Quit"
    console.print(Panel(actions, box=box.MINIMAL, style="grey50"))

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
    console.print(f"\n[bold cyan]--- {file_type} Auswahl ---[/bold cyan]")
    file_list = get_file_list(directory)
    
    current_name = os.path.basename(current_path) if current_path else 'None'
    
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Filename", style="white")
    
    table.add_row("0", f"Beibehalten: {current_name}")
    
    for i, filename in enumerate(file_list, 1):
        table.add_row(str(i), filename)
        
    console.print(table)
    
    if not file_list:
        console.print(f"[yellow]Keine lokalen Dateien in './{directory}' gefunden.[/yellow]")

    print("\n[A] Manuellen Pfad eingeben")
    if hf_allowed: print("[ID] HuggingFace ID verwenden")
    if file_type == "LoRA": print("[X] LoRA deaktivieren")
    
    choice = Prompt.ask("Wahl", default="0")
    
    choice_lower = choice.lower()

    if choice_lower == 'x' and file_type == "LoRA":
        return None
    
    if choice.isdigit():
        idx = int(choice)
        if idx == 0:
            return current_path
        elif 1 <= idx <= len(file_list):
            return os.path.join(directory, file_list[idx-1])
        else:
            console.print("[red]Ungültige Nummer.[/red]")
            return current_path

    if hf_allowed and choice_lower == 'id':
        hf_id = Prompt.ask("HuggingFace ID")
        if hf_id: return hf_id
        return current_path

    if choice_lower == 'a':
        raw_path = Prompt.ask("Pfad")
        return get_clean_path(raw_path)

    return current_path

def load_favorites():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_favorites(favorites):
    try:
        with open(FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=4, ensure_ascii=False)
    except IOError as e:
        console.print(f"[red]Fehler beim Speichern: {e}[/red]")

def main():
    config = SessionConfig()
    engine = None
    
    while True:
        print_header(config)
        choice = console.input("\n[bold green]Befehl[/bold green] oder [bold white][ENTER][/bold white] für Generierung: ").strip().lower()

        if choice == 'q':
            console.print("[bold magenta]👋 Bis bald![/bold magenta]")
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
                console.print(f"[green]Modellpfad aktualisiert auf: {new_path}[/green]")
                if engine is not None: engine.cleanup()
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
                    config.lora_scale = FloatPrompt.ask("LoRA Scale", default=config.lora_scale)

        elif choice == 'r':
            config.use_refiner = not config.use_refiner
        
        elif choice == 'p':
            config.pony_mode = not config.pony_mode
            if config.pony_mode:
                console.print("[magenta]🦄 Pony Modus aktiviert![/magenta]")
                if "score_4" not in config.neg_prompt:
                    config.neg_prompt = config.pony_neg + config.neg_prompt
            else:
                 console.print("[grey50]Pony Modus deaktiviert.[/grey50]")

        elif choice == 'f':
            console.print("\n[bold cyan]--- Favoriten ---[/bold cyan]")
            if not config.favourites:
                console.print("[yellow]Keine Favoriten gespeichert.[/yellow]")
                input("Weiter...")
                continue
            
            fav_table = Table(show_header=True, box=box.SIMPLE)
            fav_table.add_column("#", style="cyan", width=3)
            fav_table.add_column("Prompt", style="white")
            
            for i, fav in enumerate(config.favourites, 1):
                fav_table.add_row(str(i), f"{fav[:80]}...")
            console.print(fav_table)
                
            console.print("[D] Löschen | [ENTER] Abbrechen")
            fav_choice = Prompt.ask("Wahl")
            
            if not fav_choice: continue

            if fav_choice.lower() == 'd':
                try:
                    del_index = IntPrompt.ask("Nummer zum Löschen") - 1
                    if 0 <= del_index < len(config.favourites):
                        deleted = config.favourites.pop(del_index)
                        save_favorites(config.favourites)
                        console.print(f"[red]Gelöscht: {deleted[:30]}...[/red]")
                except: pass
                continue
                
            try:
                load_index = int(fav_choice) - 1
                if 0 <= load_index < len(config.favourites):
                    # WICHTIG: Prompt laden
                    config.prompt = config.favourites[load_index]
                    console.print(f"[green]✅ Favorit geladen:[/green] {config.prompt[:50]}...")
                    # Wir warten hier nicht mehr auf Input, sondern kehren direkt zum Menu zurück,
                    # damit man sofort ENTER drücken kann.
                else:
                    console.print("[red]Ungültige Nummer.[/red]")
                    input("Weiter...")
            except: pass

        elif choice == '1':
            config.steps = IntPrompt.ask("Neue Steps", default=config.steps)
        
        elif choice == '2':
            config.guidance = FloatPrompt.ask("Neue Guidance", default=config.guidance)
        
        elif choice == '3':
            config.neg_prompt = Prompt.ask("Neuer Negative Prompt", default=config.neg_prompt)

        elif choice == '':
            # WICHTIG: Hier nutzen wir config.prompt als Default-Wert
            # Wenn config.prompt leer ist, ist der Default None (User muss tippen)
            default_prompt = config.prompt if config.prompt else None
            
            prompt_text = "\n✨ [bold yellow]PROMPT[/bold yellow]"
            if default_prompt:
                prompt_text += f" [dim](Enter für: {default_prompt[:20]}...)[/dim]"

            prompt_input = Prompt.ask(prompt_text, default=default_prompt)
            
            if not prompt_input:
                continue
            
            # Aktualisieren des gespeicherten Prompts für die nächste Runde
            config.prompt = prompt_input

            if engine is None:
                try:
                    with console.status("[bold green]Lade Modell...[/bold green]"):
                        engine = T2IEngine(base_model_id=config.model_path)
                except Exception as e:
                    console.print(f"[bold red]❌ Fehler beim Laden des Modells: {e}[/bold red]")
                    input("Drücke Enter...")
                    continue

            final_prompt = prompt_input
            if config.pony_mode:
                final_prompt = config.pony_prefix + prompt_input
            
            console.print(f"\n[dim]Generiere: {final_prompt[:80]}...[/dim]")
            
            try:
                # Generierung starten
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
                
                # --- PREVIEW LOGIC ---
                console.print(f"[bold green]✅ Gespeichert:[/bold green] {saved_path}")
                
                if is_kitty_compatible():
                    console.print("\n[bold cyan]Vorschau:[/bold cyan]")
                    print_image_preview(saved_path)
                else:
                    if os.name == 'nt':
                        os.startfile(saved_path)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{saved_path}"')

                if Confirm.ask("Als Favorit speichern?", default=False):
                    if final_prompt not in config.favourites:
                        config.favourites.append(final_prompt)
                        save_favorites(config.favourites)
                        console.print("[green]⭐ Gespeichert![/green]")
                
                input("\nDrücke [ENTER]...")

            except Exception as e:
                console.print(f"\n[bold red]❌ Fehler: {e}[/bold red]")
                import traceback
                traceback.print_exc()
                input("Drücke Enter...")
        
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Abbruch.[/red]")
