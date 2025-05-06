#!/bin/bash
# DeepDict launcher script for Linux and macOS

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if virtual environment exists
VENV_DIR="$ROOT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo "Using virtual environment at $VENV_DIR"
    
    # Activate virtual environment
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    else
        echo "Error: Virtual environment activation script not found."
        echo "Try reinstalling with: python -m venv venv"
        exit 1
    fi
else
    echo "Warning: Virtual environment not found at $VENV_DIR"
    echo "Running with system Python (dependencies may be missing)"
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