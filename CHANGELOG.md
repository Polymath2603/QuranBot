# Changelog

---

## 2026-02-24 (Session 3)

### Fixed
- **`build_verse_keyboard` crash** — `TypeError: InlineKeyboardMarkup.__init__() takes 2 positional arguments but 3 were given`. Function was passing two separate positional lists instead of one list-of-rows, and was missing its `return` statement entirely (was returning `None`).
- **Empty `CHANNEL_URL` crash** — `BadRequest: text buttons are unallowed in the inline keyboard`. The welcome keyboard always added the channel button even when `CHANNEL_URL = ""`. Fixed: button is only added when the URL is non-empty.

### Added
- **Search results as verse keyboards** — search results shown as up to 8 tappable `InlineKeyboardButton`s (sura name + aya + first 40 chars of verse). Tapping opens the full verse with the standard keyboard (tafsir / text / audio / video).
- **`/admin` command** — shows: total users, queue depth, free disk (MB), number of cached `file_id`s, top 5 reciters by user count. Restricted to `ADMIN_IDS` in `config.py`; if empty, anyone can use it.
- **Max aya cap** — `MAX_AYAS_PER_REQUEST = 50` in `config.py`. Both audio and video handlers reject requests exceeding this with a localized message before queuing or generating anything.
- **`ADMIN_IDS` in `config.py`** — list of Telegram user IDs allowed to use `/admin`.
- **`file_id_count()` in `core/utils.py`** — public helper for admin panel; avoids importing private `_file_ids` dict.
- **New locale keys** (both `ar.json` and `en.json`): `too_many_ayas`, `search_results_hdr`, `search_tap_hint`, `admin_not_allowed`, `admin_title`, `admin_users`, `admin_queue`, `admin_disk`, `admin_cache`, `admin_top_voices`.

---

## 2026-02-24 (Session 2)

### Fixed
- **Arabic-Indic aya numbers in video** — verse numbers now render as `١٢٣` (Arabic-Indic digits) instead of `(123)`. Implemented via `_to_arabic_numerals()` in `video.py`.
- **`"off"` removed from text formats** — format cycle is now `msg → txt → lrc → srt` only; `"off"` option removed from `setting_format_toggle` and all `send_text_*` functions.

### Added
- **Request queue with position tracking** (`core/queue.py`) — new `QueueItem` SQLite table; single consumer task processes one job at a time; status messages auto-edit as position changes (`⏳ أنت رقم ٣ في قائمة الانتظار`); survives bot restarts.
- **Cancel button** on every queued request (`queue_cancel_{id}` callback). Cancels if still pending; shows alert if already processing.
- **Telegram `file_id` permanent cache** (`output/file_ids.json`) — audio and video `file_id`s stored permanently after first upload. Identical requests served instantly with no re-upload, no queue entry. Keys: `audio:{voice}:{sura}:{start}:{end}` / `video:{voice}:{sura}:{start}:{end}:{bits}`.
- **Progress strings as locale keys** — all video generation progress labels moved from hardcoded English strings in `bot.py` to `locales/ar.json` and `locales/en.json`: `progress_rendering`, `progress_encoding`, `progress_concat`, `progress_compositing`, `progress_uploading`.
- **Queue locale keys**: `queue_position`, `queue_processing`, `queue_cancelled`, `queue_cancel_btn`, `queue_done_audio`, `queue_done_video`.
- **`core/queue.py`** — `RequestQueue` class: `enqueue()`, `cancel()`, `position()`, `_consume()`, `_broadcast_positions()`.
- **`init_db()` updated** — imports `QueueItem` before `create_all()` so the `request_queue` table is created automatically.
- **Video settings UI** — background toggle removed from the settings screen (code preserved, button hidden) pending rework. Color, border, ratio remain.
- **`ThreadPoolExecutor` reduced to 2 workers** — prevents memory pressure from parallel FFmpeg processes on mobile.
- **`post_init` hook** — `request_queue.start(bot)` called via `Application.post_init` so the queue consumer starts cleanly after the bot is built.

---

## 2026-02-24 (Session 1)

### Fixed
- **Audio repeat at end of video** — audio was re-looping because `total_dur = max(text_total, audio_dur)` combined with `-stream_loop -1` on the audio input caused FFmpeg to restart audio when video was longer. Fixed: `total_dur = audio_dur`; audio input has no `-stream_loop`; video/text track loops to fill audio duration.
- **Bot blocking during generation** — replaced `asyncio.to_thread()` with `loop.run_in_executor(_WORKER_POOL, fn)` using a named `ThreadPoolExecutor`. Event loop stays responsive; other users can interact during encoding.
- **Video cache miss due to missing voice in filename** — output filename now includes `voice`: `{voice}_{range_id}_{bits}.mp4`.

