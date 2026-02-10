import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

AUDIO_API = "https://everyayah.com/data"
QURAN_API = "https://api.alquran.cloud/v1"

DEFAULT_VOICE = "Alafasy_64kbps"
VOICES = {
    "Alafasy_64kbps":                "مشاري العفاسي",
    "Husary_64kbps":                 "محمود الحصري",
    "Minshawi_Murattal_128kbps":     "محمد المنشاوي",
    "Abdul_Basit_Mujawwad_128kbps":  "عبد الباسط عبد الصمد",
}