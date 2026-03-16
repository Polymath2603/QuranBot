# 📋 Changelog

---

## 🟢 2026-03-16 — Search Intelligence, Resource Expansion & Font Update

### ✨ Added
- **Search Highlighting** — Search results now feature word-level bold highlighting (`<b>` tags) for matching terms, making results easier to scan in the UI.
- **Enhanced Reciters (VOICES)** — Cleaned up duplicates and significantly expanded the list of voices to include popular reciters like Saood ash-Shuraym, Ali Al-Hudhaify, and Muhammad Ayyoub.
- **Global Tafsirs** — Expanded `TAFSIR_SOURCES` to include translations in Indonesian, Turkish, Spanish, German, and French.
- **Configurable Font Behavior** — New `FONT_SETTINGS` in `config.py` allows per-font control over text cleaning, numeral styles, and brackets.
- **Verse Number Brackets Toggle** — Verse numbers can now be toggled between bracketed `(3)` and plain `3` styles via configuration.

### 🔄 Changed
- **Uthmani Font Upgrade** — Updated the core Hafs font to the latest official **KFGQPC Hafs v14** (`UthmanicHafs1-Ver14.ttf`) for superior rendering.
- **Smart Text Cleanup** — The `clean_verse` logic now uses regex to selectively remove Quranic pause marks and annotations, ensure a premium look.
- **HTML Search Results** — Search result handlers in `bot.py` now use `parse_mode="HTML"` to support rich highlighting.

### 🐛 Fixed
- **Image Generation Payload** — Corrected a critical typo in the generation queue that previously caused empty or mismatched images.
- **Video Text Looping** — Disabled the unintended looping of the text track, ensuring it doesn't repeat when audio is longer than the verse content.

---

## 🟢 2026-03-14 — Visual Consistency & System Stability

### ✨ Added
- **Hardware Acceleration** — FFmpeg now auto-detects and uses hardware encoders (NVENC for NVIDIA, VAAPI for Linux, VideoToolbox for macOS) for dramatically faster video rendering.
- **Search Context Snippets** — Search results now display the matching word with surrounding words for better context, instead of just the first few words of the verse.
- **Safe Queue Processor** — Implemented a robust error-handling wrapper for background tasks to ensure the bot remains stable even if a specific generation job fails.

### 🔄 Changed
- **Unified Quran Text** — All visual generation (Images, Videos) and text responses now exclusively use the high-quality Uthmani script (`quran-uthmani.txt`) for total visual consistency.
- **Regrouped Settings Menu** — Simplified the main settings menu into four categories: Language, Reciter, Media (Image/Video), and a "More" sub-menu for advanced options (Tafsir, Mushaf, Text Format).
- **Admin Panel Cleanup** — Removed noisy user statistics (top reciters, language breakdown) to focus on operational health, queue status, and system resources.

### 🧹 Removed
- **Unused Code** — Stripped dozens of unused imports and dead variables from `bot.py` to improve maintainability and performance.

### 🐛 Fixed
- **Queue Persistence** — Improved cancellation tracking across bot restarts to prevent orphaned tasks in the database.
- **Verse Boundary Checks** — Fixed edge cases in the search result handler where verse numbers could exceed sura limits.

---

## 🟢 2026-03-14 — Queue Administration, CLI Export & Pipeline Polish

### ✨ Added

- **Simple Export CLI (`cli.py`)** — New command-line tool to generate verse audio, images, and videos directly from the terminal. Supports theme/font overrides and custom output paths.
- **Admin Cancel All** — Added `/cancelall` command for administrators to flush the entire system queue.
- **Individual Cancellation** — Added a "Cancel" button to the active generation progress message, allowing users to abort their own requests mid-queue.
- **Future Roadmap** — Created `TODO.md` to track planned UI/UX, performance, and feature enhancements.

### 🐛 Fixed

