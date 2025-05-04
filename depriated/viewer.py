import json
import tkinter as tk
from tkinter import ttk, scrolledtext

class DictionaryViewer:
    def __init__(self, root, data):
        self.root = root
        self.root.title("Language Learner's Dictionary")
        self.root.geometry("800x600")
        
        self.data = data
        self.filtered_data = data
        self.filename = "output.json"
        
        # Create top panel for reload button
        self.top_panel = tk.Frame(root)
        self.top_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add reload button to top right
        self.reload_btn = ttk.Button(self.top_panel, text="Reload Data", command=self.reload_data)
        self.reload_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create left panel for search and headword list
        self.left_panel = tk.Frame(root, width=200, bg="#f0f0f0")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Search box
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.left_panel, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_headwords)
        
        # Headword list
        self.headword_list = tk.Listbox(self.left_panel)
        self.headword_list.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.headword_list.bind("<<ListboxSelect>>", self.show_entry)
        
        # Language filter controls
        self.language_filter_frame = tk.Frame(self.left_panel)
        self.language_filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Target language dropdown
        tk.Label(self.language_filter_frame, text="Target Language:").pack(anchor=tk.W)
        self.target_lang_var = tk.StringVar()
        self.target_lang_dropdown = ttk.Combobox(
            self.language_filter_frame, 
            textvariable=self.target_lang_var,
            state="readonly"
        )
        self.target_lang_dropdown.pack(fill=tk.X, pady=(0, 5))
        self.target_lang_dropdown.bind("<<ComboboxSelected>>", self.apply_language_filters)
        
        # Source language dropdown
        tk.Label(self.language_filter_frame, text="Source Language:").pack(anchor=tk.W)
        self.source_lang_var = tk.StringVar()
        self.source_lang_dropdown = ttk.Combobox(
            self.language_filter_frame, 
            textvariable=self.source_lang_var,
            state="readonly"
        )
        self.source_lang_dropdown.pack(fill=tk.X)
        self.source_lang_dropdown.bind("<<ComboboxSelected>>", self.apply_language_filters)
        
        # Create right panel for displaying entries
        self.right_panel = tk.Frame(root)
        self.right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Entry display
        self.entry_display = scrolledtext.ScrolledText(
            self.right_panel, wrap=tk.WORD, font=("Arial", 12), padx=10, pady=10
        )
        self.entry_display.pack(expand=True, fill=tk.BOTH)
        self.entry_display.config(state=tk.DISABLED)
        
        # Initialize language dropdowns
        self.update_language_options()
        self.update_headword_list()
    
    def reload_data(self):
        """Reload data from the JSON file and update the display"""
        try:
            new_data = load_json_data(self.filename)
            self.data = new_data
            self.filtered_data = new_data
            self.update_language_options()
            self.update_headword_list()
            self.entry_display.config(state=tk.NORMAL)
            self.entry_display.delete(1.0, tk.END)
            self.entry_display.config(state=tk.DISABLED)
            print("Data reloaded successfully")
        except Exception as e:
            print(f"Error reloading data: {e}")
    
    def update_language_options(self):
        """Update the available options in language dropdowns"""
        target_langs = sorted({entry["metadata"]["target_language"] for entry in self.data})
        source_langs = sorted({entry["metadata"]["source_language"] for entry in self.data})
        
        self.target_lang_dropdown["values"] = ["All"] + target_langs
        self.source_lang_dropdown["values"] = ["All"] + source_langs
        
        # Reset selections
        self.target_lang_var.set("All")
        self.source_lang_var.set("All")
    
    def apply_language_filters(self, event=None):
        """Apply language filters based on dropdown selections"""
        target_lang = self.target_lang_var.get()
        source_lang = self.source_lang_var.get()
        
        self.filtered_data = self.data
        
        if target_lang != "All":
            self.filtered_data = [
                entry for entry in self.filtered_data 
                if entry["metadata"]["target_language"] == target_lang
            ]
        
        if source_lang != "All":
            self.filtered_data = [
                entry for entry in self.filtered_data 
                if entry["metadata"]["source_language"] == source_lang
            ]
        
        self.update_headword_list()
    
    def filter_headwords(self, event=None):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.apply_language_filters()  # Just apply language filters
        else:
            self.filtered_data = [
                entry for entry in self.filtered_data 
                if search_term in entry["headword"].lower()
            ]
            self.update_headword_list()
    
    def update_headword_list(self):
        self.headword_list.delete(0, tk.END)
        for entry in sorted(self.filtered_data, key=lambda x: x["headword"]):
            self.headword_list.insert(tk.END, entry["headword"])
    
    def show_entry(self, event):
        selection = self.headword_list.curselection()
        if not selection:
            return
        
        selected_word = self.headword_list.get(selection[0])
        entry = next((e for e in self.filtered_data if e["headword"] == selected_word), None)
        if not entry:
            return
        
        self.entry_display.config(state=tk.NORMAL)
        self.entry_display.delete(1.0, tk.END)
        
        # Display language information
        metadata = entry["metadata"]
        self.entry_display.insert(tk.END, 
            f"{metadata['source_language']} → {metadata['target_language']} (Definitions in {metadata['definition_language']})\n\n", 
            "language_header")
        
        # Display headword and part of speech
        self.entry_display.insert(tk.END, f"{entry['headword']}\n", "headword")
        
        # Handle both part_of_speech and part_of speech variations
        part_of_speech = entry.get("part_of_speech") or entry.get("part_of speech", "unknown")
        self.entry_display.insert(tk.END, f"({part_of_speech})\n\n", "pos")
        
        # Display each meaning
        for i, meaning in enumerate(entry["meanings"], 1):
            self.entry_display.insert(tk.END, f"{i}. {meaning['definition']}\n", "definition")
            
            # Display grammar info if available
            grammar_info = []
            for k, v in meaning["grammar"].items():
                if v:
                    grammar_info.append(f"{k}: {v}")
            
            if grammar_info:
                self.entry_display.insert(tk.END, "   " + ", ".join(grammar_info) + "\n", "grammar")
            
            # Display examples
            for example in meaning["examples"]:
                self.entry_display.insert(tk.END, f"\n   Example:\n", "example_label")
                self.entry_display.insert(tk.END, f"   {example['sentence']}\n", "example")
                self.entry_display.insert(tk.END, f"   {example['translation']}\n\n", "translation")
        
        self.entry_display.config(state=tk.DISABLED)
        
        # Configure tags for formatting
        self.entry_display.tag_config("language_header", font=("Arial", 10), foreground="gray")
        self.entry_display.tag_config("headword", font=("Arial", 16, "bold"))
        self.entry_display.tag_config("pos", font=("Arial", 12, "italic"))
        self.entry_display.tag_config("definition", font=("Arial", 12, "bold"))
        self.entry_display.tag_config("grammar", font=("Arial", 10), foreground="gray")
        self.entry_display.tag_config("example_label", font=("Arial", 10, "italic"))
        self.entry_display.tag_config("example", font=("Arial", 12))
        self.entry_display.tag_config("translation", font=("Arial", 10, "italic"), foreground="blue")

def load_json_data(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

if __name__ == "__main__":
    # Load data from the output.json file
    data = load_json_data("output.json")
    
    root = tk.Tk()
    app = DictionaryViewer(root, data)
    root.mainloop()
