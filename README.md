<div align="center">

# 🌙 QuranBot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

[🇸🇦 العربية](README.ar.md) · 🌐 English

**[▶️ Open Bot](https://t.me/YOUR_BOT_USERNAME)** · **[📢 Channel](https://t.me/YOUR_CHANNEL_USERNAME)**

</div>

---

A comprehensive Quran toolset featuring a powerful Telegram Bot and standalone Desktop utilities (GUI/CLI) for high-quality verse video generation.

---

## ✨ Features

- 📖 **Mushaf API** — High-quality Quran pages (Hafs, Warsh, Tajweed) fetched remotely or served locally.
- 🎬 **Universal Video Engine** — Generate verse videos with synchronized audio, text strokes, and dynamic backgrounds.
- 🖥️ **Standalone Desktop GUI** — Native Python/Tkinter app for verse video production with settings persistence.
- ⌨️ **Powerful CLI** — Headless video generation for batch processing and terminal lovers.
- 🎨 **Modular Templates** — Choose between `default` (standard) or `enhanced` (with permanent sura name overlays and glyphs) rendering styles.
- 🎧 **25+ Reciters** — Full support for everyayah.com reciters with automatic caching.
- 🔍 **Smart Search** — Full-text search with bold highlighting and Arabic normalization.
- 📚 **12+ Tafsirs** — Comprehensive library including Al-Muyassar, Al-Jalalayn, and multi-language translations.
- 📄 **Export** — SRT and LRC with accurate per-verse timestamps.

---

## 🚀 Desktop Tools (New!)

### 🖥️ Video GUI
Generate professional Quran videos for social media without touching a line of code.
- **Persistent Settings**: Remembers your last used reciter, colors, and paths.
- **Native File Pickers**: Uses `Zenity` (Linux) or standard dialogs for a native feel.
- **Dynamic Range**: Automatically adjusts ayah range based on the selected sura.

```bash
python3 video_gui.py
```

### ⌨️ Video CLI
Perfect for automation and headless environments.
- **Full control**: Overrides for fonts, colors, templates, and backgrounds.
- **Fast**: Leverages the same high-performance FFmpeg pipeline as the bot.

```bash
# Example: Generate Sura Al-Kawthar with Alafasy voice and enhanced template
python3 video_cli.py -s 108 -v Alafasy_64kbps -t enhanced -o kawthar.mp4
```

---

## 🤖 Telegram Bot

The bot remains the centerpiece for user-facing interaction:
- **Mushaf Browsing**: `/page <n>`
- **Verse Search**: `/search <query>`
- **Daily Hadiths**: Automatic scheduling to a channel.
- **Hardware Acceleration**: Built-in support for NVENC (NVIDIA), VAAPI, and VideoToolbox.

---

## 🛠️ Setup

**Requirements:** Python 3.10+, FFmpeg

1. **Clone & Install**:
   ```bash
   git clone https://github.com/yourname/quranbot
   cd quranbot
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Set your BOT_TOKEN and other credentials
   ```

3. **Run**:
   - For the Telegram Bot: `python3 bot.py`
   - For the Desktop GUI: `python3 video_gui.py`

---

## ☕ Support / Donate

If you find this project useful, you can support its development:

| | |
|---|---|
| 💳 **PayPal** | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔸 **Binance** | `1011264323` |
| 🟡 **Bybit** | `467077834` |
| 🟢 **TRC20** | `TMW5uSDN6sMUBNirMoqY1icpsfa7GhPZfK` |
| 🟢 **BEP20/ERC20** | `0x7a8887c2ac3e596f6170c9e28b44e6b6d025c854` |
| 🔵 **LTC** | `LVswXiD6Vd2dejXvGbZLa1R8jkvg748F4q` |
| 🔵 **TON** | `UQAllRezWgHi3LPrSwyvAb4zazIph6j6goU7lMaqcFWFBxVH` |
| 🟠 **BTC** | `1rSX6BDN1nqDMyBHqceySkZSs6PHUP23m` |
| 🟣 **SOL** | `d8RonhC8oEHssrQjN1Y4UWHnd6MMP33XGCKtfNL4j59` |
| ⭐ **Telegram Stars** | Directly via the bot |

---

## 📖 Data Sources

| | Source | License |
|---|---|---|
| Quran text + metadata | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| Audio files | [EveryAyah.com](https://everyayah.com) | Free, non-commercial |
| Tafsir API | [AlQuran.cloud](https://alquran.cloud/api) | Free API |
| Uthmanic font | [KFGQPC](https://fonts.qurancomplex.gov.sa) | Free, non-commercial |
| Hadith databases | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
