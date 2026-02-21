# QBot - TODO / Refactor Plan

Status legend: ⬜ Pending | 🔄 In Progress | ✅ Done

---

## 🐛 Bug Fixes

- ✅ **BUG-1** `tafsir.py` + `tafsir_handler`: `user.tafsir_source` is stored but never passed to `get_tafsir()`. Hardcoded `ar.muyassar`. Fix: pass source from user prefs and map to correct API edition string.
- ✅ **BUG-2** `back_to_verse_handler`: single-aya back button builds `text_{sura}_{start}_{end}` but single-aya messages originally use `text_{sura}_{aya}` (no end). Causes `text_handler` misparsing.
- ✅ **BUG-3** `voice_handler`: `query.data.replace("voice_", "", 1)` is fragile — relies on router order to not catch `voice_list_*` first. Fix: use more specific matching.
- ✅ **BUG-4** `text_handler`: early return on `fmt in [srt, lrc, txt]` skips Back button for the user. Fix: always send nav keyboard.
- ✅ **BUG-5** `audio.py` FFmpeg metadata: `"metadata"` / `"metadata:g:1"` keys are non-standard in ffmpeg-python. Fallback path also drops metadata entirely. Fix both paths.
- ✅ **BUG-6** `gen_video` output filename collision: uses `title` as filename, so two users requesting same surah share the same path. Fix: include `sura_start_end` in filename like `gen_mp3` does.

---

## ⚠️ Warnings / Safety

- ✅ **WARN-1** `tafsir.py`: bare `except` silently swallows all errors. Add `logging.warning` with exception info.
- ✅ **WARN-2** `bot.py` `play_audio_handler`: `open(mp3_path, "rb")` not in a `with` block — file leaks if `reply_audio` raises. Use `with open(...)`.
- ✅ **WARN-3** `bot.py` `setting_format_toggle`: detached `user` object re-added to a new session. Re-query user inside the session instead.
- ✅ **WARN-4** Error messages expose raw exceptions to users (`f"Error: {e}"`). Log internally, show generic message to user.
- ✅ **WARN-5** `downloader.py`: uses `print` instead of `logging`. Switch to `logging`.

---

## 🗑️ Dead Code Removal

- ✅ **DEAD-1** Remove `setting_text_toggle` function (empty, commented out in router).
- ✅ **DEAD-2** Remove `tafnav_` legacy branch in `callback_router` (never triggered).
- ✅ **DEAD-3** Remove `search_handler` function and `menu_search` callback branch (NLU handles search automatically).
- ✅ **DEAD-4** Remove `waiting_for_search` logic in `message_router`.
- ✅ **DEAD-5** Remove `text_source` column from `User` model (stored but never read/written).

---

## 🔁 Duplicate / Repeated Code

- ✅ **DUP-1** Extract `build_verse_keyboard(sura, start, end, lang, fmt)` helper — keyboard built identically in 4+ places in `bot.py`.
- ✅ **DUP-2** Extract `async def delete_status_msg(msg)` helper — identical `edit_text(".")` + `delete()` pattern in `play_audio_handler` and `video_generate_handler`.
- ✅ **DUP-3** Unify `start` and `main_menu` — both build identical keyboard/text, differ only in `reply_text` vs `edit_message_text`.
- ✅ **DUP-4** Remove duplicate `get_page` in `data.py` — `search.py` is the correct owner (with -2 offset). `data.py` version is inconsistent.
- ✅ **DUP-5** Extract `safe_filename(title)` utility — `title.replace("/", "-").replace(":", "-")` repeated in `play_audio_handler`, `video_generate_handler`, `text_handler`, and `video.py`.
- ✅ **DUP-6** Extract `get_sura_start_index(quran_data, sura)` into `data.py` — `int(quran_data["Sura"][sura][0])` inlined in 3+ places in `bot.py`.

---

## 🔧 Refactoring

- ✅ **REF-1** Replace `callback_router` giant if-elif chain (~30 branches) with a dispatch dict + prefix matcher.
- ✅ **REF-2** Move `get_db_user` and `update_user_lang` from `bot.py` to `database.py`.
- ✅ **REF-3** Refactor `parse_message` in `nlu.py`: split into clearly named sub-functions, avoid reusing `text` variable for both normalized and keyword-replaced versions.
- ✅ **REF-4** Separate single-aya and range paths in `text_handler` — currently tangled with mixed branching throughout.
- ✅ **REF-5** Add callback data validation — `data.split("_")` with index access has no bounds checking. Wrap in try/except with graceful fallback.
- ✅ **REF-6** `video.py` should import rendering functions from `srt2mp4/genMP4.py` instead of copying inferior versions. Add `srt2mp4/__init__.py`. Delete duplicated `render_text_image`, `_smart_wrap`, `_font_cache`, `_get_font` from `video.py`.
- ✅ **REF-7** Align `video.py` constants with `srt2mp4`: FPS (30 vs 60), font size (90 vs 100).

---

## 🧹 Session / DB Improvements

- ✅ **DB-1** Reduce double DB hits: many handlers call `get_db_user` then open a second session to update. Combine into single session where possible.
- ✅ **DB-2** Persist tafsir cache to SQLite (new `tafsir_cache` table) with TTL (e.g. 30 days). Replace unbounded in-memory dict.

---

## 💾 Storage Management

- ✅ **STOR-1** Add `utils.py` with `check_and_purge_storage(threshold_mb=200, warn_mb=500)`. Purge oldest files from `data/audio/` and `output/` by mtime when free space is low.
- ✅ **STOR-2** Call storage check before every audio/video generation in `bot.py`.
- ✅ **STOR-3** Apply same purge logic to `output/` directory (generated MP3/MP4 files accumulate forever).

---

## 🚦 Rate Limiting

- ✅ **RATE-1** Add per-user rate limiting for audio/video generation (expensive operations). Suggested: max 3 concurrent or 10/hour per user. Implement in `utils.py` using a simple in-memory dict with timestamps.

---

## 📦 Project Structure

- ✅ **PROJ-1** Add `Pillow`, `moviepy`, `numpy` to `requirements.txt` (used but missing).
- ✅ **PROJ-2** Add `srt2mp4/__init__.py` to make it importable as a package.
- ✅ **PROJ-3** Create `utils.py` for: `safe_filename`, `delete_status_msg`, storage purge, rate limiter.

---

## 📝 Docs

- ✅ **DOC-1** Update `README.md` to reflect current features, removed search button, new utils.
- ✅ **DOC-2** Update `CHANGELOG.md` with all changes made in this refactor.
