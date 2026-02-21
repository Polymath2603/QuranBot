# QBot: Quran Telegram Bot

A Telegram bot for accessing the Quran — browse by verse, range, or page; listen to recitations; watch verse videos; and read Tafsir.

## Features

- **Natural Language Search**: Accepts queries in Arabic and English (e.g., `Baqarah 255`, `صفحة 10`, `1:1-5`).
- **Audio Playback**: Stream or download recitations from multiple reciters with embedded metadata.
- **Video Generation** _(Beta)_: Create MP4 videos of verses with timed subtitles, configurable backgrounds and text styling.
- **Tafsir**: Access verse interpretations fetched from AlQuran.cloud.
- **Page Navigation**: Browse all 604 pages of the Quran with ◀️/▶️ buttons.
- **Text Export**: Export verses as TXT, SRT, or LRC files.
- **Localization**: Arabic (default) and English interfaces.

## Quick Start

```bash
git clone https://github.com/yourusername/qbot
cd qbot
pip install -r requirements.txt
cp .env.example .env   # Add your TELEGRAM_BOT_TOKEN
python bot.py
```

## Usage Examples

- **Single verse**: `2:255` or `Baqarah 255`
- **Range**: `1:1-7` or `Al-Fatihah 1 to 7`
- **Full Surah**: `Kahf` or `سورة الكهف`
- **By page**: `page 1` or `صفحة 200`
- **Search**: Any text is auto-detected as search

## Data Sources

| File                | Source                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| `quran-data.json`   | [tanzil.net](https://tanzil.net) — downloaded as `quran-data.js`, reformatted to JSON without changes |
| `quran-uthmani.txt` | [tanzil.net](https://tanzil.net) — used as-is                                                         |
| `UthmanTN_v2-0.ttf` | Uthmani font for video text rendering                                                                 |

## APIs

| API                                                  | Purpose                                    |
| ---------------------------------------------------- | ------------------------------------------ |
| [everyayah.com](https://everyayah.com)               | Audio recitations (per-verse MP3 files)    |
| [api.alquran.cloud/v1](https://api.alquran.cloud/v1) | Tafsir (Al-Muyassar, Jalalayn, and others) |

## Project Structure

```
QBot/
├── bot.py          # Bot logic and Telegram handlers
├── nlu.py          # Query parsing (verse, range, page, search)
├── audio.py        # FFmpeg audio concatenation and metadata
├── video.py        # MP4 video generation (delegates rendering to srt2mp4)
├── search.py       # Arabic-normalizing full-text search
├── tafsir.py       # Tafsir fetching with LRU + SQLite cache
├── data.py         # Quran data and text loading
├── downloader.py   # Per-verse MP3 downloader with retry logic
├── database.py     # SQLite models: User, TafsirCache; session helpers
├── lang.py         # Localization (ar/en)
├── config.py       # Paths, API URLs, reciter list
├── utils.py        # Shared helpers: safe_filename, storage purge, rate limiter
├── locales/        # ar.json, en.json
├── data/
│   ├── quran-data.json
│   ├── quran-uthmani.txt
│   ├── UthmanTN_v2-0.ttf
│   └── audio/      # Cached per-verse MP3s (auto-purged on low disk)
├── output/         # Generated MP3s and MP4s (auto-purged on low disk)
└── ../srt2mp4/     # Video rendering engine (shared with standalone CLI tool)
    ├── genMP4.py
    └── backgrounds/ # Optional background images/videos for video generation
```

## Support

### 🌟 Telegram Stars

Donate directly via the `/start` menu inside the bot.

### 💰 Crypto

- **BTC**: `15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp`
- **ETH / BNB**: `0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf`
- **Solana**: `EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn`

### 📈 Exchanges

- **Binance**: [app.binance.com/uni-qr/Uzof5Lrq](https://app.binance.com/uni-qr/Uzof5Lrq) · ID `1011264323`
- **Bybit**: [i.bybit.com/W2abUWF](https://i.bybit.com/W2abUWF) · ID `467077834`

### 💳 PayPal

[paypal.com/ncp/payment/W78F6W4TXZ4CS](https://www.paypal.com/ncp/payment/W78F6W4TXZ4CS)

---

Jazakallahu Khairan 🤲
