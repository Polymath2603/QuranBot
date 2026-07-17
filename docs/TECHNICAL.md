# 🔧 Technical Documentation

→ [README](README.en.md) · [Changelog](CHANGELOG.md)

---

## Project structure

```
QuranBot/
├── bot.py              # All Telegram handlers, callback router & monkey-patching
├── config.py           # Every constant in one place — edit here, not in modules
├── core/
│   ├── audio.py        # gen_mp3(): download per-verse MP3s → FFmpeg concat + strip
│   ├── video.py        # gen_video(): Dynamic template loading → FFmpeg graph (compositing)
│   ├── video_templates/ # Modular rendering styles (default, enhanced)
│   │   ├── default.py   # Standard verse rendering
│   │   └── enhanced.py  # Sura name glyphs & permanent overlays
│   ├── image.py        # gen_verse_image(): portrait (default) PNG, font/theme/resolution
│   ├── mushaf.py       # send_mushaf_page(): remote API or local PNG → file_id cache
│   ├── verses.py       # build_verse_keyboard(), send helpers, text formatting
│   ├── subtitles.py    # SRT / LRC export with real ffprobe timestamps
│   ├── nlu.py          # Natural language parser — suras, ranges, pages, search
│   ├── search.py       # Full-text search with Arabic normalization
│   ├── tafsir.py       # Local file → DB cache → AlQuran.cloud API
│   ├── data.py         # load_quran_data/text(), basmala helpers, index lookups
│   ├── downloader.py   # Per-verse MP3 downloader with retry
│   ├── database.py     # SQLAlchemy models: User, TafsirCache, BotStats, QueueItem
│   ├── queue.py        # Serial request queue: SQLite-backed, async cancelling `/cancelall`
│   ├── hadith.py       # Random hadith from local SQLite DBs (uses config.HADITH_FILES)
│   ├── lang.py         # t(key, lang, **kwargs) — loads ar.json + en.json
│   └── utils.py        # Storage purge, rate limiter, file_id cache, log_error
├── locales/
│   ├── ar.json         # Arabic UI strings
│   └── en.json         # English UI strings
├── data/
│   ├── quran-data.json          # Sura metadata + page map (Tanzil.net)
│   ├── quran-uthmani.txt        # Uthmani text, one verse per line
│   ├── quran-simple.txt         # Simplified text for display/search/subtitles
│   ├── KFGQPC *.ttf             # Uthmanic font
│   ├── Amiri-Regular.ttf        # (optional) Amiri font
│   ├── NotoNaskhArabic-Regular.ttf  # (optional) Noto Naskh font
│   ├── audio/                   # Per-verse MP3 cache
│   ├── hadith/                  # SQLite hadith databases (see config.HADITH_FILES)
│   ├── images/                  # Mushaf page images (optional)
│   │   ├── hafs/                # 1.png … 604.png  +  ids.json (auto-created)
│   │   ├── warsh/
│   │   └── tajweed/
│   └── tafsir/                  # Local tafsir JSON (optional)
│       ├── muyassar.json        # {"1:1": "text", ...}
│       └── jalalayn.json
├── output/
│   ├── {reciter_code}/          # Generated MP3s and MP4s
│   └── file_ids.json            # Permanent Telegram file_id cache (audio/video/image)
├── bin/                         # (optional) Local ffmpeg/ffprobe static binaries
├── .env
├── .env.example
├── .video_settings.json # (ignored) Persisted GUI settings
├── video_gui.py         # Standalone Desktop app (Tkinter)
├── video_cli.py         # Headless generation tool (argparse)
├── README.md
├── README.ar.md
├── requirements.txt
└── TECHNICAL.md
```

---

## Architecture

### Aya keyboard flow

```
User sends text
    → NLU (nlu.py) → type: aya / range / surah / page / search
    → reply with title + build_verse_keyboard()

Keyboard buttons:
    text_   → send_text_single / send_text_range   (edit message)
    tafsir_ → tafsir_handler                        (edit message)
    img_    → image_handler (queue if not cached)   (new message)
    vid_    → video_generate_handler (queue)         (new message)
    mushaf_ → send_mushaf_page (local PNG / cache)  (edit message)
    play_   → play_audio_handler (queue)             (new message)
```

Image button is hidden when the verse text exceeds `CHAR_LIMIT` characters.

### Queue & Cancelling

`core/queue.py` runs a **single consumer task** — one job at a time across audio, video, and image. Jobs are stored in SQLite so they survive restarts. Status message is edited with progress (`▰▱▱▱▱ 20%`), then deleted on completion. Users can manually click `❌ Cancel` while the item is pending to strip it from the queue.

Background tasks are wrapped in `_safe_process_queue_item()` which captures exceptions and marks the database record as `error`, updating the status message to `❌` for visibility. Admin users can clear queues with `/cancelall`.

