"""
video.py — Video generation for QBot.

Pipeline:
  1. Wrap text: >= 4 words per line (DP balancer).
  2. Render each verse as RGBA PNG (white text, no border, black bg).
  3. Encode each PNG → clip with fade-in/fade-out baked in.
  4. Concatenate clips → silent text track (concat demuxer, -c:v copy).
  5. Final FFmpeg pass:
       - Black background (solid color lavfi source).
       - Text track: sync offset + loop/trim to audio duration.
       - Audio is master clock; output = exact audio duration.

Ratio (landscape/portrait) controls output resolution from VIDEO_SIZES.
Progress callback: gen_video accepts progress_cb(pct: int, msg: str).
"""

import json, logging, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_FPS, VIDEO_FADE_DURATION, VIDEO_SYNC_OFFSET,
    VIDEO_FONT_SIZE, VIDEO_MIN_FONT_SIZE,
    VIDEO_PADDING, VIDEO_FALLBACK_DUR, FONT_PATH,
    VIDEO_SIZES, VIDEO_DEFAULT_RATIO,
)

logger = logging.getLogger(__name__)

# ── Font cache ────────────────────────────────────────────────────────────────

_font_cache: dict = {}

def _font(size: int):
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
        except IOError:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


# ── Text measurement ──────────────────────────────────────────────────────────

