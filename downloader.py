import urllib.request
from pathlib import Path
from config import AUDIO_API, DATA_DIR


def download_audio(voice, sura, aya):
    url = f"{AUDIO_API}/{voice}/{sura:03d}{aya:03d}.mp3"
    path = DATA_DIR / "audio" / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
    
    if path.exists():
        return path
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"Downloading {sura}:{aya}...")
        urllib.request.urlretrieve(url, path)
        return path
    except Exception as e:
        print(f"Failed: {e}")
        return None


def download_sura(quran_data, voice, sura_num):
    aya_count = int(quran_data["Sura"][sura_num][1])
    files = []
    
    for aya in range(1, aya_count + 1):
        path = download_audio(voice, sura_num, aya)
        if path:
            files.append(path)
        else:
            return None
    
    return files