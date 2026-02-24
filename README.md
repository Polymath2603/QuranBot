# 🌙 QBot — بوت القرآن الكريم

A Telegram bot for listening to, reading, and studying the Holy Quran.  
اللهم اجعله خالصاً لوجهك الكريم 🤲

---

## ✨ What Can It Do?

| Feature | Description |
|---|---|
| 🎧 **Audio** | Listen to any verse or surah with your chosen reciter |
| 🎬 **Video** | Receive a beautiful synced recitation video |
| 📖 **Text** | Read verses inline, or export as TXT / SRT / LRC |
| 📚 **Tafsir** | Read Al-Muyassar or Jalalayn explanations |
| 🔍 **Search** | Find verses by text — tap any result to open it |
| 📄 **Page view** | Browse all 604 pages of the Mushaf |

---

## 💬 How to Use

Just **send a message** — the bot understands Arabic and English naturally:

| What you type | What you get |
|---|---|
| `2:255` | Al-Baqarah verse 255 (Ayat Al-Kursi) |
| `البقرة ٢٥٥` | Same, Arabic input |
| `Baqarah 255` | Same, English input |
| `1:1-7` | Al-Fatihah verses 1–7 |
| `الكهف` | Full Surah Al-Kahf |
| `Kahf` | Same in English |
| `page 5` / `صفحة ٥` | Page 5 of the Mushaf |
| Any Arabic phrase | Full-text search across the Quran |

After the bot responds, tap the buttons:

- **📖 تفسير** — Tafsir (explanation)
- **📖 نص** — Text / file export
- **🎧 صوت** — Audio recitation
- **🎬 فيديو** — Synced verse video

---

## ⚙️ Settings

Tap **⚙️ الإعدادات** from the welcome screen:

| Setting | What it does |
|---|---|
| 🌐 Language | Switch between Arabic and English interface |
| 📄 Format | Choose how text is delivered: message / TXT / SRT / LRC |
| 📖 Tafsir | Toggle between Al-Muyassar and Jalalayn |
| 🎬 Video Settings | Text colour, border, landscape / portrait |
| 🎙️ Reciter | Choose from 18 reciters |

### 🎬 Video Settings

| Setting | Options | Default |
|---|---|---|
| Text colour | White / Black | White |
| Border/shadow | On / Off | On |
| Ratio | Landscape 16:9 / Portrait 9:16 | Landscape |

> The background setting is temporarily hidden while being reworked — default is black.

---

## 🚀 Setup (Self-Hosting)

### Requirements
- Python 3.11+
- FFmpeg in PATH (`ffmpeg` must work in your terminal)
- A bot token from [@BotFather](https://t.me/BotFather)

### Install & Run
```bash
git clone https://github.com/yourusername/qbot
cd qbot
pip install -r requirements.txt
cp .env.example .env        # then set TELEGRAM_BOT_TOKEN inside
python bot.py
```

### Optional: Add Video Backgrounds
Place `.mp4`, `.jpg`, or `.png` files in `data/backgrounds/`.  
These are used in the Random background mode (coming soon to settings).

### Admin Panel
Add your Telegram user ID to `ADMIN_IDS` in `config.py`, then use `/admin` to see:
- Total users, queue depth, free disk space, cached files, top reciters

---

## 💝 Support

Running this bot takes resources. If you find it useful:

- **Inside the bot** → `/start` → 💝 Donate → pay with Telegram Stars
- **PayPal**: [paypal.com/ncp/payment/W78F6W4TXZ4CS](https://www.paypal.com/ncp/payment/W78F6W4TXZ4CS)
- **Binance** ID: `1011264323`  ·  **Bybit** ID: `467077834`
- **BTC**: `15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp`
- **ETH/BNB**: `0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf`
- **SOL**: `EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn`

جزاكم الله خيراً 🤲

---

## 🙏 Attribution

- Quran text & metadata — [tanzil.net](https://tanzil.net)
- Audio recitations — [everyayah.com](https://everyayah.com)
- Tafsir API — [alquran.cloud](https://alquran.cloud)
- Uthmanic font — KFGQPC (King Fahd Quran Printing Complex)

---

📋 [Changelog](CHANGELOG.md) · ✅ [Todo](TODO.md) · 🔧 [Technical Docs](TECHNICAL.md)
