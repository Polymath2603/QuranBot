# QBot - Quran Bot

A comprehensive Telegram bot for accessing the Quran with advanced features including Natural Language Understanding, multi-language support, and audio playback with professional metadata.

## Key Features

### 🧠 **Natural Language Understanding (NLU)**

- Understands natural queries in both Arabic and English
- Examples:
  - `سورة البقرة` or `Surah Baqarah`
  - `سورة الحج آية 2` or `Surah Hajj verse 2`
  - `سورة البقرة الاية من 1 حتى 18` (Range within a Surah)
  - `من سورة الفاتحة 1 الى البقرة 4` (Cross-Surah range)
- Fuzzy matching for Surah names
- Arabic character normalization (handles different forms of Alif, Hamza, etc.)

### 🌍 **Localization**

- Default language: Arabic
- Supports English and Arabic interfaces
- User preferences stored in database
- Easy language switching via settings

### 💾 **Database Integration**

- SQLite database for user preferences
- Stores: language, reciter choice, and custom settings
- Automatic user registration

### 🎵 **Audio Features**

- High-quality MP3 audio from EveryAyah.com
- Multiple reciters available
- Audio metadata includes:
  - **Title**: Surah name and verse range (localized)
  - **Artist**: Reciter name
  - No album art (clean audio files)
- Status messages auto-delete after audio is sent

### 📖 **Text Display**

- Beautiful formatting with Arabic ornamental brackets: `﴿ ... ﴾`
- Format: `📖 Surah Name (Verse Range)`
- Verse numbers included in parentheses

### 📚 **Tafsir Integration**

- Access Quranic interpretation (Tafsir Al-Muyassar)
- Available via button on verse responses
- Fetched from AlQuran.cloud API

### 🔍 **Advanced Search**

- Arabic text normalization for better results
- Handles diacritics and character variations
- Returns top 5 results with Surah, verse, and page numbers

### 💝 **Donation Support**

- **Telegram Stars**: Primary donation method (50, 100, 500 Stars)
- Traditional methods: PayPal, Crypto (BTC, ETH, BNB, SOL)
- Exchange platforms: Binance, Bybit

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/qbot
cd qbot

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your TELEGRAM_BOT_TOKEN

# Run the bot
python bot.py
```

## Usage Examples

### Natural Language Queries

- **Single Verse**: `2:255` or `Baqarah 255` → Returns Ayatul Kursi
- **Surah**: `Kahf` or `سورة الكهف` → Shows Surah Al-Kahf options
- **Range**: `2:1-5` or `Baqarah 1 to 5` → First 5 verses of Baqarah
- **Search**: `الرحمن` → Searches for verses containing "الرحمن"

### Bot Commands

- `/start` - Initialize bot and show main menu
- Use inline buttons for navigation
- Settings menu for changing reciter and language

## Project Structure

```
QBot/
├── bot.py              # Main bot logic
├── nlu.py              # Natural Language Understanding
├── database.py         # SQLite database models
├── audio.py            # Audio generation with metadata
├── search.py           # Search with Arabic normalization
├── tafsir.py           # Tafsir integration
├── data.py             # Quran data loading
├── downloader.py       # Audio file downloader
├── lang.py             # Localization system
├── config.py           # Configuration
├── locales/            # Language files (en.json, ar.json)
├── data/               # Quran data and audio files
└── output/             # Generated audio files
```

## APIs Used

- **Audio**: [EveryAyah.com](https://everyayah.com) - Quranic recitations
- **Tafsir**: [AlQuran.cloud](https://alquran.cloud) - Tafsir and translations
- Not affiliated. Educational use only.

## Technical Details

### Download Logic

1. **Audio Source**: EveryAyah.com provides individual verse MP3 files
2. **Downloader**: `downloader.py` fetches files for requested verses
3. **Audio Generation**: `audio.py` uses FFmpeg to:
   - Concatenate individual verse files
   - Set metadata (Title, Artist)
   - Remove album art (audio-only output)
   - Output final MP3 file

### Dependencies

- `python-telegram-bot` (>=21.3) - Telegram Bot API with Stars support
- `SQLAlchemy` - Database ORM
- `rapidfuzz` - Fuzzy string matching for NLU
- `ffmpeg-python` - Audio processing
- `python-dotenv` - Environment variables

## Support This Project

### ⭐ Telegram Stars

Donate directly within the bot using Telegram Stars!

### 💰 Cryptocurrency

<img src="https://img.shields.io/badge/Bitcoin-000000?style=for-the-badge&logo=bitcoin&logoColor=white" alt="Bitcoin"/>

```
15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp
```

<img src="https://img.shields.io/badge/Ethereum-3C3C3D?style=for-the-badge&logo=ethereum&logoColor=white" alt="Ethereum"/>

```
0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf
```

<img src="https://img.shields.io/badge/BNB-F3BA2F?style=for-the-badge&logo=binance&logoColor=white" alt="BNB"/>

```
0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf
```

<img src="https://img.shields.io/badge/Solana-9945FF?style=for-the-badge&logo=solana&logoColor=white" alt="Solana"/>

```
EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn
```

### 🏦 Exchange Platforms

<img src="https://img.shields.io/badge/Binance-FCD535?style=for-the-badge&logo=binance&logoColor=white" alt="Binance"/>

- **URL:** https://app.binance.com/uni-qr/Uzof5Lrq
- **ID:** `1011264323`

<img src="https://img.shields.io/badge/Bybit-F7A600?style=for-the-badge&logo=bybit&logoColor=white" alt="Bybit"/>

- **URL:** https://i.bybit.com/W2abUWF
- **ID:** `467077834`

### 💳 Traditional

<img src="https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="PayPal"/>

https://www.paypal.com/ncp/payment/W78F6W4TXZ4CS

Jazakallahu Khairan! 🤲

## License

Educational use. See individual API terms of service.

**Source:** github.com/yourusername/qbot
