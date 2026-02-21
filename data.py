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


def get_sura_start_index(quran_data: dict[str, Any], sura_num: int) -> int:
    """Get the absolute verse index (0-based) where a sura starts in the verses list."""
    return int(quran_data["Sura"][sura_num][0])