"""
Search module: Provides functionality for searching Quran verses.
"""

import difflib
from typing import Dict, List

from .data import get_sura_name


def search_verses(quran_data: dict, verses: List[str], query: str, 
                 max_results: int = 10) -> List[Dict]:
    """
    Search for verses containing query text.
    Uses substring matching first, then fuzzy matching.
    
    Args:
        quran_data: Quran data dictionary
        verses: List of all verses
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with keys: sura, aya, text
    """
    if not query or len(query) < 3:
        return []
    
    results = []
    query_lower = query.lower()
    
    # Phase 1: Substring matching
    for i, verse in enumerate(verses):
        if query_lower in verse.lower():
            sura_idx = _find_sura_for_verse_index(quran_data, i)
            if sura_idx is not None:
                aya = i - int(quran_data["Sura"][sura_idx][0]) + 1
                results.append({
                    "sura": sura_idx,
                    "aya": aya,
                    "text": verse
                })
                if len(results) >= max_results:
                    return results
    
    # Phase 2: Fuzzy matching if no substring matches found
    if not results:
        close_matches = difflib.get_close_matches(
            query, verses, n=max_results, cutoff=0.6
        )
        for verse in close_matches:
            try:
                i = verses.index(verse)
                sura_idx = _find_sura_for_verse_index(quran_data, i)
                if sura_idx is not None:
                    aya = i - int(quran_data["Sura"][sura_idx][0]) + 1
                    results.append({
                        "sura": sura_idx,
                        "aya": aya,
                        "text": verse
                    })
            except ValueError:
                continue
    
    return results


def _find_sura_for_verse_index(quran_data: dict, verse_index: int) -> int:
    """
    Find sura number that contains a verse at given index.
    
    Args:
        quran_data: Quran data dictionary
        verse_index: 0-based verse index
        
    Returns:
        1-based sura number or None
    """
    for sura_num in range(1, len(quran_data.get("Sura", []))):
        sura_start = int(quran_data["Sura"][sura_num][0])
        sura_end = sura_start + int(quran_data["Sura"][sura_num][1])
        if sura_start <= verse_index < sura_end:
            return sura_num
    return None


def format_search_results(results: List[Dict], quran_data: dict, 
                         lang: str = "ar") -> str:
    """
    Format search results as readable text.
    
    Args:
        results: List of search results from search_verses
        quran_data: Quran data dictionary
        lang: Language for sura names (ar, en)
        
    Returns:
        Formatted string for display
    """
    if not results:
        return "No results found"
    
    lines = [f"{'Sura':20} {'Aya':5} Text"]
    lines.append("-" * 80)
    
    for result in results:
        sura_name = get_sura_name(quran_data, result["sura"], lang)
        lines.append(
            f"{sura_name:20} {str(result["aya"]):5} {result["text"]}"
        )
    
    return "\n".join(lines)