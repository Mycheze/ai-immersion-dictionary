import sys
import re
import json
import os
from pathlib import Path
from openai import OpenAI
from database_manager import DatabaseManager
from user_settings import UserSettings

class DictionaryEngine:
    """
    Engine for dictionary operations including lemmatization,
    entry creation, and saving entries
    """
    
    def __init__(self, db_manager=None, user_settings=None):
        """Initialize the dictionary engine with API key and settings"""
        # Get the application root directory
        self.app_root = Path(__file__).parent.parent.absolute()
        
        # Define key paths
        self.api_key_path = self.app_root / 'api_key.txt'
        self.config_dir = self.app_root / 'config'
        
        # Read API key
        self.api_key = self.read_api_key(self.api_key_path)
        
        # Use provided user settings or create a new one
        self.user_settings = user_settings if user_settings else UserSettings()
        
        # Get settings in template replacement format
        self.settings = self.user_settings.get_template_replacements()
        
        # Initialize API client only if we have a valid API key
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        else:
            self.client = None
        
        # Use provided database manager or create a new one
        self.db_manager = db_manager if db_manager else DatabaseManager()
        
        # Cache for validated language names
        self.language_validation_cache = {}
    
    def read_api_key(self, file_path):
        """Read API key from file"""
        try:
            # Convert to Path object if it's a string
            path = Path(file_path) if isinstance(file_path, str) else file_path
            
            with path.open('r') as f:
                api_key = f.read().strip()
                if not api_key:
                    raise ValueError("API key file is empty")
                return api_key
        except FileNotFoundError:
            print(f"Error: {path} not found - please run setup.py to configure your API key.")
            print(f"You can run: python {self.app_root}/setup.py")
            self._show_api_key_error()
            return None
        except Exception as e:
            print(f"Error reading {path}: {str(e)}")
            print(f"Please run setup.py to reconfigure your API key.")
            self._show_api_key_error()
            return None
            
    def _show_api_key_error(self):
        """Display API key error message in GUI if possible"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create a hidden root window for messagebox
            root = tk.Tk()
            root.withdraw()
            
            messagebox.showerror(
                "API Key Error",
                "API key not found or invalid.\n\n"
                "Please run setup.py to configure your API key:\n"
                "python setup.py"
            )
            
            # Exit application after showing error
            root.destroy()
            sys.exit(1)
        except Exception:
            # If GUI display fails, just exit with error code
            sys.exit(1)
    
    def read_system_prompt(self, filename):
        """Read system prompt from file"""
        try:
            # Handle both string paths and existing Path objects
            if isinstance(filename, str):
                # If it's just a relative filename, look in the config directory
                if not os.path.isabs(filename):
                    path = self.config_dir / filename
                else:
                    path = Path(filename)
            else:
                path = filename
                
            with path.open('r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: {path} not found - please create this file with your system prompt.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading {path}: {str(e)}")
            sys.exit(1)
            
    def process_prompt(self, prompt_content, settings=None, additional_vars=None):
        """Process a prompt template by replacing variables"""
        # Use provided settings or default to self.settings
        settings = settings if settings is not None else self.settings
        
        variables = set(re.findall(r'\[([A-Z_]+)\]', prompt_content))
        missing = [var for var in variables if var not in settings]
        
        if missing:
            print(f"Error: Missing settings for variables: {', '.join(missing)}")
            sys.exit(1)
            
        for var in variables:
            prompt_content = prompt_content.replace(f'[{var}]', settings[var])
        
        if additional_vars:
            for var, value in additional_vars.items():
                prompt_content = prompt_content.replace(f'[{var}]', value)
            
        return prompt_content
    
    def call_api(self, messages, temperature=None):
        """Make an API call to the language model"""
        if self.client is None:
            print("\nAPI Error: No API client available - please set up your API key")
            self._show_api_key_error()
            return None
            
        try:
            params = {
                "model": "deepseek-chat",
                "messages": messages,
                "stream": False
            }
            
            # Add optional temperature parameter for increased randomness
            if temperature is not None:
                params["temperature"] = temperature
                
            response = self.client.chat.completions.create(**params)
            return response
        except Exception as e:
            print(f"\nAPI Error: {str(e)}")
            # If we get an authentication error, it might be an invalid API key
            if "auth" in str(e).lower() or "key" in str(e).lower() or "credential" in str(e).lower():
                print("This may be due to an invalid API key. Please run setup.py to reconfigure.")
                self._show_api_key_error()
            return None
    
    def get_lemma(self, word, sentence_context=None):
        """Get the lemma form of the word (using cache when available)"""
        try:
            target_language = self.settings.get('TARGET_LANGUAGE', 'Czech')
            
            # First, check if we have a cached lemma (skip context for cache lookup)
            cached_lemma = self.db_manager.get_cached_lemma(word, target_language)
            if cached_lemma and not sentence_context:
                print(f"Cache hit: {word} -> {cached_lemma}")
                return cached_lemma
            
            # If sentence context is provided, use context-aware lemmatization
            if sentence_context:
                return self.get_lemma_with_context(word, sentence_context)
            
            # If not in cache and no context, call the API with standard prompt
            lemma_prompt = self.read_system_prompt('lemma_prompt.txt')
            
            lemma_settings = self.settings.copy()
            lemma_settings['TARGET_WORD'] = word
            
            processed_lemma_prompt = self.process_prompt(lemma_prompt, lemma_settings)
            
            messages = [
                {"role": "system", "content": "You are a lemmatization function inside a dictionary that must preserve multi-word expressions."},
                {"role": "user", "content": processed_lemma_prompt}
            ]
            
            response = self.call_api(messages)
            
            if not response or not response.choices or not response.choices[0].message.content:
                print("\nError: Received empty response from lemma API call")
                return word
            
            lemma = response.choices[0].message.content.strip()
            
            # Remove only leading/trailing punctuation, but preserve internal spaces and hyphens
            lemma = re.sub(r'^[^\w\s-]+|[^\w\s-]+$', '', lemma)
            lemma = lemma if lemma else word
            
            # Cache the result for future use
            self.db_manager.cache_lemma(word, lemma, target_language)
            print(f"Cached: {word} -> {lemma}")
            
            return lemma
            
        except Exception as e:
            print(f"\nError during lemma processing: {str(e)}")
            return word
    
    def get_lemma_with_context(self, word, sentence_context):
        """Get the lemma form of the word with sentence context"""
        try:
            target_language = self.settings.get('TARGET_LANGUAGE', 'Czech')
            
            # Read context-aware lemma prompt
            lemma_prompt = self.read_system_prompt('lemma_context_prompt.txt')
            
            lemma_settings = self.settings.copy()
            lemma_settings['TARGET_WORD'] = word
            lemma_settings['SENTENCE_CONTEXT'] = sentence_context
            
            processed_lemma_prompt = self.process_prompt(lemma_prompt, lemma_settings)
            
            messages = [
                {"role": "system", "content": "You are a lemmatization function that uses sentence context."},
                {"role": "user", "content": processed_lemma_prompt}
            ]
            
            response = self.call_api(messages)
            
            if not response or not response.choices or not response.choices[0].message.content:
                print("\nError: Received empty response from context lemma API call")
                return word
            
            lemma = response.choices[0].message.content.strip()
            
            # Remove only leading/trailing punctuation, but preserve internal spaces and hyphens
            lemma = re.sub(r'^[^\w\s-]+|[^\w\s-]+$', '', lemma)
            lemma = lemma if lemma else word
            
            # We don't cache context-aware lemmas to avoid confusion with standard lemmas
            # This is because the same word might have different lemmas in different contexts
            print(f"Context-based lemma: {word} -> {lemma}")
            
            return lemma
            
        except Exception as e:
            print(f"\nError during context lemma processing: {str(e)}")
            return word
    
    def create_new_entry(self, word, target_lang=None, source_lang=None, sentence_context=None, variation_prompt=None):
        """Create a new dictionary entry"""
        try:
            # If sentence context is provided, use context-aware entry creation
            if sentence_context:
                return self.create_new_entry_with_context(word, sentence_context, target_lang, source_lang)
            
            # Otherwise use standard entry creation
            # Read the system prompt
            raw_prompt = self.read_system_prompt('prompt.txt')
            
            # Create settings with language overrides if provided
            entry_settings = self.settings.copy()
            
            # Apply target language override if provided
            if target_lang:
                entry_settings['TARGET_LANGUAGE'] = target_lang
                
            # Handle source and definition language overrides
            if source_lang:
                # If source_lang is provided, set both source and definition language to the same value
                entry_settings['SOURCE_LANGUAGE'] = source_lang
                entry_settings['DEFINITION_LANGUAGE'] = source_lang
            elif 'DEFINITION_LANGUAGE' in entry_settings:
                # Otherwise ensure source language matches definition language
                entry_settings['SOURCE_LANGUAGE'] = entry_settings['DEFINITION_LANGUAGE']
            
            # Process the prompt template
            system_prompt = self.process_prompt(raw_prompt, entry_settings)
            
            # Debug: Print the settings being used
            print(f"Creating entry with settings:")
            print(f"  TARGET_LANGUAGE: {entry_settings.get('TARGET_LANGUAGE')}")
            print(f"  BASE_LANGUAGE: {entry_settings.get('SOURCE_LANGUAGE')}")
            print(f"  DEFINITION_LANGUAGE: {entry_settings.get('DEFINITION_LANGUAGE')}")
            
            # Create API messages
            if variation_prompt:
                # For regeneration - include variation instructions
                messages = variation_prompt + [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": word}
                ]
                # Use slightly higher temperature for subtle variation in regenerated entries
                temperature = 0.7
            else:
                # Standard message format
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": word}
                ]
                temperature = 0.7
            
            # Call the API with the appropriate temperature
            print(f"Calling API with temperature: {temperature}")
            response = self.call_api(messages, temperature=temperature)
            
            if not response or not response.choices or not response.choices[0].message.content:
                print("\nError: Received empty response from API")
                return None
                
            response_content = response.choices[0].message.content
            
            # Clean JSON content
            cleaned_content = re.sub(
                r'^\s*```(json)?\s*$', 
                '', 
                response_content, 
                flags=re.MULTILINE
            ).strip()
            
            # Remove trailing backticks if present
            cleaned_content = re.sub(r'```\s*$', '', cleaned_content, flags=re.MULTILINE).strip()
            
            # Parse JSON response
            try:
                entry = json.loads(cleaned_content)
                
                # Debug: Verify the entry structure
                print(f"Parsed entry metadata: {entry.get('metadata', 'MISSING METADATA')}")
                print(f"Entry headword: {entry.get('headword', 'MISSING HEADWORD')}")
                print(f"Number of meanings: {len(entry.get('meanings', []))}")
                
                return entry
            except json.JSONDecodeError:
                print("\nError: Failed to parse API response as JSON")
                print("Raw response content:")
                print(response_content)
                return None
                
        except Exception as e:
            print(f"\nError creating new entry: {str(e)}")
            return None
    
    def create_new_entry_with_context(self, word, sentence_context, target_lang=None, source_lang=None):
        """Create a new dictionary entry with sentence context"""
        try:
            # Read the context-aware system prompt
            raw_prompt = self.read_system_prompt('prompt_with_context.txt')
            
            # Create settings with language overrides if provided
            entry_settings = self.settings.copy()
            
            # Apply target language override if provided
            if target_lang:
                entry_settings['TARGET_LANGUAGE'] = target_lang
                
            # Handle source and definition language overrides
            if source_lang:
                # If source_lang is provided, set both source and definition language to the same value
                entry_settings['SOURCE_LANGUAGE'] = source_lang
                entry_settings['DEFINITION_LANGUAGE'] = source_lang
            elif 'DEFINITION_LANGUAGE' in entry_settings:
                # Otherwise ensure source language matches definition language
                entry_settings['SOURCE_LANGUAGE'] = entry_settings['DEFINITION_LANGUAGE']
                
            # Add sentence context to settings
            entry_settings['TARGET_WORD'] = word
            entry_settings['SENTENCE_CONTEXT'] = sentence_context
            
            # Process the prompt template
            system_prompt = self.process_prompt(raw_prompt, entry_settings)
            
            # Debug: Print the settings being used
            print(f"Creating contextual entry with settings:")
            print(f"  TARGET_LANGUAGE: {entry_settings.get('TARGET_LANGUAGE')}")
            print(f"  BASE_LANGUAGE: {entry_settings.get('SOURCE_LANGUAGE')}")
            print(f"  DEFINITION_LANGUAGE: {entry_settings.get('DEFINITION_LANGUAGE')}")
            print(f"  SENTENCE_CONTEXT: {sentence_context}")
            
            # Create API messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": word}
            ]
            
            # Call the API
            print(f"Calling API for context-aware entry...")
            response = self.call_api(messages, temperature=0.7)
            
            if not response or not response.choices or not response.choices[0].message.content:
                print("\nError: Received empty response from API")
                return None
                
            response_content = response.choices[0].message.content
            
            # Clean JSON content
            cleaned_content = re.sub(
                r'^\s*```(json)?\s*$', 
                '', 
                response_content, 
                flags=re.MULTILINE
            ).strip()
            
            # Remove trailing backticks if present
            cleaned_content = re.sub(r'```\s*$', '', cleaned_content, flags=re.MULTILINE).strip()
            
            # Parse JSON response
            try:
                entry = json.loads(cleaned_content)
                
                # Debug: Verify the entry structure
                print(f"Parsed context entry metadata: {entry.get('metadata', 'MISSING METADATA')}")
                print(f"Context entry headword: {entry.get('headword', 'MISSING HEADWORD')}")
                print(f"Number of meanings: {len(entry.get('meanings', []))}")
                
                return entry
            except json.JSONDecodeError:
                print("\nError: Failed to parse API response as JSON")
                print("Raw response content:")
                print(response_content)
                return None
                
        except Exception as e:
            print(f"\nError creating context entry: {str(e)}")
            return None
    
    def save_entry(self, entry, db_manager=None):
        """Save a dictionary entry to the database"""
        try:
            # Use provided database manager or self.db_manager
            manager = db_manager if db_manager else self.db_manager
            
            entry_id = manager.add_entry(entry)
            if entry_id is not None:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"\nError saving entry: {str(e)}")
            return False
    
    def format_entry(self, entry):
        """Format an entry for display"""
        try:
            return json.dumps(entry, indent=2, ensure_ascii=False)
        except Exception:
            return str(entry)
            
    def validate_language(self, language_name):
        """
        Validates a language name using the LLM.
        Returns a dictionary with standardized_name and display_name.
        """
        try:
            # Check if we have this language in cache
            if language_name in self.language_validation_cache:
                print(f"Cache hit for language validation: {language_name}")
                return self.language_validation_cache[language_name]
            
            # Read the validation prompt template
            validation_prompt = self.read_system_prompt('language_validation_prompt.txt')
            
            # Process the prompt with the language name
            processed_prompt = validation_prompt.replace('[INPUT_LANGUAGE]', language_name)
            
            # Create the messages for the API call
            messages = [
                {"role": "system", "content": "You are a language identification and standardization assistant."},
                {"role": "user", "content": processed_prompt}
            ]
            
            # Call the API
            response = self.call_api(messages)
            
            if not response or not response.choices or not response.choices[0].message.content:
                print(f"\nError: Received empty response from language validation API call for '{language_name}'")
                # Return default values if API fails
                return {
                    "standardized_name": language_name,
                    "display_name": language_name
                }
            
            # Extract the response content
            response_content = response.choices[0].message.content.strip()
            
            # Clean JSON content if needed
            cleaned_content = re.sub(
                r'^\s*```(json)?\s*$', 
                '', 
                response_content, 
                flags=re.MULTILINE
            ).strip()
            
            # Remove trailing backticks if present
            cleaned_content = re.sub(r'```\s*$', '', cleaned_content, flags=re.MULTILINE).strip()
            
            try:
                # Parse the JSON response
                validation_result = json.loads(cleaned_content)
                
                # Ensure we have the expected keys
                if "standardized_name" not in validation_result or "display_name" not in validation_result:
                    print(f"Missing expected keys in language validation response for '{language_name}'")
                    validation_result = {
                        "standardized_name": language_name, 
                        "display_name": language_name
                    }
                
                # Add to cache
                self.language_validation_cache[language_name] = validation_result
                return validation_result
                
            except json.JSONDecodeError:
                print(f"Error parsing language validation response for '{language_name}'")
                print(f"Raw response: {response_content}")
                # Return default values if parsing fails
                return {
                    "standardized_name": language_name,
                    "display_name": language_name
                }
                
        except Exception as e:
            print(f"Error validating language name '{language_name}': {str(e)}")
            # Return default values if any exception occurs
            return {
                "standardized_name": language_name,
                "display_name": language_name
            }

    def regenerate_entry(self, headword, target_lang=None, source_lang=None, definition_lang=None, variation_seed=None):
        """Regenerate an existing dictionary entry"""
        try:
            print(f"Starting regeneration of entry: '{headword}'")
            
            # Make sure source_lang and definition_lang are the same
            if source_lang is None and definition_lang is not None:
                source_lang = definition_lang
            elif definition_lang is None and source_lang is not None:
                definition_lang = source_lang
            
            # Delete the existing entry first, if it exists
            original_entry = self.db_manager.get_entry_by_headword(
                headword,
                source_lang=source_lang,
                target_lang=target_lang,
                definition_lang=definition_lang
            )
            
            if not original_entry:
                print(f"Entry not found for '{headword}', cannot regenerate")
                return None
            
            # Add a special parameter to ensure subtle variation in the regenerated entry
            # while maintaining accuracy and quality of the content
            current_time = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            system_messages = [
                {"role": "system", "content": "You are a dictionary entry creator focused on accuracy and educational value."},
                {"role": "system", "content": f"Create a dictionary entry for '{headword}' that is linguistically accurate and pedagogically sound."},
                {"role": "system", "content": f"Current time: {current_time}. Session ID: {variation_seed if variation_seed else 'default'}"},
                {"role": "system", "content": "Provide slightly different phrasings and examples while maintaining complete accuracy of meaning and usage."}
            ]
            
            print(f"Preparing to delete old entry for '{headword}'")
                
            # Delete the old entry first
            success = self.db_manager.delete_entry(
                headword,
                source_lang=source_lang, 
                target_lang=target_lang,
                definition_lang=definition_lang
            )
            
            if not success:
                print(f"Failed to delete old entry for '{headword}'")
                return None
                
            print(f"Successfully deleted old entry, creating new entry for '{headword}'")
            
            # Create the new entry with variation - source_lang will be used for both source and definition languages
            new_entry = self.create_new_entry(headword, target_lang, source_lang, variation_prompt=system_messages)
            
            if not new_entry:
                print(f"Failed to generate new entry for '{headword}'")
                return None
            
            print(f"Successfully created new entry, saving to database: '{headword}'")
            
            # Save the new entry
            entry_id = self.db_manager.add_entry(new_entry)
            
            if entry_id:
                print(f"Successfully regenerated and saved entry for '{headword}'")
                return new_entry
            else:
                print(f"Failed to save regenerated entry for '{headword}'")
                return None
                
        except Exception as e:
            print(f"Error regenerating entry: {str(e)}")
            return None