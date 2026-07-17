"""Tests for core.subtitles — timestamp formatting and SRT/LRC builders."""
from core.subtitles import _lrc_ts, _srt_ts, build_lrc, build_srt


def test_srt_timestamp_format():
    assert _srt_ts(0.0) == "00:00:00,000"
    assert _srt_ts(1.5) == "00:00:01,500"
    assert _srt_ts(3661.0) == "01:01:01,000"


def test_lrc_timestamp_format():
    assert _lrc_ts(0.0) == "[00:00.00]"
    assert _lrc_ts(65.0) == "[01:05.00]"
    assert _lrc_ts(125.5) == "[02:05.50]"


def test_build_srt_emits_cumulative_timing():
    pairs = [(1, "abc"), (2, "def")]
    durations = [1.0, 2.0]
    srt = build_srt(pairs, durations)
    assert "1\n00:00:00,000 --> 00:00:01,000\nabc (1)" in srt
    assert "2\n00:00:01,000 --> 00:00:03,000\ndef (2)" in srt


def test_build_lrc_includes_headers():
    pairs = [(1, "abc")]
    lrc = build_lrc(pairs, durations=[1.0], title="T", artist="A")
    assert "[ti:T]" in lrc
    assert "[ar:A]" in lrc
    assert "[00:00.00]abc (1)" in lrc


def test_build_srt_raises_on_missing_duration():
    import pytest

    with pytest.raises(IndexError):
        build_srt([(1, "x")], durations=[])
