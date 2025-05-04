# AI-Powered Language Dictionary

An AI-powered dictionary application to help language learners with personalized entries, lemmatization, and multiple language support.

## Features

- AI-powered dictionary entry creation using DeepSeek API
- Multi-language support with customizable language preferences
- Intelligent lemmatization with caching
- SQLite database with efficient search and filtering
- User-friendly Tkinter GUI
- Customizable language settings

## Tech Stack

- Python 3.x
- Tkinter for GUI
- SQLite for database
- OpenAI/DeepSeek API for AI processing
- JSON file handling

## Quick Start

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Set up API key:
    ```bash
    cp .env.example api_key.txt
    # Edit api_key.txt with your API key
    ```
5. Run the application
    ```bash
    ./launchdict.sh
    ```
## Project Structure

- /config - Configuration files and prompts
- /data - Database and data files
- /docs - Documentation
- /tests - Unit tests
- /deprecated - Legacy code

## Configuration
The application uses JSON-based configuration for user settings:

- target_language - Language you're learning
- source_language - Your native language
- definition_language - Language for definitions
