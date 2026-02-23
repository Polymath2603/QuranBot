"""utils.py — Shared utility functions for QBot."""
import logging, shutil, time
from collections import OrderedDict
from pathlib import Path
from config import PURGE_THRESHOLD_MB, WARN_THRESHOLD_MB, RATE_WINDOW_SECONDS, RATE_MAX_REQUESTS

logger = logging.getLogger(__name__)

def safe_filename(title: str) -> str:
    return title.replace("/", "-").replace(":", "-")

async def delete_status_msg(msg) -> None:
    if not msg: return
    try:
        await msg.edit_text(".")
        await msg.delete()
    except Exception: pass

def get_free_mb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024 * 1024)

def _purge_dir_by_mtime(directory: Path, target_free_mb: float) -> int:
    if not directory.exists(): return 0
    files = sorted([f for f in directory.rglob("*") if f.is_file()], key=lambda f: f.stat().st_mtime)
    deleted = 0
    for f in files:
        if get_free_mb(directory) >= target_free_mb: break
        try: f.unlink(); deleted += 1; logger.info(f"Purged: {f}")
        except Exception as e: logger.warning(f"Could not delete {f}: {e}")
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir():
            try: d.rmdir()
            except OSError: pass
    return deleted

def check_and_purge_storage(*dirs: Path) -> None:
    if not dirs: return
    for d in dirs: d.mkdir(parents=True, exist_ok=True)
    free_mb = get_free_mb(dirs[0])
    if free_mb >= WARN_THRESHOLD_MB: return
    logger.warning(f"Low disk space: {free_mb:.0f} MB free.")
    if free_mb < PURGE_THRESHOLD_MB:
        logger.warning("Starting storage purge...")
        total = sum(_purge_dir_by_mtime(d, PURGE_THRESHOLD_MB * 1.5) for d in dirs)
        logger.info(f"Purge complete. Deleted {total} file(s).")

_rate_store: dict[int, list[float]] = {}

def is_rate_limited(telegram_id: int) -> bool:
    now = time.monotonic()
    ts = [t for t in _rate_store.get(telegram_id, []) if now - t < RATE_WINDOW_SECONDS]
    if len(ts) >= RATE_MAX_REQUESTS:
        _rate_store[telegram_id] = ts
        return True
    ts.append(now)
    _rate_store[telegram_id] = ts
    return False

class LRUCache:
    def __init__(self, max_size: int = 500):
        self._store: OrderedDict = OrderedDict()
        self._max_size = max_size
    def get(self, key: str):
        if key not in self._store: return None
        self._store.move_to_end(key)
        return self._store[key]
    def set(self, key: str, value) -> None:
        if key in self._store: self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size: self._store.popitem(last=False)
    def __contains__(self, key: str) -> bool:
        return key in self._store
