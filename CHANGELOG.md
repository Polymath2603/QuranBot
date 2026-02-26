# 📋 Changelog

---

## 🟢 2026-02-26 — Current

### 🐛 Fixed
- **Album art stripping** — previous implementation used `-map_metadata 0` which preserved APIC (image) ID3 frames. Fixed: metadata is now fully dropped with `-map_metadata -1`, then only `title` and `artist` text tags are re-added from `ffprobe` output. Album art is gone.
- **Verse format inconsistency** — `back_to_verse_handler` was still rendering `﴿ text ﴾` without the aya number. All verse display paths are now consistent.

### ✨ Added
- **Audio progress bar** — `gen_mp3` now accepts `progress_cb`. Download phase reports 0–70% (one tick per file), concat 85%, strip 100%. Bar format: `🎧\n▰▰▱▱▱ 40%`.

### 🔄 Changed
- **Verse text format** — inline message display now shows `﴿ verse (aya_number) ﴾` for single ayas, and `﴿ verse1 (1) verse2 (2) ... ﴾` as a continuous block for ranges. Consistent across text handler, back-to-verse, and all send paths.
- **Progress bars simplified** — state description labels removed from both audio and video bars. Format is now just `🎧\n{bar} {pct}%` / `🎬\n{bar} {pct}%`.
- **Wait messages removed** — both audio and video handlers no longer send a wait message on enqueue. Media arrives silently.
- **TXT format removed** — `txt` stripped from format cycle, `_fmt_label`, all defaults, `verses.py`, `subtitles.py` import, and locale files. Format cycle is now `msg → lrc → srt`.

### 🗑️ Removed
- `fmt_txt` locale key.
- `generating_audio` / `generating_video` locale keys (no longer shown to users).
- `build_txt` import from `verses.py`.

---

## 🔵 2026-02-25

### 🐛 Fixed
- **`NameError: 'title' is not defined`** in `play_audio_handler` — `title = _sura_title(...)` line was missing entirely. Fixed.
- **`NameError: 'help_handler' is not defined`** — handlers were written to the working copy but the output files were never updated. All 14 files are now shipped together every session.
- **`DetachedInstanceError` on startup** — `queue.start()` accessed `item.id` after `session.close()`. Fixed by collecting IDs into a plain list before closing the session.
- **`ImportError: cannot import 'get_sura_display_name'`** — `core/data.py` was not re-shipped in the previous session. Fixed.
- **`start_aya > end_aya`** — both handlers now reject invalid ranges with a localized error before enqueueing.
- **Aya bounds** — `start_aya < 1` or `end_aya > sura_length` rejected with `aya_out_of_range` message.
- **Queue wait message** — now sent before enqueue so all users (pos 1, 2, 3…) see a progress indicator.

### ✨ Added
- **`/help`** — localized usage guide: input syntax, button descriptions, command list.
- **`/feedback <text>`** — forwards message to all `ADMIN_IDS` with user full name, @username, and Telegram ID.
- **Donation addresses in bot** — PayPal, Binance ID, Bybit ID, BTC, ETH/BNB, SOL shown in the donate screen.
- **Enhanced `/admin`** — AR/EN user split, processing queue count, total done jobs, cached files on disk, currently rate-limited user count.
- **`ٰ` (superscript alif, U+0670)** normalized to `ا` in search — fixes matches for words like `ٱلرَّحْمَـٰنِ`.
- **Go-to-page button** on single-aya keyboard — jumps directly to the Mushaf page.
- **Search results as message text** — verse shown inline with 2-per-row sura/aya buttons and character-length pagination.
- **Range text paging by character length** — 3,500-char pages, never cuts mid-verse.
- **Tafsir paging by character length** — 3,800-char pages, replaces old fixed 10-aya-per-page logic.
- **`get_sura_display_name()`** — always prefixes `سورة` / `Surah` in all user-facing text.
- **`README.en.md`** — English version of the README with bidirectional navigation links.

### 🔄 Changed
- **`voice` → `reciter_code`**, **`artist_name` → `reciter`** — renamed across all handlers and queue params.
- **Status message lifecycle** — after media is sent the wait message is edited to `"."` then deleted (clean dismissal).
- **Video ratio toggle inline** — sits directly in the settings keyboard as a toggle button; no submenu.
- **Max-aya cap** — 50-aya limit applies to ranges only; full-sura requests are always allowed regardless of length.
- **All docs** rewritten in English (TECHNICAL.md, CHANGELOG.md, TODO.md). README.md stays Arabic; README.en.md is English.

