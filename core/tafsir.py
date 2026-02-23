"""tafsir.py — Fetch and cache Quran tafsir from alquran.cloud."""
import json, logging, urllib.request
from datetime import datetime, timezone, timedelta
from config import QURAN_API, DOWNLOAD_TIMEOUT
from .utils import LRUCache

logger    = logging.getLogger(__name__)
_mem      = LRUCache(max_size=500)
EDITIONS  = {"muyassar": "ar.muyassar", "jalalayn": "ar.jalalayn"}
CACHE_TTL = timedelta(days=30)

def _db_get(key: str) -> str | None:
    try:
        from .database import get_session, TafsirCache
        s = get_session()
        row = s.query(TafsirCache).filter_by(cache_key=key).first()
        s.close()
        if row:
            age = datetime.now(timezone.utc) - row.created_at.replace(tzinfo=timezone.utc)
            if age < CACHE_TTL: return row.text
            s2 = get_session()
            s2.query(TafsirCache).filter_by(cache_key=key).delete()
            s2.commit(); s2.close()
    except Exception as e:
        logger.warning(f"DB tafsir read: {e}")
    return None

def _db_set(key: str, text: str) -> None:
    try:
        from .database import get_session, TafsirCache
        s = get_session()
        row = s.query(TafsirCache).filter_by(cache_key=key).first()
        if row: row.text = text; row.created_at = datetime.now(timezone.utc)
        else: s.add(TafsirCache(cache_key=key, text=text))
        s.commit(); s.close()
    except Exception as e:
        logger.warning(f"DB tafsir write: {e}")

def get_tafsir(sura: int, aya: int, source: str = "muyassar") -> str | None:
    edition = EDITIONS.get(source, "ar.muyassar")
    key = f"{edition}:{sura}:{aya}"
    cached = _mem.get(key)
    if cached is not None: return cached
    db = _db_get(key)
    if db is not None: _mem.set(key, db); return db
    url = f"{QURAN_API}/ayah/{sura}:{aya}/editions/quran-uthmani,{edition}"
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as r:
            data = json.loads(r.read())
            if data.get("data") and len(data["data"]) > 1:
                text = data["data"][1].get("text", "")
                _mem.set(key, text); _db_set(key, text)
                return text
    except Exception as e:
        logger.warning(f"Tafsir API failed {sura}:{aya}: {e}")
    return None
