# Git Commits Log

## [2026-02-12] Major Release: QBot v1.0 - Core Fixes, Enhancements & Polish

This major update consolidates all recent development work, fixing critical bugs, enhancing the user experience, and polishing the UI for a production-ready Quran Bot.

### Core Fixes & Performance

- **Search Precision**: Fixed a 28-verse mapping offset and a 1-page shift in results. Improved Arabic normalization for better recall.
- **Audio Reliability**: Fixed FFmpeg metadata errors, concatenation stream mapping, and implemented zero-padding for audio filenames (`001001.mp3`).
- **Database Persistence**: Moved all user preferences (language, reciter, text sources) from volatile context storage to a persistent SQLite database.
- **Improved NLU**: Enhanced the Natural Language Understanding engine to handle complex range queries (e.g., "Sura 1:3", "من 1 الى 5") and fixed cross-surah ambiguity.

### Feature Enhancements

- **Multiple Sources**: Integrated support for various Quran text sources (Uthmani, Tajweed, Warsh) and Tafsir sources (Muyassar, Jalalayn, etc.).
- **Text Exports**: Implemented formatted text downloads (SRT, LRC, TXT) with unified naming conventions matching the audio files.
- **UI & UX Polish**:
  - Stacked settings buttons into a clean 2-column layout.
  - Localized all source names and UI strings in both Arabic and English.
  - Added "Text" button to Surah download responses and Tafsir view.
  - Removed redundant buttons from audio messages for a cleaner chat history.

### Project Cleanup

- Removed legacy `core/` directory and redundant test scripts.
- Purged unused assets from `data/` including non-API tafsir data, unused translations, font files, and redundant images.
- Unified project structure around the root implementation.
- Standardized metadata embedding across all audio generation paths.
