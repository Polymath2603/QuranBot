<div align="center">

# 🌙 QuranBot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

[🇸🇦 العربية](README.md) · 🌐 English

**[▶️ Open Bot](https://t.me/YOUR_BOT_USERNAME)** · **[📢 Channel](https://t.me/YOUR_CHANNEL_USERNAME)**

</div>

---

A Telegram bot for the Quran. Search, listen, read tafsir, and watch verse videos with audio.

---

## Features

- 📖 **Mushaf** — Display Quran pages from three sources: Hafs, Warsh, Color Tajweed. Caches file\_id after first send.
- 🖼️ **Verse Images** — High-quality images (1080px) with 3 fonts and 3 themes. Auto or fixed dimensions.
- 🎬 **Video** — Verse videos with synchronized audio, portrait or landscape.
- 🎧 **18 Reciters** — Alafasy, As-Sudais, Abdul Basit, Al-Husary, and more.
- 🔍 **Smart Search** — Full-text search with contextual snippets and comprehensive Arabic normalization.
- 📚 **Two Tafsirs** — Al-Muyassar and Al-Jalalayn, from local file then API fallback.
- 📄 **Export** — SRT and LRC with accurate per-verse timestamps.
- 📿 **Hadiths** — `/hadith` sends a random hadith. Auto-posts to channel daily.
- ⚡ **Instant resend** — file_id cached for every previously sent file.
- 🚀 **Hardware Acceleration** — Support for NVENC, VAAPI, and VideoToolbox for ultra-fast video production.
- 🌐 **Arabic & English** — Full bilingual interface.

---

## Usage

Send a sura name, aya number, page number, or Arabic text to search:

| Input | Example |
|---|---|
| Sura + aya | `Baqarah 255` · `البقرة 255` |
| Range | `Fatiha 1-7` · `1:1-7` |
| Sura name | `Kahf` · `الكهف` |
| Page | `page 5` · `صفحة 5` |
| Search | `whatever they hide` |

The aya appears with action buttons:

| Button | |
|---|---|
| 📖 Text | Display text or download as SRT / LRC |
| 📚 Tafsir | Al-Muyassar or Al-Jalalayn |
| 🖼️ Image | Verse image (shown when verse fits screen) |
| 🎬 Video | Video with synchronized audio |
| 📄 Page N | Mushaf page |
| 🎧 Audio | MP3 |

---

## Settings

```
⚙️ Settings
├─ 🌐 Language
├─ 🎙️ Reciter
├─ 🖼️🎬 Media (Image / Video)
└─ ▪️ Other
    ├─ 📚 Tafsir
    ├─ 📖 Source
    └─ 📄 Format
```

---

## Setup

**Requirements:** Python 3.10+, FFmpeg

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set BOT_TOKEN at minimum
python bot.py
```

**Static FFmpeg binaries** (optional — if FFmpeg isn't in PATH):

```bash
mkdir -p bin
wget -q https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz -O /tmp/ff.tar.xz
tar -xf /tmp/ff.tar.xz -C /tmp
cp /tmp/ffmpeg-*/bin/{ffmpeg,ffprobe} bin/
chmod +x bin/ffmpeg bin/ffprobe
```

### Mushaf page images (optional)

Place PNG files in `data/images/{source}/`:

```
data/images/hafs/1.png  …  604.png
data/images/warsh/1.png  …
data/images/tajweed/1.png  …
```

The bot caches Telegram file\_ids in `ids.json` automatically after the first send.

### Local tafsir files (optional)

```
data/tafsir/muyassar.json   {"1:1": "tafsir text", ...}
data/tafsir/jalalayn.json
```
If they don't exist, the bot falls back to the alquran.cloud API.

### Quick Export (CLI)

You can now export verses as audio, image, or video directly from the command line without running the Telegram bot:

```bash
# Export video (aya range, with theme and font override)
python3 cli.py 2:255 -v --theme parchment --font uthmani --output out.mp4

# Export image (Al-Fatihah full)
python3 cli.py 1:1-7 -i --theme dark --output fatiha.png

# Export audio (Alafasy reciter)
python3 cli.py 18:1-10 -a --reciter Alafasy_64kbps
```

---

## Data Sources

| | Source | License |
|---|---|---|
| Quran text + metadata | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| Audio files | [EveryAyah.com](https://everyayah.com) | Free, non-commercial |
| Tafsir API | [AlQuran.cloud](https://alquran.cloud/api) | Free API |
| Uthmanic font | [KFGQPC](https://fonts.qurancomplex.gov.sa) | Free, non-commercial |
| Hadith databases | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
