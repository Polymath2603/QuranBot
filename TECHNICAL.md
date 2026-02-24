# QBot — Technical Documentation

→ [README](README.md) · [Changelog](CHANGELOG.md) · [Todo](TODO.md)

---

## Project Structure

```
QBot/
├── bot.py              # All Telegram handlers + callback router
├── config.py           # Every constant in one place — edit here, not in modules
├── core/
│   ├── audio.py        # gen_mp3(): downloads per-verse MP3s, concatenates with FFmpeg
│   ├── video.py        # gen_video(): renders text PNGs with Pillow, composites with FFmpeg
│   ├── subtitles.py    # SRT / LRC / TXT export using real ffprobe timestamps
│   ├── verses.py       # build_verse_keyboard(), send helpers, format_verse_file()
│   ├── nlu.py          # Natural language parser — sura names, ranges, pages, search
│   ├── search.py       # Full-text search with Arabic normalization (diacritics, alif variants)
│   ├── tafsir.py       # AlQuran.cloud fetch + SQLite persistent cache + LRU in-memory
│   ├── data.py         # load_quran_data(), load_quran_text(), index lookups
│   ├── downloader.py   # Per-verse MP3 downloader with retry + DOWNLOAD_TIMEOUT
│   ├── database.py     # SQLAlchemy models: User, TafsirCache, QueueItem
│   ├── queue.py        # Serial request queue: SQLite-backed, consumer task, cancel support
│   ├── lang.py         # t(key, lang, **kwargs) — loads locales/ar.json + en.json
│   └── utils.py        # safe_filename, storage purge, rate limiter, file_id cache, LRUCache
├── locales/
│   ├── ar.json         # Arabic UI strings (default language)
│   └── en.json         # English UI strings
├── data/
│   ├── quran-data.json       # Sura metadata, page map (tanzil.net)
│   ├── quran-uthmani.txt     # Full Uthmani text, one verse per line (tanzil.net)
│   ├── KFGQPC *.ttf          # Uthmani font for video frame rendering
│   ├── audio/                # Per-verse MP3 cache — auto-purged when disk is low
│   └── backgrounds/          # Optional bg images/videos for Random background mode
├── output/
│   ├── {voice}/              # Generated MP3s and MP4s, namespaced by reciter
│   └── file_ids.json         # Permanent Telegram file_id cache (survives restarts)
├── .env.example
├── requirements.txt
├── README.md
├── TECHNICAL.md      ← you are here
├── CHANGELOG.md
└── TODO.md
```

---

## Architecture

### Request flow

```
User message
    → message_router (NLU parse)
        → build_verse_keyboard → user taps button
            → callback_router → handler
                → rate limiter check
                → max aya cap check
                → file_id cache hit? → send instantly
                → else: request_queue.enqueue()
                    → queue consumer (_process_queue_item)
                        → run_in_executor (ThreadPoolExecutor, 2 workers)
                            → gen_mp3 / gen_video
                        → send result to user
                        → set_file_id() → saved to output/file_ids.json
```

### Queue system (`core/queue.py`)

- `QueueItem` table in SQLite stores every pending/processing/done/cancelled request.
- A single `asyncio` consumer task processes jobs one at a time — no parallel FFmpeg on mobile.
- After each job, all pending items get their status messages edited with the updated position.
- `Cancel` button: sets status to `cancelled`; consumer skips it.
- Survives restarts: `pending` and interrupted `processing` items are re-queued on startup.

### Video pipeline (`core/video.py`)

1. **Text wrapping** — DP balancer enforces ≥4 words per line.
2. **Frame rendering** — each verse → RGBA PNG with Pillow (Arabic font, shadow/border, auto font-size shrink).
3. **Per-verse clip** — each PNG → silent video clip via FFmpeg; fade-in/out baked into duration.
4. **Concatenation** — clips joined with FFmpeg concat demuxer (`-c:v copy`, lossless).
5. **Final composite** — one FFmpeg pass: background (solid/image/video) + text overlay + audio. Audio is master clock; text track loops/trims to exact audio duration. `VIDEO_SYNC_OFFSET` shifts text forward vs audio.

### File ID cache (`output/file_ids.json`)

