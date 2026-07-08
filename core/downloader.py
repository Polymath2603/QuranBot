import logging
import urllib.request
from pathlib import Path
from config import AUDIO_API, AUDIO_DIR, DOWNLOAD_TIMEOUT

logger = logging.getLogger(__name__)

def download_audio(voice: str, sura: int, aya: int) -> Path | None:
    url  = f"{AUDIO_API}/{voice}/{sura:03d}{aya:03d}.mp3"
    path = AUDIO_DIR / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            logger.info(f"Downloading {sura}:{aya} (attempt {attempt+1})")
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as r:
                path.write_bytes(r.read())
            return path
        except Exception as e:
            logger.warning(f"Download attempt {attempt+1} failed for {sura}:{aya}: {e}")
            if path.exists():
                path.unlink()
    return None


