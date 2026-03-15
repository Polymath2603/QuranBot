"""image.py — Verse image generation.

Public API
----------
gen_verse_image(text, font_key, bg_key, resolution) -> bytes
render_verse_png(text, font_key, bg_key, resolution) -> Image  (caller closes)
to_arabic(n)    -> str   Arabic-Indic digits  (0→٠, 1→١ …)
to_number(n, font_key) -> str  arabic for uthmani, western for others
basmala_for_font(verse_text, sura, aya, font_key) -> str  ﷽ or raw text
clean_verse(text) -> str  Remove Quranic annotation marks
get_font(key, size) -> ImageFont
get_text_width(draw, text, font) -> int
wrap_text(draw, text, font, max_w) -> list[str]

No CDN, no channel — all caching is done via file_ids.json in utils.
"""
from __future__ import annotations

import logging
import re
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from config import (
    FONT_PATHS, IMAGE_DEFAULT_FONT,
    IMAGE_BACKGROUNDS, IMAGE_TEXT_COLORS, IMAGE_DEFAULT_BG,
    IMAGE_PADDING,
    IMAGE_RESOLUTIONS, DEFAULT_IMAGE_RESOLUTION,
)

logger = logging.getLogger(__name__)

# ── Arabic-Indic numerals ─────────────────────────────────────────────────────

_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"

def to_arabic(n: int) -> str:
    """Convert integer to Arabic-Indic digit string."""
    return "".join(_AR_DIGITS[int(d)] for d in str(n))

def to_number(n: int, font_key: str) -> str:
    """Arabic-Indic for uthmani font; western digits for all others."""
    return to_arabic(n) if font_key == "uthmani" else str(n)


# ── Basmala helper ────────────────────────────────────────────────────────────

BASMALA_GLYPH = "﷽"

def basmala_for_font(verse_text: str, font_key: str) -> str:
    """Return the basmala representation appropriate for font_key.

    uthmani → the actual Arabic text (already in verse_text prefix)
    others  → ﷽ glyph (single codepoint, renders as ligature in Amiri/Noto)
    """
    if font_key == "uthmani":
        # Return the raw text up to (not including) the body; caller extracts it.
        # We expose the glyph as fallback; extraction happens in _build_img_text.
        return verse_text   # sentinel: caller must use strip_basmala for the body
    return BASMALA_GLYPH


# ── Font cache ────────────────────────────────────────────────────────────────

_font_cache: dict[tuple, ImageFont.FreeTypeFont] = {}

def get_font(key: str, size: int) -> ImageFont.FreeTypeFont:
    ck = (key, size)
    if ck not in _font_cache:
        path = FONT_PATHS.get(key, FONT_PATHS[IMAGE_DEFAULT_FONT])
        try:
            _font_cache[ck] = ImageFont.truetype(path, size)
        except (IOError, OSError):
            try:
                _font_cache[ck] = ImageFont.truetype(FONT_PATHS[IMAGE_DEFAULT_FONT], size)
            except (IOError, OSError):
                _font_cache[ck] = ImageFont.load_default()
    return _font_cache[ck]


# ── Text measurement ──────────────────────────────────────────────────────────

def get_text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return int(bb[2] - bb[0])


# ── DP text wrapper ───────────────────────────────────────────────────────────

