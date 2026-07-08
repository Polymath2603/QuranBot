"""tafsir.py — Quran tafsir from AlQuran.cloud API.

Cache hierarchy:
  1. In-memory LRU
  2. SQLite DB (persistent across restarts, 30-day TTL)
  3. AlQuran.cloud API
"""
import json
import logging
import urllib.request
import asyncio
from datetime import datetime, timezone, timedelta

from config import QURAN_API, DOWNLOAD_TIMEOUT, TAFSIR_SOURCES, DEFAULT_TAFSIR
from .utils import LRUCache

logger    = logging.getLogger(__name__)
_mem      = LRUCache(max_size=500)
CACHE_TTL = timedelta(days=30)


async def _db_get(key: str) -> str | None:
    try:
        from .database import get_session, TafsirCache, select
        s   = get_session()
        result = await s.execute(select(TafsirCache).filter_by(cache_key=key))
        row = result.scalars().first()
        if row:
            age = datetime.now(timezone.utc) - row.created_at.replace(tzinfo=timezone.utc)
            if age < CACHE_TTL:
                await s.close()
                return row.text
            # Use execution to delete
            from sqlalchemy import delete
            await s.execute(delete(TafsirCache).filter_by(cache_key=key))
            await s.commit()
        await s.close()
    except Exception as e:
        logger.warning("DB tafsir read: %s", e)
    return None


async def _db_set(key: str, text: str) -> None:
    try:
        from .database import get_session, TafsirCache, select
        s   = get_session()
        result = await s.execute(select(TafsirCache).filter_by(cache_key=key))
        row = result.scalars().first()
        if row:
            row.text = text; row.created_at = datetime.now(timezone.utc)
        else:
            s.add(TafsirCache(cache_key=key, text=text))
        await s.commit()
        await s.close()
    except Exception as e:
        logger.warning("DB tafsir write: %s", e)


def _fetch_sync(url: str):
    """Blocking network fetch."""
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as r:
        return json.loads(r.read())


async def get_tafsir(sura: int, aya: int, source: str = "muyassar") -> str | None:
    src_info = TAFSIR_SOURCES.get(source, TAFSIR_SOURCES[DEFAULT_TAFSIR])
    edition  = src_info["edition"]
    key      = f"{edition}:{sura}:{aya}"

    cached = _mem.get(key)
    if cached is not None:
        return cached

    db = await _db_get(key)
    if db is not None:
        _mem.set(key, db)
        return db

    url = f"{QURAN_API}/ayah/{sura}:{aya}/editions/quran-uthmani,{edition}"
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch_sync, url)
        if data.get("data") and len(data["data"]) > 1:
            text = data["data"][1].get("text", "")
            _mem.set(key, text)
            await _db_set(key, text)
            return text
    except Exception as e:
        logger.warning("Tafsir API failed %s:%s: %s", sura, aya, e)

    return None
