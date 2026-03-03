# 🔧 Technical Documentation

→ [README](README.en.md) · [Changelog](CHANGELOG.md) · [Todo](TODO.md)

---

## 🗂️ Project structure

```
QuranBot/
├── 🤖 bot.py              # All Telegram handlers + callback router
├── ⚙️  config.py           # Every constant in one place — edit here, not in modules
├── core/
│   ├── 🔊 audio.py        # gen_mp3(): downloads per-verse MP3s, concat + album-art strip
│   ├── 🎬 video.py        # gen_video(): Pillow PNGs + 3-pass FFmpeg pipeline
│   ├── 📄 subtitles.py    # SRT / LRC export with real ffprobe timestamps
│   ├── 📖 verses.py       # build_verse_keyboard(), send helpers, basmala handling
│   ├── 🧠 nlu.py          # Natural language parser — suras, ranges, pages, search
│   ├── 🔍 search.py       # Full-text search with comprehensive Arabic normalization
│   ├── 📚 tafsir.py       # AlQuran.cloud fetch + SQLite cache + LRU in-memory
│   ├── 📊 data.py         # load_quran_data(), load_quran_text(), index lookups
│   ├── ⬇️  downloader.py   # Per-verse MP3 downloader with retry
│   ├── 🗃️  database.py     # SQLAlchemy models: User, TafsirCache, BotStats, QueueItem
│   ├── ⏳ queue.py        # Serial request queue: SQLite-backed, position tracking, cancel
│   ├── 📿 hadith.py       # Random hadith from 9 local SQLite DBs — /hadith, /chadith
│   ├── 🌐 lang.py         # t(key, lang, **kwargs) — loads ar.json + en.json
│   └── 🛠️  utils.py        # safe_filename, storage purge, rate limiter, file_id cache
├── locales/
│   ├── 🇸🇦 ar.json         # Arabic UI strings
│   └── 🌐 en.json         # English UI strings
├── data/
│   ├── quran-data.json          # Sura metadata + page map (Tanzil.net)
│   ├── quran-uthmani.txt        # Full Uthmani text, one verse per line (Tanzil.net)
│   ├── quran-simple.txt         # Simplified text for display/search/subtitles (Tanzil.net)
│   ├── KFGQPC *.ttf             # Uthmanic font for video rendering
│   ├── audio/                   # Per-verse MP3 cache, auto-purged on low disk
│   └── hadith/                  # 9 SQLite databases (~35k hadiths total)
│       ├── ara-bukhari1.sqlite  # صحيح البخاري
│       ├── ara-muslim1.sqlite   # صحيح مسلم
│       ├── ara-abudawud1.sqlite # سنن أبي داود
│       ├── ara-tirmidhi1.sqlite # جامع الترمذي
│       ├── ara-nasai1.sqlite    # سنن النسائي
│       ├── ara-ibnmajah1.sqlite # سنن ابن ماجه
│       ├── ara-malik1.sqlite    # موطأ مالك
│       ├── ara-nawawi1.sqlite   # الأربعون النووية
│       ├── ara-qudsi1.sqlite    # الأحاديث القدسية
│       └── ara-dehlawi1.sqlite  # حجة الله البالغة
├── output/
│   ├── {reciter_code}/          # Generated MP3s and MP4s
│   └── file_ids.json            # Permanent Telegram file_id cache
├── bin/                         # (optional) Local ffmpeg/ffprobe binaries
│   ├── ffmpeg                   # Injected into PATH automatically by config.py
│   └── ffprobe
├── .env
├── .env.example
├── requirements.txt
├── README.md           # Arabic
├── README.en.md        # English
├── TECHNICAL.md
├── CHANGELOG.md
└── TODO.md
```

---

## 📦 Data sources & licenses

