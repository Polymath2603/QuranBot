"""
utils.py — Shared utility functions for QBot.
"""
import logging
import shutil
import time
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def safe_filename(title: str) -> str:
    """Sanitize a title for use as a filename."""
    return title.replace("/", "-").replace(":", "-")


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

async def delete_status_msg(msg) -> None:
    """Silently delete a Telegram status message (edit to '.' first for mobile)."""
    if not msg:
        return
    try:
        await msg.edit_text(".")
        await msg.delete()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Storage management
# ---------------------------------------------------------------------------

PURGE_THRESHOLD_MB = 200   # start purging below this free space
WARN_THRESHOLD_MB  = 500   # log a warning below this free space


def get_free_mb(path: Path) -> float:
    """Return free disk space in MB for the partition containing *path*."""
    usage = shutil.disk_usage(path)
    return usage.free / (1024 * 1024)


def _purge_dir_by_mtime(directory: Path, target_free_mb: float) -> int:
    """
    Delete the oldest files in *directory* (by mtime) until free space
    exceeds *target_free_mb*.  Returns the number of files deleted.
    """
    if not directory.exists():
        return 0

    files = sorted(
        [f for f in directory.rglob("*") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
    )

    deleted = 0
    for f in files:
        if get_free_mb(directory) >= target_free_mb:
            break
        try:
            f.unlink()
            deleted += 1
            logger.info(f"Purged old file: {f}")
        except Exception as e:
            logger.warning(f"Could not delete {f}: {e}")

    # Remove empty subdirectories
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()  # only succeeds if empty
            except OSError:
                pass

    return deleted


def check_and_purge_storage(*dirs: Path) -> None:
    """
    Check free disk space and purge oldest files from the given directories
    if space is critically low.

    Call this before expensive audio/video generation.
    """
    if not dirs:
        return

    ref_path = dirs[0]
    free_mb = get_free_mb(ref_path)

    if free_mb >= WARN_THRESHOLD_MB:
        return

    logger.warning(f"Low disk space: {free_mb:.0f} MB free.")

    if free_mb < PURGE_THRESHOLD_MB:
        logger.warning("Starting storage purge...")
        total_deleted = 0
        for d in dirs:
            total_deleted += _purge_dir_by_mtime(d, target_free_mb=PURGE_THRESHOLD_MB * 1.5)
        logger.info(f"Purge complete. Deleted {total_deleted} file(s).")


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

# { telegram_id: [timestamp, timestamp, ...] }
_rate_store: dict[int, list[float]] = {}

RATE_WINDOW_SECONDS = 3600   # 1 hour window
RATE_MAX_REQUESTS   = 10     # max heavy operations per window


def is_rate_limited(telegram_id: int) -> bool:
    """
    Return True if the user has exceeded the heavy-operation rate limit.
    Automatically cleans up old timestamps.
    """
    now = time.monotonic()
    timestamps = _rate_store.get(telegram_id, [])

    # Remove timestamps outside the window
    timestamps = [t for t in timestamps if now - t < RATE_WINDOW_SECONDS]

    if len(timestamps) >= RATE_MAX_REQUESTS:
        _rate_store[telegram_id] = timestamps
        return True

    timestamps.append(now)
    _rate_store[telegram_id] = timestamps
    return False


# ---------------------------------------------------------------------------
# LRU cache (for tafsir in-memory fallback)
# ---------------------------------------------------------------------------

class LRUCache:
    """Simple LRU cache with a maximum size."""

    def __init__(self, max_size: int = 500):
        self._store: OrderedDict = OrderedDict()
        self._max_size = max_size

    def get(self, key: str):
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key: str, value) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def __contains__(self, key: str) -> bool:
        return key in self._store
