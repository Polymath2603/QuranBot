"""hadith.py — Arabic hadith from multiple local SQLite databases.

Each rawi (narrator) has their own SQLite file with schema:
    - hadiths: id, hadith_number, text, section_id, book_id
    - book_info: id, book_name, hadith_count
    - grades: id, hadith_id, scholar_name, grade

Files are stored in DATA_DIR/hadith/ and mapped to Arabic names via FILE_MAP.
Source: https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite

format_hadith() returns plain text — no Markdown or HTML.
"""
from __future__ import annotations

import logging
import random
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import DATA_DIR

logger = logging.getLogger(__name__)

# ── File mapping: filename → Arabic book name ───────────────────────────────
FILE_MAP: Dict[str, str] = {
    "ara-bukhari1.sqlite":  "صحيح البخاري",
    "ara-muslim1.sqlite":   "صحيح مسلم",
    "ara-abudawud1.sqlite": "سنن أبي داود",
    "ara-tirmidhi1.sqlite": "جامع الترمذي",
    "ara-nasai1.sqlite":    "سنن النسائي",
    "ara-ibnmajah1.sqlite": "سنن ابن ماجه",
    "ara-malik1.sqlite":    "موطأ مالك",
    "ara-nawawi1.sqlite":   "الأربعون النووية",
    "ara-qudsi1.sqlite":    "الأحاديث القدسية",
    "ara-dehlawi1.sqlite":  "حجة الله البالغة",
}


# ── Cached index: list of (db_path, book_name, hadith_count) ────────────────
# Built once at import time; DBs that don't exist are silently skipped.

def _build_index() -> List[Tuple[Path, str, int]]:
    """Scan available DB files and cache their hadith counts."""
    index = []
    for filename, book_name in FILE_MAP.items():
        db_path = DATA_DIR / "hadith" / filename
        if not db_path.exists():
            continue
        try:
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute("SELECT COUNT(*) FROM hadiths").fetchone()
                count = row[0] if row else 0
            if count > 0:
                index.append((db_path, book_name, count))
            else:
                logger.warning("Hadith DB %s is empty, skipping.", filename)
        except Exception as e:
            logger.warning("Failed to index %s: %s", filename, e)
    return index


_DB_INDEX: List[Tuple[Path, str, int]] = _build_index()
_TOTAL_COUNT: int = sum(c for _, _, c in _DB_INDEX)


# ── Internal fetch ─────────────────────────────────────────────────────────

def _fetch_random(db_path: Path, book_name: str, total: int) -> Optional[Dict]:
    """Fetch one random hadith from a single database."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            for _ in range(5):
                offset = random.randint(0, total - 1)
                row = conn.execute(
                    "SELECT hadith_number, text, id FROM hadiths LIMIT 1 OFFSET ?",
                    (offset,)
                ).fetchone()
                if not row:
                    continue
                hadith_number, text, hadith_id = row
                text = (text or "").strip()
                if not text:
                    continue
                grade = ""
                try:
                    g = conn.execute(
                        "SELECT grade FROM grades WHERE hadith_id = ? LIMIT 1",
                        (hadith_id,)
                    ).fetchone()
                    if g:
                        grade = g[0] or ""
                except Exception:
                    pass
                return {
                    "text":      text,
                    "book_name": book_name,
                    "number":    str(hadith_number) if hadith_number else "",
                    "grade":     grade,
                }
    except Exception as e:
        logger.warning("DB fetch failed for %s: %s", book_name, e)
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def get_total_count() -> int:
    """Total hadith count across all indexed databases (computed at startup)."""
    return _TOTAL_COUNT


def get_random_hadith() -> Optional[Dict]:
    """Return a random hadith dict: {text, book_name, number, grade}.

    Weighted by database size so larger collections are sampled more often.
    Returns None if no databases are available.
    """
    if not _DB_INDEX:
        return None

    # Weighted selection using precomputed counts
    pick = random.randint(1, _TOTAL_COUNT)
    cumulative = 0
    for db_path, book_name, count in _DB_INDEX:
        cumulative += count
        if pick <= cumulative:
            return _fetch_random(db_path, book_name, count)

    # Fallback: last entry (handles floating-point edge cases)
    db_path, book_name, count = _DB_INDEX[-1]
    return _fetch_random(db_path, book_name, count)


def format_hadith(entry: Dict) -> str:
    """Format a hadith dict for Telegram (plain text, no markup).

    Format:
        {hadith text}
        ─────────────
        {book name} | حديث رقم {number}
    """
    text = (entry.get("text") or "").strip()
    if not text:
        return ""

    book   = (entry.get("book_name") or "").strip()
    number = str(entry.get("number") or "").strip()

    parts = [text, "─────────────"]
    info  = []
    if book:
        info.append(book)
    if number:
        info.append(f"حديث رقم {number}")
    if info:
        parts.append(" | ".join(info))

    return "\n".join(parts)