### 🗑️ Removed
- **Video background, color, border** — stripped completely from `gen_video()`, `bot.py`, `config.py`, and locale files. Video is always black background + white text.
- Dead `video_settings_handler`, `video_toggle_handler` functions.
- `BG_DIR` from `config.py`.
- Locale keys: `video_settings`, `video_bg`, `video_color`, `video_border`, `video_ratio`, `video_ratio_toggle`.
- `menu_video_settings` from the callback dispatch table.

---

## 🔵 2026-02-24

### 🐛 Fixed
- **`build_verse_keyboard` crash** — `TypeError: InlineKeyboardMarkup.__init__()` — function was returning `None`. Fixed.
- **Empty `CHANNEL_URL` crash** — channel button now only added when `CHANNEL_URL` is non-empty.
- **Arabic-Indic aya numbers in video** — verse numbers render as `١٢٣` not `(123)`.
- **`"off"` text format** — removed; cycle is `msg → txt → lrc → srt` only.
- **Audio looping at end of video** — `total_dur = audio_dur`; audio no longer loops.
- **Bot blocking during generation** — `run_in_executor` replaces `asyncio.to_thread`.
- **Video cache miss** — output filename now includes reciter code.
- **`rate_limited` locale key** missing (was crashing with `KeyError`).

### ✨ Added
- **Serial request queue** (`core/queue.py`) — SQLite-backed `QueueItem`; single consumer task; position tracking; cancel button; survives restarts.
- **Telegram `file_id` cache** — audio and video served instantly on repeat requests with no re-upload.
- **`/admin` command** — users, queue depth, free disk, cached file_ids, top reciters by count.
- **`MAX_AYAS_PER_REQUEST = 50`** in `config.py`.
- **`ADMIN_IDS`** in `config.py`.
- **Progress bar** — 5-step bar (0→20→40→60→80→100%) editing the status message from the worker thread.
- **Video ratio** — portrait (9:16) / landscape (16:9), toggled in settings.
- **Album art stripping** from generated MP3s.
- **`config.py`** — all constants centralised; no more magic numbers in modules.
- **NLU** — Arabic + English verse / range / page / search + fuzzy sura name matching (rapidfuzz).
- **Localization** — `ar.json` / `en.json`, `t()` helper with `{placeholder}` support.
- **Telegram Stars** donations.
- **Tafsir** — Al-Muyassar + Al-Jalalayn via AlQuran.cloud, SQLite + LRU in-memory cache, 30-day TTL.
- **SRT / LRC / TXT export** with real `ffprobe` timestamps.
- **`VIDEO_SYNC_OFFSET`** — tunable text-audio alignment without touching code.
- **`ThreadPoolExecutor(max_workers=2)`** — prevents memory pressure from parallel FFmpeg processes.

### 🔄 Changed
- **Video pipeline** — per-verse transparent PNGs (Pillow) + single FFmpeg composite pass. Solid black `#141414` background baked in.
- **Reciter-namespaced output paths** — `output/{reciter_code}/…`.
- **`core/` restructured** as a proper Python package with relative imports throughout.

---

## 🔵 2026-02-23

### ✨ Added
- `subtitles.py`, `verses.py`, `utils.py`, `nlu.py`, `search.py` extracted from the monolithic `bot.py`.
- SQLite user database via SQLAlchemy.
- Storage purge, rate limiter (10 req/user/hour), `LRUCache` in `utils.py`.
- Persistent tafsir cache (SQLite + LRU, 30-day TTL).
- `callback_router` dispatch dict replacing a 30-branch if-elif chain.

### 🐛 Fixed
- SRT/LRC timestamps were fake — now derived from `ffprobe` on cached MP3s.
- All `core/` relative imports.
- Video vertical centring (removed erroneous `+ fs // 2` offset).
- `DOWNLOAD_TIMEOUT` was hardcoded 10s — now from config.

---

## 🟣 2026-02-10 — Initial release

- Verse retrieval, audio playback, 18 reciters, sura list.
- SQLite user database, full localization, Telegram Stars, tafsir integration.