Once a file is uploaded to Telegram, its `file_id` is saved permanently. On the next identical request (same voice + sura + range + settings), the file is sent using only the `file_id` — no disk read, no re-upload, instant delivery. Format: `"audio:{voice}:{sura}:{start}:{end}"` or `"video:{voice}:{sura}:{start}:{end}:{bits}"`.

---

## External APIs

| API | Used for | Docs |
|---|---|---|
| `https://everyayah.com/data/{voice}/{sura:03}{aya:03}.mp3` | Per-verse MP3 download | [everyayah.com](https://everyayah.com) |
| `https://api.alquran.cloud/v1/ayah/{ref}/{edition}` | Tafsir text | [alquran.cloud/api](https://alquran.cloud/api) |
| Telegram Bot API | Everything else | [core.telegram.org/bots/api](https://core.telegram.org/bots/api) |

---

## Data Files

| File | Source | Format |
|---|---|---|
| `quran-data.json` | [tanzil.net](https://tanzil.net) | JSON: sura list, page map, aya counts |
| `quran-uthmani.txt` | [tanzil.net](https://tanzil.net) | Plain text, one verse per line, 6236 lines |
| `KFGQPC *.ttf` | King Fahd Quran Printing Complex | TrueType, Uthmanic script |

---

## Configuration Reference (`config.py`)

| Constant | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — | From `TELEGRAM_BOT_TOKEN` env var |
| `CHANNEL_URL` | `""` | Set to show a channel button on /start; empty = hidden |
| `ADMIN_IDS` | `[]` | Telegram user IDs that can use /admin; empty = anyone |
| `MAX_AYAS_PER_REQUEST` | `50` | Max ayas per audio/video request |
| `HTTP_CONNECT_TIMEOUT` | `20` | Telegram connection timeout (s) |
| `HTTP_READ_TIMEOUT` | `90` | Telegram read timeout — important for large uploads |
| `DOWNLOAD_TIMEOUT` | `30` | EveryAyah per-verse MP3 download timeout (s) |
| `VIDEO_FPS` | `23` | Output video frame rate |
| `VIDEO_FADE_DURATION` | `1` | Fade-out + fade-in between verses (s total) |
| `VIDEO_SYNC_OFFSET` | `-0.2` | Shift text track vs audio (s); negative = text leads |
| `VIDEO_FONT_SIZE` | `30` | Starting font size; auto-shrinks to fit |
| `VIDEO_MIN_FONT_SIZE` | `23` | Floor font size |
| `VIDEO_PADDING` | `40` | Frame edge padding (px) |
| `VIDEO_FALLBACK_DUR` | `5.0` | Seconds per verse when MP3 not yet cached |
| `VIDEO_DEFAULT_RATIO` | `"landscape"` | `"landscape"` (1120×630) or `"portrait"` (630×1120) |
| `PURGE_THRESHOLD_MB` | `200` | Purge old output files when free disk drops below this |
| `WARN_THRESHOLD_MB` | `500` | Log a warning when free disk drops below this |
| `RATE_WINDOW_SECONDS` | `3600` | Rate limit window (1 hour) |
| `RATE_MAX_REQUESTS` | `10` | Max audio/video requests per user per window |

---

## Database Schema

```
users
  id, telegram_id, language, voice, tafsir_source, preferences (JSON), created_at, updated_at

tafsir_cache
  id, cache_key, text, created_at

request_queue
  id, user_id, chat_id, request_type, params_json, lang, status, status_msg_id, created_at
```

`preferences` JSON keys: `text_format`, `video_bg`, `video_color`, `video_border`, `video_ratio`

---

## Adding a New Locale String

1. Add the key to `locales/ar.json` and `locales/en.json`.
2. Use `t("your_key", lang)` anywhere — supports `{placeholder}` via `t("key", lang, foo=bar)`.
3. No restart needed if you reload (locales are loaded at import time; restart required in production).

## Adding a New Reciter

Add an entry to `VOICES` in `config.py`:
```python
"ReciterFolderName_bitrate": {"ar": "الاسم بالعربي", "en": "English Name"},
```
The folder name must match the path structure on everyayah.com.
