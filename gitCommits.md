# Git Commits Log

## [2026-02-12] Major Release: QBot v1.1 - Unified Handlers and UI/UX Refinement

This update polishes the QBot experience by unifying handlers, simplifying the NLU engine, and improving file/text delivery logic.

### Core Logic Refinements

- **Unified Sura Handlers**: Inputting a sura name now presents a range-based interface (1-last) with Audio, Text, and Tafsir options, providing a consistent experience.
- **Removed Cross-Surah Logic**: Stripped legacy cross-surah functionality from NLU and bot routing to prevent errors and maintain simplified user interaction.
- **Long Text Optimization**: Implemented a "file-only" rule for messages exceeding 4000 characters. These are now sent exclusively as TXT/SRT/LRC files to ensure full content delivery.
- **Dynamic Filenames**: Files sent to the user (audio and text) now use the "Sura Name (Range)" as the filename (e.g., "Al-Fatihah (1-7).mp3"), matching the display title perfectly.

### UI & UX Polish

- **Settings Simplified**: Hidden the "Text Source" toggle from the settings menu while preserving the internal selection logic for potential future use.
- **Metadata Consistency**: All audio generation paths now embed the correct reciter mapping and metadata tags correctly.
- **Search Precision**: Fixed page offsets and verse mapping shifts for high-accuracy results.

### Project Cleanup

- Removed legacy `core/` directory and redundant test scripts (`verify_nlu.py`).
- Purged unused assets from `data/` including non-API tafsir data, unused translations, and redundant metadata files.
- Cleaned up unused dependencies in `bot.py` (e.g., `downloader.download_sura`).
