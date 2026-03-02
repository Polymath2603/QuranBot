# 📋 Changelog

---

## 🟢 2026-03-02 — Current

### ✨ Added
- **Daily hadith scheduler** — `_daily_hadith_job` sends a random hadith to `CHANNEL_ID` automatically. Powered by PTB's built-in `JobQueue` (no extra scheduler dependency). Scheduled via `_post_init` using `run_daily()` at configurable UTC hours.
- **`DAILY_HADITH_COUNT`** — number of hadiths sent per day (default `3`, set `0` to disable). Configured via `.env`.
- **`DAILY_HADITH_HOURS`** — comma-separated UTC hours for each send (default `7,14,20`). Configured via `.env`.

### 🔄 Changed
- **`requirements.txt`** — `python-telegram-bot>=21.3` → `python-telegram-bot[job-queue]>=21.3` to enable `JobQueue`.

---

## 🟡 2026-03-01

### 🐛 Fixed
- **`.env.example` wrong token key** — was `TELEGRAM_BOT_TOKEN`; `config.py` reads `BOT_TOKEN`. Anyone following the example would start the bot with an empty token and get a silent failure on first update. Fixed to `BOT_TOKEN`.
- **`subtitles._dur()` silent wrong output** — guard was commented out with a reference to `VIDEO_FALLBACK_DUR` which no longer exists. If `durations` was shorter than the verse count, the function silently returned garbage or crashed unpredictably. Now raises an explicit `IndexError` with a descriptive message pointing to the likely cause (missing audio files).
- **`video._clean_verse()` importing `re` inside function** — `import re as _re` ran on every video frame. Moved to module-level import.

### ✨ Added
- **`DONATE_URL`** — new `.env` variable. Points to a channel post listing all donation addresses. Donate screen now shows a link button instead of embedding raw addresses in the bot message. Addresses are in the README and the linked post only.
- **Channel button labelled `قناة نور الحديث`** — both `ar.json` and `en.json` updated. Arabic name used in both languages as requested.

### 🔄 Changed
- **Hadith source: hadeethenc.com API → local SQLite** — `core/hadith.py` completely rewritten. Now reads from 9 local SQLite files in `data/hadith/` (~35k hadiths across all books). DB counts are indexed at module import time — no repeated filesystem scans or connections per request. Weighted random selection by DB size is O(n_books). `threading.Lock` and `_ready` flag removed (startup index is deterministic and never changes). `get_hadith(id)` removed (was in changelog but never implemented). `get_total_count()` kept for completeness.
- **`FILE_MAP` corrected** — `ara-dehlawi1.sqlite` (حجة الله البالغة) added; it was present in `data/hadith/` but never used. All 10 books now mapped.
- **Donate handler** — `donate_manual` locale key removed; donate screen shows Stars buttons + `DONATE_URL` link button only. Addresses live in README and the linked channel post.
- **Queue cancel fast-path** — `RequestQueue._cancelled_ids` set added. `cancel()` marks the item in-memory; `_consume()` checks the set first and skips the DB round-trip entirely for cancelled items.
- **Dead locale keys removed** (both `ar.json` and `en.json`): `download_sura`, `search`, `progress_rendering`, `progress_encoding`, `progress_concat`, `progress_compositing`, `progress_uploading`, `donate_manual`.

### 🗑️ Removed
- **`CHAR_LIMIT = CHAR_LIMIT`** (bot.py line 818) — pointless self-assignment, already imported from config.
- **`get_total_count` from bot.py import** — was imported but never called.

### 📄 Docs
- **TECHNICAL.md** fully rewritten — correct video pipeline (3 FFmpeg passes, not 1), correct audio pipeline (`mutagen` not `-map_metadata -1`), correct hadith source (local SQLite not hadeethenc.com API), azkar scheduler section removed, `data/hadith/` directory documented, `quran-simple.txt` added to data sources table, all config variables updated, database models table added, `file_id` cache key format documented.
- **README.md / README.en.md** — donation addresses updated to match current bot values, hadith description corrected (local SQLite, not hadeethenc.com), `DONATE_URL` added to `.env` example, `MAX_AYAS_PER_REQUEST` corrected to 40, azkar daily-send claim removed.
- **TODO.md** — "50-aya cap" corrected to 40, azkar entry removed from Done, donate entry updated.

---

## 🟡 2026-02-28


### 🐛 Fixed
- **Search: long queries returned no results** — root cause: U+0670 (dagger alif ٰ)
  inside words like `إِلَٰهَ` was being converted to a full ا letter in step 1 of
  `normalize_arabic()`, turning 'إله' (3 chars) into 'الاه' (4 chars). User queries
  without dagger alif never matched. Fix: strip U+0670 before any letter substitution.
  Additionally, Quranic annotation marks U+06D6–U+06ED (pause signs ۚ ۖ, small waw ۥ,
  etc.) were surviving normalization and breaking word boundaries. Both fixed.
- **Album art not removed** — previous approach used `ffmpeg -c:a copy` + `-map_metadata -1`
  to strip APIC frames. In codec-copy mode some ffmpeg versions preserve APIC frames as
  part of the bitstream, not container metadata. Replaced entirely with `mutagen` (ID3
  library): directly deletes APIC frames in-place, no temp file, no re-mux, 100% reliable.
  `mutagen>=1.47.0` added to `requirements.txt`.
- **Azkar constants lingering in config.py** — `AZKAR_HOUR` and `AZKAR_MINUTE` removed.

