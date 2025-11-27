import os
import sys
import json
import base64
from app.engine import T2IEngine

# Rich Imports für das UI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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
        abs_path = os.path.abspath(image_path)
        b64_path = base64.b64encode(abs_path.encode('utf-8')).decode('ascii')
        sys.stdout.write(f"\x1b_Gf=100,a=T,t=f;{b64_path}\x1b\\")
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        console.print(f"[yellow]Vorschau fehlgeschlagen: {e}[/yellow]")

def load_favorites():
    """Lädt Favoriten und migriert alte String-Listen automatisch."""
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                migrated = []
                for item in data:
                    # Migration: Alter String-Eintrag -> Neues Objekt-Format
                    if isinstance(item, str):
                        migrated.append({
                            "name": item[:25].strip() + "...", 
                            "prompt": item
                        })
                    # Bereits neues Format
                    elif isinstance(item, dict) and "prompt" in item:
                        if "name" not in item: item["name"] = "Unbenannt"
                        migrated.append(item)
                return migrated
        except json.JSONDecodeError:
            return []
    return []

def save_favorites(favorites):
    try:
        with open(FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=4, ensure_ascii=False)
    except IOError as e:
        console.print(f"[red]Fehler beim Speichern: {e}[/red]")

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
    if not file_list: console.print(f"[yellow]Keine lokalen Dateien in './{directory}' gefunden.[/yellow]")

    print("\n[A] Pfad eingeben | " + ("[ID] HuggingFace ID | " if hf_allowed else "") + ("[X] Deaktivieren" if file_type == "LoRA" else ""))
    choice = Prompt.ask("Wahl", default="0")
    
    if choice.lower() == 'x' and file_type == "LoRA": return None
    if choice.lower() == 'id' and hf_allowed: return Prompt.ask("HuggingFace ID") or current_path
    if choice.lower() == 'a': return get_clean_path(Prompt.ask("Pfad"))
    
    if choice.isdigit():
        idx = int(choice)
        if idx == 0: return current_path
        if 1 <= idx <= len(file_list): return os.path.join(directory, file_list[idx-1])
    
    return current_path

def print_header(config):
    clear_screen()
    console.print(Panel("[bold magenta]🚀 PYTHON SDXL GENERATOR[/bold magenta] - [dim]Interactive Session[/dim]", box=box.DOUBLE))

    table = Table(show_header=False, box=box.ROUNDED, expand=True)
    table.add_column("Setting", style="cyan"); table.add_column("Value", style="bold white"); table.add_column("Key", style="dim green", justify="right")

    m_name = os.path.basename(config.model_path) if config.model_path.lower().endswith((".safetensors", ".ckpt")) else config.model_path
    if len(m_name) > 40: m_name = m_name[:17] + "..." + m_name[-20:]
    l_name = os.path.basename(config.lora_path) if config.lora_path else 'None'

    table.add_row("Model", m_name, "[M]")
    table.add_row("LoRA", f"{l_name} (Scale: {config.lora_scale})", "[L]")
    table.add_row("Refiner", "ON" if config.use_refiner else "OFF", "[R]")
    table.add_row("Pony Mode", "🦄 ON" if config.pony_mode else "OFF", "[P]")
    table.add_section()
    table.add_row("Steps", str(config.steps), "[1]")
    table.add_row("Guidance", str(config.guidance), "[2]")
    table.add_row("Neg Prompt", f"{config.neg_prompt[:60]}...", "[3]")
    
    console.print(table)
    if config.prompt: console.print(f"[dim]Aktueller Prompt: {config.prompt[:90]}...[/dim]", style="italic grey50")
    console.print(Panel("[bold white][ENTER][/bold white] Generate | [bold white][F][/bold white] Favorites | [bold white][Q][/bold white] Quit", box=box.MINIMAL, style="grey50"))

