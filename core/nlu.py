"""nlu.py — Natural Language Understanding for QBot."""
import re
from rapidfuzz import process, fuzz
from .search import normalize_arabic

def _build_sura_names(quran_data):
    names = []
    for i, entry in enumerate(quran_data["Sura"][1:], 1):
        if len(entry) > 4:
            names.append({"name": entry[4], "sura": i})
            names.append({"name": normalize_arabic(entry[4]), "sura": i})
        if len(entry) > 5:
            names.append({"name": entry[5], "sura": i})
    return names

def _match_sura_name(text, sura_names):
    if not text.strip(): return None
    # Guard: long multi-word text without digits is almost certainly a search query,
    # not a sura name. Sura names are 1-3 words max. Fuzzy-matching a full sentence
    # against short sura names produces false positives via partial_ratio.
    words = text.strip().split()
    if len(words) > 3 and not re.search(r'\d', text):
        return None
    best = process.extractOne(text, [x["name"] for x in sura_names], scorer=fuzz.WRatio)
    if best and best[1] > 80:
        m = next((x for x in sura_names if x["name"] == best[0]), None)
        return m["sura"] if m else None
    return None

def _parse_chunk(text, sura_names):
    if not text: return None
    clean    = re.sub(r"(FROM|SURAH|AYAH|VERSE|SURA|AYA)", "", text, flags=re.IGNORECASE).strip()
    numbers  = re.findall(r"\d+", clean)
    txt_part = re.sub(r"\d+", "", clean).strip()
    if not txt_part and numbers:
        sura = int(numbers[0])
        if not 1 <= sura <= 114: return None
        return {"sura": sura, "aya": int(numbers[1]) if len(numbers) > 1 else None}
    sura = _match_sura_name(txt_part, sura_names)
    if sura: return {"sura": sura, "aya": int(numbers[0]) if numbers else None}
    return None

def _detect_page(text):
    m = re.search(r"(page|صفحة)\s+(\d+)", text, flags=re.IGNORECASE)
    if m:
        p = int(m.group(2))
        if 1 <= p <= 604: return {"type": "page", "page": p}
    return None

def _detect_colon(original, sura_names):
    m = re.search(r"(\d+):(\d+)(?:-(\d+))?", original)
    if not m: return None
    s1, a1 = int(m.group(1)), int(m.group(2))
    a2     = int(m.group(3)) if m.group(3) else None
    prefix = original[:m.start()].strip()
    if prefix:
        sura = _match_sura_name(normalize_arabic(prefix), sura_names)
        if sura:
            # s1:a1[-a2] where prefix already gives the sura.
            # If s1 == sura, the user repeated the sura number → treat a1 as aya.
            # Otherwise s1 is from_aya and a1/a2 are to_aya.
            if s1 == sura:
                if a2: return {"type": "range", "sura": sura, "from_aya": a1, "to_aya": a2}
                return {"type": "aya", "sura": sura, "aya": a1}
            else:
                if a2: return {"type": "range", "sura": sura, "from_aya": s1, "to_aya": a2}
                return {"type": "range", "sura": sura, "from_aya": s1, "to_aya": a1}
    if a2: return {"type": "range", "sura": s1, "from_aya": a1, "to_aya": a2}
    return {"type": "aya", "sura": s1, "aya": a1}

def _detect_range(normalized, sura_names):
    if "TO " not in normalized: return None
    p1, p2 = normalized.split("TO ", 1)
    info1  = _parse_chunk(p1.strip(), sura_names)
    if not info1: return None
    sura, from_aya = info1["sura"], info1.get("aya") or 1
    if p2.strip().isdigit(): return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": int(p2.strip())}
    info2 = _parse_chunk(p2.strip(), sura_names)
    if info2 and info2.get("aya"): return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": info2["aya"]}
    nums = re.findall(r"\d+", p2)
    if nums: return {"type": "range", "sura": sura, "from_aya": from_aya, "to_aya": int(nums[0])}
    return None

def _detect_single(normalized, sura_names):
    info = _parse_chunk(normalized, sura_names)
    if not info: return None
    if info.get("aya"): return {"type": "aya", "sura": info["sura"], "aya": info["aya"]}
    return {"type": "surah", "sura": info["sura"]}

def parse_message(text: str, quran_data: dict) -> dict:
    original   = text.strip()
    normalized = normalize_arabic(original)
    keywords   = re.sub(r"(from|من)\s+",                       "FROM ", normalized, flags=re.IGNORECASE)
    keywords   = re.sub(r"(to|الي|إلي|حتي)\s+",                        "TO ",   keywords,   flags=re.IGNORECASE)
    names      = _build_sura_names(quran_data)
    return (
        _detect_page(keywords) or
        _detect_colon(original, names) or
        _detect_range(keywords, names) or
        _detect_single(keywords, names) or
        {"type": "search", "query": original}
    )
