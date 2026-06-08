#!/usr/bin/env bash
# Bitmap Vector Studio - macOS/Linux GUI Launcher
# Version: 0.2.0

set -euo pipefail

PROJECT_NAME="Bitmap Vector Studio"
VERSION="0.2.0"

# Colors for terminal output (safe fallback)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Display startup info
echo "============================================"
echo "  ${PROJECT_NAME} v${VERSION}"
echo "============================================"
echo ""

# Check if app.py exists in current directory
if [[ ! -f "app.py" ]]; then
    echo -e "${RED}[ERROR]${NC} app.py not found in current directory."
    echo "Please run this script from the project root directory:"
    echo "  ./scripts/run_gui.sh"
    exit 1
fi

# Detect and activate virtual environment if present
if [[ -d ".venv" && -f ".venv/bin/activate" ]]; then
    echo -e "${GREEN}[INFO]${NC} Activating virtual environment (.venv)..."
    # shellcheck source=/dev/null
    source ".venv/bin/activate"
elif [[ -d "venv" && -f "venv/bin/activate" ]]; then
    echo -e "${GREEN}[INFO]${NC} Activating virtual environment (venv)..."
    # shellcheck source=/dev/null
    source "venv/bin/activate"
else
    echo -e "${YELLOW}[INFO]${NC} No virtual environment found, using system Python."
fi

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} streamlit is not installed."
    echo "Please install dependencies first:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Launch the GUI
echo -e "${GREEN}[INFO]${NC} Starting Streamlit GUI..."
echo ""

if ! streamlit run app.py; then
    echo ""
    echo -e "${RED}[ERROR]${NC} Failed to start the GUI. Please check the error message above."
    exit 1
fi
