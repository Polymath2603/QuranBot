# 📋 Changelog

---

## 🟢 2026-03-01 (Session 2) — Current

### 🔄 Changed
- **`ffmpeg-python` → `static-ffmpeg`** (`pip install static-ffmpeg`, no `apt` required).
  `static_ffmpeg.add_paths()` downloads a pre-built static binary on first run and injects
  it into PATH automatically.
  - `core/audio.py`: removed `ffmpeg` Python library; rewrote concat using subprocess with
    the concat demuxer (`-f concat -safe 0`, stream-copy, no re-encode). filter_complex
    fallback retained.
  - `core/video.py` / `core/subtitles.py`: subprocess calls now resolve binaries through
    `_resolve_ff()` / `_resolve_ffprobe()` — same static-ffmpeg mechanism.
  - `requirements.txt`: `ffmpeg-python>=0.2.0` → `static-ffmpeg>=2.5`.
- **Hadith** (`core/hadith.py`): 9 bundled SQLite databases in `data/hadith/`.
  Weighted random selection across all books. No network required.

---

## 🟡 2026-03-01 (Session 1) —
- changelog not updated yet
- neither are documents
- all documents might include outdated information currently 
- it's 2AM so i won't update it now
- i updated the code but not the documents
- wait next commit, maybe tomorrow or next week

## 🟡 2026-02-28 (Session 3)

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

## 🟡 2026-02-28 (Session 2)

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

## 🟡 2026-02-28 (Session 1)

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