MIN_WORDS_PER_LINE = 4

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    n       = len(words)
    min_wpl = MIN_WORDS_PER_LINE if n >= MIN_WORDS_PER_LINE else 1
    sp_w    = get_text_width(draw, " ", font)
    ww      = [get_text_width(draw, w, font) for w in words]

    def line_px(i, j):
        return sum(ww[i:j]) + sp_w * max(0, j - i - 1)

    def try_k(k):
        if k > n or n < k * min_wpl:
            return None
        INF = float("inf")
        dp  = [[INF] * (k + 1) for _ in range(n + 1)]
        par = [[-1]  * (k + 1) for _ in range(n + 1)]
        dp[0][0] = 0.0
        for lv in range(1, k + 1):
            for j in range(lv * min_wpl, n + 1):
                if (n - j) < (k - lv) * min_wpl:
                    continue
                for i in range((lv - 1) * min_wpl, j - min_wpl + 1):
                    if dp[i][lv - 1] == INF:
                        continue
                    px = line_px(i, j)
                    if px > max_w:
                        continue
                    cost = dp[i][lv - 1] + px ** 2
                    if cost < dp[j][lv]:
                        dp[j][lv] = cost
                        par[j][lv] = i
        if dp[n][k] == INF:
            return None
        segs, j, lv = [], n, k
        while lv > 0:
            i = par[j][lv]
            segs.append(" ".join(words[i:j]))
            j, lv = i, lv - 1
        segs.reverse()
        return segs

    max_k = max(1, -(-n // min_wpl))
    for k in range(1, max_k + 1):
        r = try_k(k)
        if r is not None:
            return r
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if line_px(0, len(cur)) > max_w and len(cur) > 1:
            lines.append(" ".join(cur[:-1]))
            cur = [w]
    lines.append(" ".join(cur))
    return lines


# ── Verse text cleaner ────────────────────────────────────────────────────────

def clean_verse(text: str) -> str:
    """
    Remove specific non-letter characters for cleaner visual display:
    - U+06E3: small sub س, not supported by font
    - U+0670: Dagger Alif (pronunciation guide, often visually distracting in some fonts).
    - U+06D6-U+06ED: Quranic annotation marks (pause signs, small high letters etc.) 
      that are not part of the core letters but are pronunciation/recitation guides.
    """
    text = re.sub(r'\u06E3', '', text)
    # text = re.sub(r'\u0670', '', text)
    # text = re.sub(r'[\u06D6-\u06ED]', '', text)
    return text


# ── Layout constants ──────────────────────────────────────────────────────────

FONT_SIZE_MAX = 38
FONT_SIZE_MIN = 24
LINE_SPACING  = 1.5
BLANK         = "\x00"    # sentinel for half-height spacer line


# ── Core renderer ─────────────────────────────────────────────────────────────

def render_verse_png(
    text:       str,
    font_key:   str = IMAGE_DEFAULT_FONT,
    bg_key:     str = IMAGE_DEFAULT_BG,
    resolution: str = DEFAULT_IMAGE_RESOLUTION,
) -> Image.Image:
    """Render Arabic verse text to a PIL Image.

    resolution:
      "auto"      → auto-height, natural width (1080px), content-fitted
      "portrait"  → 1080×1920 fixed canvas
      "landscape" → 1920×1080 fixed canvas
    Caller must close the returned Image.
    """
    PADDING = IMAGE_PADDING
    fixed   = IMAGE_RESOLUTIONS.get(resolution)   # None = auto-height
    canvas_w = fixed[0] if fixed else 1080
    max_w   = canvas_w - 2 * PADDING
    bg      = IMAGE_BACKGROUNDS.get(bg_key, IMAGE_BACKGROUNDS[IMAGE_DEFAULT_BG])
    fg      = IMAGE_TEXT_COLORS.get(bg_key, IMAGE_TEXT_COLORS[IMAGE_DEFAULT_BG])

    # ── Choose font size that fits all text in max_w ──────────────────────
    fs = FONT_SIZE_MAX
    while fs >= FONT_SIZE_MIN:
        probe = Image.new("RGBA", (1, 1))
        draw  = ImageDraw.Draw(probe)
        font  = get_font(font_key, fs)
        ok    = True
        for para in text.split("\n"):
            if not para.strip():
                continue
            for line in wrap_text(draw, para, font, max_w):
                if get_text_width(draw, line, font) > max_w:
                    ok = False; break
            if not ok: break
        probe.close()
        if ok:
            break
        next_fs = max(FONT_SIZE_MIN, int(fs * 0.88))
        if next_fs == fs: break
        fs = next_fs

    # ── Build layout (lines + blank spacers) ──────────────────────────────
    probe = Image.new("RGBA", (1, 1))
    draw  = ImageDraw.Draw(probe)
    font  = get_font(font_key, fs)

    layout: list[str] = []
    paragraphs = text.split("\n")
    for p_idx, para in enumerate(paragraphs):
        stripped = para.strip()
        if not stripped:
            layout.append(BLANK)
            continue
        layout.extend(wrap_text(draw, stripped, font, max_w))
        if p_idx < len(paragraphs) - 1:
            layout.append(BLANK)
    probe.close()

    # ── Compute canvas size ────────────────────────────────────────────────
    line_h  = int(fs * LINE_SPACING)
    half_h  = line_h // 2

    if fixed:
        fixed_h = fixed[1]
        total_h = sum(half_h if ln == BLANK else line_h for ln in layout)
        y       = (fixed_h - total_h) // 2
        canvas_h = fixed_h
    else:
        total_h = sum(half_h if ln == BLANK else line_h for ln in layout)
        canvas_h = total_h + 2 * PADDING
        y       = PADDING

    # ── Draw ──────────────────────────────────────────────────────────────
    img  = Image.new("RGBA", (canvas_w, canvas_h), bg)
    draw = ImageDraw.Draw(img)

    for ln in layout:
        if ln == BLANK:
            y += half_h; continue
        lw = get_text_width(draw, ln, font)
        x  = (canvas_w - lw) // 2

        # Slight stroke to increase font weight artificially
        draw.text((x, y), ln, font=font, fill=fg, direction="rtl")
        y += line_h

    del draw
    return img


# ── Public API ────────────────────────────────────────────────────────────────

def gen_verse_image(
    text:       str,
    font_key:   str = IMAGE_DEFAULT_FONT,
    bg_key:     str = IMAGE_DEFAULT_BG,
    resolution: str = DEFAULT_IMAGE_RESOLUTION,
) -> bytes:
    """Render verse text to PNG bytes."""
    # clean_verse removes Dagger Alif and Quranic pause/annotation marks
    # to ensure a cleaner visual appearance in video frames.
    cleaned = clean_verse(text)

    img = render_verse_png(cleaned, font_key=font_key, bg_key=bg_key, resolution=resolution)
    try:
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    finally:
        img.close()
