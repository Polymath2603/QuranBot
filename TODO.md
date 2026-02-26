# 📋 TODO

---

## 🟡 Planned

- [ ] **Daily verse push** — `/subscribe` sends a random verse every morning via APScheduler
- [ ] **Bookmarks** — `/bookmark` saves a verse; `/bookmarks` lists them with buttons
- [ ] **Quiz mode** — show a verse, user guesses the sura, track score per user

---

## ✅ Done

### 🌟 Core features
- [x] 18 reciters — MP3 with full ID3 metadata; album art stripped from output files
- [x] **Video generation** — Pillow PNGs + FFmpeg composite; black bg, white text; landscape / portrait
- [x] Video ratio — landscape 16:9 / portrait 9:16 — direct toggle in settings (no submenu)
- [x] Text export — SRT (timestamped) · LRC (timestamped)
- [x] Two tafsirs — Al-Muyassar and Al-Jalalayn, character-length pagination
- [x] Full-text search — verse inline in message, 2-per-row buttons, char-length pagination
- [x] 604 Mushaf pages — paginated with ◀️▶️
- [x] Go-to-page button on single-aya keyboard
- [x] NLU — Arabic + English: aya / range / surah / page / search
- [x] Fuzzy sura name matching (rapidfuzz)
- [x] Telegram Stars donations + multi-method payment addresses (PayPal, BTC, ETH, SOL…)

### ⏳ Queue & concurrency
- [x] Serial request queue — SQLite-backed, survives restarts
- [x] Silent enqueue — no wait message; media arrives directly
- [x] Cancel button on every queued request
- [x] `ThreadPoolExecutor(2)` — bot stays responsive during FFmpeg encoding
- [x] 5-step progress bar for video (🎬) and audio (🎧) — `▰▰▱▱▱ 40%` format

### 🗃️ Caching & storage
- [x] Permanent `file_id` cache — instant re-send with no re-upload
- [x] Tafsir cache — SQLite + LRU, 30-day TTL
- [x] Per-verse MP3 disk cache, auto-purged when storage is low
- [x] Reciter-namespaced output paths `output/{reciter_code}/`

### 🔒 Validation & safety
- [x] `start_aya > end_aya` rejected with localized error
- [x] `start_aya < 1` or `end_aya > sura_length` rejected with localized error
- [x] 50-aya cap for ranges; full-sura requests always unrestricted
- [x] Rate limiting — 10 requests / user / hour

### 🎨 UI & UX
- [x] Arabic-Indic digits `١٢٣` in video frames
- [x] Sura names always prefixed: `سورة الإخلاص` / `Surah Al-Ikhlas`
- [x] All UI strings localized (ar.json + en.json)
- [x] `/help` — localized usage guide
- [x] `/feedback` — forwarded to ADMIN_IDS with user info
- [x] `ٰ` (superscript alif U+0670) normalized in Arabic search

### 🔧 Admin & ops
- [x] `/admin` — users (AR/EN split), queue depth, processing count, cached files, rate-limited count, top reciters
- [x] `ADMIN_IDS` in `config.py`
- [x] `MAX_AYAS_PER_REQUEST` in `config.py`
- [x] Auto storage purge on low disk
- [x] Channel button hidden when `CHANNEL_URL` is empty
