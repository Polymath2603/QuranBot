# QBot: Quran Telegram Bot

A high-performance Telegram bot for accessing the Quran with natural language search, recitation playback, and integrated Tafsir.

## Features

- **Natural Language Search**: Find verses using everyday language in both Arabic and English (e.g., "Baqarah 255", "صفحة 10", "1:1-5").
- **Quality Audio**: Stream or download recitations from various renowned reciters with embedded metadata.
- **Integrated Tafsir**: Access verse interpretations (Tafsir Al-Muyassar and others) directly in the chat.
- **Multiple Formats**: Export verses as formatted text, SRT (subtitles), or LRC (lyrics) files.
- **Page Navigation**: Browse the Quran by page with built-in navigation buttons.
- **Localization**: Full support for Arabic and English interfaces.

## Quick Start

1. **Clone and Install**:

   ```bash
   git clone https://github.com/yourusername/QuranBot
   cd qbot
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and add your `TELEGRAM_BOT_TOKEN`.

3. **Run**:
   ```bash
   python bot.py
   ```

## Usage Examples

- **Direct Access**: `2:255` or `Al-Fatihah 1-7`
- **Page View**: `page 1` or `صفحة 604`
- **Keyword Search**: `الرحمن` or `Merciful`
- **Navigation**: Use the provided inline buttons to toggle between audio, text, and tafsir.

## Project Structure

- `bot.py`: Core bot logic and Telegram interactions.
- `nlu.py`: Natural Language Understanding for query parsing.
- `audio.py`: Audio processing and metadata embedding.
- `search.py`: Search engine with Arabic text normalization.
- `data/`: Local storage for Quran metadata and cached audio.

## Support

If you find this project useful, you can support its development through any of the following methods:

### 🌟 Telegram Stars

Support directly within the bot using Telegram Stars.

### 💳 Traditional Methods

- **PayPal**: [Donate via PayPal](https://www.paypal.com/ncp/payment/W78F6W4TXZ4CS)

### 📈 Exchange Platforms

- **Binance**: [QR Link](https://app.binance.com/uni-qr/Uzof5Lrq) (ID: `1011264323`)
- **Bybit**: [QR Link](https://i.bybit.com/W2abUWF) (ID: `467077834`)

### 💰 Cryptocurrency

- **BTC**: `15kPSKNLEgVH6Jy3RtNaT2mPsxTMS6MAEp`
- **ETH/BNB**: `0xc4f7076dd25a38f2256b5c23b8ca859cc42924cf`
- **Solana**: `EWcxGVtbohy8CdFLb2HNUqSHdecRiWKLywgMLwsXByhn`

---

Jazakallahu Khairan! 🤲
