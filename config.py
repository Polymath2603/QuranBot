"""config.py — Central configuration. All constants live here.

To add a reciter: append to VOICES.
To add a tafsir source: append to TAFSIR_SOURCES.
To add a mushaf image source: append to PAGE_SOURCES.
To add a hadith database: append to HADITH_FILES.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOCALE_DIR = BASE_DIR / "locales"

# ── Bot credentials (from .env) ───────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
CHANNEL_ID  = os.getenv("CHANNEL_ID", "")
DONATE_URL  = os.getenv("DONATE_URL", "")   # link to donation post

# ── API endpoints ─────────────────────────────────────────────────────────────
AUDIO_API = "https://everyayah.com/data"
QURAN_API = "https://api.alquran.cloud/v1"

# ── FFmpeg — static builds in bin/ take priority over system install ──────────
def _find_bin(name: str) -> str:
    local = BASE_DIR / "bin" / name
    if local.exists() and local.stat().st_mode & 0o111:
        return str(local)
    return name

FFMPEG_BIN  = _find_bin("ffmpeg")
FFPROBE_BIN = _find_bin("ffprobe")

# ── HTTP / network ────────────────────────────────────────────────────────────
HTTP_CONNECT_TIMEOUT = 30
HTTP_READ_TIMEOUT    = 180
HTTP_WRITE_TIMEOUT   = 180
HTTP_POOL_SIZE       = 8
HTTP_POOL_TIMEOUT    = 60
DOWNLOAD_TIMEOUT     = 60

# ── Limits ────────────────────────────────────────────────────────────────────
CHAR_LIMIT           = 800    # max chars per Telegram message
MAX_AYAS_PER_REQUEST = 40     # max ayas per audio/video request
IMAGE_CHARS_LIMIT    = 1200   # max verse chars for image button (single-image only, no paging)

# ── Rate limiting ─────────────────────────────────────────────────────────────
RATE_WINDOW_SECONDS  = 3600
RATE_MAX_REQUESTS    = 10

# ── Storage purge ─────────────────────────────────────────────────────────────
PURGE_THRESHOLD_MB   = 200
WARN_THRESHOLD_MB    = 500

# ── Daily hadith scheduler ────────────────────────────────────────────────────
# Send times auto-distributed across 24h UTC.
# count=3 → [0, 8, 16];  count=4 → [0, 6, 12, 18]
DAILY_HADITH_COUNT = int(os.getenv("DAILY_HADITH_COUNT", "3"))
DAILY_HADITH_HOURS = [round(24 * i / DAILY_HADITH_COUNT) % 24 for i in range(DAILY_HADITH_COUNT)]

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN_IDS: list = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ── Voices / reciters ─────────────────────────────────────────────────────────
# Each entry: code → {ar: Arabic name, en: English name}
DEFAULT_VOICE = "Alafasy_64kbps"
VOICES: dict[str, dict] = {
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

# ── Tafsir sources ────────────────────────────────────────────────────────────
# Local file (if present): DATA_DIR/tafsir/{key}.json  → {"sura:aya": "text", ...}
# Fallback: AlQuran.cloud API  (edition string → EDITIONS in tafsir.py)
DEFAULT_TAFSIR = "muyassar"
TAFSIR_SOURCES: dict[str, dict] = {
    "muyassar": {"ar": "تفسير الميسر",  "en": "Al-Muyassar",  "edition": "ar.muyassar"},
    "jalalayn": {"ar": "تفسير الجلالين","en": "Al-Jalalayn",  "edition": "ar.jalalayn"},
}

# ── Mushaf page image sources ─────────────────────────────────────────────────
# Files:  DATA_DIR/images/{key}/{page_num}.png   (1-604)
# Cache:  DATA_DIR/images/{key}/ids.json         → {"1": "file_id", ...}
DEFAULT_PAGE_SOURCE = "hafs"
PAGE_SOURCES: dict[str, dict] = {
    "hafs":    {"ar": "مصحف حفص",        "en": "Hafs (IndoPak)"},
    "warsh":   {"ar": "مصحف ورش",        "en": "Warsh"},
    "tajweed": {"ar": "مصحف التجويد",    "en": "Color Tajweed"},
}

# ── Hadith databases ──────────────────────────────────────────────────────────
# Files in DATA_DIR/hadith/{filename}
# Source: https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite
HADITH_FILES: dict[str, str] = {
    "ara-bukhari1.sqlite":  "صحيح البخاري",
    "ara-muslim1.sqlite":   "صحيح مسلم",
    "ara-abudawud1.sqlite": "سنن أبي داود",
    "ara-tirmidhi1.sqlite": "جامع الترمذي",
    "ara-nasai1.sqlite":    "سنن النسائي",
    "ara-ibnmajah1.sqlite": "سنن ابن ماجه",
    "ara-malik1.sqlite":    "موطأ مالك",
    "ara-nawawi1.sqlite":   "الأربعون النووية",
    "ara-qudsi1.sqlite":    "الأحاديث القدسية",
    "ara-dehlawi1.sqlite":  "حجة الله البالغة",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
# Extra font files must be placed in data/
FONT_PATHS: dict[str, str] = {
    "uthmani": str(DATA_DIR / "KFGQPC Uthmanic Script HAFS.otf.ttf"),
    "amiri":   str(DATA_DIR / "Amiri-Regular.ttf"),
    "noto":    str(DATA_DIR / "NotoNaskhArabic-Regular.ttf"),
}
FONT_PATH = FONT_PATHS["uthmani"]   # legacy alias

IMAGE_DEFAULT_FONT = "uthmani"
VIDEO_DEFAULT_FONT = "uthmani"

# ── Image backgrounds & text colors ──────────────────────────────────────────
IMAGE_BACKGROUNDS: dict[str, tuple] = {
    "parchment": (242, 223, 185, 255),
    "dark":      (0,   0,   0,   255),
    "night":     (15,  25,  45,  255),
}
IMAGE_TEXT_COLORS: dict[str, tuple] = {
    "parchment": (55,  35,  10,  255),
    "dark":      (255, 255, 255, 255),
    "night":     (220, 200, 155, 255),
}
IMAGE_DEFAULT_BG = "parchment"

# ── Image resolution options ──────────────────────────────────────────────────
# None → auto-height (natural width, no fixed canvas)
IMAGE_RESOLUTIONS: dict[str, tuple | None] = {
    "auto":      None,
    "portrait":  (1080, 1920),
    "landscape": (1920, 1080),
}
DEFAULT_IMAGE_RESOLUTION = "auto"

# ── Video ─────────────────────────────────────────────────────────────────────
VIDEO_FPS           = 24
VIDEO_FADE_DURATION = 1
VIDEO_SYNC_OFFSET   = -0.5
VIDEO_FONT_SIZE     = 36
VIDEO_MIN_FONT_SIZE = 26
VIDEO_PADDING       = 40
IMAGE_PADDING       = 20   # smaller horizontal pad for verse images (portrait/landscape)

# Portrait 9:16 and landscape 16:9 — kept small for fast encode
VIDEO_SIZES: dict[str, tuple] = {
    "portrait":  (630, 1120),
    "landscape": (1120, 630),
}
VIDEO_DEFAULT_RATIO = "portrait"

# Video backgrounds (FFmpeg lavfi hex color)
VIDEO_BACKGROUNDS: dict[str, str] = {
    "dark":      "0x000000",
    "parchment": "0xF2DFB9",
    "night":     "0x0F192D",
}
VIDEO_DEFAULT_BG = "parchment"

# ── File-ID key index helpers ─────────────────────────────────────────────────
# Compact integer indices keep keys short and legible.
_FONT_LIST    = ["uthmani", "amiri", "noto"]
_IMG_THEME    = ["parchment", "dark", "night"]
_VID_THEME    = ["dark", "parchment", "night"]
_IMG_RES      = ["auto", "portrait", "landscape"]
_VID_RATIO    = ["portrait", "landscape"]

def img_fid_key(sura: int, start: int, end: int,
                font_key: str, bg_key: str, resolution: str) -> str:
    f = _FONT_LIST.index(font_key)  if font_key  in _FONT_LIST else 0
    t = _IMG_THEME.index(bg_key)   if bg_key    in _IMG_THEME  else 0
    r = _IMG_RES.index(resolution) if resolution in _IMG_RES   else 0
    return f"image:{sura}:{start}:{end}:{f}:{t}:{r}"

def vid_fid_key(reciter: str, sura: int, start: int, end: int,
                font_key: str, bg_key: str, ratio: str) -> str:
    f = _FONT_LIST.index(font_key) if font_key in _FONT_LIST else 0
    t = _VID_THEME.index(bg_key)  if bg_key   in _VID_THEME  else 0
    r = _VID_RATIO.index(ratio)   if ratio     in _VID_RATIO  else 0
    return f"video:{reciter}:{sura}:{start}:{end}:{f}:{t}:{r}"

def aud_fid_key(reciter: str, sura: int, start: int, end: int) -> str:
    return f"audio:{reciter}:{sura}:{start}:{end}"
