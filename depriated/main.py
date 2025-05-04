import sys
import re
import json
from openai import OpenAI

def read_api_key(filename):
    try:
        with open(filename, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: {filename} not found - please create this file with your API key.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")
        sys.exit(1)

def load_settings(filename):
    settings = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'^\s*\[([^\]]+)\]\s*=\s*(.+?)\s*$', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    settings[key] = value
                else:
                    print(f"Warning: Ignoring invalid line in settings: {line}")
        return settings
    except FileNotFoundError:
        print(f"Error: {filename} not found - please create this file with your settings.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")
        sys.exit(1)

def process_prompt(prompt_content, settings, additional_vars=None):
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

def read_system_prompt(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: {filename} not found - please create this file with your system prompt.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")
        sys.exit(1)

def get_user_input():
    try:
        return input("\nEnter your message (or type 'exit' to quit): ").strip()
    except KeyboardInterrupt:
        return None

def call_deepseek_api(client, messages):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        return response
    except Exception as e:
        print(f"\nAPI Error: {str(e)}")
        return None

def save_response(content, filename):
    try:
        json_content = json.loads(content)
        with open(filename, 'a', encoding='utf-8') as f:
            json.dump(json_content, f)
            f.write('\n')
    except json.JSONDecodeError:
        print(f"\nWarning: Response is not valid JSON, saving as text")
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{content}\n")
    except Exception as e:
        print(f"\nError saving response: {str(e)}")

def format_response(content):
    try:
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return content

def get_lemma(client, word, settings):
    """Get the lemma form of the word using the lemma prompt."""
    try:
        lemma_prompt = read_system_prompt('lemma_prompt.txt')
        
        # Create a temporary settings dict with the word included
        lemma_settings = settings.copy()
        lemma_settings['TARGET_WORD'] = word
        
        processed_lemma_prompt = process_prompt(lemma_prompt, lemma_settings)
        
        messages = [
            {"role": "system", "content": "You are a lemmatization function inside a dictionary."},
            {"role": "user", "content": processed_lemma_prompt}
        ]
        
        response = call_deepseek_api(client, messages)
        
        if not response or not response.choices or not response.choices[0].message.content:
            print("\nError: Received empty response from lemma API call")
            return word  # Return original word if lemma call fails
            
        lemma = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure it's just a single word
        # Remove any punctuation, quotes, or additional text
        lemma = re.split(r'[\s,.;!?"\'()\[\]{}]', lemma)[0]
        return lemma if lemma else word
    
    except Exception as e:
        print(f"\nError during lemma processing: {str(e)}")
        return word  # Fallback to original word if any error occurs

def main():
    api_key = read_api_key('api_key.txt')
    settings = load_settings('settings.txt')
    raw_prompt = read_system_prompt('prompt.txt')
    system_prompt = process_prompt(raw_prompt, settings)
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    while True:
        user_input = get_user_input()
        
        if not user_input:
            print("\nExiting...")
            break
        if user_input.lower() == 'exit':
            print("\nExiting...")
            break

        # First get the lemma of the input word
        lemma = get_lemma(client, user_input, settings)
        print(f"\nLemma identified: {lemma}")
        
        # Then proceed with the main API call using the lemma
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": lemma}
        ]
        
        response = call_deepseek_api(client, messages)
        
        if not response or not response.choices or not response.choices[0].message.content:
            print("\nError: Received empty response from API")
            continue  # Continue loop instead of exiting
            
        response_content = response.choices[0].message.content
        
        cleaned_content = re.sub(
            r'^\s*```(json)?\s*$', 
            '', 
            response_content, 
            flags=re.MULTILINE
        ).strip()
        
        formatted_response = format_response(cleaned_content)
        
        print(f"\nResponse:\n{formatted_response}")
        save_response(cleaned_content, 'output.json')
        print("Response saved to output.json")

if __name__ == "__main__":
    main()
