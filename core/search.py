import re


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for robust search matching.

    Key decisions:
    - U+0670 (dagger alif / superscript alif ٰ) is REMOVED first, before any
      letter-variant substitution. It is a pronunciation guide, not a letter.
      Without this, إِلَٰهَ normalizes to 'الاه' (4 chars) instead of 'اله' (3 chars),
      breaking searches like 'لا اله الا الله'.
    - U+06D6–U+06ED: Quranic annotation marks (pause signs ۚ ۖ, small letters ۥ ۦ, etc.)
      are removed. They survive standard diacritic removal and break word boundaries.
    - Alif variants (إ أ آ ٱ ا) all collapse to plain alif ا.
    - Alif maksura ى → ya ي.
    - Hamza-seat variants ؤ ئ → bare hamza ء.
    """
    if not text:
        return ""

    # 0. Remove dagger alif FIRST (U+0670) — pronunciation mark, not a letter
    text = re.sub(r'\u0670', '', text)

    # 1. Normalize alif variants → ا  (ٱ U+0671 alif wasla included)
    text = re.sub(r'[إأآٱا]', 'ا', text)

    # 2. Normalize alif maksura → ya
    text = re.sub(r'ى', 'ي', text)

    # 3. Normalize hamza seats
    text = re.sub(r'[ؤئ]', 'ء', text)

    # 4. Remove standard Arabic diacritics (tashkeel) U+064B–U+065F
    text = re.sub(r'[\u064B-\u065F]', '', text)

    # 5. Remove Quranic annotation marks U+06D6–U+06ED
    #    (small high/low signs, pause marks, sajda mark, small waw/ya ۥ ۦ, etc.)
    text = re.sub(r'[\u06D6-\u06ED]', '', text)

    # 6. Remove tatweel (kashida) ـ
    text = re.sub(r'\u0640', '', text)

    # 7. Remove zero-width characters
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)

    # 8. Collapse whitespace, lowercase non-Arabic
    text = re.sub(r'\s+', ' ', text).lower().strip()

    return text


def search(quran_data: dict, verses: list, query: str) -> list:
    if len(query) < 3:
        return []

    norm_query = normalize_arabic(query)
    if not norm_query:
        return []

    results = []
    for i, verse in enumerate(verses):
        if norm_query in normalize_arabic(verse):
            sura, aya = get_location(quran_data, i)
            page = get_page(quran_data, sura, aya)
            results.append({
                "text": verse,
                "sura": sura,
                "aya":  aya,
                "page": page,
            })
    return results


def get_location(quran_data: dict, verse_index: int) -> tuple[int, int]:
    for sura_num in range(1, len(quran_data["Sura"])):
        start = int(quran_data["Sura"][sura_num][0])
        count = int(quran_data["Sura"][sura_num][1])
        if start <= verse_index < start + count:
            return sura_num, verse_index - start + 1
    return 1, 1


def get_page(quran_data: dict, sura: int, aya: int) -> int:
    for page_num, page_data in enumerate(quran_data.get("Page", []), 1):
        if not page_data or len(page_data) < 2:
            continue
        p_sura, p_aya = page_data[0], page_data[1]
        if p_sura > sura or (p_sura == sura and p_aya > aya):
            return page_num - 2
    return 604


def make_snippet(verse: str, query: str, context_words: int = 4) -> str:
    """Return the matching phrase with `context_words` words on each side.

    Uses a word-index approach:
      1. Split verse into words; build a parallel list of normalized words.
      2. Join normalized words into a full string and find the query match.
      3. Walk the word boundaries to find which word indices cover the match.
      4. Return the corresponding original words plus context on each side.
    """
    norm_verse = normalize_arabic(verse)
    norm_query = normalize_arabic(query)
    if not norm_query or norm_query not in norm_verse:
        return verse[:120] + ("…" if len(verse) > 120 else "")

    orig_words = verse.split()
    norm_words = [normalize_arabic(w) for w in orig_words]

    # Build a joined string from norm_words with single spaces (mirrors norm_verse structure)
    joined_norm = " ".join(norm_words)

    # Find match span in joined_norm
    match_start = joined_norm.find(norm_query)
    if match_start == -1:
        return verse[:120] + ("…" if len(verse) > 120 else "")
    match_end = match_start + len(norm_query)

    # Map character positions in joined_norm → word indices
    char_to_word: list[int] = []
    for wi, nw in enumerate(norm_words):
        for _ in nw:
            char_to_word.append(wi)
        if wi < len(norm_words) - 1:
            char_to_word.append(wi)  # the space character between words

    # Find word index range that covers the match
    first_word = char_to_word[match_start] if match_start < len(char_to_word) else 0
    last_word  = char_to_word[min(match_end - 1, len(char_to_word) - 1)]

    # Context slices
    left_start  = max(0, first_word - context_words)
    right_end   = min(len(orig_words), last_word + context_words + 1)

    prefix = ("…" if left_start > 0 else "")
    suffix = ("…" if right_end < len(orig_words) else "")

    chunk = " ".join(orig_words[left_start:right_end])
    return prefix + chunk + suffix
