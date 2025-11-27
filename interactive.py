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
from app.config import SessionConfig, STYLES
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
    """Helper function to clear screen, show image, and print metadata."""
    clear_screen()
    console.print(Panel(f"[bold cyan]Image Viewer:[/bold cyan] {os.path.basename(image_path)}", box=box.DOUBLE))
    print_image_preview(image_path)
    meta = get_image_metadata(image_path)
    params = meta.get("parameters", "No parameters found.")
    console.print(Panel(params, title="Metadata / Parameters", border_style="green", box=box.ROUNDED))

def handle_gallery_menu(pre_filtered_images=None, title="Gallery"):
    """Interactive gallery to browse generated images."""
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
            current_idx = (current_idx + 1) if current_idx < len(images) - 1 else 0
        elif choice == "p":
            current_idx = (current_idx - 1) if current_idx > 0 else len(images) - 1

def select_style_menu(config):
    """Menu to select a prompt style preset."""
    console.print(f"\n[bold cyan]--- Style Selection ---[/bold cyan]")
    
    # Create a list from keys to ensure order
    style_keys = list(STYLES.keys())
    
    table = Table(show_header=True, box=box.SIMPLE)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Style Name", style="bold yellow")
    table.add_column("Description (Positive)", style="dim white")
    
    for i, key in enumerate(style_keys, 1):
        s_name = STYLES[key]["name"]
        s_desc = STYLES[key]["pos"][:50] + "..." if STYLES[key]["pos"] else "Raw input"
        
        # Mark current style
        if key == config.current_style:
            s_name = f"✅ {s_name}"
            
        table.add_row(str(i), s_name, s_desc)
    
    console.print(table)
    choice = Prompt.ask("Select Style ID", default="1")
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(style_keys):
            config.current_style = style_keys[idx]
            console.print(f"[green]Style set to: {config.current_style}[/green]")

def configure_freeu_menu(config):
    """Menu to toggle and configure FreeU parameters."""
    console.print(f"\n[bold cyan]--- FreeU Configuration ---[/bold cyan]")
    console.print("FreeU improves quality by re-weighting U-Net features.\n")
    
    if config.use_freeu:
        console.print(f"Status: [bold green]ON[/bold green]")
    else:
        console.print(f"Status: [bold red]OFF[/bold red]")
        
    console.print(f"Current Settings: {config.freeu_args}")
    
    console.print("\n[1] Toggle On/Off")
    console.print("[2] Edit Parameters")
    console.print("[0] Back")
    
    choice = Prompt.ask("Choice", default="0")
    
    if choice == '1':
        config.use_freeu = not config.use_freeu
        console.print(f"FreeU is now {'Enabled' if config.use_freeu else 'Disabled'}")
    
    elif choice == '2':
        console.print("[dim]Recommended ranges: b1/b2 (1.0-1.6), s1/s2 (0.0-1.0)[/dim]")
        try:
            config.freeu_args['b1'] = FloatPrompt.ask("b1 (Backbone 1)", default=config.freeu_args['b1'])
            config.freeu_args['b2'] = FloatPrompt.ask("b2 (Backbone 2)", default=config.freeu_args['b2'])
            config.freeu_args['s1'] = FloatPrompt.ask("s1 (Skip 1)", default=config.freeu_args['s1'])
            config.freeu_args['s2'] = FloatPrompt.ask("s2 (Skip 2)", default=config.freeu_args['s2'])
            config.use_freeu = True # Auto-enable on edit
        except ValueError:
            console.print("[red]Invalid input[/red]")

def print_header(config):
    clear_screen()
    console.print(Panel("[bold magenta]🚀 PYTHON SDXL GENERATOR[/bold magenta] - [dim]Interactive Session[/dim]", box=box.DOUBLE))

    table = Table(show_header=False, box=box.ROUNDED, expand=True)
    table.add_column("Setting", style="cyan"); table.add_column("Value", style="bold white"); table.add_column("Key", style="dim green", justify="right")

    m_name = os.path.basename(config.model_path) if config.model_path.lower().endswith((".safetensors", ".ckpt")) else config.model_path
    if len(m_name) > 40: m_name = m_name[:17] + "..." + m_name[-20:]
    l_name = os.path.basename(config.lora_path) if config.lora_path else 'None'
    
    # Status Indicators
    refiner_status = "[green]ON[/green]" if config.use_refiner else "[dim]OFF[/dim]"
    pony_status = "[magenta]🦄 ON[/magenta]" if config.pony_mode else "[dim]OFF[/dim]"
    freeu_status = "[green]ON[/green]" if config.use_freeu else "[dim]OFF[/dim]"
    style_name = STYLES.get(config.current_style, {}).get("name", config.current_style)

    table.add_row("Model", m_name, "[M]")
    table.add_row("LoRA", f"{l_name} (Scale: {config.lora_scale})", "[L]")
    table.add_row("Refiner", refiner_status, "[R]")
    table.add_row("Pony Mode", pony_status, "[P]")
    table.add_row("FreeU", freeu_status, "[U]")
    table.add_row("Style", style_name, "[S]")
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
            try:
                idx = IntPrompt.ask("Number to view images for") - 1
                if 0 <= idx < len(config.favourites):
                    fav = config.favourites[idx]
                    console.print(f"[dim]Searching images for: {fav['name']}...[/dim]")
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
        
        # New Feature Menus
        elif choice == 's': select_style_menu(config)
        elif choice == 'u': configure_freeu_menu(config)
        
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

            # --- Prompt Assembly Logic ---
            final_prompt = prompt_input
            final_neg = config.neg_prompt

            # 1. Apply Styles
            style_data = STYLES.get(config.current_style)
            if style_data and config.current_style != "None":
                # Prefix positive, Append negative
                final_prompt = f"{style_data['pos']}{final_prompt}"
                final_neg = f"{style_data['neg']}{final_neg}"

            # 2. Apply Pony Prefixes
            if config.pony_mode:
                 final_prompt = config.pony_prefix + final_prompt

            console.print(f"\n[dim]Generating...[/dim]")
            logger.info(f"Starting generation. Prompt: {final_prompt[:50]}...")
            
            try:
                # Pass FreeU config if enabled
                freeu_settings = config.freeu_args if config.use_freeu else None
                
                saved_path = engine.generate(
                    prompt=final_prompt, 
                    negative_prompt=final_neg, 
                    steps=config.steps, 
                    guidance_scale=config.guidance, 
                    seed=config.seed, 
                    use_refiner=config.use_refiner, 
                    lora_path=config.lora_path, 
                    lora_scale=config.lora_scale,
                    freeu_args=freeu_settings  # New argument
                )
                console.print(f"[bold green]✅ Saved:[/bold green] {saved_path}")
                
                # Show immediate preview with metadata summary
                display_image_with_metadata(saved_path)

                if Confirm.ask("Save as favorite?", default=False):
                    # Save the raw input prompt, not the styled one, so styles can be swapped later
                    exists = any(f['prompt'] == prompt_input for f in config.favourites)
                    if exists:
                        console.print("[yellow]Prompt already in favorites.[/yellow]")
                    else:
                        fav_name = Prompt.ask("Name (optional)").strip()
                        if not fav_name: fav_name = prompt_input[:25].strip() + "..."
                        
                        config.favourites.append({"name": fav_name, "prompt": prompt_input})
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
