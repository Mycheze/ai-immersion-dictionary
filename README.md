# DeepDict - AI-Powered Language Dictionary

An AI-powered dictionary application to help language learners with personalized entries, lemmatization, and multiple language support.

Please note that the code in this program is almost entirely generated with Claude Code and other Claude models. I have very (very) rudimentary programming skills, but working more as a project manager role and prompting Claude through feature creation allowed me to build the tool I had in my head.

If you're worried about using vibe-coded tools for any reasons, consider this your warning. But I've done my best to avoid any potential security risks. The most sensitive piece of information which this app uses is a DeepSeek API key. Clipboard monitoring could also display sensitive information, but unless it is manually searched, that will not be saved or sent anywhere.

Apart from the API calls (which obviously need an internet connect and sends the data to a third party), I have attempted to keep everything else local to your device.

## Features

- AI-powered dictionary entry creation using DeepSeek API
- Thanks to low API costs, heavy use of the program costs ~$0.03/day
- Multi-language support with customizable language preferences
- Intelligent lemmatization with caching
- Sentence context analysis for more accurate definitions
- SQLite database with efficient search and filtering
- User-friendly Tkinter GUI
- Anki flashcard integration for spaced repetition learning
- Clipboard monitoring for quick lookups

## Tech Stack

- Python 3.x
- Tkinter for GUI
- SQLite for database
- DeepSeek API for AI processing
- JSON file handling for configuration
- Claude Code and other Claude models for coding

## Installation

### Prerequisites

- Python 3.6 or higher
- DeepSeek API key (get one at https://platform.deepseek.com/)
- On Linux, you may need xclip or xsel for clipboard functionality

### Step 1: Clone the Repository

Download the ZIP file with the "Code" button above. Extract the folder and move the folder to somewhere you won't delete it.

### Step 2: Create a Virtual Environment

Open a terminal or command prompt and make sure you're in the right folder! This can be done with `cd` or by right-clicking in the right folder and clicking "open in terminal."

Then run these commands:

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

*Note*: If you have python3 or pip3, all python or pip commands will need a 3 added.

```bash
pip install -r requirements.txt
```

### Step 4: Run the Setup Script

This will prompt for your DeepSeek API key and set up necessary directories:

```bash
python setup.py
```

### Step 5: Launch the Application

**Linux/macOS:**
```bash
./scripts/launch_dictionary.sh
```

**Windows:**
```cmd
scripts\launch_dictionary.bat
```

## Usage

### Adding New Words

1. Enter a word in the bottom search box and click "Search" or press Enter
2. The application will look up the word and display its definition
3. Use the language filters on the left to select your target language and definition language

### Context-Based Lookups

1. Paste a sentence into the context area
2. Double-click or select a word in the sentence
3. Click "Search" to look up the word with contextual understanding

### Clipboard Monitoring

1. Enable "clipboard monitoring" in the bottom panel
2. Copy any text to your clipboard
3. The application will automatically populate the search box with the copied text

### Anki Integration

1. Click the "⚙️ Anki Config" button to configure Anki integration
2. Ensure AnkiConnect plugin is installed in Anki
3. Use the export button (📤) next to examples to create flashcards

## Configuration

The application uses JSON-based configuration for user settings:

- `target_language` - Language you're learning
- `source_language` - Your native language
- `definition_language` - Language for definitions
- `custom_languages` - Custom languages you've added
- `anki_enabled` - Whether Anki integration is enabled

## Project Structure

- `/src` - Main application code
- `/config` - Configuration files and prompts
- `/data` - Database and data files (created automatically)
- `/docs` - Documentation
- `/scripts` - Launch scripts for different platforms
- `/tests` - Unit tests

## Troubleshooting

### API Key Issues

If you encounter API key errors:
1. Run `python setup.py` again to reconfigure your API key
2. Ensure your DeepSeek API key has sufficient credits

### Clipboard Issues on Linux

If clipboard monitoring doesn't work on Linux:
1. Install xclip: `sudo apt-get install xclip`
2. Or install xsel: `sudo apt-get install xsel`

### Database Issues

If you encounter database errors:
1. Check that the `data` directory exists and is writable
2. Delete the database file (`data/dictionary.db`) and restart to rebuild it

## License

This project is licensed under the MIT License - see the LICENSE file for details.