| File | Source | License |
|---|---|---|
| `quran-data.json` | [Tanzil.net](https://tanzil.net) — quran-data.js | [CC BY 3.0](https://tanzil.net/docs/quran_metadata) |
| `quran-uthmani.txt` | [Tanzil.net](https://tanzil.net) — Uthmani text | [CC BY 3.0](https://tanzil.net/docs/quran_text) |
| `quran-simple.txt` | [Tanzil.net](https://tanzil.net) — Simple text | [CC BY 3.0](https://tanzil.net/docs/quran_text) |
| `KFGQPC *.ttf` | [King Fahd Quran Printing Complex](https://fonts.qurancomplex.gov.sa) | Free for non-commercial use |
| `data/hadith/*.sqlite` | [IsmailHosenIsmailJames/compressed_hadith_sqlite](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
| Audio files | [EveryAyah.com](https://everyayah.com) | Free for non-commercial use |
| Tafsir API | [AlQuran.cloud](https://alquran.cloud/api) | Free API |

---

## 🏗️ Architecture

### Request flow

```
User message
  → message_router (NLU)
      → build_verse_keyboard → user taps button
          → callback_router → handler
              → rate limiter check
              → aya bounds + range validation
              → max aya cap (ranges only)
              → file_id cache hit? → send instantly, return
              → send position message ⏳
              → request_queue.enqueue(status_msg_id=pos_msg.id)
                  → _process_queue_item() [ThreadPoolExecutor]
                      → edit position msg to progress bar
                      → gen_mp3() / gen_video()
                      → edit to "." → delete
                      → bot.send_audio() / bot.send_video()
                      → cache file_id
```

### Concurrency

| Component | Role |
|---|---|
| asyncio main loop | All Telegram updates |
| `ThreadPoolExecutor(2)` | `gen_mp3` / `gen_video` off the asyncio event loop |
| `RequestQueue` | Serial consumer — one job at a time |
| `asyncio.run_coroutine_threadsafe` | Posts progress edits from worker thread |
| `hadith.py` | `get_random_hadith()` → local SQLite → `format_hadith()` → send |

---

## 🎬 Video pipeline (3 FFmpeg passes)

```
gen_video(verse_texts, start_aya, title, sura, voice, audio_path, ratio, ...)
  │
  ├─ 1. Per verse: render_verse_png() via Pillow
  │       └─ Black #141414 bg, white text, KFGQPC font
  │          Auto-shrinks from VIDEO_FONT_SIZE → VIDEO_MIN_FONT_SIZE
  │          DP line-balancer (≥4 words/line)
  │          Quranic annotation marks + dagger alif stripped (_clean_verse)
  │          Basmala stripped before this point (aya 1 of non-1 sura)
  │
  ├─ 2. Per verse: FFmpeg pass 1 — PNG → verse clip with fade in/out
  │       └─ libx264, ultrafast, crf 18, yuv420p, no audio (-an)
  │
  ├─ 3. FFmpeg pass 2 — concat demuxer → silent text track (-c:v copy)
  │
  └─ 4. FFmpeg pass 3 — final composite:
          color=#141414 [bg] + text track (looped, trimmed) + audio → .mp4
          libx264 fast, crf 23, aac 128k, exact audio duration
          └─ file_id cached → instant re-send
```

**Video constants (`config.py`):**

| Constant | Value | Description |
|---|---|---|
| `VIDEO_FPS` | 24 | Frame rate |
| `VIDEO_FADE_DURATION` | 1s | Fade in/out per verse clip |
| `VIDEO_SYNC_OFFSET` | -0.5s | Text track shift relative to audio |
| `VIDEO_FONT_SIZE` | 36 | Starting font size |
| `VIDEO_MIN_FONT_SIZE` | 26 | Minimum font size |
| `VIDEO_PADDING` | 40px | Inner frame padding |
| `VIDEO_SIZES` | portrait: 630×1120, landscape: 1120×630 | Output dimensions |

---

## 🔊 Audio pipeline

```
gen_mp3(audio_dir, output_dir, quran_data, voice, ..., progress_cb)
  │
  ├─ Phase 0 — Download: per verse, check disk cache → download from everyayah.com
  │       progress_cb(0–65%) per file
  │
  ├─ Phase 1 — FFmpeg concat demuxer:
  │       Writes a concat list file → ffmpeg -f concat -safe 0
  │       -map_metadata -1 (strips all incoming tags)
  │       -metadata title= -metadata artist= -id3v2_version 3
  │       -codec:a copy  (no re-encode)
  │       → intermediate concat.mp3 in temp dir
  │       progress_cb(82%)
  │
  └─ Phase 2 — FFmpeg strip (copy-only):
          ffmpeg -i concat.mp3 -map_metadata -1 -codec:a copy → output.mp3
          Removes any residual ID3 frames and album-art (APIC) that survived
          from source files, regardless of FFmpeg version behaviour.
          progress_cb(100%)
```

No re-encoding in either pass. `ffmpeg-python` and `mutagen` are not used — all
FFmpeg calls go through `subprocess.run` via a thin `_ffmpeg()` wrapper.

---

## 📿 Hadith feature

- **Source:** 9 local SQLite files in `data/hadith/` (~35k hadiths total)
- **DB index:** Built once at module import time — hadith counts cached, no repeated filesystem scans
- **Selection:** Weighted random by DB size, so larger collections (Bukhari, Muslim) are sampled proportionally
- **Schema per DB:** `hadiths(id, hadith_number, text, section_id, book_id)`, `grades(id, hadith_id, scholar_name, grade)`, `book_info(id, book_name, hadith_count)`
- **`/hadith`** — sends a random hadith to the requesting user
- **`/chadith`** — admin only: sends a random hadith to `CHANNEL_ID`
- **Format:** Arabic text → separator line → book name | حديث رقم N (grade field commented out pending data quality review)

---

## 🔤 Basmala handling

The Uthmani text includes the full basmala (`بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ`) as part of aya 1 for most suras (not 1:1 which is the basmala itself, and not 9:1 which has no basmala).

| Context | Treatment |
|---|---|
| Text display / search | `﷽` placed **before** `﴿...﴾` brackets |
| Page navigation | Replaced with `﷽` + newline |
| Video frames | Stripped entirely |
| SRT / LRC files | Stripped entirely |

---

## 🔍 Arabic search normalization

`normalize_arabic()` in `core/search.py`:

| Transform | Example |
|---|---|
| Dagger alif (U+0670) removed **first** | prevents `إِلَٰهَ` → `الاه` mis-match |
| Alif variants + alif wasla (U+0671) | `إأآٱا` → `ا` |
| Alif maqsura | `ى` → `ي` |
| Hamza seats | `ؤئ` → `ء` |
| Tashkeel (diacritics) U+064B–U+065F | stripped |
| Quranic annotation marks U+06D6–U+06ED | stripped (pause signs, small letters) |
| Tatweel / kashida (U+0640) | stripped |
| Zero-width chars | stripped |

---

## ⚙️ Key config (`config.py`)

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From BotFather (via `.env`) |
| `ADMIN_IDS` | Telegram user IDs for `/admin` and `/chadith` |
| `CHANNEL_URL` | e.g. `https://t.me/yourchannel` — inline button in menu |
| `CHANNEL_ID` | e.g. `@yourchannel` — target for `/chadith` |
| `DAILY_HADITH_COUNT` | 3 — hadiths sent to channel per day (0 to disable). Send times are auto-distributed evenly across 24h UTC — e.g. 3 → 00:00, 08:00, 16:00 |
| `FFMPEG_BIN` | Path to `ffmpeg` binary — auto-resolved to `bin/ffmpeg` if present, else system PATH |
| `FFPROBE_BIN` | Path to `ffprobe` binary — same resolution logic |
| `DONATE_URL` | Link to a public channel post listing donation addresses — shown as button |
| `MAX_AYAS_PER_REQUEST` | 40 — range cap (full suras exempt) |
| `VIDEO_DEFAULT_RATIO` | `"portrait"` or `"landscape"` |
| `DEFAULT_VOICE` | Reciter key from `VOICES` dict |
| `PURGE_THRESHOLD_MB` | 200 — auto-purge audio cache below this |
| `WARN_THRESHOLD_MB` | 500 — log warning below this |
| `RATE_WINDOW_SECONDS` | 3600 — rate limit window |
| `RATE_MAX_REQUESTS` | 10 — max requests per window |

---

## 🎙️ Adding a reciter

1. Verify files at `everyayah.com/data/{ReciterCode}/{sura}{aya}.mp3`
2. Add to `VOICES` in `config.py`:

```python
"ReciterCode_64kbps": {"ar": "الاسم", "en": "Name"},
```

---

## 📦 Core dependencies

```
python-telegram-bot[job-queue]>=21.3
python-dotenv
sqlalchemy
rapidfuzz
Pillow
json5
```

FFmpeg static binaries must be placed in `bin/ffmpeg` and `bin/ffprobe` (chmod +x). If not present, `config.py` falls back to system PATH. `FFMPEG_BIN` and `FFPROBE_BIN` constants are used throughout — never hardcoded strings. Download from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases).

---

## 🗃️ Database models (`core/database.py`)

| Table | Description |
|---|---|
| `users` | One row per Telegram user. Stores `language`, `voice`, `tafsir_source`, `preferences` (JSON: `text_format`, `video_ratio`) |
| `tafsir_cache` | Persistent tafsir API responses. Key: `{edition}:{sura}:{aya}`. TTL: 30 days. |
| `bot_stats` | Singleton row (id=1). Counters: `generated_audio`, `generated_video`, `hadiths_sent_personal`, `hadiths_sent_channel`, `stars_donations` |
| `request_queue` | Pending/processing/done/cancelled jobs with `params_json`, `status_msg_id` for progress editing |

---

## 🚨 Error log (`errors.json`)

`BASE_DIR/errors.json` — appended by `log_error()` in `core/utils.py` on every caught exception.
Capped at 500 entries (oldest dropped). Each record:

| Field | Content |
|---|---|
| `ts` | UTC ISO-8601 timestamp |
| `context` | Where it happened (`error_handler`, `queue_processor`, `daily_hadith_job`, …) |
| `type` | Exception class name |
| `msg` | `str(exception)` |
| `tb` | Full traceback string |
| `user_id` / `chat_id` | Set when available (Telegram update context) |
| `item_id` | Set for queue processor errors |

---

## 💾 file_id cache (`output/file_ids.json`)

Telegram `file_id` values are permanent per-bot. Once a file is sent, the ID is saved to `file_ids.json` keyed as:

```
audio:{reciter_code}:{sura}:{start_aya}:{end_aya}
video:{reciter_code}:{sura}:{start_aya}:{end_aya}:{ratio_bit}
```

On repeat requests the file is sent instantly without re-upload or re-generation.
