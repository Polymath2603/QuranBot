# QBot — TODO

---

## 🔴 Next Up (Chosen)

*(pick from the list below)*

---

## 🟡 Planned

- [ ] **Background selector** — re-enable the bg button in video settings; add support for uploading custom backgrounds per user.
- [ ] **Daily verse push** — opt-in `/subscribe`; sends a random verse every morning via APScheduler.
- [ ] **Inline mode** — `@bot البقرة ١` in any chat returns verse text + buttons.
- [ ] **Bookmarks** — `/bookmark` saves a verse; `/bookmarks` lists them with buttons.
- [ ] **Quiz mode** — show a verse, user guesses the sura; track score per user.

---

## 🟢 Done ✅

### Features
- [x] Audio recitation — 18 reciters, MP3 with embedded metadata
- [x] Video generation — Pillow text PNGs + FFmpeg composite, fade transitions
- [x] Text export — TXT, SRT (timestamped), LRC (timestamped)
- [x] Tafsir — Al-Muyassar & Jalalayn via AlQuran.cloud (LRU + SQLite cache)
- [x] Full-text search → tappable results that open verse keyboard
- [x] Page view — all 604 pages, paginated with ◀️▶️
- [x] NLU — Arabic + English verse / range / surah / page / search
- [x] Fuzzy sura name matching (rapidfuzz)
- [x] Telegram Stars donations
- [x] 18 reciters, 2-column voice list with pagination

### Queue & Concurrency
- [x] Serial request queue (`core/queue.py`) — SQLite-backed, survives restarts
- [x] Position tracking — status message auto-edits as queue advances
- [x] Cancel button on every queued request
- [x] `ThreadPoolExecutor` (2 workers) — bot stays responsive during FFmpeg encoding
- [x] Progress bar with 20% steps (edits status message from worker thread)

### Caching
- [x] Telegram `file_id` permanent cache (`output/file_ids.json`) — instant re-send, no re-upload
- [x] Tafsir persistent cache (SQLite + LRU, 30-day TTL)
- [x] Per-verse MP3 disk cache (auto-purged on low disk)
- [x] Reciter-namespaced output paths (`output/{voice}/…`)

### Video
- [x] Arabic-Indic aya numbers (`١٢٣`) in video frames
- [x] Audio is master clock — output duration = audio duration exactly
- [x] `VIDEO_SYNC_OFFSET` — tunable text-audio alignment
- [x] Background moved to final FFmpeg pass (one composite, not N)
- [x] Zoom-to-fit background (no distortion)
- [x] Per-verse fade-in/fade-out (half-fade each side)
- [x] ≥4 words per line enforced by DP balancer
- [x] Auto font-size shrink to fit frame
- [x] Landscape (16:9) / portrait (9:16) ratio setting
- [x] Text colour (white/black), border toggle
- [x] Background toggle code preserved (UI hidden pending rework)

### Settings & UX
- [x] Language toggle (AR / EN)
- [x] Text format toggle (msg / txt / lrc / srt) — `"off"` removed
- [x] Tafsir source toggle (Muyassar / Jalalayn)
- [x] Video settings screen
- [x] All UI strings localized (ar.json + en.json) — no hardcoded labels in bot.py

### Admin & Ops
- [x] `/admin` command — users, queue, disk, cache, top reciters
- [x] `ADMIN_IDS` in config — restrict admin access
- [x] `MAX_AYAS_PER_REQUEST = 50` — rejects oversized requests before queuing
- [x] Rate limiting — 10 requests/user/hour
- [x] Storage purge — deletes oldest files when disk < threshold
- [x] `CHANNEL_URL` guard — channel button hidden when URL is empty

### Architecture
- [x] `core/` subpackage — all business logic separated from handlers
- [x] `config.py` — all constants in one place
- [x] `callback_router` dispatch dict
- [x] SQLAlchemy models: `User`, `TafsirCache`, `QueueItem`
- [x] `post_init` hook — queue consumer started after bot is built
- [x] All relative imports in `core/` fixed

---

## 🐛 Known Issues

- [ ] `start_aya > end_aya` not validated — FFmpeg will error; user sees generic message.
- [ ] Very long suras (e.g. Al-Baqarah, 286 ayas) would exceed `MAX_AYAS_PER_REQUEST`; users need to request a sub-range manually.
- [ ] Portrait video may appear letterboxed in Telegram desktop client.
- [ ] Background video files with unusual pixel formats may cause FFmpeg errors (no `-pix_fmt` coercion on bg input).
