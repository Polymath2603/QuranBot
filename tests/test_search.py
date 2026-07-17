"""Tests for core.search — Arabic normalization and full-text search."""
from core.search import make_snippet, normalize_arabic, search


def test_normalize_collapses_alif_variants():
    # إ أ آ ٱ ا all collapse to ا
    assert normalize_arabic("إبراهيم") == normalize_arabic("ابراهيم")
    assert "ا" in normalize_arabic("إبراهيم")


def test_normalize_removes_dagger_alif_and_diacritics():
    # Dagger alif (U+0670) and tashkeel vanish; word spaces are preserved.
    assert "لا اله الا الله" == normalize_arabic("لاَٰ إِلَٰهَ إِلَّا اللَّٰهُ")


def test_normalize_empty_input():
    assert normalize_arabic("") == ""


def test_search_requires_minimum_query_length(simple_verses, quran_data):
    assert search(quran_data, simple_verses, "ab") == []


def test_search_finds_known_phrase(simple_verses, quran_data):
    # "الحمد لله" (Alhamdulillah) appears in Al-Fatiha aya 2 (aya 1 is the basmala).
    results = search(quran_data, simple_verses, "الحمد لله")
    assert results
    assert all("sura" in r and "aya" in r for r in results)
    assert results[0]["sura"] == 1 and results[0]["aya"] == 2


def test_make_snippet_highlights_match():
    verse = "الحمد لله رب العالمين"
    snip = make_snippet(verse, "الحمد لله")
    assert "<b>" in snip  # match wrapped in bold


def test_make_snippet_fallback_when_no_match():
    verse = "الحمد لله رب العالمين"
    snip = make_snippet(verse, "zzznotfound")
    assert snip == verse[:120]
