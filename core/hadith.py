"""hadith.py — Arabic hadith from multiple local SQLite databases.

Each rawi (narrator) has their own SQLite file with schema:
    - hadiths: id, hadith_number, text, section_id, book_id
    - book_info: id, book_name, hadith_count
    - grades: id, hadith_id, scholar_name, grade

Files are stored in DATA_DIR and mapped to Arabic names via FILE_MAP.
Source: https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite

format_hadith() returns plain text — no Markdown or HTML.
"""
from __future__ import annotations

import logging
import random
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from config import DATA_DIR

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_ready = False   # set to True after first successful DB probe

# ── File mapping: filename → Arabic book name ───────────────────────────────
FILE_MAP: Dict[str, str] = {
    "ara-bukhari1.sqlite": "صحيح البخاري",
    "ara-muslim1.sqlite": "صحيح مسلم",
    "ara-abudawud1.sqlite": "سنن أبي داود",
    "ara-tirmidhi1.sqlite": "جامع الترمذي",
    "ara-nasai1.sqlite": "سنن النسائي",
    "ara-ibnmajah1.sqlite": "سنن ابن ماجه",
    "ara-malik1.sqlite": "موطأ مالك",
    "ara-nawawi1.sqlite": "الأربعون النووية",
    "ara-qudsi1.sqlite": "الأحاديث القدسية",
}


# ── DB helpers ─────────────────────────────────────────────────────────────

def _get_available_dbs() -> List[Tuple[Path, str]]:
    """Return list of (db_path, book_name) for available databases."""
    available = []
    for filename, book_name in FILE_MAP.items():
        db_path = DATA_DIR / "hadith" / filename
        if db_path.exists():
            available.append((db_path, book_name))
    return available


def _get_db_total(conn: sqlite3.Connection) -> int:
    """Get total hadith count from hadiths table."""
    try:
        row = conn.execute("SELECT COUNT(*) FROM hadiths").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def _get_random_from_db(conn: sqlite3.Connection, book_name: str) -> Dict | None:
    """Fetch a random hadith from a single database."""
    total = _get_db_total(conn)
    if total == 0:
        return None

    # Try up to 5 times to get a non-empty text
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

        # Try to get grade from grades table
        grade = ""
        try:
            grade_row = conn.execute(
                "SELECT grade FROM grades WHERE hadith_id = ? LIMIT 1",
                (hadith_id,)
            ).fetchone()
            if grade_row:
                grade = grade_row[0] or ""
        except Exception:
            pass

        return {
            "text": text,
            "book_name": book_name,
            "number": str(hadith_number) if hadith_number else "",
            "grade": grade,
        }
    
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def _ensure_dbs() -> bool:
    """Check if any DB files are available. Thread-safe."""
    global _ready
    with _lock:
        if _ready:
            return True
        available = _get_available_dbs()
        if available:
            _ready = True
            return True
        return False


def get_total_count() -> int:
    """Get total hadith count across all databases."""
    if not _ensure_dbs():
        return 0
    
    total = 0
    for db_path, _ in _get_available_dbs():
        try:
            conn = sqlite3.connect(str(db_path))
            total += _get_db_total(conn)
            conn.close()
        except Exception as e:
            logger.warning("Failed to count %s: %s", db_path.name, e)
    
    return total


def get_random_hadith() -> Dict | None:
    """Return a random hadith dict with keys: text, book_name, number, grade."""
    if not _ensure_dbs():
        return None
        
    available = _get_available_dbs()
    if not available:
        return None
    
    # Pick a random database weighted by size
    weights = []
    for db_path, _ in available:
        try:
            conn = sqlite3.connect(str(db_path))
            count = _get_db_total(conn)
            conn.close()
            weights.append(max(count, 1))
        except Exception:
            weights.append(1)
    
    # Select database based on weights
    total_weight = sum(weights)
    if total_weight == 0:
        return None
        
    pick = random.randint(1, total_weight)
    cumulative = 0
    selected_idx = 0
    for i, w in enumerate(weights):
        cumulative += w
        if pick <= cumulative:
            selected_idx = i
            break
    
    db_path, book_name = available[selected_idx]
    
    try:
        conn = sqlite3.connect(str(db_path))
        entry = _get_random_from_db(conn, book_name)
        conn.close()
        return entry
    except Exception as e:
        logger.warning("DB hadith fetch failed for %s: %s", book_name, e)
        return None


def format_hadith(entry: Dict) -> str:
    """Format a hadith dict for Telegram (plain text, no markup).

    Format:
        {hadith text}
        ─────────────
        {book name} | حديث رقم {number}
        {grade (if present)}
    """
    text = (entry.get("text") or "").strip()
    if not text:
        return ""
    
    book = (entry.get("book_name") or "").strip()
    number = str(entry.get("number") or "").strip()
    grade = (entry.get("grade") or "").strip()

    parts = [text, "─────────────"]
    info = []
    if book:
        info.append(book)
    if number:
        info.append(f"حديث رقم {number}")
    if info:
        parts.append(" | ".join(info))
    
    # if grade:
    #    parts.append(f"الدرجة: {grade}")

    return "\n".join(parts)
