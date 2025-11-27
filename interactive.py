import os
import sys
import traceback
import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm

from app.engine import T2IEngine
from app.config import SessionConfig
# Updated imports to include new metadata functions
from app.utils import (
    print_image_preview, 
    get_file_list, 
    get_clean_path, 
    get_all_generated_images, 
    get_image_metadata, 
    find_images_by_prompt_content
)

# --- Logging Configuration ---
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

console = Console()

CHECKPOINTS_DIR = "models/checkpoints"
LORAS_DIR = "models/loras"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def select_file_from_list(file_type, current_path, directory, hf_allowed=False):
    """Interactive CLI menu to select files."""
    console.print(f"\n[bold cyan]--- {file_type} Selection ---[/bold cyan]")
    file_list = get_file_list(directory)
    
    current_name = os.path.basename(current_path) if current_path else 'None'
    
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Filename", style="white")
    table.add_row("0", f"Keep current: {current_name}")
    
    for i, filename in enumerate(file_list, 1):
        table.add_row(str(i), filename)
        
    console.print(table)
    if not file_list: 
        console.print(f"[yellow]No local files found in './{directory}'.[/yellow]")

    print("\n[A] Manual Path | " + ("[ID] HuggingFace ID | " if hf_allowed else "") + ("[X] Disable" if file_type == "LoRA" else ""))
    choice = Prompt.ask("Choice", default="0")
    
    if choice.lower() == 'x' and file_type == "LoRA": return None
    if choice.lower() == 'id' and hf_allowed: return Prompt.ask("HuggingFace ID") or current_path
    if choice.lower() == 'a': return get_clean_path(Prompt.ask("Path"))
    
    if choice.isdigit():
        idx = int(choice)
        if idx == 0: return current_path
        if 1 <= idx <= len(file_list): return os.path.join(directory, file_list[idx-1])
    
    return current_path

def display_image_with_metadata(image_path: str):
    """
    Helper function to clear screen, show image, and print metadata.
    """
    clear_screen()
    console.print(Panel(f"[bold cyan]Image Viewer:[/bold cyan] {os.path.basename(image_path)}", box=box.DOUBLE))
    
    # 1. Render Image (Ghostty/Kitty)
    print_image_preview(image_path)
    
    # 2. Retrieve and show Metadata
    meta = get_image_metadata(image_path)
    params = meta.get("parameters", "No parameters found.")
    
    console.print(Panel(params, title="Metadata / Parameters", border_style="green", box=box.ROUNDED))

def handle_gallery_menu(pre_filtered_images=None, title="Gallery"):
    """
    Interactive gallery to browse generated images.
    
    Args:
        pre_filtered_images (list): Optional list of paths to show. If None, shows all.
        title (str): Title for the gallery header.
    """
    if pre_filtered_images is not None:
        images = pre_filtered_images
    else:
        images = get_all_generated_images()

    if not images:
        console.print("[yellow]No images found in output directory.[/yellow]")
        Prompt.ask("Press Enter...")
        return

    current_idx = 0
    while True:
        img_path = images[current_idx]
        display_image_with_metadata(img_path)
        
        console.print(f"\n[bold white]Image {current_idx + 1} of {len(images)}[/bold white]")
        console.print("[green][N][/green]ext | [green][P][/green]rev | [red][Q][/red]uit Gallery")
        
        choice = Prompt.ask("Action", choices=["n", "p", "q"], default="n")
        
        if choice == "q":
            break
        elif choice == "n":
            if current_idx < len(images) - 1:
                current_idx += 1
            else:
                console.print("[yellow]End of gallery. Looping to start.[/yellow]")
                current_idx = 0
        elif choice == "p":
            if current_idx > 0:
                current_idx -= 1
            else:
                current_idx = len(images) - 1

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
    if config.prompt: console.print(f"[dim]Current Prompt: {config.prompt[:90]}...[/dim]", style="italic grey50")
    console.print(Panel("[bold white][ENTER][/bold white] Generate | [bold white][G][/bold white] Gallery | [bold white][F][/bold white] Favorites | [bold white][Q][/bold white] Quit", box=box.MINIMAL, style="grey50"))