- **Text Fading in Generated Video** — Improved video rendering by using a solid black background pass followed by a colorkey filter, ensuring text and background themes blend without visual artifacts.
- **Python-Telegram-Bot Compatibility** — Monkey-patched `Message` methods to resolve `TypeError` issues caused by incorrect `reply_to_message_id` handling in newer library versions.
- **Hardcoded Emojis in Locales** — Stripped UI symbols (like ⚙️) from `ar.json` and `en.json` to improve RTL compatibility; symbols are now managed dynamically in code.
- **Error Privacy** — Technical stack traces are now masked from users, replaced with a generic localized error message while logging the full trace for debugging.
- **Queue Error UX** — Generation errors now update the existing progress message (❌) instead of sending a new unlinked message.
- **Git Hygiene** — Updated `.gitignore` to properly exclude generated outputs and database files while preserving core data assets.

### 🔄 Changed

- **Visual Defaults** — Default theme for both images and videos is now `"parchment"` (paper-like aesthetic).
- **Cache Persistence** — Upgraded cache storage IDs and filenames to include theme, font, and aspect ratio, preventing cache collisions when visual settings change.
- **Increased Timeouts** — Network and download timeouts significantly increased to handle large video composites and slow API responses more reliably.
- **Start Command** — Removed redundant usage counters from the `/start` handler to streamline database operations.
- **Documentation** — Refreshed `README.md`, `README.en.md`, and `TECHNICAL.md` with new features and architecture details.

---

## 🟢 2026-03-12 — Bug fixes & UX corrections

### 🐛 Fixed

- **Image button always appeared** — "More" keyboard now hides Image button when aya count exceeds `AYAS_PER_IMG_PAGE` (default 5).
- **Text message aya numbers were Arabic-Indic** — all aya numbers in text messages, titles, and captions now use western digits (123).
- **Image resolution "auto" was removed by mistake** — restored as default. Video ratio was never affected.
- **Image canvas was fixed at portrait/landscape** — "auto" resolution is now the default again, rendering content-fitted auto-height images at 1080px width.
- **Back button had label text** — `back` locale keys now contain only `🔙` (no "Back" / "رجوع" text).

### 🔄 Changed

- `build_more_keyboard` gates Image button: hidden when `end - start + 1 > AYAS_PER_IMG_PAGE`.
- `IMAGE_PADDING = 20` still in effect for fixed-canvas modes (portrait/landscape).
- `DEFAULT_IMAGE_RESOLUTION = "auto"` restored.

---

## 🟢 2026-03-12 — UX Polish

### 🔄 Changed

- **Settings → Other**: added Language toggle button (`🌐`) at top of the sub-menu.
- **Settings**: Source and Reciter are now on separate rows (were combined on one row).
- **Aya keyboard**: "More" expands to image / video / page / back (was already implemented; keyboard spec finalized).
- **Image renderer**: `IMAGE_PADDING` reduced to 20px (from 40px) — text now uses near-full canvas width.
- **Image resolution**: "auto" option removed; portrait (1080×1920) is now the default. Resolutions are portrait and landscape only.
- **Video frames**: basmala completely removed from video frames (stripped before render, not displayed).
- **Paging arrows**: ➡️ = next, ⬅️ = previous, 🔙 = back — applied uniformly across text paging, image paging, tafsir paging, mushaf pages, sura list, and voice list.
- **Number format in text messages**: aya numbers always rendered as Arabic-Indic (٣) in all text message contexts.

### 🗑️ Removed

- `"auto"` image resolution option and `res_auto` locale key.
- Basmala display logic from `video.py` `_build_entries` (basmala is now stripped, not rendered).

---

## 🟢 2026-03-12 — UX Reformat, Mushaf, Image Queue

### 🐛 Fixed

- **`_build_entries` NameError in `core/video.py`** — function body existed but the `def` line was accidentally stripped, causing a crash on every video generation request.

### ✨ Added

- **Mushaf pages** (`core/mushaf.py`) — serves local PNG files from `data/images/{source}/`. Caches Telegram `file_id` in `ids.json` per source. Three sources: hafs, warsh, tajweed (configured in `config.PAGE_SOURCES`). Not affected by text format settings.
- **Image queue** — verse images now go through the serial request queue when not cached, same as audio/video.
- **Image resolution setting** — auto (height from content), portrait (1080×1920), landscape (1920×1080).
- **Photo settings sub-menu** — font, theme, resolution.
- **`config.py` centralised lists** — `PAGE_SOURCES`, `TAFSIR_SOURCES`, `HADITH_FILES`, `IMAGE_RESOLUTIONS`, `img_fid_key()`, `vid_fid_key()`, `aud_fid_key()`. Adding/removing a reciter, tafsir, or mushaf source now requires only a config edit.

