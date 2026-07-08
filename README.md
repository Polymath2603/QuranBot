# QuranBot

[![GitHub Release](https://img.shields.io/github/v/release/user/quranbot)](https://github.com/user/quranbot/releases)
[![GitHub Stars](https://img.shields.io/github/stars/user/quranbot?style=social)](https://github.com/user/quranbot/stargazers)
[![GitHub Downloads](https://img.shields.io/github/downloads/user/quranbot/total)](https://github.com/user/quranbot/releases)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)

[العربية](README.ar.md) | English

**Status:** Active development 🟢

Quran toolkit with Telegram bot and desktop video generation tools.

## Features

- **Mushaf API** — Quran pages (Hafs, Warsh, Tajweed)
- **Video Engine** — Generate verse videos with synchronized audio and text
- **Desktop GUI** — Tkinter app for video production with settings persistence
- **CLI** — Headless video generation for batch processing
- **25+ Reciters** — Full support for everyayah.com reciters
- **Search** — Full-text search with Arabic normalization
- **12+ Tafsirs** — Including Al-Muyassar, Al-Jalalayn, and translations
- **Export** — SRT and LRC with per-verse timestamps

## Desktop Tools

### Video GUI

```bash
python3 video_gui.py
```

- Persistent settings (reciter, colors, paths)
- Native file pickers (Zenity on Linux)
- Dynamic ayah range based on selected sura

### Video CLI

```bash
python3 video_cli.py -s 108 -v Alafasy_64kbps -t enhanced -o kawthar.mp4
```

## Telegram Bot

- `/page <n>` — Browse Mushaf
- `/search <query>` — Verse search
- `/hadith` — Random hadith
- Hardware acceleration: NVENC, VAAPI, VideoToolbox

## Setup

**Requirements:** Python 3.10+, FFmpeg

```bash
git clone https://github.com/user/quranbot
cd quranbot
pip install -r requirements.txt

cp .env.example .env
# Set your BOT_TOKEN

# Run the bot
python3 bot.py

# Or the desktop GUI
python3 video_gui.py
```

## Support

| | |
|---|---|
| PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| Binance | `1011264323` |
| Bybit | `467077834` |
| TRC20 | `TMW5uSDN6sMUBNirMoqY1icpsfa7GhPZfK` |
| BEP20/ERC20 | `0x7a8887c2ac3e596f6170c9e28b44e6b6d025c854` |
| LTC | `LVswXiD6Vd2dejXvGbZLa1R8jkvg748F4q` |
| TON | `UQAllRezWgHi3LPrSwyvAb4zazIph6j6goU7lMaqcFWFBxVH` |
| BTC | `1rSX6BDN1nqDMyBHqceySkZSs6PHUP23m` |
| SOL | `d8RonhC8oEHssrQjN1Y4UWHnd6MMP33XGCKtfNL4j59` |

## Data Sources

| Source | License |
|--------|---------|
| [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| [EveryAyah.com](https://everyayah.com) | Free, non-commercial |
| [AlQuran.cloud](https://alquran.cloud/api) | Free API |
| [KFGQPC](https://fonts.qurancomplex.gov.sa) | Free, non-commercial |
| [Hadith DB](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
