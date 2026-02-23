import json
from config import LOCALE_DIR

_strings: dict = {}

def load_locales() -> None:
    global _strings
    LOCALE_DIR.mkdir(parents=True, exist_ok=True)
    for f in LOCALE_DIR.glob("*.json"):
        try:
            _strings[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error loading locale {f.stem}: {e}")

load_locales()

def t(key: str, lang: str = "ar", **kwargs) -> str:
    text = _strings.get(lang, _strings.get("ar", {})).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