def handle_favorites_menu(config):
    """Sub-Menü für Favoriten-Verwaltung."""
    while True:
        clear_screen()
        console.print(Panel("[bold cyan]⭐ FAVORITEN VERWALTUNG[/bold cyan]", box=box.DOUBLE))
        
        if not config.favourites:
            console.print("[yellow]Keine Favoriten gespeichert.[/yellow]")
            if Confirm.ask("Zurück zum Hauptmenü?"): return
            
        else:
            table = Table(show_header=True, box=box.SIMPLE, expand=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Name", style="bold yellow", width=25)
            table.add_column("Vorschau", style="white")
            
            for i, fav in enumerate(config.favourites, 1):
                preview = fav['prompt'][:60].replace('\n', ' ') + "..."
                table.add_row(str(i), fav['name'], preview)
            console.print(table)

        console.print("\n[bold white]Aktionen:[/bold white]")
        console.print("[green][Nummer][/green] Laden | [cyan][D][/cyan]etails (Full View) | [yellow][E][/yellow]ditieren | [red][L][/red]öschen | [white][ENTER][/white] Zurück")
        
        choice = Prompt.ask("Wahl").strip().lower()
        
        if not choice:
            return # Zurück zum Hauptmenü

        # --- LÖSCHEN ---
        if choice == 'l':
            try:
                idx = IntPrompt.ask("Nummer zum Löschen") - 1
                if 0 <= idx < len(config.favourites):
                    deleted = config.favourites.pop(idx)
                    save_favorites(config.favourites)
                    console.print(f"[red]Gelöscht: {deleted['name']}[/red]")
                    if not Confirm.ask("Weiter?"): return
            except: pass

        # --- DETAILS ---
        elif choice == 'd':
            try:
                idx = IntPrompt.ask("Nummer für Details") - 1
                if 0 <= idx < len(config.favourites):
                    fav = config.favourites[idx]
                    console.print(Panel(fav['prompt'], title=f"⭐ {fav['name']}", border_style="cyan"))
                    Prompt.ask("Drücke Enter...")
            except: pass

        # --- EDITIEREN ---
        elif choice == 'e':
            try:
                idx = IntPrompt.ask("Nummer zum Bearbeiten") - 1
                if 0 <= idx < len(config.favourites):
                    fav = config.favourites[idx]
                    console.print(f"[dim]Aktueller Name: {fav['name']}[/dim]")
                    new_name = Prompt.ask("Neuer Name (leer = behalten)")
                    if new_name: fav['name'] = new_name
                    
                    console.print(f"[dim]Aktueller Prompt beginnt mit: {fav['prompt'][:50]}...[/dim]")
                    # Wir bieten hier keine volle Prompt-Eingabe an, weil das CLI unübersichtlich ist, 
                    # aber man kann den Prompt durch einen neuen String ersetzen.
                    if Confirm.ask("Prompt-Text komplett ersetzen?", default=False):
                         new_prompt = Prompt.ask("Neuer Prompt Text")
                         if new_prompt: fav['prompt'] = new_prompt
                    
                    save_favorites(config.favourites)
                    console.print("[green]Änderungen gespeichert![/green]")
                    if not Confirm.ask("Weiter?"): return
            except: pass
            
        # --- LADEN (Nummer) ---
        elif choice.isdigit():
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(config.favourites):
                    config.prompt = config.favourites[idx]['prompt']
                    console.print(f"[green]✅ Favorit '{config.favourites[idx]['name']}' geladen![/green]")
                    return # Zurück zum Hauptmenü zum Generieren
            except: pass


def main():
    config = SessionConfig()
    engine = None
    
    while True:
        print_header(config)
        choice = console.input("\n[bold green]Befehl[/bold green] oder [bold white][ENTER][/bold white] für Generierung: ").strip().lower()

        if choice == 'q':
            console.print("[bold magenta]👋 Bis bald![/bold magenta]")
            break

        # --- SETTINGS ---
        elif choice == 'm':
            new_path = select_file_from_list("Model", config.model_path, CHECKPOINTS_DIR, hf_allowed=True)
            if new_path and new_path != config.model_path:
                if engine: engine.cleanup()
                config.model_path = new_path; engine = None
        
        elif choice == 'l':
            new_lora = select_file_from_list("LoRA", config.lora_path, LORAS_DIR)
            if new_lora != config.lora_path:
                config.lora_path = new_lora
                if new_lora: config.lora_scale = FloatPrompt.ask("LoRA Scale", default=config.lora_scale)

        elif choice == 'r': config.use_refiner = not config.use_refiner
        elif choice == 'p': 
            config.pony_mode = not config.pony_mode
            if config.pony_mode and "score_4" not in config.neg_prompt: config.neg_prompt = config.pony_neg + config.neg_prompt

        elif choice == '1': config.steps = IntPrompt.ask("Steps", default=config.steps)
        elif choice == '2': config.guidance = FloatPrompt.ask("Guidance", default=config.guidance)
        elif choice == '3': config.neg_prompt = Prompt.ask("Negative Prompt", default=config.neg_prompt)

        # --- FAVORITEN MENU ---
        elif choice == 'f':
            handle_favorites_menu(config)

        # --- GENERIERUNG ---
        elif choice == '':
            default_prompt = config.prompt if config.prompt else None
            prompt_text = "\n✨ [bold yellow]PROMPT[/bold yellow]" + (f" [dim](Enter für geladenen Prompt)[/dim]" if default_prompt else "")
            
            prompt_input = Prompt.ask(prompt_text, default=default_prompt)
            if not prompt_input: continue
            
            config.prompt = prompt_input # Als aktuell merken

            if engine is None:
                try:
                    with console.status("[bold green]Lade Modell...[/bold green]"):
                        engine = T2IEngine(base_model_id=config.model_path)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]"); input(); continue

            final_prompt = (config.pony_prefix + prompt_input) if config.pony_mode else prompt_input
            console.print(f"\n[dim]Generiere...[/dim]")
            
            try:
                saved_path = engine.generate(final_prompt, config.neg_prompt, config.steps, config.guidance, config.seed, config.use_refiner, config.lora_path, config.lora_scale)
                console.print(f"[bold green]✅ Gespeichert:[/bold green] {saved_path}")
                
                if is_kitty_compatible():
                    console.print("\n[bold cyan]Vorschau:[/bold cyan]"); print_image_preview(saved_path)
                else:
                    if os.name == 'nt': os.startfile(saved_path)
                    elif sys.platform == 'darwin': os.system(f'open "{saved_path}"')

                # --- FAVORIT SPEICHERN ---
                if Confirm.ask("Als Favorit speichern?", default=False):
                    # Check, ob Prompt Text schon existiert
                    exists = any(f['prompt'] == final_prompt for f in config.favourites)
                    if exists:
                        console.print("[yellow]Dieser Prompt existiert bereits in den Favoriten.[/yellow]")
                    else:
                        fav_name = Prompt.ask("Name für Favorit (optional)").strip()
                        if not fav_name: fav_name = final_prompt[:25].strip() + "..."
                        
                        config.favourites.append({"name": fav_name, "prompt": final_prompt})
                        save_favorites(config.favourites)
                        console.print(f"[green]⭐ Gespeichert als '{fav_name}'![/green]")
                
                input("\nDrücke [ENTER]...")
            except Exception as e:
                console.print(f"\n[red]Fehler: {e}[/red]"); import traceback; traceback.print_exc(); input()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: console.print("\n[red]Abbruch.[/red]")