- **Search false negatives** — NLU `_match_sura_name()` was fuzzy-matching full sentences against sura names via `WRatio`'s partial matching, causing long queries to be classified as sura navigation instead of search. Fix: skip sura name matching when input is more than 3 words and contains no digits.
- **Album art not stripped on cached files** — `gen_mp3()` early-returned on cache hit without running `_strip_album_art()`. Fix: always run `_strip_album_art()` on the returned path (idempotent).

- **`/dhikr` error messages not localized** — all five status strings now use `t()`.
- **`donate_title` bold syntax** — was Markdown `**bold**` inside HTML-mode message. Fixed by switching to MarkdownV2.
- **`donate_manual` addresses not click-to-copy** — rewritten in MarkdownV2 with `>\`address\`` format.
- **PayPal link preview** — `disable_web_page_preview=True` added.
- **`feedback_empty` / `help_text` en.json** — synced to ar.json.

### ✨ Added
- **Hadith feature** (`core/hadith.py`) — random Arabic hadiths from local SQLite databases.
  - `/hadith` — sends a random hadith to the requesting user.
  - `/chadith` — admin only: sends a random hadith to the configured channel.
- **Admin statistics** — `/admin` now shows: users, queue, audio generated, video generated,
  hadiths sent (personal + channel), Telegram Stars donations, disk, cache, cached files,
  rate-limited users, top reciters.

- **`BotStats` table** — new SQLite table tracking lifetime counters: `generated_audio`, `generated_video`, `hadiths_sent_personal`, `hadiths_sent_channel`, `stars_donations`.
- **Admin panel expanded** — now shows all `BotStats` counters.

---

- **25 Stars donation tier** — keyboard now 2×2.
- **Dhikr locale keys** — `dhikr_no_channel`, `dhikr_pool_empty`, `dhikr_no_text`, `dhikr_sent`, `dhikr_error`.

### 🗑️ Removed
- **Azkar entirely** — `core/azkar.py` deleted. `data/husn_en.json` can be safely deleted.
  All scheduler code removed. Replaced by Hadith feature.

---

### 🔄 Changed
- **Donate handler** — switched to `parse_mode="MarkdownV2"`.
- **Donate keyboard** — 4 Stars buttons in 2×2 grid.

---

---

## 🟡 2026-02-27

### 🐛 Fixed
- **Queue position messages never shown** — `status_msg_id=None` was passed to the queue. Fixed: handlers now send a `⏳` message immediately and pass its ID.
- **Delete without edit** — progress messages now edited to `"."` before deletion.
- **TXT format mentioned in help text** — removed from both locale files.
- **Arabic-Indic numerals in locale strings** — replaced with ASCII digits in locale files (video keeps Arabic-Indic via Pillow independently).

### ✨ Added
- **Basmala handling** — context-sensitive: `﷽` in text/search, `﷽\n` in page view, stripped in video/SRT/LRC.
- **`CHANNEL_ID`** added to `config.py`.
- **Improved `/help`**.

### 🔄 Changed
- **Position message reused as progress bar** — edited in-place instead of sending a new message.
- **Cached hits skip the queue entirely**.

---

## 🔵 2026-02-26

### 🐛 Fixed
- **Album art stripping** — `-map_metadata 0` preserved APIC frames. Fixed: `-map_metadata -1` + re-add title/artist only.
- **Verse format inconsistency** — `back_to_verse_handler` rendered without aya number. Now consistent.

### ✨ Added
- **Audio progress bar** — `gen_mp3` accepts `progress_cb`. Download phase 0–70%, concat 85%, strip 100%.

### 🔄 Changed
- **Verse text format** — `﴿ verse (aya) ﴾` for single ayas; continuous block for ranges.
- **Progress bars simplified** — format: `🎧\n{bar} {pct}%` / `🎬\n{bar} {pct}%`.
- **TXT format removed** — cycle is now `msg → lrc → srt`.

---

## 🔵 2026-02-25

### 🐛 Fixed
- `NameError: 'title' is not defined` in `play_audio_handler`.
- `NameError: 'help_handler' is not defined`.
- `DetachedInstanceError` on startup.
- `start_aya > end_aya` and aya bounds validation.

### ✨ Added
- `/help`, `/feedback`. Enhanced `/admin`. Superscript alif search normalization.
- Go-to-page button, search results inline, char-length pagination.
- `README.en.md`.

### 🔄 Changed
- `voice` → `reciter_code`. Video ratio toggle inline. Max-aya cap for ranges only.

---

## 🔵 2026-02-24

### 🐛 Fixed
- `build_verse_keyboard` crash. Empty `CHANNEL_URL` crash. Arabic-Indic aya numbers. Audio looping.

### ✨ Added
- Serial request queue, permanent `file_id` cache, `/admin`, 5-step progress bar, video ratio, album art stripping, NLU, localization, Telegram Stars, tafsir, SRT/LRC.

### 🔄 Changed
- Video pipeline — Pillow PNGs + FFmpeg composite, solid black `#141414` background.
- Reciter-namespaced output paths.

---

## 🔵 2026-02-23

### ✨ Added
- `subtitles.py`, `verses.py`, `utils.py`, `nlu.py`, `search.py` extracted from `bot.py`.
- SQLite user database, storage purge, rate limiter, LRU cache, persistent tafsir cache.

### 🐛 Fixed
- SRT/LRC timestamps from `ffprobe`. Relative imports throughout `core/`.

---

## 🟣 2026-02-10 — Initial release

- Verse retrieval, audio playback, 18 reciters, localization, Telegram Stars, tafsir.
