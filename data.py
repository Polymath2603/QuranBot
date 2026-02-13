import json
from pathlib import Path
from typing import Any


def load_quran_data(data_dir: Path) -> dict[str, Any]:
    """Load Quran metadata from JSON or JS files."""
    json_path = data_dir / "metadata" / "quran-data.json"
    js_path   = data_dir / "metadata" / "quran-data.js"

    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))

    if js_path.exists():
        raw   = js_path.read_text(encoding="utf-8")
        start = raw.find("{")
        end   = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])

    raise FileNotFoundError("No quran-data.json or quran-data.js found in data/metadata/")


def load_quran_text(data_dir: Path, source: str = "hafs") -> list[str]:
    """Load Quran text from specified source."""
    text_sources = {
        "hafs": "quran-uthmani.txt",
        "tajweed": "quran-tajweed.txt",
        "warsh": "quran-warsh.txt"
    }
    
    filename = text_sources.get(source, f"quran-{source}.txt")
    path = data_dir / "text" / filename
    
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        # Files start directly with verse 1:1, no header to skip.
        return lines[:6236]
    
    return []





def get_sura_name(quran_data: dict[str, Any], sura_num: int, lang: str = "ar") -> str:
    """Get sura name in specified language."""
    entry = quran_data["Sura"][sura_num]
    
    if lang == "ar":
        return entry[4] if len(entry) > 4 else f"Sura {sura_num}"
    return entry[5] if len(entry) > 5 else entry[4] if len(entry) > 4 else f"Sura {sura_num}"


def get_sura_aya_count(quran_data: dict[str, Any], sura_num: int) -> int:
    """Get number of ayas in specified sura."""
    return int(quran_data["Sura"][sura_num][1])


def get_page(quran_data: dict[str, Any], sura: int, aya: int) -> int:
    """Get page number for specified sura and aya."""
    pages = quran_data.get("Page", [])
    for page_num in range(1, len(pages)):
        p_data = pages[page_num]
        if not p_data:
            continue
        p_sura, p_aya = p_data[0], p_data[1]
        if p_sura > sura or (p_sura == sura and p_aya > aya):
            return page_num - 1
    return 604