def handle_favorites_menu(config):
    """Sub-menu for favorites management."""
    while True:
        clear_screen()
        console.print(Panel("[bold cyan]⭐ FAVORITES MANAGER[/bold cyan]", box=box.DOUBLE))
        
        if not config.favourites:
            console.print("[yellow]No favorites saved.[/yellow]")
            if Confirm.ask("Back to Main Menu?"): return
            
        else:
            table = Table(show_header=True, box=box.SIMPLE, expand=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Name", style="bold yellow", width=25)
            table.add_column("Preview", style="white")
            
            for i, fav in enumerate(config.favourites, 1):
                preview = fav['prompt'][:60].replace('\n', ' ') + "..."
                table.add_row(str(i), fav['name'], preview)
            console.print(table)

        console.print("\n[bold white]Actions:[/bold white]")
        console.print("[green][Number][/green] Load | [cyan][V][/cyan]iew Images | [yellow][E][/yellow]dit | [red][D][/red]elete | [white][ENTER][/white] Back")
        
        choice = Prompt.ask("Choice").strip().lower()
        if not choice: return 

        if choice == 'd':
            try:
                idx = IntPrompt.ask("Number to delete") - 1
                if 0 <= idx < len(config.favourites):
                    deleted = config.favourites.pop(idx)
                    config.save_favorites()
                    console.print(f"[red]Deleted: {deleted['name']}[/red]")
                    if not Confirm.ask("Continue?"): return
            except: pass

        elif choice == 'v':
            # NEW: View images associated with a favorite
            try:
                idx = IntPrompt.ask("Number to view images for") - 1
                if 0 <= idx < len(config.favourites):
                    fav = config.favourites[idx]
                    console.print(f"[dim]Searching images for: {fav['name']}...[/dim]")
                    
                    # Search images by prompt content
                    found_images = find_images_by_prompt_content(fav['prompt'])
                    
                    if found_images:
                        handle_gallery_menu(found_images, title=f"Images for: {fav['name']}")
                    else:
                        console.print(f"[red]No images found matching prompt for '{fav['name']}'[/red]")
                        Prompt.ask("Press Enter...")
            except: pass

        elif choice == 'e':
            try:
                idx = IntPrompt.ask("Number to edit") - 1
                if 0 <= idx < len(config.favourites):
                    fav = config.favourites[idx]
                    console.print(f"[dim]Current Name: {fav['name']}[/dim]")
                    new_name = Prompt.ask("New Name (empty to keep)")
                    if new_name: fav['name'] = new_name
                    
                    if Confirm.ask("Replace prompt text completely?", default=False):
                         new_prompt = Prompt.ask("New Prompt Text")
                         if new_prompt: fav['prompt'] = new_prompt
                    
                    config.save_favorites()
                    console.print("[green]Changes saved![/green]")
                    if not Confirm.ask("Continue?"): return
            except: pass
            
        elif choice.isdigit():
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(config.favourites):
                    config.prompt = config.favourites[idx]['prompt']
                    console.print(f"[green]✅ Loaded favorite '{config.favourites[idx]['name']}'![/green]")
                    return 
            except: pass

def main():
    logger.info("Starting Interactive Session")
    config = SessionConfig()
    engine = None
    
    while True:
        print_header(config)
        choice = console.input("\n[bold green]Command[/bold green] or [bold white][ENTER][/bold white] to generate: ").strip().lower()

        if choice == 'q':
            console.print("[bold magenta]Saving session and exiting...[/bold magenta]")
            config.save_session_state()
            logger.info("Session ended by user.")
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

        # --- FAVORITES & GALLERY ---
        elif choice == 'f':
            handle_favorites_menu(config)
        
        elif choice == 'g':
            handle_gallery_menu()

        # --- GENERATE ---
        elif choice == '':
            default_prompt = config.prompt if config.prompt else None
            prompt_text = "\n✨ [bold yellow]PROMPT[/bold yellow]" + (f" [dim](Enter for loaded prompt)[/dim]" if default_prompt else "")
            
            prompt_input = Prompt.ask(prompt_text, default=default_prompt)
            if not prompt_input: continue
            
            config.prompt = prompt_input 
            config.save_session_state()

            if engine is None:
                try:
                    with console.status("[bold green]Loading Model...[/bold green]"):
                        logger.info(f"Initializing engine with model: {config.model_path}")
                        engine = T2IEngine(base_model_id=config.model_path)
                except Exception as e:
                    logger.error(f"Failed to load model: {e}")
                    console.print(f"[red]Error loading model: {e}[/red]"); input(); continue

            final_prompt = (config.pony_prefix + prompt_input) if config.pony_mode else prompt_input
            console.print(f"\n[dim]Generating...[/dim]")
            logger.info(f"Starting generation. Prompt: {final_prompt[:50]}...")
            
            try:
                saved_path = engine.generate(final_prompt, config.neg_prompt, config.steps, config.guidance, config.seed, config.use_refiner, config.lora_path, config.lora_scale)
                console.print(f"[bold green]✅ Saved:[/bold green] {saved_path}")
                
                # Show immediate preview with metadata summary
                display_image_with_metadata(saved_path)

                if Confirm.ask("Save as favorite?", default=False):
                    exists = any(f['prompt'] == final_prompt for f in config.favourites)
                    if exists:
                        console.print("[yellow]Prompt already in favorites.[/yellow]")
                    else:
                        fav_name = Prompt.ask("Name (optional)").strip()
                        if not fav_name: fav_name = final_prompt[:25].strip() + "..."
                        
                        config.favourites.append({"name": fav_name, "prompt": final_prompt})
                        config.save_favorites()
                        console.print(f"[green]⭐ Saved as '{fav_name}'![/green]")
                
                input("\nPress [ENTER]...")
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                logger.error(traceback.format_exc())
                console.print(f"\n[red]Generation Error: {e}[/red]")
                input()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: console.print("\n[red]Aborted.[/red]")
