#!/bin/bash

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Kami Hybrid App (Wayland)...${NC}"

# Memory Optimization
export PYTORCH_ALLOC_CONF=expandable_segments:True

# Force Native Wayland for PyQt6 / QML
export QT_QPA_PLATFORM=wayland

# Activate Venv
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
fi

# Run the App
python main.py
