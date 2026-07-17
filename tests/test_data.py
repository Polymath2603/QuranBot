"""Tests for core.data — basmala handling and sura metadata helpers."""
from core.data import (
    get_sura_aya_count,
    get_sura_display_name,
    get_sura_name,
    get_sura_start_index,
    replace_basmala_symbol,
    strip_basmala,
)


def test_strip_basmala_removes_prefix_on_normal_sura():
    # Sura 2 (Al-Baqarah) aya 1 carries the basmala in Uthmani text.
    text = "بسم الله الرحمن الرحيم الذى"  # simplified stand-in
    out = strip_basmala(text, sura=2, aya=1)
    assert not out.startswith("بسم الله")
    assert out.startswith("الذى")


def test_strip_basmala_noop_when_not_aya1():
    text = "بسم الله الرحمن الرحيم xyz"
    assert strip_basmala(text, sura=2, aya=5) == text


def test_strip_basmala_noop_for_sura1_and_sura9():
    text = "بسم الله الرحمن الرحيم xyz"
    assert strip_basmala(text, sura=1, aya=1) == text
    assert strip_basmala(text, sura=9, aya=1) == text


def test_replace_basmala_symbol_prefixed():
    text = "بسم الله الرحمن الرحيم الذى"
    out = replace_basmala_symbol(text, sura=2, aya=1)
    assert out.startswith("﷽")


def test_replace_basmala_symbol_noop_for_sura9():
    text = "بسم الله الرحمن الرحيم الذى"
    assert replace_basmala_symbol(text, sura=9, aya=1) == text


def test_sura_metadata_roundtrip(quran_data):
    # Sura 1 (Al-Fatiha) has 7 ayas and starts at index 0.
    assert get_sura_aya_count(quran_data, 1) == 7
    assert get_sura_start_index(quran_data, 1) == 0
    name = get_sura_name(quran_data, 1, lang="en")
    assert name  # non-empty
    display = get_sura_display_name(quran_data, 1, lang="en")
    assert display.startswith("Surah")
    assert get_sura_display_name(quran_data, 112, lang="ar").startswith("سورة")
