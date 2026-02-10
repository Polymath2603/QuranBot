import json
import urllib.request
from config import QURAN_API

cache = {}


def get_tafsir(sura, aya, edition="ar.muyassar"):
    key = f"{edition}:{sura}:{aya}"
    
    if key in cache:
        return cache[key]
    
    url = f"{QURAN_API}/ayah/{sura}:{aya}/editions/quran-uthmani,{edition}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            if data.get("data") and len(data["data"]) > 1:
                text = data["data"][1].get("text", "")
                cache[key] = text
                return text
    except:
        pass
    
    return None