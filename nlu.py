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
    text = re.sub(r"(from|من)\s+", "FROM ", text, flags=re.IGNORECASE)
    text = re.sub(r"(to|الى|إلى|حتى)\s+", "TO ", text, flags=re.IGNORECASE)
    # text = re.sub(r"(surah|sura|سورة|سوره)\s+", "SURAH ", text, flags=re.IGNORECASE) # Handled in helper
    
    # Direct Patterns
    match = re.match(r"^(\d+):(\d+)$", original_text)
    if match:
        return {"type": "aya", "sura": int(match.group(1)), "aya": int(match.group(2))}
        
    sura_names = get_all_sura_names(quran_data)

    # Check for "TO" split
    if "TO " in text:
        parts = text.split("TO ")
        part1 = parts[0].strip()
        part2 = parts[1].strip()
        
        info1 = extract_sura_aya(part1, sura_names)
        info2 = extract_sura_aya(part2, sura_names)
        
        if info1:
            if info2 and info2.get("sura"):
                # Cross-Surah: Surah X ... Surah Y
                return {
                    "type": "range_cross",
                    "from_sura": info1["sura"],
                    "from_aya": info1.get("aya", 1),
                    "to_sura": info2["sura"],
                    "to_aya": info2.get("aya", 1)
                }
            elif info1 and info2 and not info2.get("sura") and info2.get("aya"):
                 # Should not happen because helper requires sura usually? 
                 # Ah, helper returns None if no sura found in numbers check.
                 # But if part2 is just "5", helper returns sura=5.
                 # Meaning "Surah Baqarah 1 TO 5" -> Part2 is "5" -> Sura=5.
                 # This is ambiguous. "5" can be Surah 5 or Ayah 5.
                 # If Part 1 has Sura X Ayah Y, and Part 2 is just "5", it likely means Ayah 5 of Sura X.
                 pass
            elif info1 and not info2:
                 # Check if Part 2 is just a number
                 nums = re.findall(r"\d+", part2)
                 if nums:
                     to_aya = int(nums[0])
                     return {
                         "type": "range",
                         "sura": info1["sura"],
                         "from_aya": info1.get("aya", 1),
                         "to_aya": to_aya
                     }

    # If no TO logic worked, try single entity
    info = extract_sura_aya(text, sura_names)
    if info:
        if info.get("aya"):
             return {"type": "aya", "sura": info["sura"], "aya": info["aya"]}
        else:
             return {"type": "surah", "sura": info["sura"]}

    return {"type": "search", "query": original_text}
