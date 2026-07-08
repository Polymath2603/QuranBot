#!/usr/bin/env python3
"""Analyze word count per aya across all suras and write JSON."""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.data import load_quran_data, load_quran_text_simple, get_sura_start_index, get_sura_name


DATA_DIR = Path(__file__).parent / "data"


def count_words(text: str) -> int:
    return len(text.split())


def main():
    quran_data = load_quran_data(DATA_DIR)
    verses = load_quran_text_simple(DATA_DIR)

    results = []
    for sura in range(1, 115):
        sura_data = quran_data["Sura"][sura]
        aya_count = int(sura_data[1])
        sura_name = get_sura_name(quran_data, sura)

        counts = []
        for aya in range(1, aya_count + 1):
            idx = get_sura_start_index(quran_data, sura) + aya - 1
            verse = verses[idx]
            counts.append(count_words(verse))

        results.append({
            "name": sura_name,
            "sura": sura,
            "ayats": aya_count,
            "min": min(counts),
            "avg": round(statistics.mean(counts), 2),
            "max": max(counts),
        })

    out_path = Path(__file__).parent / "v.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Wrote {out_path} ({len(results)} suras)")


if __name__ == "__main__":
    main()
