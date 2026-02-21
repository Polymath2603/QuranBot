"""
nlu.py — Natural Language Understanding for QBot.

Parses free-text user messages into structured intents:
  - aya:    specific verse  { sura, aya }
  - range:  verse range     { sura, from_aya, to_aya }
  - surah:  full surah      { sura }
  - page:   quran page      { page }
  - search: text search     { query }
"""
import re
from rapidfuzz import process, fuzz
from search import normalize_arabic


# ---------------------------------------------------------------------------
# Surah name helpers
# ---------------------------------------------------------------------------

def _build_sura_names(quran_data: dict) -> list[dict]:
    """Return a list of {name, sura, lang} entries for all surah names."""
    names = []
    for i, entry in enumerate(quran_data["Sura"][1:], 1):
        if len(entry) > 4:
            names.append({"name": entry[4],                   "sura": i, "lang": "ar"})
            names.append({"name": normalize_arabic(entry[4]), "sura": i, "lang": "ar_norm"})
        if len(entry) > 5:
            names.append({"name": entry[5], "sura": i, "lang": "en"})
    return names


def _match_sura_name(text: str, sura_names: list[dict]) -> int | None:
    """
    Fuzzy-match *text* against known surah names.
    Returns the sura number on a confident match (score > 80), else None.
    """
    if not text.strip():
        return None
    choices     = [x["name"] for x in sura_names]
    best        = process.extractOne(text, choices, scorer=fuzz.WRatio)
    if best and best[1] > 80:
        matched = next((x for x in sura_names if x["name"] == best[0]), None)
        return matched["sura"] if matched else None
    return None


# ---------------------------------------------------------------------------
# Chunk parser: extract sura+aya from a text fragment
# ---------------------------------------------------------------------------

def _parse_chunk(text: str, sura_names: list[dict]) -> dict | None:
    """
    Parse a text fragment into {sura, aya?}.
    Handles:
      - Pure numbers:     "2 255"  → sura=2, aya=255
      - Name + number:    "Baqarah 255" → sura=2, aya=255
      - Name only:        "Baqarah"  → sura=2, aya=None
    Returns None if nothing useful found.
    """
    if not text:
        return None

    clean    = re.sub(r"(FROM|SURAH|AYAH|VERSE|SURA|AYA)", "", text, flags=re.IGNORECASE).strip()
    numbers  = re.findall(r"\d+", clean)
    text_part = re.sub(r"\d+", "", clean).strip()

    # Pure numbers
    if not text_part and numbers:
        sura = int(numbers[0])
        if not 1 <= sura <= 114:
            return None
        aya = int(numbers[1]) if len(numbers) > 1 else None
        return {"sura": sura, "aya": aya}

    # Name (possibly + number)
    sura = _match_sura_name(text_part, sura_names)
    if sura:
        aya = int(numbers[0]) if numbers else None
        return {"sura": sura, "aya": aya}

    return None


# ---------------------------------------------------------------------------
# Intent detectors
# ---------------------------------------------------------------------------

def _detect_page(text: str) -> dict | None:
    """Detect 'page N' intent."""
    m = re.search(r"(page|صفحة)\s+(\d+)", text, flags=re.IGNORECASE)
    if m:
        page_num = int(m.group(2))
        if 1 <= page_num <= 604:
            return {"type": "page", "page": page_num}
    return None


def _detect_colon_notation(original: str, sura_names: list[dict]) -> dict | None:
    """
    Detect 'S:A' or 'S:A-B' notation, with optional surah name prefix.
    e.g. '2:255', 'Baqarah 2:255', '2:1-5'
    """
    m = re.search(r"(\d+):(\d+)(?:-(\d+))?", original)
    if not m:
        return None

    s1, a1 = int(m.group(1)), int(m.group(2))
    a2     = int(m.group(3)) if m.group(3) else None
    prefix = original[:m.start()].strip()

    if prefix:
        # Try to resolve prefix as a surah name
        sura = _match_sura_name(normalize_arabic(prefix), sura_names)
        if sura:
            # "Baqarah 2:5" → sura=Baqarah, range s1→a1
            if a2:
                return {"type": "range", "sura": sura, "from_aya": s1, "to_aya": a2}
            return {"type": "range", "sura": sura, "from_aya": s1, "to_aya": a1}

    if a2:
        return {"type": "range", "sura": s1, "from_aya": a1, "to_aya": a2}
    return {"type": "aya", "sura": s1, "aya": a1}


def _detect_range(normalized: str, sura_names: list[dict]) -> dict | None:
    """Detect 'X to Y' / 'X TO Y' range patterns."""
    if "TO " not in normalized:
        return None

    parts = normalized.split("TO ", 1)
    part1, part2 = parts[0].strip(), parts[1].strip()
    info1 = _parse_chunk(part1, sura_names)
    if not info1:
        return None

    sura     = info1["sura"]
    from_aya = info1.get("aya") or 1

    # part2 is a plain number
    if part2.isdigit():
        return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": int(part2)}

    info2 = _parse_chunk(part2, sura_names)
    if info2 and info2.get("aya"):
        return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": info2["aya"]}

    # Fall back: extract first number from part2
    nums = re.findall(r"\d+", part2)
    if nums:
        return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": int(nums[0])}

    return None


def _detect_single(normalized: str, sura_names: list[dict]) -> dict | None:
    """Detect a single aya or full surah reference."""
    info = _parse_chunk(normalized, sura_names)
    if not info:
        return None
    if info.get("aya"):
        return {"type": "aya", "sura": info["sura"], "aya": info["aya"]}
    return {"type": "surah", "sura": info["sura"]}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_message(text: str, quran_data: dict) -> dict:
    """
    Parse a user message into a structured intent dict.

    Returns one of:
      {"type": "page",   "page": int}
      {"type": "aya",    "sura": int, "aya": int}
      {"type": "range",  "sura": int, "from_aya": int, "to_aya": int}
      {"type": "surah",  "sura": int}
      {"type": "search", "query": str}
    """
    original   = text.strip()
    normalized = normalize_arabic(original)

    # Keyword normalization (operate on normalized copy)
    keywords = normalize_arabic(normalized)
    keywords = re.sub(r"(from|من)\s+",                         "FROM ",  keywords, flags=re.IGNORECASE)
    keywords = re.sub(r"(to|الي|إلي|حتي|الى|إلى|حتى)\s+",    "TO ",    keywords, flags=re.IGNORECASE)

    sura_names = _build_sura_names(quran_data)

    # 1. Page
    result = _detect_page(keywords)
    if result:
        return result

    # 2. Colon notation (use original to preserve numbers accurately)
    result = _detect_colon_notation(original, sura_names)
    if result:
        return result

    # 3. Range (FROM … TO …)
    result = _detect_range(keywords, sura_names)
    if result:
        return result

    # 4. Single aya / surah
    result = _detect_single(keywords, sura_names)
    if result:
        return result

    # 5. Fallback: text search
    return {"type": "search", "query": original}