### File-ID key format

```python
# Audio
"audio:{reciter}:{sura}:{start}:{end}"

# Video
"video:{reciter}:{sura}:{start}:{end}:{font_idx}:{theme_idx}:{ratio_idx}"

# Image
"image:{sura}:{start}:{end}:{font_idx}:{theme_idx}:{resolution_idx}"
```

Indices are positions in `config._FONT_LIST`, `_IMG_THEME`, etc. — stable across restarts.

### Search Highlighting

Full-text search results in `core/search.py` use a two-step highlighting process:
1. **Normalization**: Both the search query and the Quranic text are normalized (removing diacritics, dagger alifs, etc.) to find character-level matches.
2. **Word-Level bolding**: The match offsets are mapped back to word indices in the original (non-normalized) simplified text. All words covering the match range are wrapped in `<b>` tags.
3. **Display**: Handlers in `bot.py` must use `parse_mode="HTML"` for these snippets to render correctly in Telegram.

### Mushaf pages

```
1. Check ids.json for cached file_id
2. If found → InputMediaPhoto(file_id) → edit_message_media
3. If not → open data/images/{source}/{page}.png
4. Send photo → cache file_id in ids.json
5. If PNG missing → show text notice
```

No image generation for mushaf pages. Not affected by text format settings.

### Image generation

`core/image.py` — `render_verse_png()`:
- Width fixed at 1080px (or fixed size for portrait/landscape)
- Height auto-computed from rendered line count
- DP text-balancing wrapper (min 4 words/line)
- Font-conditional: Configured via `FONT_SETTINGS` in `config.py` (Numerals, Cleaning, Brackets per font).

### Video pipeline

`gen_video()` now uses a **Modular Template System**:

1. **Preprocessing**:
   - Audio is fetched and concatenated using `gen_mp3()`.
   - Per-verse alignments are loaded from `core/subtitles.py`.
2. **Template Loading**:
   - `core/video.py` dynamically imports a template module (e.g., `core/video_templates/enhanced.py`).
   - The template provides a `render_frame()` function and optional `get_static_overlay()`.
3. **Rendering & Compositing**:
   - Verses are rendered into temporary PNG sequences via the template.
   - If a static overlay (e.g., Sura name glyphs) is provided, it is pre-rendered once.
   - FFmpeg Filter Graph:
     - `[bg0][static]overlay[bg]` → Injects the permanent non-fading layer.
     - Dynamic text layers are composited on top using the video background (Image, Video, or Solid Color).
4. **Encoding**:
   - Leverages Hardware Acceleration (`nvenc`, `vaapi`, `videotoolbox`) automatically.
   - Outputs to `DATA_DIR/videos` aligned with the bot's storage.

### Audio pipeline

```
gen_mp3():
  Phase 0: Download missing per-verse MP3s from everyayah.com
  Phase 1: FFmpeg concat demuxer → joined MP3, strip all metadata
  Phase 2: FFmpeg copy-only pass → strip residual ID3/album-art tags
```

### Configuration (config.py)

All lists that may need editing are in `config.py`:

| Constant | Purpose |
|---|---|
| `VOICES` | Reciters: code, Arabic name, English name |
| `TAFSIR_SOURCES` | Sources: key, names, API edition string |
| `PAGE_SOURCES` | Mushaf image sources: key, display names |
| `HADITH_FILES` | Hadith SQLite filenames and book names |
| `FONT_PATHS` | Font key → .ttf file path |
| `IMAGE_BACKGROUNDS` / `IMAGE_TEXT_COLORS` | Theme RGBA tuples |
| `VIDEO_SIZES` | Portrait/landscape pixel dimensions |
| `IMAGE_RESOLUTIONS` | Auto/portrait/landscape dimensions |
| `img_fid_key()` / `vid_fid_key()` / `aud_fid_key()` | File-ID key builders |

---

## Data sources & licenses

| File | Source | License |
|---|---|---|
| `quran-data.json` | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| `quran-uthmani.txt` | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| `quran-simple.txt` | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| `KFGQPC *.ttf` | [King Fahd Quran Printing Complex](https://fonts.qurancomplex.gov.sa) | Free, non-commercial |
| `data/hadith/*.sqlite` | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
| Audio files | [EveryAyah.com](https://everyayah.com) | Free, non-commercial |
| Tafsir API | [AlQuran.cloud](https://alquran.cloud/api) | Free |

---

## Adding optional fonts

```bash
# Amiri
wget https://github.com/alif-type/amiri/releases/latest/download/amiri.zip -O /tmp/amiri.zip
unzip -j /tmp/amiri.zip "*/Amiri-Regular.ttf" -d data/

# Noto Naskh Arabic
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf \
     -O data/NotoNaskhArabic-Regular.ttf
```