### Added
- **`VIDEO_SYNC_OFFSET = 0.15`** in `config.py` — shifts text track forward vs audio via `setpts=PTS+{sync}/TB`. Tunable without code changes.
- **Progress bar with 20% steps** — `gen_video()` accepts `progress_cb(pct, msg)`. Bot creates a closure that calls `asyncio.run_coroutine_threadsafe()` to post edits from the worker thread. Labels at 0 / 20 / 40 / 60 / 80 / 100%.
- **`ThreadPoolExecutor(max_workers=4)`** in `bot.py` for both audio and video generation.

---

## 2026-02-23 (Session 2)

### Added
- **Video ratio setting** — portrait (9:16) and landscape (16:9); toggled in Video Settings; 4th bit in cache filename.
- **`config.py` centralised constants** — all magic numbers extracted: `VIDEO_FPS`, `VIDEO_FADE_DURATION`, `VIDEO_FONT_SIZE`, `VIDEO_MIN_FONT_SIZE`, `VIDEO_PADDING`, `VIDEO_FALLBACK_DUR`, `FONT_PATH`, `BG_DIR`, `VIDEO_SIZES`, `VIDEO_DEFAULT_RATIO`, `HTTP_CONNECT_TIMEOUT`, `HTTP_READ_TIMEOUT`, `DOWNLOAD_TIMEOUT`, `PURGE_THRESHOLD_MB`, `WARN_THRESHOLD_MB`, `RATE_WINDOW_SECONDS`, `RATE_MAX_REQUESTS`, `LOCALE_DIR`.
- **`core/__init__.py`** — makes `core/` a proper Python package.
- **New locale keys**: `rate_limited`, `video_ratio`, `landscape`, `portrait`, `tafsir_not_found`, `page_sura_header`, `file_caption`, `video_caption`, `lang_name_ar`, `lang_name_en`.

### Fixed
- All relative imports in `core/` — every module uses `from .module import …`.
- `core/lang.py` locale path — now reads `LOCALE_DIR` from `config.py`.
- `core/video.py` background path — `BG_DIR` now from `config.BG_DIR`.
- Video vertical centring — removed erroneous `+ fs // 2` offset.
- `rate_limited` locale key missing (was causing `KeyError` crash).
- `DOWNLOAD_TIMEOUT` — was hardcoded `10s`; now from config.

### Changed
- **Video pipeline** — background moved to final FFmpeg pass. Per-verse step renders transparent PNGs only. Final pass: background + text overlay + audio in one FFmpeg invocation.
- **Zoom-to-fit background** — `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`.
- **Reciter-namespaced output paths** — `output/{voice}/…`.
- **`HTTPXRequest` timeouts** — `connect=20s`, `read=90s`.

---

## 2026-02-23 (Session 1)

### Added
- `subtitles.py` — SRT / LRC / TXT export with real ffprobe timestamps.
- `verses.py` — verse display / send logic extracted from `bot.py`.
- White background option for video.
- Video bg toggle cycle: black → white → random → black.

### Fixed
- SRT / LRC timestamps were fake; now from ffprobe on cached MP3s.
- 3-bit video cache filename differentiates settings (bg / color / border).
- Video pipeline: replaced moviepy + numpy with Pillow + FFmpeg subprocess.
- Border/shadow colour always opposite of text colour.

---

## 2026-02-21

### Fixed
- Tafsir source ignored (was hardcoded `ar.muyassar`).
- Back button missing after single-aya text display.
- Video filename collision between users.
- Detached SQLAlchemy object in settings toggle.
- Raw exception messages exposed to users.

### Added
- `utils.py` — `safe_filename`, `delete_status_msg`, storage purge, rate limiter, `LRUCache`.
- Persistent tafsir cache (SQLite + in-memory LRU, 30-day TTL).
- `callback_router` dispatch dict replacing 30-branch if-elif chain.

---

## 2026-02-10

### Added
- NLU — Arabic + English verse / range / page / search parsing, fuzzy sura name matching.
- SQLite user database via SQLAlchemy.
- Localization system — `ar.json` / `en.json`, `lang.py` / `t()`.
- Telegram Stars donations.
- Audio metadata embedding (title, artist, ID3v2).
- Tafsir integration via AlQuran.cloud.

---

## Initial Release

- Basic verse retrieval, audio playback, search, multi-reciter support, sura list.
