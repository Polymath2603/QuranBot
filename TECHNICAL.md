# 🔧 Technical Documentation

→ [README](README.en.md) · [Changelog](CHANGELOG.md) · [Todo](TODO.md)

---

## 🗂️ Project structure

```
QuranBot/
├── 🤖 bot.py              # All Telegram handlers + callback router
├── ⚙️  config.py           # Every constant in one place — edit here, not in modules
├── core/
│   ├── 🔊 audio.py        # gen_mp3(): downloads per-verse MP3s, concatenates with FFmpeg
│   ├── 🎬 video.py        # gen_video(): renders text PNGs with Pillow, composites with FFmpeg
│   ├── 📄 subtitles.py    # SRT / LRC / TXT export using real ffprobe timestamps
│   ├── 📖 verses.py       # build_verse_keyboard(), send helpers, format_verse_file()
│   ├── 🧠 nlu.py          # Natural language parser — sura names, ranges, pages, search
│   ├── 🔍 search.py       # Full-text search with comprehensive Arabic normalization
│   ├── 📚 tafsir.py       # AlQuran.cloud fetch + SQLite persistent cache + LRU in-memory
│   ├── 📊 data.py         # load_quran_data(), load_quran_text(), index lookups
│   ├── ⬇️  downloader.py   # Per-verse MP3 downloader with retry + DOWNLOAD_TIMEOUT
│   ├── 🗃️  database.py     # SQLAlchemy models: User, TafsirCache, QueueItem
│   ├── ⏳ queue.py        # Serial request queue: SQLite-backed, cancel support, position tracking
│   ├── 🌐 lang.py         # t(key, lang, **kwargs) — loads locales/ar.json + en.json
│   └── 🛠️  utils.py        # safe_filename, storage purge, rate limiter, file_id cache, LRUCache
├── locales/
│   ├── 🇸🇦 ar.json         # Arabic UI strings (default)
│   └── 🌐 en.json         # English UI strings
├── data/
│   ├── quran-data.json        # Sura metadata + page map (tanzil.net)
│   ├── quran-uthmani.txt      # Full Uthmani text, one verse per line (tanzil.net)
│   ├── KFGQPC *.ttf           # Uthmanic font for video frame rendering
│   └── audio/                 # Per-verse MP3 cache — auto-purged when disk is low
├── output/
│   ├── {reciter_code}/        # Generated MP3s and MP4s, namespaced by reciter
│   └── file_ids.json          # Permanent Telegram file_id cache (survives restarts)
├── .env
├── requirements.txt
├── README.md           # Arabic
├── README.en.md        # English
├── TECHNICAL.md        ← you are here
├── CHANGELOG.md
└── TODO.md
```

---

## 🏗️ Architecture

### Request flow

```
User message
  → message_router (NLU parse)
      → build_verse_keyboard → user taps button
          → callback_router → handler
              → rate limiter check
              → aya bounds + range validation
              → max aya cap check (ranges only)
              → file_id cache hit? → send instantly
              → send wait message
              → request_queue.enqueue()
                  → _process_queue_item() [ThreadPoolExecutor]
                      → gen_mp3() / gen_video()
                      → bot.send_audio() / bot.send_video()
                      → cache file_id
                      → edit wait message to "." → delete
```

### Concurrency model

| Component | Role |
|---|---|
| `asyncio` main loop | Handles all Telegram updates |
| `ThreadPoolExecutor(2)` | Runs `gen_mp3` / `gen_video` off the event loop |
| `RequestQueue` | Serial consumer — one job at a time |
| `asyncio.run_coroutine_threadsafe` | Posts progress edits from worker thread back to the loop |

---

## 🎬 Video pipeline

