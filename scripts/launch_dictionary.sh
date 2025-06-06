#!/bin/bash
# DeepDict launcher script for Linux and macOS

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    echo "Please install Python 3 to use this application."
    exit 1
fi

# Check if virtual environment exists
VENV_DIR="$ROOT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating one at $VENV_DIR..."
    python3 -m venv "$VENV_DIR" || {
        echo "Error: Failed to create virtual environment."
        echo "Please check that you have the venv module installed."
        echo "On Debian/Ubuntu: sudo apt-get install python3-venv"
        exit 1
    }
    VENV_CREATED=1
fi

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Error: Virtual environment activation script not found."
    echo "Try reinstalling with: python3 -m venv venv"
    exit 1
fi

# If we just created the venv or requirements flag is set, install dependencies
if [ "$VENV_CREATED" = "1" ] || [ "$1" = "--update-deps" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r "$ROOT_DIR/requirements.txt"
fi

# Ensure data directory exists
mkdir -p "$ROOT_DIR/data"

# Check if API key exists
if [ ! -f "$ROOT_DIR/api_key.txt" ]; then
    echo "API key not found. Running setup script..."
    python "$ROOT_DIR/setup.py"
fi

# Launch the application
echo "Launching DeepDict..."
python "$ROOT_DIR/src/app.py"

# Deactivate virtual environment (if we activated it)
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi