import json
from pathlib import Path

# Base directory for locales
LOCALE_DIR = Path(__file__).parent / "locales"

_strings = {}

def load_locales():
    """Load all locale JSON files from the locales directory."""
    global _strings
    if not LOCALE_DIR.exists():
        LOCALE_DIR.mkdir()
        
    for file in LOCALE_DIR.glob("*.json"):
        lang_code = file.stem
        try:
            with open(file, "r", encoding="utf-8") as f:
                _strings[lang_code] = json.load(f)
        except Exception as e:
            print(f"Error loading locale {lang_code}: {e}")

# Initial load
load_locales()

def t(key, lang="en", **kwargs):
    """Get a localized string."""
    lang_strings = _strings.get(lang, _strings.get("en", {}))
    text = lang_strings.get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
            
    return text