# Kami - Local SDXL Workstation

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green?style=for-the-badge&logo=qt)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)
![Style](https://img.shields.io/badge/Theme-Catppuccin_Mocha-pink?style=for-the-badge)

**A powerful, privacy-focused desktop application for generating images locally using Stable Diffusion XL (SDXL).**

Built with Python and PyQt6, Kami provides a modern, responsive interface for managing prompts, models, and galleries without relying on web browsers or external servers.

[Key Features](#-key-features) • [Installation](#-installation) • [Configuration](#-configuration) • [Usage](#-usage) • [Troubleshooting](#-troubleshooting)

</div>

---

## ✨ Key Features

* **🚀 Native Desktop Experience:** Fast and responsive GUI based on PyQt6 (supports Wayland & X11).
* **🎨 SDXL Powerhouse:** Full support for SDXL Base + Refiner pipelines.
* **🦄 Pony Diffusion Mode:** Specialized mode for "Pony" based models with automatic score-tag handling (`score_9`, `source_anime`, etc.).
* **⚡ FreeU Integration:** Integrated U-Net feature re-weighting for enhanced image quality at no extra cost.
* **📂 Local Gallery:** Built-in SQLite database to browse, filter, and manage your generations efficiently.
* **💾 Metadata Presets:** Reuse parameters from any generated image with a single click.
* **🎲 Image of the Day:** Roll the dice to generate random creative prompts based on internal templates.
* **🖥️ Terminal Integration:** Supports image previews directly in **Kitty** or **Ghostty** terminals.

## 🛠️ Prerequisites

* **OS:** Linux (Arch Linux recommended, tested on Wayland), Windows, or macOS.
* **Python:** 3.10 or newer.
* **GPU:** NVIDIA GPU with at least 8GB VRAM (CUDA support) is highly recommended.

## 📦 Installation

### 1. Clone the Repository

```
git clone git@github.com:rootlogic7/Kami.git
cd Kami
```

### 2. Set up Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

Linux / macOS:

```
python -m venv venv
source venv/bin/activate
```

Windows:

```
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install Dependencies

Install the required Python packages (Diffusers, Torch, PyQt6, etc.).

```
pip install -r requirements.txt
```

## ⚙️ Configuration

Kami expects a specific folder structure for your models.
1. Directory Structure

Create the following folders inside the root directory:
Plaintext

Kami/

├── models/

│   ├── checkpoints/   <-- Place .safetensors (SDXL Base, Pony, etc.) here

│   └── loras/         <-- Place .safetensors (LoRA files) here

├── output_images/     <-- Generated images will appear here

└── styles.json        <-- Custom style presets

2. Adding Models

    Checkpoints: Download SDXL models (e.g., JuggernautXL, PonyDiffusionV6) and place them in models/checkpoints/.

    LoRAs: Place Low-Rank Adaptation files in models/loras/.

3. Custom Styles

You can edit styles.json to add your own prompt templates. The app comes with defaults like Anime, Cinematic, and Photographic.

## 🚀 Usage
Graphical Interface (GUI)

The recommended way to use Kami.

Linux (using startup script): The start.sh script handles environment activation and memory optimizations.
Bash

```
chmod +x start.sh
./start.sh
```

Manual Start:
Bash

```
# Ensure venv is active
python gui.py
```

Command Line Interface (CLI)

You can also generate images directly from the terminal without the GUI.
Bash

```
python main_cli.py "A cyberpunk city in rain, neon lights" --model "models/checkpoints/my_model.safetensors" --steps 30 --guidance 7.0
```

CLI Arguments:

```
    prompt: The text prompt (required).

    --neg: Negative prompt.

    --steps: Denoising steps (default: 30).

    --guidance: CFG Scale (default: 7.0).

    --lora: Path to a LoRA file.

    --refiner: Enable the SDXL Refiner.
```

## 🔧 Troubleshooting
Issue	Solution
Wayland Crashes	

If you experience crashes on Linux/Wayland, try forcing XCB:

```
export QT_QPA_PLATFORM=xcb && python gui.py
CUDA OOM	
```

1. Disable the Refiner.

2. Kami attempts to offload to CPU automatically.

3. Use smaller resolutions if possible.
Missing Models	Ensure your .safetensors files are strictly in models/checkpoints or models/loras and restart the app.

## 📜 License

This project is intended for personal use. See the source code headers for library licenses (Diffusers, PyQt6, etc.).
