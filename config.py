import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOCALE_DIR = BASE_DIR / "locales"

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
CHANNEL_ID  = os.getenv("CHANNEL_ID", "")
DONATE_URL  = os.getenv("DONATE_URL", "")  # link to channel post with donation addresses

AUDIO_API = "https://everyayah.com/data"
QURAN_API = "https://api.alquran.cloud/v1"

# ---------------------------------------------------------------------------
# FFmpeg binaries — static builds in bin/ take priority over system install
# ---------------------------------------------------------------------------
def _find_bin(name: str) -> str:
    """Return path to local bin/{name} if it exists and is executable, else name (system PATH)."""
    local = BASE_DIR / "bin" / name
    if local.exists() and local.stat().st_mode & 0o111:
        return str(local)
    return name   # rely on system PATH

FFMPEG_BIN  = _find_bin("ffmpeg")
FFPROBE_BIN = _find_bin("ffprobe")

CHAR_LIMIT  = 800

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
HTTP_CONNECT_TIMEOUT = 20
HTTP_READ_TIMEOUT    = 90
HTTP_WRITE_TIMEOUT   = 90   # sending large audio/video files
HTTP_POOL_SIZE       = 8    # keep small on phone/low-RAM server
HTTP_POOL_TIMEOUT    = 30   # seconds to wait for a free connection
DOWNLOAD_TIMEOUT     = 30

# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------
VIDEO_FPS           = 24
VIDEO_FADE_DURATION = 1          # seconds between verse transitions
VIDEO_SYNC_OFFSET   = -0.5       # fixed seconds to shift text track forward relative to audio
VIDEO_FONT_SIZE     = 36         # starting font size, auto-shrinks to fit
VIDEO_MIN_FONT_SIZE = 26
VIDEO_PADDING       = 40         # px padding inside frame
FONT_PATH           = str(DATA_DIR / "KFGQPC Uthmanic Script HAFS.otf.ttf")

# Portrait 9:16 and landscape 16:9 — kept small for fast encode
VIDEO_SIZES = {
    "portrait":  (630, 1120),
    "landscape": (1120, 630),
}
VIDEO_DEFAULT_RATIO = "portrait"

# ---------------------------------------------------------------------------
# Storage / rate limiting
# ---------------------------------------------------------------------------
PURGE_THRESHOLD_MB  = 200
WARN_THRESHOLD_MB   = 500
RATE_WINDOW_SECONDS = 3600
RATE_MAX_REQUESTS   = 10

# ---------------------------------------------------------------------------
# Daily hadith scheduler
# ---------------------------------------------------------------------------
# Number of hadiths sent to CHANNEL_ID each day (set 0 to disable).
# Send times are auto-distributed evenly across 24h UTC:
#   DAILY_HADITH_COUNT=1 → [0]
#   DAILY_HADITH_COUNT=3 → [0, 8, 16]
#   DAILY_HADITH_COUNT=4 → [0, 6, 12, 18]
DAILY_HADITH_COUNT = int(os.getenv("DAILY_HADITH_COUNT", "3"))
# Auto-distribute sends evenly across 24h: count=3 → [0,8,16], count=4 → [0,6,12,18]
DAILY_HADITH_HOURS = [round(24 * i / DAILY_HADITH_COUNT) % 24 for i in range(DAILY_HADITH_COUNT)]

# ---------------------------------------------------------------------------
# Admin & request limits
# ---------------------------------------------------------------------------
# Telegram user IDs allowed to use /admin — add yours here
ADMIN_IDS: list = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
# Max ayas allowed per single audio/video request
MAX_AYAS_PER_REQUEST = 40

# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------
DEFAULT_VOICE = "Alafasy_64kbps"
VOICES = {
    "Alafasy_64kbps":                 {"ar": "مشاري العفاسي",         "en": "Mishary Alafasy"},
    "Husary_64kbps":                  {"ar": "محمود الحصري",          "en": "Mahmoud Al-Husary"},
    "Abdul_Basit_Murattal_192kbps":   {"ar": "عبد الباسط عبد الصمد", "en": "Abdul Basit"},
    "Abdurrahmaan_As-Sudais_192kbps": {"ar": "عبد الرحمن السديس",    "en": "Abdurrahman As-Sudais"},
    "Abu_Bakr_Ash-Shaatree_64kbps":   {"ar": "أبو بكر الشاطري",      "en": "Abu Bakr Ash-Shatri"},
    "Ahmed_ibn_Ali_al-Ajamy_128kbps": {"ar": "أحمد العجمي",          "en": "Ahmed Al-Ajamy"},
    "Ghamadi_40kbps":                 {"ar": "سعد الغامدي",          "en": "Saad Al-Ghamadi"},
    "Hani_Rifai_192kbps":             {"ar": "هاني الرفاعي",         "en": "Hani Ar-Rifai"},
    "Maher_AlMuaiqly_64kbps":         {"ar": "ماهر المعيقلي",        "en": "Maher Al-Muaiqly"},
    "MahmoudKhalil_Al-Husary_64kbps": {"ar": "محمود خليل الحصري",   "en": "Mahmoud Khalil Al-Husary"},
    "Minshawy_Murattal_128kbps":      {"ar": "محمد صديق المنشاوي",  "en": "Mohamed Siddiq Al-Minshawi"},
    "Nasser_Alqatami_128kbps":        {"ar": "ناصر القطامي",         "en": "Nasser Al-Qatami"},
    "Parhizgar_48kbps":               {"ar": "عبدالباسط هاشمي",      "en": "Shahriar Parhizgar"},
    "Yasser_Ad-Dussary_128kbps":      {"ar": "ياسر الدوسري",         "en": "Yasser Ad-Dussary"},
    "Ayman_Sowaid_64kbps":            {"ar": "أيمن سويد",            "en": "Ayman Sowaid"},
    "Aziz_Alili_128kbps":             {"ar": "عزيز عليلي",           "en": "Aziz Alili"},
    "Sahl_Yassin_128kbps":            {"ar": "سهل ياسين",            "en": "Sahl Yassin"},
    "Warsh_Ibrahim_Walk_192kbps":     {"ar": "إبراهيم الأخضر (ورش)", "en": "Ibrahim Walk (Warsh)"},
}