### 🔄 Changed

- **Aya keyboard** — text | tafsir | audio on row 1; "More →" expands image, video, page, back.
- **Image button** — only shown inside "More" menu; verse character length no longer gates it.
- **Page button** — opens mushaf image (not text). Works via `mushaf_handler`.
- **Format cycle** — `msg → lrc → srt` (image removed from text format; image is its own button).
- **Settings hierarchy** — Source + Reciter at top; Other → tafsir, format, video, photo.
- **File-ID keys** — compact indexed format: `audio:{reciter}:{sura}:{start}:{end}`, `video:{reciter}:{sura}:{start}:{end}:{font}:{theme}:{ratio}`, `image:{sura}:{start}:{end}:{font}:{theme}:{res}`.
- **Basmala + numbers in video** — same font-conditional logic as images: uthmani font uses raw Arabic basmala text and Arabic-Indic numerals; other fonts use ﷽ glyph and western digits.
- **Tafsir** — cloud only (alquran.cloud API + DB cache); local file fallback removed.

### 🗑️ Removed

- `IMAGE_CHANNEL_ID` env var and all CDN upload logic.
- `core/image.py`: `upload_to_cdn()`, `_img_cache_key()`.
- `img` removed from text format cycle.

---

## 🟢 2026-02-28 — Latest changelog update

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

### ✨ Added

- **Hadith feature** (`core/hadith.py`) — random Arabic-only hadiths via
  `hadeethenc.com/api/v1`. No auth required. Format: hadith text + separator + attribution.
  - `/hadith` — sends a random hadith to the requesting user.
  - `/chadith` — admin only: sends a random hadith to the configured channel.
- **Admin statistics** — `/admin` now shows: users, queue, audio generated, video generated,
  hadiths sent (personal + channel), Telegram Stars donations, disk, cache, cached files,
  rate-limited users, top reciters.

### 🗑️ Removed

- **Azkar entirely** — `core/azkar.py` deleted. `data/husn_en.json` can be safely deleted.
  `AZKAR_HOUR` / `AZKAR_MINUTE` removed from `config.py`. All scheduler code removed.
  Replaced by Hadith feature.

---

## 🟡 2026-02-28

### 🐛 Fixed

- **Search false negatives** — NLU `_match_sura_name()` was fuzzy-matching full sentences (e.g. "الله لا اله الا هو الحي القيوم") against sura names via `WRatio`'s partial matching, causing long queries to be classified as sura navigation instead of search. Fix: skip sura name matching when input is more than 3 words and contains no digits.
- **Album art not stripped on cached files** — `gen_mp3()` early-returned on cache hit without running `_strip_album_art()`. Old files generated before the strip was added were served with album art forever. Fix: always run `_strip_album_art()` on the returned path (idempotent — no-op if already clean).

### ✨ Added

- **`/hadith`** — sends a random Arabic hadith to the requesting user. Fetches from `hadeethenc.com` API (Arabic, authenticated hadiths only). Format: hadith text → attribution line (source | grade).
- **`/chadith`** — admin-only: pushes a random Arabic hadith to the channel. Same source as `/hadith`.
- **`BotStats` table** — new SQLite table tracking lifetime counters: `generated_audio`, `generated_video`, `hadiths_sent_personal`, `hadiths_sent_channel`, `stars_donations`.
- **Admin panel expanded** — now shows all `BotStats` counters in addition to existing user/queue/disk stats.
- **`core/hadith.py`** — new module. Wraps `hadeethenc.com/api/v1/` with `get_random_hadith()`, `get_hadith(id)`, `get_total_count()`, and `format_hadith()`.

### 🗑️ Removed

