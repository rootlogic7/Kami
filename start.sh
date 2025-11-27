#!/bin/bash

# Farben für schöne Ausgaben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Local T2I Generator...${NC}"

# 1. Prüfen, ob wir im richtigen Verzeichnis sind
if [ ! -f "interactive.py" ]; then
    echo -e "${RED}Error: interactive.py not found!${NC}"
    echo "Please run this script from the project root folder."
    exit 1
fi

# 2. Virtual Environment suchen und aktivieren
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment (venv)...${NC}"
    source venv/bin/activate
elif [ -d "env" ]; then
    echo -e "${YELLOW}Activating virtual environment (env)...${NC}"
    source env/bin/activate
else
    echo -e "${RED}Warning: No virtual environment found (venv/env).${NC}"
    echo "Attempting to run with system Python..."
fi

# 3. Anwendung starten
python interactive.py

# 4. Cleanup nach Beenden (optional)
echo -e "${GREEN}See you next time! 👋${NC}"
