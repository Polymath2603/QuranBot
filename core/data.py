import json5
import re
from pathlib import Path
from typing import Any

# Diacritics and Tatweel (U+0640) — stripped for normalization
_DIACRITICS = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u0640]')
# Bare basmala for prefix detection (after normalization)
_BASMALA_BARE = 'بسم الله الرحمن الرحيم'


def _normalize_basmala(text: str) -> str:
    """Strip diacritics and normalize alif variants for basmala detection only."""
    return _DIACRITICS.sub('', text).replace('ٱ', 'ا').replace('\u0671', 'ا')


def strip_basmala(verse_text: str, sura: int, aya: int) -> str:
    """
    Remove the basmala prefix from a verse if applicable.
    Applies to aya==1 of any sura except sura 1 (the basmala itself) and sura 9 (no basmala).
    Uses normalization-based detection to handle diacritic ordering variants in the Uthmani text.
    """
    if aya != 1 or sura in (1, 9):
        return verse_text
    norm = _normalize_basmala(verse_text)
    if not norm.startswith(_BASMALA_BARE):
        return verse_text
    # Walk original chars, counting non-diacritic chars until we've consumed BASMALA_BARE
    orig_idx = 0
    norm_idx = 0
    blen = len(_BASMALA_BARE)
    while norm_idx < blen and orig_idx < len(verse_text):
        if not _DIACRITICS.match(verse_text[orig_idx]):
            norm_idx += 1
        orig_idx += 1
    # Skip trailing diacritics that belong to the last basmala letter
    while orig_idx < len(verse_text) and _DIACRITICS.match(verse_text[orig_idx]):
        orig_idx += 1
    # Skip space separator
    while orig_idx < len(verse_text) and verse_text[orig_idx] == ' ':
        orig_idx += 1
    return verse_text[orig_idx:]


def replace_basmala_symbol(verse_text: str, sura: int, aya: int) -> str:
    """Replace basmala prefix with ﷽ symbol. For text/search display."""
    if aya != 1 or sura in (1, 9):
        return verse_text
    norm = _normalize_basmala(verse_text)
    if not norm.startswith(_BASMALA_BARE):
        return verse_text
    rest = strip_basmala(verse_text, sura, aya)
    return ('﷽ ' + rest).strip() if rest else '﷽'


def replace_basmala_page(verse_text: str, sura: int, aya: int) -> str:
    """Replace basmala prefix with ﷽ + newline. For page navigation display."""
    if aya != 1 or sura in (1, 9):
        return verse_text
    norm = _normalize_basmala(verse_text)
    if not norm.startswith(_BASMALA_BARE):
        return verse_text
    rest = strip_basmala(verse_text, sura, aya)
    return ('﷽\n' + rest).strip() if rest else '﷽'


def load_quran_data(data_dir: Path) -> dict[str, Any]:
    """Load Quran metadata from quran-data.json.
    
    Source: tanzil.net — https://tanzil.net/docs/quran_metadata
    License: CC BY 3.0
    """
    json_path = data_dir / "quran-data.json"
    if json_path.exists():
        return json5.loads(json_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"quran-data.json not found in {data_dir}")


def load_quran_text(data_dir: Path) -> list[str]:
    """Load Quran text (Uthmani script) — for video rendering.
    
    Source: tanzil.net — https://tanzil.net/docs/quran_text  (quran-uthmani.txt)
    License: CC BY 3.0
    """
    path = data_dir / "quran-uthmani.txt"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[:6236]
    return []


def load_quran_text_simple(data_dir: Path) -> list[str]:
    """Load simplified Quran text — for display, search, tafsir, subtitles.

    Source: tanzil.net — https://tanzil.net/docs/quran_text  (quran-simple.txt)
    License: CC BY 3.0
    """
    path = data_dir / "quran-simple.txt"
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[:6236]
    raise FileNotFoundError(f"quran-simple.txt not found in {data_dir}")


def get_sura_name(quran_data: dict[str, Any], sura_num: int, lang: str = "ar") -> str:
    """Get bare sura name (no prefix)."""
    entry = quran_data["Sura"][sura_num]
    if lang == "ar":
        return entry[4] if len(entry) > 4 else f"سورة {sura_num}"
    return entry[5] if len(entry) > 5 else entry[4] if len(entry) > 4 else f"Sura {sura_num}"


def get_sura_display_name(quran_data: dict[str, Any], sura_num: int, lang: str = "ar") -> str:
    """Get sura name always prefixed: 'سورة الإخلاص' / 'Surah Al-Ikhlas'."""
    bare = get_sura_name(quran_data, sura_num, lang)
    prefix = "سورة" if lang == "ar" else "Surah"
    return f"{prefix} {bare}"


def get_sura_aya_count(quran_data: dict[str, Any], sura_num: int) -> int:
    return int(quran_data["Sura"][sura_num][1])


def get_sura_start_index(quran_data: dict[str, Any], sura_num: int) -> int:
    return int(quran_data["Sura"][sura_num][0])
