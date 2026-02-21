# Changelog

All notable changes to QBot will be documented in this file.

## [2.1.0] - 2026-02-21

### Fixed
- **Tafsir source ignored**: `get_tafsir()` was hardcoded to `ar.muyassar` regardless of user's selected source. Now correctly uses the user's `tafsir_source` preference and maps it to the correct AlQuran.cloud edition.
- **Back button after single-aya text**: `back_to_verse_handler` built incorrect callback data for single-aya messages, causing `text_handler` to misparse. Fixed to use consistent `verse_back_{sura}_{start}_{end}` format.
- **Text handler missing Back button**: Early-return on file format exports skipped the navigation keyboard. Back button is now always rendered.
- **FFmpeg metadata embedding**: `metadata` / `metadata:g:1` keys were non-standard in ffmpeg-python. Fixed to use `metadata:g:0` / `metadata:g:1`. Fallback concat now also embeds metadata.
- **Video filename collision**: `gen_video` used the human-readable title as filename, causing concurrent users requesting the same surah to share/overwrite the same file. Now uses `{sura:03d}_{start:03d}_{end:03d}.mp4`.
- **Detached SQLAlchemy object**: `setting_format_toggle` re-added a detached `User` object to a new session. Now re-queries the user within the session before updating.
- **Raw exceptions exposed to users**: `f"Error: {e}"` replaced with a generic localized error message; full traceback logged internally.
- **`downloader.py` used `print` instead of `logging`**: Switched to `logging` throughout.

### Added
- **`utils.py`**: New shared utility module containing:
  - `safe_filename(title)` — sanitizes titles for use as filenames (replaces `/` and `:`)
  - `delete_status_msg(msg)` — safely deletes Telegram status messages
  - `check_and_purge_storage(*dirs)` — checks free disk space; purges oldest files from `data/audio/` and `output/` when space is critically low (threshold: 200 MB, warning: 500 MB)
  - `is_rate_limited(telegram_id)` — per-user rate limiter for audio/video generation (10 requests/hour)
  - `LRUCache` — bounded LRU cache (max 500 entries) used by tafsir
- **Persistent tafsir cache**: Tafsir responses are now cached in a new `tafsir_cache` SQLite table with a 30-day TTL, surviving bot restarts. Backed by in-memory LRU for fast repeat lookups.
- **`TafsirCache` DB model**: New SQLAlchemy model in `database.py`.
- **`get_db_user` / `update_user_field`** moved to `database.py` (were in `bot.py`).
- **`get_sura_start_index()`** added to `data.py`; all inline `int(quran_data["Sura"][sura][0])` calls replaced.
- **`srt2mp4/__init__.py`**: Makes `srt2mp4` importable as a Python package.

### Changed
- **`video.py` now imports from `srt2mp4`**: `render_text_image`, `get_cached_font` imported from `srt2mp4/genMP4.py` instead of being duplicated. Video FPS aligned to 60, font size to 100 (matching `srt2mp4`).
- **`callback_router` refactored**: Replaced ~30-branch if-elif chain with a dispatch dict (`_EXACT_ROUTES`) and ordered prefix list (`_PREFIX_ROUTES`).
- **`build_verse_keyboard()` extracted**: The Audio/Text/Tafsir/Video keyboard was duplicated in 4+ places; now a single helper function.
- **`delete_status_msg()` extracted**: Identical status-deletion pattern in `play_audio_handler` and `video_generate_handler` replaced with shared utility.
- **`start` and `main_menu` unified**: Both now share `_welcome_keyboard()` helper.
- **`parse_message` refactored** (`nlu.py`): Split into clearly named sub-functions (`_detect_page`, `_detect_colon_notation`, `_detect_range`, `_detect_single`, `_parse_chunk`, `_match_sura_name`). The `text` variable is no longer reused for both normalized and keyword-replaced content.
- **`text_handler` split**: Single-aya and range paths separated into `_send_text_single` and `_send_text_range`. File formatting extracted to `_format_verse_file`.
- **Storage purge called** before every audio and video generation.
- **Rate limiting enforced** for audio and video generation.
- **Duplicate `get_page`** in `data.py` removed; `search.py` is the single source of truth.

### Removed
- **Dead code**: `setting_text_toggle` (empty function), `tafnav_` legacy callback branch, `menu_search` button and `search_handler`, `waiting_for_search` user_data flag, `text_source` column from `User` model.
- **`safe_filename` inline duplication**: Four identical `title.replace("/", "-").replace(":", "-")` expressions replaced with `utils.safe_filename()`.

### Dependencies
- Added `Pillow>=10.0.0`, `moviepy>=1.0.3`, `numpy>=1.24.0` to `requirements.txt` (were used but undeclared).

## [2.0.0] - 2026-02-10

### Added

- **Natural Language Understanding (NLU)**
  - Intelligent parsing of Surah names and verse references in Arabic and English
  - Support for complex queries: "من سورة الفاتحة 1 الى البقرة 4"
  - Fuzzy matching for Surah names using rapidfuzz
  - Arabic character normalization (Alif, Hamza, Taa Marbuta, Ya variations)
- **Database Integration**
  - SQLite database for persistent user data
  - User model storing: telegram_id, language preference, custom settings
  - Automatic user registration on first interaction
- **Localization System**
  - Separate locale files (en.json, ar.json)
  - Default language: Arabic
  - Dynamic string loading based on user preference
  - Settings menu for language switching
- **Telegram Stars Donations**
  - Primary donation method with preset amounts (50, 100, 500 Stars)
  - Invoice generation and payment handling
  - Thank you messages after successful payment
- **Enhanced Audio Features**
  - Audio metadata: Title (Surah + Range), Artist (Reciter name)
  - Album art removal for cleaner files
  - Status message auto-deletion after audio is sent
  - Reply-to-message support for better context
- **Tafsir Integration**
  - Tafsir button on verse responses
  - Fetches Tafsir Al-Muyassar from AlQuran.cloud
  - Available for single verses
- **UI Improvements**
  - Removed "Download Sura" and "Tafsir" from main menu (NLU handles this)
  - Added "Our Channel" button
  - Improved text formatting with Arabic ornamental brackets `﴿ ... ﴾`
  - Verse numbers displayed in parentheses

### Changed

- **Default Language**: Changed from auto-detect to Arabic for all new users
- **Search Enhancement**: Improved Arabic text normalization for better search results
- **Text Format**: Updated to `📖 Surah (Verse Range) \n\n ﴿ text ﴾`
- **Donation Links**: Updated PayPal link to current payment URL

### Technical

- Updated `python-telegram-bot` to >=21.3 for Telegram Stars support
- Added `SQLAlchemy` for database ORM
- Added `rapidfuzz` for fuzzy string matching
- Refactored `bot.py` for better modularity
- Created `nlu.py` for intent detection
- Created `database.py` for data persistence
- Updated `audio.py` to handle metadata via FFmpeg

## [1.0.0] - Initial Release

### Features

- Basic Quran verse retrieval
- Audio playback from EveryAyah.com
- Search functionality
- Multiple reciter support
- Manual Surah selection
- Basic donation links (crypto, PayPal)