```
gen_video(verse_texts, audio_path, ratio, ...)
  │
  ├─ 1. Per verse: render_verse_png()
  │       └─ Pillow: black #141414 background, white text, Uthmanic font
  │          Auto-shrinks font from VIDEO_FONT_SIZE → VIDEO_MIN_FONT_SIZE
  │          Line-breaking via DP balancer (≥4 words/line enforced)
  │
  ├─ 2. Single FFmpeg pass:
  │       lavfi color=#141414 [bg]
  │       PNGs → overlay with fade-in/out between verses
  │       audio → map 0:a
  │       output .mp4
  │
  └─ 3. file_id saved → instant re-send on repeat requests
```

**Video config (`config.py`):**

| Constant | Value | Description |
|---|---|---|
| `VIDEO_FPS` | 23 | Frame rate |
| `VIDEO_FADE_DURATION` | 1s | Cross-fade between verses |
| `VIDEO_SYNC_OFFSET` | -0.2s | Shifts text track relative to audio |
| `VIDEO_FONT_SIZE` | 30 | Starting font size, auto-shrinks |
| `VIDEO_MIN_FONT_SIZE` | 23 | Minimum font size allowed |
| `VIDEO_PADDING` | 40px | Inner frame padding |
| `VIDEO_FALLBACK_DUR` | 5.0s | Seconds per verse when MP3 not cached |
| `VIDEO_SIZES` | portrait: 630×1120, landscape: 1120×630 | Output dimensions |

---

## 🔊 Audio pipeline

```
gen_mp3(audio_dir, output_dir, quran_data, reciter_code, sura, start, sura, end, ...)
  │
  ├─ 1. Per verse: check disk cache → download from everyayah.com
  ├─ 2. FFmpeg concat → single MP3
  ├─ 3. ID3 metadata (title, artist, track, album)
  └─ 4. _strip_album_art() → remove any embedded images
```

---

## 🔍 Arabic search normalization

`normalize_arabic()` in `core/search.py` applies:

| Transform | Example |
|---|---|
| Alif variants (incl. superscript alif U+0670) | `إأآٱاٰ` → `ا` |
| Alif maqsura | `ى` → `ي` |
| Hamza variants | `ؤئ` → `ء` |
| Tashkeel (diacritics) | stripped entirely |

Then Jaccard/trigram similarity via `rapidfuzz` for fuzzy sura name matching.

---

## 🌐 Adding a new UI language

1. Copy `locales/ar.json` → `locales/xx.json`
2. Translate all values (keep keys unchanged)
3. Add the language option in `setting_lang_toggle` in `bot.py`

---

## 🔑 Adding a locale string

Add the key to **both** `ar.json` and `en.json`:

```json
"my_key": "النص بالعربي"
"my_key": "English text here"
```

Use it: `t("my_key", lang, param=value)`

The `t()` function supports `{placeholders}` via `.format(**kwargs)`.

---

## 🗃️ Database schema

| Table | Contents |
|---|---|
| `users` | `telegram_id`, `language`, `voice`, `preferences` (JSON), `tafsir_source` |
| `tafsir_cache` | `sura`, `aya`, `source`, `text`, `cached_at` (30-day TTL) |
| `request_queue` | `user_id`, `chat_id`, `request_type`, `params_json`, `status`, `status_msg_id` |

---

## 🎙️ Adding a reciter

1. Verify files exist at `everyayah.com/data/{ReciterCode}/{sura}{aya}.mp3`
2. Add to `VOICES` in `config.py`:

```python
"ReciterCode_64kbps": {"ar": "الاسم بالعربي", "en": "Name in English"},
```

No other changes needed.

---

## 📋 Callback routing

Callbacks are dispatched via two structures in `bot.py`:

```python
_EXACT: dict   # exact string match → handler
_PREFIX: list  # startswith match → handler (first match wins)
```

All handler functions are `async def handler(update, context)`.

---

## ⚙️ Environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from BotFather |

---

## 📦 Core dependencies

```
python-telegram-bot[all]>=21
sqlalchemy
Pillow
ffmpeg-python
rapidfuzz
httpx
python-dotenv
```

FFmpeg must be installed at the system level.
