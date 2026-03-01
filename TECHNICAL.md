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
│   ├── 🎬 video.py        # gen_video(): Pillow PNGs + single FFmpeg composite pass
│   ├── 📄 subtitles.py    # SRT / LRC export with real ffprobe timestamps
│   ├── 📖 verses.py       # build_verse_keyboard(), send helpers, basmala handling
│   ├── 🧠 nlu.py          # Natural language parser — suras, ranges, pages, search
│   ├── 🔍 search.py       # Full-text search with comprehensive Arabic normalization
│   ├── 📚 tafsir.py       # AlQuran.cloud fetch + SQLite cache + LRU in-memory
│   ├── 📊 data.py         # load_quran_data(), load_quran_text(), index lookups
│   ├── ⬇️  downloader.py   # Per-verse MP3 downloader with retry
│   ├── 🗃️  database.py     # SQLAlchemy models: User, TafsirCache, QueueItem
│   ├── ⏳ queue.py        # Serial request queue: SQLite-backed, position tracking, cancel
│   ├── 📿 hadith.py        # Random hadith feature — /hadith (user), /chadith (admin→channel)
│   ├── 🌐 lang.py         # t(key, lang, **kwargs) — loads ar.json + en.json
│   └── 🛠️  utils.py        # safe_filename, storage purge, rate limiter, file_id cache
├── locales/
│   ├── 🇸🇦 ar.json         # Arabic UI strings
│   └── 🌐 en.json         # English UI strings
├── data/
│   ├── quran-data.json        # Sura metadata + page map
│   ├── quran-uthmani.txt      # Full Uthmani text, one verse per line
│   ├── KFGQPC *.ttf           # Uthmanic font for video rendering
│   ├── hadeethenc.com API      # Hadith source (no auth required)
│   └── audio/                 # Per-verse MP3 cache, auto-purged on low disk
├── output/
│   ├── {reciter_code}/        # Generated MP3s and MP4s
│   └── file_ids.json          # Permanent Telegram file_id cache
├── .env
├── .env.example
├── requirements.txt
├── README.md           # Arabic
├── README.en.md        # English ← you are here
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
| `KFGQPC *.ttf` | [King Fahd Quran Printing Complex](https://fonts.qurancomplex.gov.sa) | Free for non-commercial use |
| `hadeethenc.com API` | [hadeethenc.com](https://hadeethenc.com) | Public API |
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
| `ThreadPoolExecutor(2)` | `gen_mp3` / `gen_video` off the event loop |
| `RequestQueue` | Serial consumer — one job at a time |
| `asyncio.run_coroutine_threadsafe` | Posts progress edits from worker thread |
| `hadith.py` | `get_random_hadith()` → API call → `format_hadith()` → send |

---

## 🎬 Video pipeline

```
gen_video(verse_texts, start_aya, title, sura, voice, audio_path, ratio, ...)
  │
  ├─ 1. Per verse: render_verse_png() via Pillow
  │       └─ Black #141414 bg, white text, KFGQPC font
  │          Auto-shrinks from VIDEO_FONT_SIZE → VIDEO_MIN_FONT_SIZE
  │          DP line-balancer (≥4 words/line)
  │          Basmala stripped before this point (aya 1 of non-1 sura)
  │
  ├─ 2. Single FFmpeg pass:
  │       color=#141414 [bg] + PNGs with fade + audio → .mp4
  │
  └─ 3. file_id cached → instant re-send
```

**Video constants (`config.py`):**

| Constant | Value | Description |
|---|---|---|
| `VIDEO_FPS` | 24 | Frame rate |
| `VIDEO_FADE_DURATION` | 1s | Cross-fade between verses |
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
  ├─ 1. Per verse: check disk cache → download from everyayah.com
  │       progress_cb(0–70%) per file
  ├─ 2. FFmpeg concat → single MP3 (progress_cb 85%)
  ├─ 3. ID3 metadata: title + artist only
  └─ 4. _strip_album_art(): -map_metadata -1, re-add text tags (progress_cb 100%)
```

---

## 📿 Azkar scheduler

- Reads `data/hadeethenc.com API` on startup
- Sends **Arabic body text only** to `CHANNEL_ID` once per day at `hadeethenc.com/api/v1` UTC (default 18:44)
- Bot must be an admin in the channel
- Set `CHANNEL_ID` in `.env` (e.g. `@yourchannel` or `-100123456789`)
- `/chadith` command (admin only) sends a random Arabic hadith to the channel on demand

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
| Alif variants + superscript alif (U+0670) | `إأآٱاٰ` → `ا` |
| Alif maqsura | `ى` → `ي` |
| Hamza variants | `ؤئ` → `ء` |
| Tashkeel (diacritics) | stripped |

---

## ⚙️ Key config (`config.py`)

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From BotFather (also via `.env`) |
| `ADMIN_IDS` | Telegram user IDs for `/admin` |
| `CHANNEL_URL` | e.g. `https://t.me/yourchannel` — inline button |
| `CHANNEL_ID` | e.g. `@yourchannel` — hadith feature target |
| `MAX_AYAS_PER_REQUEST` | 40 — range cap (full suras exempt) |
| `VIDEO_DEFAULT_RATIO` | `"landscape"` or `"portrait"` |
| `DEFAULT_VOICE` | Reciter key from `VOICES` dict |
| `PURGE_THRESHOLD_MB` | Auto-purge audio cache below this |
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
python-telegram-bot[all]>=21
sqlalchemy
Pillow
ffmpeg-python
rapidfuzz
httpx
python-dotenv
```

FFmpeg must be installed system-wide. No extra packages needed for scheduling (uses asyncio).
