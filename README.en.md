<div align="center">

# 🌙 Quran Bot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 [العربية](README.md) · 🌐 English

</div>

---

A Telegram bot for the Holy Quran. Search, listen, read tafsir, export subtitles, and generate verse videos — all from a single chat.

---

## Features

- 🎬 **Video generation** — verse-by-verse video with synced audio, landscape or portrait. The only Quran bot on Telegram with this feature.
- 🎧 **18 reciters** — Alafasy, Sudais, Abdul Basit, Husary, and more.
- 🔍 **Smart Arabic search** — full Quran text search with normalization (alif variants, tashkeel, hamza, superscript alif).
- 📚 **Tafsir** — Al-Muyassar and Al-Jalalayn, paginated.
- 📄 **Subtitle export** — SRT and LRC with accurate per-verse timestamps from ffprobe.
- 📿 **Hadith** — `/hadith` sends a random Arabic hadith from local SQLite databases (9 books, ~35k hadiths). `/chadith` (admin) pushes one to the channel.
- ⚡ **Instant delivery** — generated files are cached; repeat requests skip the queue entirely.
- 🌐 **Arabic and English** UI.

---

## Usage

Send a surah name, aya reference, page number, or Arabic text to search:

| Input | Example |
|---|---|
| Surah + aya | `Baqarah 255` · `البقرة 255` |
| Range | `Fatihah 1-7` · `1:1-7` |
| Surah name | `Kahf` · `الكهف` |
| Page | `page 5` · `صفحة 5` |
| Search | `وما توفيقي إلا بالله` |

The verse appears with action buttons:

| Button | |
|---|---|
| 📚 Tafsir | Al-Muyassar or Al-Jalalayn |
| 📖 Text | Inline or download as SRT / LRC |
| 🎧 Audio | MP3 with your chosen reciter |
| 🎬 Video | Generated video with synced audio |
| 📄 Page N | Jump to that Mushaf page |

---

## Settings

| | Options |
|---|---|
| Language | العربية / English |
| Text format | Inline message / SRT / LRC |
| Tafsir | Al-Muyassar / Al-Jalalayn |
| Video ratio | Landscape 16:9 / Portrait 9:16 |
| Reciter | 18 options |

---

## Self-hosting

**Requirements:** Python 3.10+, FFmpeg (place binaries in `bin/` or install system-wide)

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
```

Create `.env`:

```env
BOT_TOKEN=your_token_here
CHANNEL_URL=https://t.me/yourchannel
CHANNEL_ID=@yourchannel
ADMIN_IDS=123456789
DONATE_URL=https://t.me/yourchannel/123
```

```bash
python bot.py
```

**Key settings in `config.py`:**

```python
ADMIN_IDS            = [123456789]
CHANNEL_URL          = "https://t.me/yourchannel"   # inline button
CHANNEL_ID           = "@yourchannel"               # channel for /chadith
MAX_AYAS_PER_REQUEST = 40
VIDEO_DEFAULT_RATIO  = "portrait"
DEFAULT_VOICE        = "Alafasy_64kbps"
```

---

## Support

| | |
|---|---|
| 💳 PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔸 Binance ID | `1011264323` |
| 🟡 Bybit ID | `467077834` |
| 🟢 TRC20 | `TMW5uSDN6sMUBNirMoqY1icpsfa7GhPZfK` |
| 🟢 BEP20/ERC20 | `0x7a8887c2ac3e596f6170c9e28b44e6b6d025c854` |
| 🔵 LTC | `LVswXiD6Vd2dejXvGbZLa1R8jkvg748F4q` |
| 🔵 TON | `UQAllRezWgHi3LPrSwyvAb4zazIph6j6goU7lMaqcFWFBxVH` |
| 🟠 BTC | `1rSX6BDN1nqDMyBHqceySkZSs6PHUP23m` |
| 🟣 SOL | `d8RonhC8oEHssrQjN1Y4UWHnd6MMP33XGCKtfNL4j59` |
| ⭐ Telegram Stars | Via the bot directly |

---

## Credits & data sources

| | Source | License |
|---|---|---|
| Quran text + metadata | [Tanzil.net](https://tanzil.net) | CC BY 3.0 |
| Audio files | [EveryAyah.com](https://everyayah.com) | Free, non-commercial |
| Tafsir API | [AlQuran.cloud](https://alquran.cloud/api) | Free API |
| Uthmanic font | [KFGQPC](https://fonts.qurancomplex.gov.sa) | Free, non-commercial |
| Hadith databases | [IsmailHosenIsmailJames](https://github.com/IsmailHosenIsmailJames/compressed_hadith_sqlite) | MIT |
