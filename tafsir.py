"""
tafsir.py — Fetch and cache Quran tafsir from alquran.cloud API.

Cache strategy:
  1. In-memory LRU cache (max 500 entries) for fast repeat lookups.
  2. SQLite persistent cache (via database.py) with 30-day TTL.
  3. On miss: fetch from API, store in both caches.
"""
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta

from config import QURAN_API
from utils import LRUCache

logger = logging.getLogger(__name__)

# In-memory LRU cache
_mem_cache: LRUCache = LRUCache(max_size=500)

# Map user-facing tafsir source names to alquran.cloud edition identifiers
TAFSIR_EDITIONS: dict[str, str] = {
    "muyassar":  "ar.muyassar",
    "jalalayn":  "ar.jalalayn",
    "qurtubi":   "ar.qurtubi",
    "ibn-kathir": "ar.ibnikathir",
}

CACHE_TTL_DAYS = 30


def _get_db_cache(key: str) -> str | None:
    """Look up a tafsir entry in the SQLite cache. Returns text or None."""
    try:
        from database import get_session, TafsirCache
        session = get_session()
        row = session.query(TafsirCache).filter_by(cache_key=key).first()
        session.close()
        if row:
            age = datetime.now(timezone.utc) - row.created_at.replace(tzinfo=timezone.utc)
            if age < timedelta(days=CACHE_TTL_DAYS):
                return row.text
            # Expired — delete it
            session2 = get_session()
            session2.query(TafsirCache).filter_by(cache_key=key).delete()
            session2.commit()
            session2.close()
    except Exception as e:
        logger.warning(f"DB tafsir cache read error: {e}")
    return None


def _set_db_cache(key: str, text: str) -> None:
    """Store a tafsir entry in the SQLite cache."""
    try:
        from database import get_session, TafsirCache
        session = get_session()
        row = session.query(TafsirCache).filter_by(cache_key=key).first()
        if row:
            row.text = text
            row.created_at = datetime.now(timezone.utc)
        else:
            session.add(TafsirCache(cache_key=key, text=text))
        session.commit()
        session.close()
    except Exception as e:
        logger.warning(f"DB tafsir cache write error: {e}")


def get_tafsir(sura: int, aya: int, source: str = "muyassar") -> str | None:
    """
    Fetch tafsir text for a given sura/aya and tafsir source.

    Args:
        sura:   Surah number (1-114).
        aya:    Ayah number.
        source: User-facing source name (muyassar, jalalayn, qurtubi, ibn-kathir).

    Returns:
        Tafsir text string, or None if unavailable.
    """
    edition = TAFSIR_EDITIONS.get(source, "ar.muyassar")
    key = f"{edition}:{sura}:{aya}"

    # 1. In-memory cache
    cached = _mem_cache.get(key)
    if cached is not None:
        return cached

    # 2. DB cache
    db_cached = _get_db_cache(key)
    if db_cached is not None:
        _mem_cache.set(key, db_cached)
        return db_cached

    # 3. Fetch from API
    url = f"{QURAN_API}/ayah/{sura}:{aya}/editions/quran-uthmani,{edition}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
            if data.get("data") and len(data["data"]) > 1:
                text = data["data"][1].get("text", "")
                _mem_cache.set(key, text)
                _set_db_cache(key, text)
                return text
    except Exception as e:
        logger.warning(f"Tafsir API fetch failed for {sura}:{aya} ({edition}): {e}")

    return None
