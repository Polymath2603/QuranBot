import sys
from pathlib import Path

import pytest

# Make the repo root importable as a flat package (same as running `python3 bot.py`).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data import load_quran_data, load_quran_text, load_quran_text_simple  # noqa: E402


@pytest.fixture(scope="session")
def quran_data():
    return load_quran_data(ROOT / "data")


@pytest.fixture(scope="session")
def verses():
    return load_quran_text(ROOT / "data")


@pytest.fixture(scope="session")
def simple_verses():
    return load_quran_text_simple(ROOT / "data")
