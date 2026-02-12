import re
from rapidfuzz import process, fuzz
from search import normalize_arabic

def get_all_sura_names(quran_data):
    """Extract all Surah names (English and Arabic) with their numbers."""
    names = []
    for i, entry in enumerate(quran_data["Sura"][1:], 1):
        if len(entry) > 4:
            names.append({"name": entry[4], "sura": i, "lang": "ar"})
            names.append({"name": normalize_arabic(entry[4]), "sura": i, "lang": "ar_norm"})
        if len(entry) > 5:
            names.append({"name": entry[5], "sura": i, "lang": "en"})
    return names

def extract_sura_aya(text, sura_names):
    """
    Helper to extract Surah and Ayah from a text chunk.
    Returns: { "sura": int, "aya": int|None } or None
    """
    if not text:
        return None
        
    # Remove keywords
    clean = re.sub(r"(FROM|SURAH|AYAH|VERSE|SURA|AYA)", "", text, flags=re.IGNORECASE).strip()
    
    # Extract numbers
    numbers = re.findall(r"\d+", clean)
    
    # Text without numbers to find name
    text_no_nums = re.sub(r"\d+", "", clean).strip()
    
    # Case 1: Just numbers "2 255" or "2"
    if not text_no_nums and numbers:
        sura = int(numbers[0])
        if sura > 114 or sura < 1:
            return None # Invalid sura number usually
        aya = int(numbers[1]) if len(numbers) > 1 else None
        return {"sura": sura, "aya": aya}

    # Case 2: Name + Numbers "Baqarah 255"
    choices = [x["name"] for x in sura_names]
    best_match = process.extractOne(text_no_nums, choices, scorer=fuzz.WRatio)
    
    if best_match and best_match[1] > 80:
        matched_name = best_match[0]
        sura_info = next((x for x in sura_names if x["name"] == matched_name), None)
        if sura_info:
            sura = sura_info["sura"]
            aya = int(numbers[0]) if len(numbers) > 0 else None
            return {"sura": sura, "aya": aya}
            
    return None

def parse_message(text, quran_data):
    original_text = text.strip()
    text = normalize_arabic(original_text)
    
    # Keyword Normalization
    # Note: normalize_arabic changes ى to ي, so الى becomes الي
    text = re.sub(r"(from|من)\s+", "FROM ", text, flags=re.IGNORECASE)
    text = re.sub(r"(to|الي|إلي|حتي|الى|إلى|حتى)\s+", "TO ", text, flags=re.IGNORECASE)
    # text = re.sub(r"(surah|sura|سورة|سوره)\s+", "SURAH ", text, flags=re.IGNORECASE) # Handled in helper
    
    # Support "Sura 1:3" or "1:3"
    match = re.search(r"(\d+):(\d+)(?:-(\d+))?", original_text)
    if match:
        s1 = int(match.group(1))
        a1 = int(match.group(2))
        a2 = int(match.group(3)) if match.group(3) else None
        
        # If we have a sura name before it, use that
        sura_names = get_all_sura_names(quran_data)
        prefix = original_text[:match.start()].strip()
        if prefix:
            info = extract_sura_aya(prefix, sura_names)
            if info:
                # If prefix is "Baqarah 2:3", info["sura"]=2, a1=3. Wait.
                # Usually it's "Baqarah 2:3" meaning Aya 2 to 3? Or Sura 2 Aya 3?
                # If prefix has a number, extract_sura_aya uses it as Sura.
                # Let's be simpler: if prefix matches a name, use that name's sura and treat s1 as aya.
                choices = [x["name"] for x in sura_names]
                best_match = process.extractOne(prefix, choices, scorer=fuzz.WRatio)
                if best_match and best_match[1] > 80:
                    matched_info = next(x for x in sura_names if x["name"] == best_match[0])
                    if a2: return {"type": "range", "sura": matched_info["sura"], "from_aya": a1, "to_aya": a2}
                    # "Baqarah 2:3" -> Sura 2 (Baqarah), Aya 2 to 3.
                    return {"type": "range", "sura": matched_info["sura"], "from_aya": s1, "to_aya": a1}

        if a2: return {"type": "range", "sura": s1, "from_aya": a1, "to_aya": a2}
        return {"type": "aya", "sura": s1, "aya": a1}

    sura_names = get_all_sura_names(quran_data)

    # Check for "TO" split
    if "TO " in text:
        parts = text.split("TO ")
        part1 = parts[0].strip()
        part2 = parts[1].strip()
        
        info1 = extract_sura_aya(part1, sura_names)
        
        if info1:
            # If part2 is just a number, it's an Ayah in the same Sura
            if part2.isdigit():
                return {
                    "type": "range",
                    "sura": info1["sura"],
                    "from_aya": info1.get("aya", 1),
                    "to_aya": int(part2)
                }
            
            info2 = extract_sura_aya(part2, sura_names)
            if info2 and info2.get("sura"):
                # If both have same sura, it's a normal range
                if info1["sura"] == info2["sura"]:
                    return {
                        "type": "range",
                        "sura": info1["sura"],
                        "from_aya": info1.get("aya", 1),
                        "to_aya": info2.get("aya", 1)
                    }
                # Cross-Surah: Surah X ... Surah Y
                return {
                    "type": "range_cross",
                    "from_sura": info1["sura"],
                    "from_aya": info1.get("aya", 1),
                    "to_sura": info2["sura"],
                    "to_aya": info2.get("aya", 1)
                }
            elif not info2:
                 # Check if Part 2 contains a number at all
                 nums = re.findall(r"\d+", part2)
                 if nums:
                     return {
                         "type": "range",
                         "sura": info1["sura"],
                         "from_aya": info1.get("aya", 1),
                         "to_aya": int(nums[0])
                     }

    # If no TO logic worked, try single entity
    info = extract_sura_aya(text, sura_names)
    if info:
        if info.get("aya"):
             return {"type": "aya", "sura": info["sura"], "aya": info["aya"]}
        else:
             return {"type": "surah", "sura": info["sura"]}

    return {"type": "search", "query": original_text}
