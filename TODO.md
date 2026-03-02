# 📋 TODO

---

## 🟡 Planned

- [ ] **Bookmarks** — `/bookmark` saves an aya; `/bookmarks` lists them with buttons
- [ ] **Quiz mode** — show a verse, user guesses the sura, track score per user
- [ ] **Daily verse push to users** — `/subscribe` to opt in; sends a random verse every morning

---

## ✅ Done

### 🌟 Core features
- [x] 18 reciters — MP3 with full ID3 metadata; album art stripped from output files
- [x] **Video generation** — Pillow PNGs + 3-pass FFmpeg pipeline; black #141414 bg, white text; landscape / portrait. The only Quran bot on Telegram with this feature.
- [x] Video ratio — landscape 16:9 / portrait 9:16, inline toggle in settings
- [x] Text export — SRT (timestamped) · LRC (timestamped)
- [x] Two tafsirs — Al-Muyassar and Al-Jalalayn, character-length pagination
- [x] Full-text Arabic search — comprehensive normalization, verse inline in message, 2-per-row buttons, char-length pagination
- [x] 604 Mushaf pages — paginated with ◀️▶️, go-to-page button on single-aya keyboard
- [x] NLU — Arabic + English: aya / range / surah / page / search
- [x] Fuzzy sura name matching (rapidfuzz)
- [x] Telegram Stars + multi-method donations (PayPal, BTC, ETH, SOL…) via channel post link
- [x] **Basmala handling** — `﷽` in text/search, `﷽\n` in page view, removed in video/subtitles
- [x] **Hadith** — `/hadith` (user) and `/chadith` (admin→channel). 9 local SQLite DBs, ~35k hadiths, weighted random selection.

### ⏳ Queue & concurrency
- [x] Serial request queue — SQLite-backed, survives restarts
- [x] Position message sent immediately → reused as progress bar → `"."` → deleted
- [x] Cached file_id hits bypass queue entirely — sent instantly from handler
- [x] Cancel button on every queued request
- [x] `ThreadPoolExecutor(2)` — bot stays responsive during FFmpeg encoding
- [x] 5-step progress bar for video (🎬) and audio (🎧) — `▰▰▱▱▱ 40%` format

### 🗃️ Caching & storage
- [x] Permanent `file_id` cache — instant re-send with no re-upload
- [x] Tafsir cache — SQLite + LRU, 30-day TTL
- [x] Per-verse MP3 disk cache, auto-purged when storage is low
- [x] Reciter-namespaced output paths `output/{reciter_code}/`
- [x] Hadith DB counts cached at module load — no repeated filesystem scans

### 🔒 Validation & safety
- [x] `start_aya > end_aya` and out-of-range ayas rejected with localized errors
- [x] 40-aya cap for ranges; full-sura requests always unrestricted
- [x] Rate limiting — 10 requests / user / hour

### 🎨 UI & UX
- [x] Arabic-Indic digits `١٢٣` in video frames only
- [x] Sura names always prefixed: `سورة الإخلاص` / `Surah Al-Ikhlas`
- [x] All UI strings in ar.json + en.json (no Arabic-Indic numerals in locale strings)
- [x] `/help` — detailed guide with channel link and feedback instructions
- [x] `/feedback` — forwarded to ADMIN_IDS with user info
- [x] Channel button label: قناة نور الحديث (both languages)
- [x] Donate page — Stars buttons + link to channel post for other methods (DONATE_URL)

### 🔧 Admin & ops
- [x] `/admin` — users (AR/EN split), queue, processing, cached files, rate-limited, top reciters, lifetime stats
- [x] `ADMIN_IDS`, `MAX_AYAS_PER_REQUEST`, `CHANNEL_ID`, `CHANNEL_URL`, `DONATE_URL` in `config.py`
- [x] Auto storage purge on low disk
- [x] Channel button hidden when `CHANNEL_URL` is empty
- [x] `bin/` directory auto-injected into PATH by `config.py`
