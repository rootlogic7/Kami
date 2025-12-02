# Kami - Hybrid Local SDXL Workstation

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Qt](https://img.shields.io/badge/Native_UI-PySide6%20(QML)-green?style=for-the-badge&logo=qt)
![React](https://img.shields.io/badge/Web_UI-React_%2B_Vite-cyan?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)

**A powerful, privacy-focused hybrid application for generating images locally using Stable Diffusion XL (SDXL).**

Kami combines a high-performance native desktop interface (QML) with a modern web frontend (React), allowing you to generate images on your workstation or remotely from any device on your local network.

[Features](#-key-features) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture)

</div>

---

## ✨ Key Features

* **🚀 Hybrid Architecture:** Runs a native GPU-accelerated UI on your PC and a Web UI for laptops/tablets simultaneously.
* **🎨 SDXL Powerhouse:** Full support for SDXL Base + Refiner pipelines and LoRA networks.
* **🦄 Pony Diffusion Mode:** Specialized mode for "Pony" based models with automatic score-tag handling.
* **⚡ Native Performance:** Python backend with thread-safe engine management and queue handling.
* **📂 Unified Gallery:** Browse and manage your generations from both the desktop app and the web interface.
* **🔌 API-First:** Built on FastAPI, allowing easy integration with other tools.

## 🛠️ Prerequisites

* **OS:** Linux (Arch Linux recommended, Wayland supported), Windows, or macOS.
* **Python:** 3.10 or newer.
* **Node.js:** v18+ (required for building the frontend).
* **GPU:** NVIDIA GPU with at least 8GB VRAM (CUDA) recommended.

## 📦 Installation

### 1. Clone the Repository

```bash
git clone git@github.com:rootlogic7/Kami.git
cd Kami
```

### 2. Backend Setup (Python)

Create a virtual environment and install dependencies:
Bash

```bash
python -m venv venv
```
```bash
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows
```
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup (React)

Install the Node.js dependencies for the web interface:

```bash
cd frontend
npm install
cd ..
```

## ⚙️ Configuration

Kami expects a specific folder structure for your models. Create the following folders inside the root directory:

```plaintext
Kami/
├── models/
│   ├── checkpoints/   <-- Place .safetensors (SDXL Base, Pony, etc.) here
│   └── loras/         <-- Place .safetensors (LoRA files) here
```

## 🚀 Usage
### Option A: Start Everything (Recommended)

The startup script handles environment activation, memory optimizations, and launches both the backend and native UI.

```bash
chmod +x start.sh
./start.sh
```

Desktop App: Opens immediately.

Web Interface: Accessible at http://<YOUR-PC-IP>:3000 (requires running npm run dev in frontend/ separately for development mode).

### Option B: Development Mode

For active development, run the components in separate terminals:

Backend & Native UI:
```bash
./start.sh
```

Web Frontend (Hot Reload):
```bash
cd frontend
npm run dev
```

## 🏗️ Architecture

Kami uses a hybrid "Headless-First" architecture:

    Core: app/engine.py manages the diffusers pipeline and GPU memory.

    Server: app/server.py (FastAPI) wraps the core and exposes REST endpoints.

    Native UI: main.py starts the server and launches a PySide6 (QML) window that communicates via internal signals.

    Web UI: A React SPA (Single Page Application) communicates with the server via HTTP API.

## 📜 License

This project is intended for personal use. See source code headers for library licenses (Diffusers, Qt, etc.).