- **Azkar entirely** — `core/azkar.py` deleted. `data/husn_en.json` can be safely deleted. All scheduler code, `load_azkar` calls, dhikr locale keys removed from `bot.py`. Replaced by Hadith feature.

---

## 🟡 2026-02-28

### 🐛 Fixed

- **`/dhikr` error messages not localized** — all five status strings (no channel, pool empty, no text, sent, error) now use `t()` with locale keys in both `ar.json` and `en.json`.
- **`donate_title` bold syntax** — was Markdown `**bold**` inside an HTML-mode message, rendering literally. Fixed by switching donate handler to MarkdownV2 and rewriting `donate_title` in both locales accordingly.
- **`donate_manual` addresses not click-to-copy** — HTML `<blockquote>` tags with backticks were rendering backticks as literal characters. Rewritten in MarkdownV2: `>\`address\`` combines block-quote visual with monospace click-to-copy.
- **PayPal link preview** — donate message now sets `disable_web_page_preview=True` to suppress the PayPal preview card.
- **`feedback_empty` en.json** — synced to ar.json: example command now on its own line.
- **`help_text` en.json** — `/feedback <message>` wording synced to ar.json.

### ✨ Added

- **25 Stars donation tier** — new ⭐ 25 Stars button added to donate keyboard. Keyboard is now 2×2 (25/50 top row, 100/500 bottom row).
- **Telegram Stars section in donate_manual** — moved to bottom of the message after all wallet addresses, in both locales.
- **Dhikr locale keys** — `dhikr_no_channel`, `dhikr_pool_empty`, `dhikr_no_text`, `dhikr_sent`, `dhikr_error` added to both `ar.json` and `en.json`.

### 🔄 Changed

- **Donate handler** — switched from `parse_mode="Html"` to `parse_mode="MarkdownV2"`. `donate_title` and `donate_manual` in both locales rewritten for MDV2 (escaped special chars, `>\`code\`` for addresses).
- **`donate_title`** — Stars heading removed from both locales (Stars section now appears at the end of `donate_manual` instead).
- **Donate keyboard layout** — 4 Stars buttons arranged in 2×2 grid instead of 2+1 rows.

---

## 🟡 2026-02-27

### 🐛 Fixed

- **Queue position messages never shown** — `status_msg_id=None` was passed to the queue, so `_broadcast_positions` had nothing to edit. Fixed: handlers now send a `⏳` message immediately and pass its ID to the queue.
- **Delete without edit** — progress/position messages are now edited to `"."` before deletion for a clean visual dismissal.
- **TXT format still mentioned in help text** — removed from both `ar.json` and `en.json` `help_text` keys.
- **Arabic-Indic numerals in locale strings** — all `٠١٢٣٤٥٦٧٨٩` replaced with `0-9` in both locale files (video generation keeps Arabic-Indic digits independently via Pillow rendering).

### ✨ Added

- **Daily azkar to channel** (`core/azkar.py`) — loads `data/hisnAlMuslim.json` (Husn Al-Muslim DB), picks a random dhikr, sends it to `CHANNEL_ID` at 07:00 UTC every day. Bot must be admin in the channel. Scheduler uses a lightweight asyncio loop (no extra dependencies).
- **Basmala handling** — suras that start with `بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ` (all except 1:1 and 9:1) are now handled context-sensitively:
  - **Text / search** → replaced with `﷽` symbol
  - **Page navigation** → replaced with `﷽` + line break
  - **Video / SRT / LRC** → removed entirely
- **`CHANNEL_ID`** added to `config.py` (separate from `CHANNEL_URL` — ID is used by azkar scheduler, URL is used by inline button).
- **Improved `/help`** — covers all input formats, all buttons, all commands, channel link, feedback instructions.
- **Click-to-copy donation addresses** — all wallet addresses wrapped in backticks (Telegram inline code) in `donate_manual` locale key.

### 🔄 Changed

- **Position message reused as progress bar** — instead of sending a new message when generation starts, the position message is edited in-place to show the progress bar (`🎧\n▰▱▱▱▱ 20%`). One less message in chat.
- **Cached hits skip the queue entirely** — if `file_id` cache hits in the handler, media is sent directly with no queue entry and no position message.

