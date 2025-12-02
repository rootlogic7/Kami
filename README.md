Kami - Local SDXL Workstation

<div align="center">

Kami is a powerful, privacy-focused desktop application for generating images locally using Stable Diffusion XL (SDXL). Built with Python and PyQt6, it provides a modern, responsive GUI for managing prompts, models, and galleries without relying on web browsers or external servers.

</div>

📑 Table of Contents

✨ Key Features

🛠️ Prerequisites

📦 Installation

⚙️ Configuration & Models

🚀 Usage

🔧 Troubleshooting

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

Tab

Description

Generate

Enter prompts (Positive/Negative), adjust Steps & CFG, and generate images.

Settings

Select Checkpoints, Refiners, and LoRAs. Enable Pony Mode or FreeU.

Gallery

Browse history, filter by model/date, and reuse parameters from previous images.

Favorites

Save and manage your best prompts for quick access.

🔧 Troubleshooting

"Wayland" errors on startup

If you experience crashes on Linux/Wayland, try forcing the XCB platform plugin:

export QT_QPA_PLATFORM=xcb
python gui.py


Out of Memory (CUDA OOM)

Disable the Refiner if currently enabled.

Kami automatically attempts to offload models to CPU when not in use.

Use the "Unload Models" button in the Settings tab to forcefully free VRAM.

📜 License

This project is intended for personal use.
