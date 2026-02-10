"""
Settings management module: Handles user preferences and configuration.
"""

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_SETTINGS = {
    "voice": "Nasser_Alqatami_128kbps",
    "reminder": {
        "enabled": False,
        "pages": 1,
        "time": "08:00",
        "progress": 0
    },
    "sendText": {
        "enabled": False,
        "format": "normal"  # normal, lrc, srt
    },
    "textSource": "hafs",  # hafs, tajweed, warsh
    "language": "ar"  # ar, en
}


class Settings:
    """Manages user settings with file persistence."""
    
    def __init__(self, settings_file: Path):
        """
        Initialize settings from file or defaults.
        
        Args:
            settings_file: Path to settings.json file
        """
        self.settings_file = settings_file
        self.data = self._load_or_create()
    
    def _load_or_create(self) -> Dict[str, Any]:
        """Load settings from file or create with defaults."""
        if self.settings_file.exists():
            try:
                return json.loads(self.settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Corrupted file, use defaults
                return DEFAULT_SETTINGS.copy()
        else:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            self._save(DEFAULT_SETTINGS.copy())
            return DEFAULT_SETTINGS.copy()
    
    def _save(self, data: Dict[str, Any]) -> None:
        """Save settings to file."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value and save."""
        self.data[key] = value
        self._save(self.data)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        self.data.update(updates)
        self._save(self.data)
    
    def reset(self) -> None:
        """Reset settings to defaults."""
        self.data = DEFAULT_SETTINGS.copy()
        self._save(self.data)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like assignment."""
        self.set(key, value)