---

## 🔵 2026-02-26

### 🐛 Fixed

- **Album art stripping** — previous implementation used `-map_metadata 0` which preserved APIC (image) ID3 frames. Fixed: metadata fully dropped with `-map_metadata -1`, then only `title` and `artist` re-added from `ffprobe`.
- **Verse format inconsistency** — `back_to_verse_handler` still rendered `﴿ text ﴾` without aya number. Now consistent everywhere.

### ✨ Added

- **Audio progress bar** — `gen_mp3` accepts `progress_cb`. Download phase 0–70%, concat 85%, strip 100%. Bar: `🎧\n▰▰▱▱▱ 40%`.

### 🔄 Changed

- **Verse text format** — `﴿ verse (aya) ﴾` for single ayas; `﴿ verse1 (1) verse2 (2) ... ﴾` continuous block for ranges.
- **Progress bars simplified** — state description labels removed. Format: `🎧\n{bar} {pct}%` / `🎬\n{bar} {pct}%`.
- **Wait messages removed** — no wait message on enqueue; media arrives after progress bar disappears.
- **TXT format removed** — cycle is now `msg → lrc → srt`. Removed from all code, locale, and docs.

### 🗑️ Removed

- `fmt_txt` locale key. `generating_audio` / `generating_video` locale keys. `build_txt` import.

---

## 🔵 2026-02-25

### 🐛 Fixed

- `NameError: 'title' is not defined` in `play_audio_handler`.
- `NameError: 'help_handler' is not defined` — output files not shipped. Fixed.
- `DetachedInstanceError` on startup — queue accessed item after session close.
- `start_aya > end_aya` and aya bounds — both rejected with localized errors.

### ✨ Added

- `/help` — localized usage guide. `/feedback <text>` — forwarded to `ADMIN_IDS`.
- Enhanced `/admin` — AR/EN user split, queue count, cached files, rate-limited count.
- `ٰ` (superscript alif U+0670) normalized in search.
- Go-to-page button, search results inline, char-length pagination for text and tafsir.
- `README.en.md` — English README with bidirectional nav links.

### 🔄 Changed

- `voice` → `reciter_code`, `artist_name` → `reciter`.
- Video ratio toggle inline in settings (no submenu).
- Max-aya cap only for ranges; full-sura always allowed.
- All docs converted to English.

### 🗑️ Removed

- Video background, color, border — stripped from all code and config.
- `BG_DIR` from `config.py`. Dead video settings handlers and dispatch entries.

---

## 🔵 2026-02-24

### 🐛 Fixed

- `build_verse_keyboard` crash — was returning `None`.
- Empty `CHANNEL_URL` crash — button only shown when URL non-empty.
- Arabic-Indic aya numbers in video — `١٢٣` not `(123)`.
- Audio looping at end of video. Bot blocking during generation.

### ✨ Added

- Serial request queue (`core/queue.py`) — SQLite-backed, cancel button, survives restarts.
- Permanent `file_id` cache — instant re-send with no re-upload.
- `/admin` command. `MAX_AYAS_PER_REQUEST`, `ADMIN_IDS` in `config.py`.
- 5-step progress bar. Video ratio portrait/landscape. Album art stripping.
- All constants in `config.py`. NLU, localization, Telegram Stars, tafsir, SRT/LRC export.

### 🔄 Changed

- Video pipeline — Pillow PNGs + single FFmpeg pass, solid black `#141414` background.
- Reciter-namespaced output paths. `core/` as proper Python package.

---

## 🔵 2026-02-23

### ✨ Added

- `subtitles.py`, `verses.py`, `utils.py`, `nlu.py`, `search.py` extracted from `bot.py`.
- SQLite user database, storage purge, rate limiter, LRU cache, persistent tafsir cache.
- `callback_router` dispatch dict.

### 🐛 Fixed

- SRT/LRC timestamps from `ffprobe`. Relative imports throughout `core/`.

---

## 🟣 2026-02-10 — Initial release

- Verse retrieval, audio playback, 18 reciters, localization, Telegram Stars, tafsir.
