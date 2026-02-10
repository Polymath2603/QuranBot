"""
QBot core module: Main interfaces for data, audio, settings, and search.
"""

from .audio import (
    AudioGenerationError,
    gen_lrc,
    gen_mp3,
    gen_srt,
    gen_timings,
)
from .data import (
    get_sura_aya_count,
    get_sura_name,
    load_quran_data,
    load_quran_text,
    load_voices,
)
from .search import format_search_results, search_verses
from .settings import DEFAULT_SETTINGS, Settings

__all__ = [
    # Data module
    "load_quran_data",
    "load_quran_text",
    "load_voices",
    "get_sura_name",
    "get_sura_aya_count",
    # Audio module
    "gen_mp3",
    "gen_lrc",
    "gen_srt",
    "gen_timings",
    "AudioGenerationError",
    # Settings module
    "Settings",
    "DEFAULT_SETTINGS",
    # Search module
    "search_verses",
    "format_search_results",
]