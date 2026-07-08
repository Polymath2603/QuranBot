#!/usr/bin/env python3
"""Given a s:f-l range, returns min/avg/max word count per aya."""

import sys
import statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.data import load_quran_data, load_quran_text_simple, get_sura_start_index


DATA_DIR = Path(__file__).parent / "data"


def count_words(text: str) -> int:
    return len(text.split())


def get_verse(sura: int, aya: int, verses: list[str], quran_data: dict) -> str:
    idx = get_sura_start_index(quran_data, sura)
    return verses[idx + aya - 1]


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} s:f-l")
        print("Example: 1:1-7")
        sys.exit(1)

    arg = sys.argv[1]
    if ":" not in arg or "-" not in arg:
        print(f"Invalid format. Expected s:f-l, got {arg}")
        sys.exit(1)

    sura_str, range_str = arg.split(":")
    sura = int(sura_str)
    from_str, to_str = range_str.split("-")
    frm = int(from_str)
    to = int(to_str)

    quran_data = load_quran_data(DATA_DIR)
    verses = load_quran_text_simple(DATA_DIR)

    counts = []
    for aya in range(frm, to + 1):
        verse = get_verse(sura, aya, verses, quran_data)
        counts.append(count_words(verse))

    print(f"sura {sura}, verses {frm}-{to}  ({to - frm + 1} ayas)")
    print(f"min : {min(counts)}")
    print(f"avg : {statistics.mean(counts):.2f}")
    print(f"max : {max(counts)}")


if __name__ == "__main__":
    main()
