import re

def normalize_arabic(text):
    """Comprehensive Arabic text normalization for search."""
    if not text:
        return ""
    
    # 1. Normalize Alif variations
    text = re.sub(r'[إأآٱ]', 'ا', text)
    
    # 2. Normalize Alif Maksura (ى) to Ya (ي)
    text = re.sub(r'ى', 'ي', text)
    
    # 3. Normalize Hamza variations
    text = re.sub(r'[ؤئ]', 'ء', text)
    
    # 4. Normalize Ta Marbuta (ة) to Ha (ه)
    text = re.sub(r'ة', 'ه', text)
    
    # 5. Remove all Arabic diacritics (Tashkeel)
    # Range covers: Fatha, Damma, Kasra, Sukun, Shadda, Madda, Hamza marks, etc.
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    
    # 6. Remove Tatweel/Kashida (elongation character ـ)
    text = re.sub(r'\u0640', '', text)
    
    # 7. Remove zero-width characters
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)
    
    # 8. Normalize whitespace and case (for non-Arabic parts)
    text = re.sub(r'\s+', ' ', text).lower().strip()
    
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
        if not page_data or len(page_data) < 2:
            continue
        p_sura, p_aya = page_data[0], page_data[1]
        if p_sura > sura or (p_sura == sura and p_aya > aya):
            return page_num - 1
    return 604