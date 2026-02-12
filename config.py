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

# Reciter voices with localized names
VOICES = {
    "Alafasy_64kbps": {"ar": "مشاري العفاسي", "en": "Mishary Alafasy"},
    "Husary_64kbps": {"ar": "محمود الحصري", "en": "Mahmoud Al-Husary"},
    "Abdul_Basit_Murattal_192kbps": {"ar": "عبد الباسط عبد الصمد", "en": "Abdul Basit"},
    "Abdurrahmaan_As-Sudais_192kbps": {"ar": "عبد الرحمن السديس", "en": "Abdurrahman As-Sudais"},
    "Abu_Bakr_Ash-Shaatree_64kbps": {"ar": "أبو بكر الشاطري", "en": "Abu Bakr Ash-Shatri"},
    "Ahmed_ibn_Ali_al-Ajamy_128kbps": {"ar": "أحمد العجمي", "en": "Ahmed Al-Ajamy"},
    "Ghamadi_40kbps": {"ar": "سعد الغامدي", "en": "Saad Al-Ghamadi"},
    "Hani_Rifai_192kbps": {"ar": "هاني الرفاعي", "en": "Hani Ar-Rifai"},
    "Maher_AlMuaiqly_64kbps": {"ar": "ماهر المعيقلي", "en": "Maher Al-Muaiqly"},
    "MahmoudKhalil_Al-Husary_64kbps": {"ar": "محمود خليل الحصري", "en": "Mahmoud Khalil Al-Husary"},
    "Minshawy_Murattal_128kbps": {"ar": "محمد صديق المنشاوي", "en": "Mohamed Siddiq Al-Minshawi"},
    "Nasser_Alqatami_128kbps": {"ar": "ناصر القطامي", "en": "Nasser Al-Qatami"},
    "Parhizgar_48kbps": {"ar": "عبدالباسط هاشمي", "en": "Shahriar Parhizgar"},
    "Yasser_Ad-Dussary_128kbps": {"ar": "ياسر الدوسري", "en": "Yasser Ad-Dussary"},
    "Ayman_Sowaid_64kbps": {"ar": "أيمن سويد", "en": "Ayman Sowaid"},
    "Aziz_Alili_128kbps": {"ar": "عزيز عليلي", "en": "Aziz Alili"},
    "Sahl_Yassin_128kbps": {"ar": "سهل ياسين", "en": "Sahl Yassin"},
    "Warsh_Ibrahim_Walk_192kbps": {"ar": "إبراهيم الأخضر (ورش)", "en": "Ibrahim Walk (Warsh)"},
}