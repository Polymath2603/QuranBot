"""config.py — Central configuration. All constants live here.

To add a reciter: append to VOICES.
To add a tafsir source: append to TAFSIR_SOURCES.
To add a mushaf image source: append to PAGE_SOURCES.
To add a hadith database: append to HADITH_FILES.

The env-derived / scalar settings are centralized in the typed ``Settings``
dataclass (single source of truth, validated once at import). The historical
flat module-level names (BOT_TOKEN, VOICES, VIDEO_SIZES, ...) are re-exported
from ``settings`` so every existing ``from config import X`` site keeps working
unchanged.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
AUDIO_DIR  = BASE_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "output"
LOCALE_DIR = BASE_DIR / "locales"


@dataclass(frozen=True)
class Settings:
    """Typed, validated application configuration.

    Built once from environment + constants. Immutable so downstream code
    can rely on stable values.
    """

    # ── Bot credentials (from .env) ──────────────────────────────────
    bot_token:  str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    channel_url: str = field(default_factory=lambda: os.getenv("CHANNEL_URL", ""))
    channel_id: str = field(default_factory=lambda: os.getenv("CHANNEL_ID", ""))
    donate_url: str = field(default_factory=lambda: os.getenv("DONATE_URL", ""))
    username:   str = field(default_factory=lambda: os.getenv("PAGE_USERNAME", ""))

    # ── API endpoints ────────────────────────────────────────────────
    audio_api: str = "https://everyayah.com/data"
    quran_api: str = "https://api.alquran.cloud/v1"

    # ── FFmpeg — system-installed binaries ───────────────────────────
    ffmpeg_bin:  str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    # ── HTTP / network ───────────────────────────────────────────────
    http_connect_timeout: int = 30
    http_read_timeout:    int = 180
    http_write_timeout:   int = 180
    http_pool_size:       int = 8
    http_pool_timeout:    int = 60
    download_timeout:     int = 60

    # ── Limits ───────────────────────────────────────────────────────
    char_limit:           int = 800
    max_ayas_per_request: int = 40
    image_chars_limit:    int = 1200

    # ── Rate limiting ────────────────────────────────────────────────
    rate_window_seconds: int = 3600
    rate_max_requests:   int = 10

    # ── Storage purge ────────────────────────────────────────────────
    purge_threshold_mb: int = 200
    warn_threshold_mb:  int = 500

    # ── Daily hadith scheduler ───────────────────────────────────────
    daily_hadith_count: int = field(
        default_factory=lambda: int(os.getenv("DAILY_HADITH_COUNT", "3"))
    )

    # ── Admin ────────────────────────────────────────────────────────
    admin_ids: list[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])


settings = Settings()

# Re-export flat scalars from the typed Settings object (back-compat API).
BOT_TOKEN   = settings.bot_token
CHANNEL_URL = settings.channel_url
CHANNEL_ID  = settings.channel_id
DONATE_URL  = settings.donate_url
USERNAME    = settings.username

AUDIO_API = settings.audio_api
QURAN_API = settings.quran_api

FFMPEG_BIN  = settings.ffmpeg_bin
FFPROBE_BIN = settings.ffprobe_bin

HTTP_CONNECT_TIMEOUT = settings.http_connect_timeout
HTTP_READ_TIMEOUT    = settings.http_read_timeout
HTTP_WRITE_TIMEOUT   = settings.http_write_timeout
HTTP_POOL_SIZE       = settings.http_pool_size
HTTP_POOL_TIMEOUT    = settings.http_pool_timeout
DOWNLOAD_TIMEOUT     = settings.download_timeout

CHAR_LIMIT           = settings.char_limit
MAX_AYAS_PER_REQUEST = settings.max_ayas_per_request
IMAGE_CHARS_LIMIT    = settings.image_chars_limit

RATE_WINDOW_SECONDS  = settings.rate_window_seconds
RATE_MAX_REQUESTS    = settings.rate_max_requests

PURGE_THRESHOLD_MB   = settings.purge_threshold_mb
WARN_THRESHOLD_MB    = settings.warn_threshold_mb

DAILY_HADITH_COUNT = settings.daily_hadith_count
DAILY_HADITH_HOURS = [
    round(24 * i / DAILY_HADITH_COUNT) % 24 for i in range(DAILY_HADITH_COUNT)
]

ADMIN_IDS: list = settings.admin_ids

# ── Voices / reciters ────────────────────────────────────────────────────────
# Each entry: code → {ar: Arabic name, en: English name}
DEFAULT_VOICE = "Nasser_Alqatami_128kbps"
VOICES: dict[str, dict] = {
    # Preferred qualities (64kbps or 128kbps)
    "Alafasy_64kbps":                 {"ar": "مشاري العفاسي",         "en": "Mishary Alafasy"},
    "Husary_64kbps":                  {"ar": "محمود الحصري",          "en": "Mahmoud Al-Husary"},
    "Abdul_Basit_Murattal_64kbps":    {"ar": "عبد الباسط (مرتل)",      "en": "Abdul Basit (Murattal)"},
    "Abdul_Basit_Mujawwad_128kbps":   {"ar": "عبد الباسط (مجود)",      "en": "Abdul Basit (Mujawwad)"},
    "Abdurrahmaan_As-Sudais_192kbps": {"ar": "عبد الرحمن السديس",    "en": "Abdurrahman As-Sudais"},
    "Saood_ash-Shuraym_64kbps":       {"ar": "سعود الشريم",           "en": "Saood ash-Shuraym"},
    "Abu_Bakr_Ash-Shaatree_64kbps":   {"ar": "أبو بكر الشاطري",      "en": "Abu Bakr Ash-Shatri"},
    "Ahmed_ibn_Ali_al-Ajamy_128kbps": {"ar": "أحمد العجمي",          "en": "Ahmed Al-Ajamy"},
    "Ghamadi_40kbps":                 {"ar": "سعد الغامدي",          "en": "Saad Al-Ghamadi"},
    "Hani_Rifai_192kbps":             {"ar": "هاني الرفاعي",         "en": "Hani Ar-Rifai"},
    "Maher_AlMuaiqly_64kbps":         {"ar": "ماهر المعيقلي",        "en": "Maher Al-Muaiqly"},
    "Minshawy_Murattal_128kbps":      {"ar": "محمد صديق المنشاوي",  "en": "Mohamed Siddiq Al-Minshawi"},
    "Minshawy_Mujawwad_64kbps":       {"ar": "المنشاوي (مجود)",      "en": "Al-Minshawi (Mujawwad)"},
    "Nasser_Alqatami_128kbps":        {"ar": "ناصر القطامي",         "en": "Nasser Al-Qatami"},
    "Yasser_Ad-Dussary_128kbps":      {"ar": "ياسر الدوسري",         "en": "Yasser Ad-Dussary"},
    "Hudhaify_64kbps":                {"ar": "علي الحذيفي",          "en": "Ali Al-Hudhaify"},
    "Muhammad_Ayyoub_128kbps":        {"ar": "محمد أيوب",             "en": "Muhammad Ayyoub"},
    "Muhammad_Jibreel_64kbps":         {"ar": "محمد جبريل",            "en": "Muhammad Jibreel"},
    "Mustafa_Ismail_64kbps":          {"ar": "مصطفي إسماعيل",        "en": "Mustafa Ismail"},
    "Mohammad_al_Tablaway_64kbps":    {"ar": "محمد الطبلاوي",         "en": "Mohammad Al-Tablaway"},
    "Ibrahim_Al_Akhdar_64kbps":       {"ar": "إبراهيم الأخضر",        "en": "Ibrahim Al-Akhdar"},
    "Aziz_Alili_128kbps":             {"ar": "عزيز عليلي",           "en": "Aziz Alili"},
    "Sahl_Yassin_128kbps":            {"ar": "سهل ياسين",            "en": "Sahl Yassin"},
    "Warsh_Ibrahim_Walk_192kbps":     {"ar": "إبراهيم الأخضر (ورش)", "en": "Ibrahim Walk (Warsh)"},
}

# ── Tafsir sources ────────────────────────────────────────────────────────────
DEFAULT_TAFSIR = "muyassar"
TAFSIR_SOURCES: dict[str, dict] = {
    "muyassar": {"ar": "تفسير الميسر",  "en": "Al-Muyassar",        "edition": "ar.muyassar"},
    "jalalayn": {"ar": "تفسير الجلالين","en": "Al-Jalalayn",        "edition": "ar.jalalayn"},
    "en.asad":       {"ar": "تفسير أسد (إنجليزي)", "en": "Asad (English)", "edition": "en.asad"},
    "en.pickthall":  {"ar": "بيكثال (إنجليزي)", "en": "Pickthall (English)", "edition": "en.pickthall"},
    "ur.ahmedali":   {"ar": "أحمد علي (أردو)",    "en": "Ahmed Ali (Urdu)",   "edition": "ur.ahmedali"},
    "fr.hamidullah": {"ar": "حميد الله (فرنسي)",   "en": "Hamidullah (French)", "edition": "fr.hamidullah"},
    "id.jalalayn":   {"ar": "الجلالين (إندونيسي)", "en": "Jalalayn (Indonesian)", "edition": "id.jalalayn"},
    "tr.diyanet":    {"ar": "ديانت (تركي)",       "en": "Diyanet (Turkish)", "edition": "tr.diyanet"},
    "es.cortes":     {"ar": "كورتيس (إسباني)",    "en": "Cortes (Spanish)",  "edition": "es.cortes"},
    "de.aburida":    {"ar": "أبو رضا (ألماني)",    "en": "Abu Rida (German)", "edition": "de.aburida"},
}

# ── Mushaf page image sources ─────────────────────────────────────────────────
# Files:  DATA_DIR/images/{key}/{page_num}.png   (1-604)
# Cache:  DATA_DIR/hafs_pages.json               → {"1": "file_id", ...}
DEFAULT_PAGE_SOURCE = "hafs"
PAGE_SOURCES: dict[str, dict] = {
    "hafs":    {"ar": "مصحف حفص",        "en": "Hafs (IndoPak)"},
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
    "uthmani": str(DATA_DIR / "hafs.18.ttf"),
    "amiri":   str(DATA_DIR / "Amiri-Regular.ttf"),
    "noto":    str(DATA_DIR / "NotoNaskhArabic-Regular.ttf"),
}

CUSTOM_FONT_PATH =  str(DATA_DIR / "QuranBot_Custom_Font.ttf")

FONT_SETTINGS: dict[str, dict] = {
    "uthmani": {"clean": True,  "num": "arabic",  "brackets": False},
    "amiri":   {"clean": True, "num": "western", "brackets": True},
    "noto":    {"clean": True, "num": "western", "brackets": True},
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
VIDEO_DEFAULT_BG = "night"

# ── Video Tool Defaults (GUI/CLI) ─────────────────────────────────────────────
VIDEO_SETTINGS_FILE = BASE_DIR / ".video_settings.json"

VIDEO_TOOL_DEFAULTS = {
    "sura": 1,
    "start": 1,
    "end": 7,
    "voice": DEFAULT_VOICE,
    "font": "uthmani",
    "template": "enhanced",
    "text_color": "#FFFFFF",
    "border_width": 1,
    "border_color": "#000000",
    "bg_mode": "folder",
    "bg_color": "#0F192D",
    "bg_path": str(DATA_DIR / "backgrounds"),
    "bg_behavior": "permanent",
    "ratio": "portrait",
}

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
