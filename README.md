Kami - Local SDXL Workstation

Kami is a powerful, privacy-focused desktop application for generating images locally using Stable Diffusion XL (SDXL). Built with Python and PyQt6, it provides a modern, responsive GUI for managing prompts, models, and galleries without relying on web browsers or external servers.

✨ Key Features

🚀 Native Desktop Experience: Fast and responsive GUI based on PyQt6 (supports Wayland & X11).

🎨 SDXL Powerhouse: Full support for SDXL Base + Refiner pipelines.

🦄 Pony Diffusion Mode: Dedicated mode for "Pony" based models with automatic score-tag handling.

🧬 LoRA Support: Easily mix and match Low-Rank Adaptation (LoRA) networks.

⚡ FreeU Integration: Integrated FreeU (U-Net feature re-weighting) for enhanced image quality without extra cost.

📂 Local Gallery: Built-in SQLite database to browse, filter, and manage your generations.

💾 Metadata Presets: Drag-and-drop metadata support – reuse parameters from any generated image.

🎲 Image of the Day: Roll the dice to generate random creative prompts.

🛠️ Prerequisites

OS: Linux (Arch Linux recommended, tested on Wayland), Windows, or macOS.

Python: 3.10 or newer.

GPU: NVIDIA GPU with at least 8GB VRAM recommended (CUDA support).

📦 Installation

1. Clone the Repository

git clone git@github.com:rootlogic7/Kami.git
cd Kami


2. Set up Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

# Create venv
python -m venv venv

# Activate venv (Linux/Bash)
source venv/bin/activate

# Activate venv (Windows PowerShell)
# .\venv\Scripts\Activate.ps1


3. Install Dependencies

Install the required Python packages, including diffusers, torch, and PyQt6.

pip install -r requirements.txt


⚙️ Configuration & Models

Kami expects a specific folder structure for your models. You can download models from Civitai or Hugging Face.

1. Create Model Directories

The application looks for models in the models/ directory.

mkdir -p models/checkpoints
mkdir -p models/loras


2. Add Your Models

Checkpoints (.safetensors): Place your main SDXL model files (e.g., JuggernautXL.safetensors, PonyDiffusionV6.safetensors) into models/checkpoints/.

LoRAs (.safetensors): Place your LoRA files into models/loras/.

3. Styles (Optional)

You can customize the available styles in styles.json. The app comes with defaults (Anime, Cinematic, Photographic, etc.), but you can add your own JSON entries there.

🚀 Usage

Starting the Application

For Linux users, a convenient startup script is provided that handles environment activation and GPU memory allocation settings.

# Make sure it is executable
chmod +x start.sh

# Run the app
./start.sh


Alternatively, you can run the Python script directly (ensure your venv is active):

python gui.py


GUI Overview

Generate Tab:

Enter your Positive and Negative prompts.

Adjust Steps (default: 30) and CFG Scale (guidance).

Hit GENERATE IMAGE.

Settings Tab:

Checkpoint: Select your base model from the dropdown.

Refiner: Enable the SDXL Refiner for high-fidelity details.

LoRA: Select a LoRA network and adjust its strength.

Advanced: Toggle Pony Mode (adds score tags automatically) or FreeU.

Gallery Tab:

Browse your history.

Filter by model, date, or search for prompt keywords.

Right-click or use buttons to Delete images or Use Parameters to regenerate.

Favorites:

Save your best prompts for quick access later.

🔧 Troubleshooting

Issue: "Wayland" errors on startup
If you experience crashes on Linux/Wayland, try forcing the XCB platform plugin in start.sh or your terminal:

export QT_QPA_PLATFORM=xcb
python gui.py


Issue: Out of Memory (CUDA OOM)

Try disabling the Refiner.

Kami automatically attempts to offload models to CPU when not in use, but you can use the "Unload Models" button in the Settings tab to forcefully free VRAM.

📜 License

This project is intended for personal use.
