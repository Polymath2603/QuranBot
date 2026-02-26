<div align="center">

# 🌙 Quran Bot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-229ED9)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

🇸🇦 [العربية](README.md) · 🌐 English

</div>

---

A Telegram bot for the Holy Quran. Search by verse, recite with 18 reciters, read tafsir, export subtitles, and generate verse videos — all from a single chat.

---

## Features

- 🎬 **Video generation** — verse-by-verse video with synced audio, landscape or portrait. The only Quran bot on Telegram that does this.
- 🎧 **18 reciters** — Alafasy, Sudais, Abdul Basit, Husary, and more.
- 🔍 **Smart search** — searches the full Quran text with Arabic normalization (alif variants, tashkeel, hamza). Works even with spelling variations.
- 📚 **Tafsir** — Al-Muyassar and Al-Jalalayn, paginated.
- 📄 **Text export** — TXT, SRT, and LRC files with accurate timestamps.
- ⚡ **Instant delivery** — generated files are cached by Telegram ID, so repeat requests are served immediately.
- 🌐 **Arabic and English** UI.

---

## Usage

Send anything — a surah name, an aya reference, a page number, or Arabic text to search:

| Input | Example |
|---|---|
| Surah + aya | `البقرة ٢٥٥` · `Baqarah 255` |
| Range | `الفاتحة ١ إلى ٧` · `1:1-7` |
| Surah name | `الكهف` · `Kahf` |
| Page | `صفحة ٥` · `page 5` |
| Search | `وما توفيقي إلا بالله` |

The verse appears with action buttons:

| Button | |
|---|---|
| 📚 تفسير | Tafsir |
| 📄 نص | Text or file (TXT / SRT / LRC) |
| 🎧 صوت | Audio |
| 🎬 فيديو | Video |
| 📄 Page N | That page in the Mushaf |

---

## Settings

| | Options |
|---|---|
| Language | العربية / English |
| Text format | Inline message / TXT / SRT / LRC |
| Tafsir | Al-Muyassar / Al-Jalalayn |
| Video ratio | Landscape 16:9 / Portrait 9:16 |
| Reciter | 18 options |

---

## Self-hosting

**Requirements:** Python 3.10+, FFmpeg

```bash
git clone https://github.com/yourname/quranbot
cd quranbot
pip install -r requirements.txt
```

Add a `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

```bash
python bot.py
```

**Key settings in `config.py`:**

```python
ADMIN_IDS            = [123456789]
MAX_AYAS_PER_REQUEST = 50          # cap for ranges; full suras are unlimited
VIDEO_DEFAULT_RATIO  = "landscape" # or "portrait"
DEFAULT_VOICE        = "Alafasy_64kbps"
```

---

## Support

| | |
|---|---|
| 💳 PayPal | `paypal.com/ncp/payment/W78F6W4TXZ4CS` |
| 🔶 Binance ID | `1011264323` |
| 🟡 Bybit ID | `467077834` |
| ₿ BTC | `15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp` |
| 🔷 ETH / BNB | `0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf` |
| 🟣 SOL | `EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn` |

---

## Credits

Quran text and page data: [Tanzil.net](https://tanzil.net)
Audio files: [EveryAyah.com](https://everyayah.com)
Tafsir API: [AlQuran.cloud](https://alquran.cloud)
Uthmanic font: [KFGQPC](https://fonts.qurancomplex.gov.sa) — King Fahd Quran Printing Complex
