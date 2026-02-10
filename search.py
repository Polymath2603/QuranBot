import re

def normalize_arabic(text):
    """Normalize Arabic text."""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"[ى]", "ي", text)
    text = re.sub(r"[ؤئ]", "ء", text)
    text = re.sub(r"[ة]", "ه", text)
    text = re.sub(r"[\u064B-\u065F]", "", text)  # Tashkeel
    return text

def search(quran_data, verses, query):
    if len(query) < 3:
        return []
    
    results = []
    # Normalize the query once
    norm_query = normalize_arabic(query)
    
    for i, verse in enumerate(verses):
        # We need to normalize the verse text for comparison
        # But we want to return the original text
        norm_verse = normalize_arabic(verse)
        
        if norm_query in norm_verse:
            sura, aya = get_location(quran_data, i)
            page = get_page(quran_data, sura, aya)
            
            # Highlight the found text? 
            # For now, just return the whole verse
            results.append({
                "text": verse,
                "sura": sura,
                "aya": aya,
                "page": page,
            })
    
    return results


def get_location(quran_data, verse_index):
    for sura_num in range(1, len(quran_data["Sura"])):
        start = int(quran_data["Sura"][sura_num][0])
        count = int(quran_data["Sura"][sura_num][1])
        if start <= verse_index < start + count:
            return sura_num, verse_index - start + 1
    return 1, 1


def get_page(quran_data, sura, aya):
    for page_num, page_data in enumerate(quran_data.get("Page", []), 1):
        p_sura, p_aya = page_data[0], page_data[1]
        if p_sura > sura or (p_sura == sura and p_aya > aya):
            return page_num - 1
    return 604