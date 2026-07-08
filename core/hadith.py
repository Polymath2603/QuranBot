"""hadith.py — Arabic hadith from multiple local SQLite databases.

Schema (each db):
    hadiths:  id, hadith_number, text, section_id, book_id
    book_info: id, book_name, hadith_count
    grades:   id, hadith_id, scholar_name, grade

FILE_MAP is now sourced from config.HADITH_FILES.
Source: https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite
"""
from __future__ import annotations

import logging
import random
import sqlite3
from pathlib import Path
from typing import Optional

from config import DATA_DIR, HADITH_FILES

logger = logging.getLogger(__name__)


# ── Index: [(db_path, book_name, hadith_count), …] ───────────────────────────

def _build_index():
    index = []
    for filename, book_name in HADITH_FILES.items():
        db_path = DATA_DIR / "hadith" / filename
        if not db_path.exists():
            continue
        try:
            con = sqlite3.connect(str(db_path))
            cur = con.execute("SELECT COUNT(*) FROM hadiths")
            count = cur.fetchone()[0]
            con.close()
            if count > 0:
                index.append((db_path, book_name, count))
        except Exception as e:
            logger.warning("hadith index build failed for %s: %s", filename, e)
    return index

_DB_INDEX    = _build_index()
_TOTAL_COUNT = sum(c for _, _, c in _DB_INDEX)


# ── Random selection ──────────────────────────────────────────────────────────

def get_random_hadith() -> Optional[dict]:
    if not _DB_INDEX or _TOTAL_COUNT == 0:
        return None

    weights = [c for _, _, c in _DB_INDEX]
    db_path, book_name, _ = random.choices(_DB_INDEX, weights=weights, k=1)[0]

    try:
        con = sqlite3.connect(str(db_path))
        count = con.execute("SELECT COUNT(*) FROM hadiths").fetchone()[0]
        row   = con.execute(
            "SELECT id, hadith_number, text FROM hadiths ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        con.close()
        if not row:
            return None
        return {
            "book":         book_name,
            "hadith_number": row[1],
            "text":         row[2],
        }
    except Exception as e:
        logger.warning("hadith fetch failed for %s: %s", db_path, e)
        return None


# ── Formatting ────────────────────────────────────────────────────────────────

def format_hadith(entry: dict) -> str:
    if not entry or not entry.get("text"):
        return ""
    book   = entry.get("book", "")
    number = entry.get("hadith_number", "")
    text   = entry["text"].strip()
    header = f"📿 {book}" + (f" ({number})" if number else "")
    return f"{header}\n\n{text}"
