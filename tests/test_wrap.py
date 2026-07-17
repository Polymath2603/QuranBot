"""Tests for core.image.wrap_text — the Arabic line-balancing DP.

We use a deterministic fake ``draw`` whose textbbox width is proportional to
character count, so the balancer logic is exercised without real fonts.
"""

class _FakeDraw:
    """textbbox width = len(text) * unit; mimics ImageDraw interface used."""
    unit = 10
    def textbbox(self, xy, text, *a, **k):
        w = len(text) * self.unit
        return (0, 0, w, 10)


def _make_font():
    # Font identity is irrelevant; wrap_text only passes it to get_text_width.
    return object()


def test_empty_returns_single_blank():
    from core.image import wrap_text
    out = wrap_text(_FakeDraw(), "", _make_font(), max_w=200)
    assert out == [""]


def test_single_short_line_when_fits():
    from core.image import wrap_text
    # 3 words, each len 3 -> total ~ (3+3+3 + 2 spaces)*10 = 110 < 200
    out = wrap_text(_FakeDraw(), "abc def ghi", _make_font(), max_w=200)
    assert out == ["abc def ghi"]


def test_respects_min_words_per_line():
    from core.image import wrap_text
    draw = _FakeDraw()
    # 8 words, each len 3 -> per-word 30, space 10. Force narrow width so it
    # must wrap, but MIN_WORDS_PER_LINE==4 means each line keeps >=4 words
    # when the verse is long enough.
    words = " ".join(f"w{i}" for i in range(8))  # w0..w7, each len 2
    out = wrap_text(draw, words, _make_font(), max_w=120)
    assert all(len(line.split()) >= 4 for line in out)


def test_no_line_exceeds_max_width():
    from core.image import wrap_text
    draw = _FakeDraw()
    words = " ".join(f"word{i}" for i in range(12))  # each len 5
    max_w = 80
    out = wrap_text(draw, words, _make_font(), max_w=max_w)
    for line in out:
        # width = (sum word len + spaces) * unit(10); recompute
        w = len(line) * draw.unit
        assert w <= max_w, f"line '{line}' width {w} > {max_w}"


def test_balancer_prefers_even_lines_over_greedy():
    from core.image import wrap_text
    draw = _FakeDraw()
    # Construct words so greedy-left would leave a very short last line while
    # the DP balancer evens them out. Use equal-length words and an exact
    # fit for 2 lines of 4 words each.
    words = " ".join("xx" for _ in range(8))  # 8 words, len 2 each
    # per word 20, space 10. 4 words/line => (20*4 + 10*3)=110 per line.
    out = wrap_text(draw, words, _make_font(), max_w=110)
    # Ideal: exactly 2 lines of 4 words each.
    assert out == ["xx xx xx xx", "xx xx xx xx"]


def test_fewest_lines_respects_min_words():
    from core.image import MIN_WORDS_PER_LINE, wrap_text
    draw = _FakeDraw()
    # 12 equal words, max_w fits exactly 4 words/line (4*20 + 3*10 = 110).
    # Fewest lines = 3, and every line must keep >= MIN_WORDS_PER_LINE.
    words = " ".join("ww" for _ in range(12))
    out = wrap_text(draw, words, _make_font(), max_w=110)
    assert len(out) == 3
    counts = [len(line.split()) for line in out]
    assert all(c >= MIN_WORDS_PER_LINE for c in counts)
    assert sum(counts) == 12


def test_short_verse_allows_smaller_min():
    from core.image import wrap_text
    draw = _FakeDraw()
    # 3 words only (< MIN_WORDS_PER_LINE): each line may have 1 word.
    words = "aa bb cc"
    out = wrap_text(draw, words, _make_font(), max_w=40)  # 2 chars+space=30 <40, 3 overflow
    # Forces 3 lines of 1 word each (min_wpl=1 when n<MIN_WORDS_PER_LINE).
    assert out == ["aa", "bb", "cc"]
