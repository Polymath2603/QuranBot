import urllib.request
from pathlib import Path
from config import AUDIO_API, DATA_DIR


def download_audio(voice, sura, aya):
    url = f"{AUDIO_API}/{voice}/{sura:03d}{aya:03d}.mp3"
    path = DATA_DIR / "audio" / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
    
    if path.exists():
        return path
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    for attempt in range(3):
        try:
            print(f"Downloading {sura}:{aya}... (Attempt {attempt + 1})")
            # Set a 10-second timeout for the download
            with urllib.request.urlopen(url, timeout=10) as response:
                with open(path, "wb") as f:
                    f.write(response.read())
            return path
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if path.exists():
                path.unlink()  # Delete partial/corrupted file
            if attempt == 2:
                return None
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