import json
from pathlib import Path
from typing import Any


def load_quran_data(data_dir: Path) -> dict[str, Any]:
    """Load Quran metadata from quran-data.json.
    
    Source: tanzil.net (downloaded as quran-data.js, reformatted to JSON).
    """
    json_path = data_dir / "quran-data.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"quran-data.json not found in {data_dir}")


def load_quran_text(data_dir: Path) -> list[str]:
    """Load Quran text (Uthmani script).
    
    Source: tanzil.net (quran-uthmani.txt, used as-is).
    """
    path = data_dir / "quran-uthmani.txt"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
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