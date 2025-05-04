# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Environment setup: `python -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Run application: `./launchdict.sh` or `python combined-version/app.py`
- Run tests: `python -m unittest discover tests`

## Code Style Guidelines
- Follow PEP 8 conventions with 4-space indentation
- Use docstrings for classes and functions
- Use type hints (from typing import List, Dict, Optional, etc.)
- Variable naming: snake_case for variables/functions, CamelCase for classes
- Imports: standard libraries first, then third-party, then local modules
- Error handling: use try/except with specific exceptions
- Use context managers for file and database operations

## Architecture Notes
- Modular design: separate classes for different components
- Database: SQLite with DatabaseManager class
- UI: Tkinter-based interface in app.py
- API: OpenAI/DeepSeek API for dictionary entry generation
- Settings: JSON-based persistent user settings