def _text_w(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


# ── Text wrapping — minimum 4 words per line ──────────────────────────────────

MIN_WORDS_PER_LINE = 4

def _wrap(draw, text: str, font, max_w: int) -> list:
    words = text.split()
    if not words:
        return [""]

    n       = len(words)
    min_wpl = MIN_WORDS_PER_LINE if n >= MIN_WORDS_PER_LINE else 1
    sp_w    = _text_w(draw, " ", font)
    ww      = [_text_w(draw, w, font) for w in words]

    def line_px(i, j):
        return sum(ww[i:j]) + sp_w * max(0, j - i - 1)

    def try_k(k):
        if k > n or n < k * min_wpl:
            return None
        INF = float("inf")
        dp  = [[INF] * (k + 1) for _ in range(n + 1)]
        par = [[-1]  * (k + 1) for _ in range(n + 1)]
        dp[0][0] = 0.0
        for l in range(1, k + 1):
            for j in range(l * min_wpl, n + 1):
                if (n - j) < (k - l) * min_wpl:
                    continue
                for i in range((l - 1) * min_wpl, j - min_wpl + 1):
                    if dp[i][l - 1] == INF:
                        continue
                    px = line_px(i, j)
                    if px > max_w:
                        continue
                    cost = dp[i][l - 1] + px ** 2
                    if cost < dp[j][l]:
                        dp[j][l] = cost
                        par[j][l] = i
        if dp[n][k] == INF:
            return None
        segs, j, l = [], n, k
        while l > 0:
            i = par[j][l]
            segs.append(" ".join(words[i:j]))
            j, l = i, l - 1
        segs.reverse()
        return segs

    max_k = max(1, -(-n // min_wpl))
    for k in range(1, max_k + 1):
        r = try_k(k)
        if r is not None:
            return r

    # Hard-wrap fallback
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if line_px(0, len(cur)) > max_w and len(cur) > 1:
            lines.append(" ".join(cur[:-1]))
            cur = [w]
    lines.append(" ".join(cur))
    return lines


# ── PNG renderer ──────────────────────────────────────────────────────────────

# Fixed style: white text, no border/shadow, black background baked into PNG
_TEXT_COLOR   = (255, 255, 255, 255)
_BG_COLOR     = (0, 0, 0, 255)

def render_verse_png(text: str, size: tuple) -> Image.Image:
    W, H  = size
    max_w = W - 2 * VIDEO_PADDING

    img  = Image.new("RGBA", size, _BG_COLOR)
    draw = ImageDraw.Draw(img)

    fs           = VIDEO_FONT_SIZE
    chosen_lines = [text]
    chosen_fs    = fs

    while fs >= VIDEO_MIN_FONT_SIZE:
        font  = _font(fs)
        lines = []
        ok    = True
        for para in text.split("\n"):
            pl = _wrap(draw, para.strip(), font, max_w)
            for line in pl:
                if _text_w(draw, line, font) > max_w:
                    ok = False; break
            if not ok:
                break
            lines.extend(pl)
        if ok:
            line_h = int(fs * 1.45)
            if len(lines) * line_h <= H - 2 * VIDEO_PADDING:
                chosen_lines = lines; chosen_fs = fs; break
        next_fs = max(VIDEO_MIN_FONT_SIZE, int(fs * 0.88))
        if next_fs == fs:
            chosen_lines = _wrap(draw, text, _font(fs), max_w)
            chosen_fs    = fs; break
        fs = next_fs

    font   = _font(chosen_fs)
    line_h = int(chosen_fs * 1.45)
    total_h = len(chosen_lines) * line_h
    y       = (H - total_h) // 2

    for line in chosen_lines:
        if not line.strip():
            y += line_h; continue
        lw = _text_w(draw, line, font)
        x  = (W - lw) // 2
        draw.text((x, y), line, font=font, fill=_TEXT_COLOR, direction="rtl")
        y += line_h

    return img


# ── Timing ────────────────────────────────────────────────────────────────────

def _to_arabic_numerals(n: int) -> str:
    ar = "٠١٢٣٤٥٦٧٨٩"
    return "".join(ar[int(d)] for d in str(n))

def _build_entries(verses_list, start_aya, verse_durations):
    entries, t = [], 0.0
    for i, verse in enumerate(verses_list):
        dur = (
            verse_durations[i]
            if verse_durations and i < len(verse_durations) and verse_durations[i] > 0
            else VIDEO_FALLBACK_DUR
        )
        aya_num = _to_arabic_numerals(start_aya + i)
        entries.append({"text": f"{verse} {aya_num}", "start": t, "end": t + dur})
        t += dur
    return entries


# ── FFmpeg helpers ────────────────────────────────────────────────────────────

def _run(cmd: list) -> None:
    full = ["ffmpeg", "-y"] + [str(x) for x in cmd]
    logger.debug("ffmpeg: %s", " ".join(full))
    r = subprocess.run(full, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))

def _probe_audio_duration(path: Path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "a", str(path)],
            capture_output=True,
        )
        streams = json.loads(r.stdout).get("streams", [])
        for s in streams:
            d = float(s.get("duration", 0))
            if d > 0:
                return d
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", path, e)
    return None


# ── Output filename — only ratio bit now ─────────────────────────────────────

def _out_filename(voice, sura, range_start, range_end, ratio) -> str:
    ratio_bit = 0 if ratio == "landscape" else 1
    range_id  = f"{sura:03d}{range_start:03d}{sura:03d}{range_end:03d}"
    return f"{voice}_{range_id}_{ratio_bit}.mp4"


# ── Main pipeline ─────────────────────────────────────────────────────────────

def gen_video(
    verses_list: list,
    start_aya: int,
    title: str,
    sura: int,
    range_start: int,
    range_end: int,
    voice: str            = "",
    audio_path            = None,
    output_dir: Path      = None,
    ratio: str            = VIDEO_DEFAULT_RATIO,
    verse_durations: list = None,
    progress_cb           = None,
) -> Path:
    """
    Generate a video for the given verses.
    Always: black background, white text, no border.
    Ratio controls output dimensions (landscape/portrait).
    Returns the path to the output .mp4 (cached if already exists).
    """

    def _progress(pct, msg=""):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    size   = VIDEO_SIZES.get(ratio, VIDEO_SIZES[VIDEO_DEFAULT_RATIO])
    vw, vh = size

    entries    = _build_entries(verses_list, start_aya, verse_durations)
    text_total = entries[-1]["end"] if entries else 10.0

    audio_dur = None
    if audio_path and Path(audio_path).exists():
        audio_dur = _probe_audio_duration(Path(audio_path))
    total_dur = audio_dur if audio_dur and audio_dur > 0 else text_total

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    out_name = _out_filename(voice, sura, range_start, range_end, ratio)
    out_path = output_dir / out_name

    if out_path.exists() and out_path.stat().st_size > 0:
        _progress(100, "cached")
        return out_path

    _progress(0, "rendering frames…")

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)

        # ── Step 1: Render verse PNGs (0–20%) ─────────────────────────────
        pngs = []
        n    = len(entries)
        for idx, entry in enumerate(entries):
            img = render_verse_png(text=entry["text"], size=size)
            p   = tmp / f"verse_{idx:04d}.png"
            img.save(str(p))
            pngs.append((p, entry["end"] - entry["start"]))
            _progress(int(20 * (idx + 1) / n), f"frame {idx+1}/{n}")

        # ── Step 2: Encode each PNG → verse clip (20–60%) ─────────────────
        half = VIDEO_FADE_DURATION / 2.0
        segs = []
        for idx, (png, dur) in enumerate(pngs):
            seg = tmp / f"seg_{idx:04d}.mp4"
            fi  = min(half, dur * 0.4)
            fo  = min(half, dur * 0.4)
            fo_start = max(0.0, dur - fo)
            vf = (
                f"fade=t=in:st=0:d={fi:.4f}:alpha=0,"
                f"fade=t=out:st={fo_start:.4f}:d={fo:.4f}:alpha=0"
            )
            _run([
                "-loop", "1", "-i", str(png),
                "-vf", vf,
                "-t", str(dur),
                "-r", str(VIDEO_FPS),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an",
                str(seg),
            ])
            segs.append(seg)
            _progress(20 + int(40 * (idx + 1) / n), f"encoding clip {idx+1}/{n}")

        # ── Step 3: Concatenate clips → silent text track (60–70%) ────────
        _progress(60, "concatenating…")
        concat_txt = tmp / "concat.txt"
        concat_txt.write_text("\n".join(f"file '{s}'" for s in segs), encoding="utf-8")
        text_track = tmp / "text_track.mp4"
        _run([
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c:v", "copy", "-an",
            str(text_track),
        ])

        # ── Step 4: Final pass — black bg + text + audio ──────────────────
        _progress(70, "compositing…")

        sync = VIDEO_SYNC_OFFSET

        # Text track input (looped)
        txt_inputs = ["-stream_loop", "-1", "-i", str(text_track)]

        # Black background via lavfi color source
        filters = [
            f"color=c=0x141414:size={vw}x{vh}:rate={VIDEO_FPS}:duration={total_dur:.4f}[bg]",
            (f"[0:v]"
             f"setpts=PTS+{sync}/TB,"
             f"trim=start=0:end={total_dur:.4f},"
             f"setpts=PTS-STARTPTS,"
             f"scale={vw}:{vh},setsar=1[txt]"),
            f"[bg][txt]overlay=0:0:format=auto,trim=0:{total_dur:.4f},setpts=PTS-STARTPTS[vout]",
        ]

        has_audio = bool(audio_path and Path(audio_path).exists())

        if has_audio:
            _run([
                *txt_inputs,
                "-i", str(audio_path),
                "-filter_complex", "; ".join(filters),
                "-map", "[vout]",
                "-map", "1:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(total_dur),
                str(out_path),
            ])
        else:
            _run([
                *txt_inputs,
                "-filter_complex", "; ".join(filters),
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-t", str(total_dur),
                str(out_path),
            ])

        _progress(100, "done")

    return out_path
