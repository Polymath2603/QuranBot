# Changelog

All notable changes to QBot will be documented in this file.

## [2.0.0] - 2026-02-10

### Added

- **Natural Language Understanding (NLU)**
  - Intelligent parsing of Surah names and verse references in Arabic and English
  - Support for complex queries: "من سورة الفاتحة 1 الى البقرة 4"
  - Fuzzy matching for Surah names using rapidfuzz
  - Arabic character normalization (Alif, Hamza, Taa Marbuta, Ya variations)
- **Database Integration**
  - SQLite database for persistent user data
  - User model storing: telegram_id, language preference, custom settings
  - Automatic user registration on first interaction
- **Localization System**
  - Separate locale files (en.json, ar.json)
  - Default language: Arabic
  - Dynamic string loading based on user preference
  - Settings menu for language switching
- **Telegram Stars Donations**
  - Primary donation method with preset amounts (50, 100, 500 Stars)
  - Invoice generation and payment handling
  - Thank you messages after successful payment
- **Enhanced Audio Features**
  - Audio metadata: Title (Surah + Range), Artist (Reciter name)
  - Album art removal for cleaner files
  - Status message auto-deletion after audio is sent
  - Reply-to-message support for better context
- **Tafsir Integration**
  - Tafsir button on verse responses
  - Fetches Tafsir Al-Muyassar from AlQuran.cloud
  - Available for single verses
- **UI Improvements**
  - Removed "Download Sura" and "Tafsir" from main menu (NLU handles this)
  - Added "Our Channel" button
  - Improved text formatting with Arabic ornamental brackets `﴿ ... ﴾`
  - Verse numbers displayed in parentheses

### Changed

- **Default Language**: Changed from auto-detect to Arabic for all new users
- **Search Enhancement**: Improved Arabic text normalization for better search results
- **Text Format**: Updated to `📖 Surah (Verse Range) \n\n ﴿ text ﴾`
- **Donation Links**: Updated PayPal link to current payment URL

### Technical

- Updated `python-telegram-bot` to >=21.3 for Telegram Stars support
- Added `SQLAlchemy` for database ORM
- Added `rapidfuzz` for fuzzy string matching
- Refactored `bot.py` for better modularity
- Created `nlu.py` for intent detection
- Created `database.py` for data persistence
- Updated `audio.py` to handle metadata via FFmpeg

## [1.0.0] - Initial Release

### Features

- Basic Quran verse retrieval
- Audio playback from EveryAyah.com
- Search functionality
- Multiple reciter support
- Manual Surah selection
- Basic donation links (crypto, PayPal)
