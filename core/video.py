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

from config import (
    VIDEO_FPS, VIDEO_FADE_DURATION, VIDEO_SYNC_OFFSET,
    VIDEO_SIZES, VIDEO_DEFAULT_RATIO,
    IMAGE_DEFAULT_FONT, VIDEO_DEFAULT_FONT, VIDEO_DEFAULT_BG, VIDEO_BACKGROUNDS,
    FFMPEG_BIN, FFPROBE_BIN,
)
from .image import _font, _wrap, _text_w, _clean_verse, to_arabic, to_number

logger = logging.getLogger(__name__)

_VIDEO_TEXT_COLOR = (255, 255, 255, 255)


def _render_frame(text: str, size: tuple, font_key: str, bg_key: str):
    """Render one video frame PNG at a fixed (W, H) canvas size.

    Unlike image.py's auto-height render, video needs every frame the same
    fixed resolution so FFmpeg can concat them without rescaling.
    """
    from PIL import Image as PILImage, ImageDraw as PILDraw
    from config import VIDEO_PADDING as PADDING, IMAGE_BACKGROUNDS, IMAGE_TEXT_COLORS, IMAGE_DEFAULT_BG
    W, H  = size
    max_w = W - 2 * PADDING
    bg    = (0, 0, 0, 255)
    fg    = IMAGE_TEXT_COLORS.get(bg_key, IMAGE_TEXT_COLORS[IMAGE_DEFAULT_BG])

    img  = PILImage.new("RGBA", size, bg)
    draw = PILDraw.Draw(img)

    fs = 36
    fs_min = 22
    chosen_lines = [text]
    chosen_fs    = fs

    while fs >= fs_min:
        font  = _font(font_key, fs)
        lines, ok = [], True
        for para in text.split("\n"):
            pl = _wrap(draw, para.strip(), font, max_w)
            for line in pl:
                if _text_w(draw, line, font) > max_w:
                    ok = False; break
            if not ok: break
            lines.extend(pl)
        if ok:
            line_h = int(fs * 1.45)
            if len(lines) * line_h <= H - 2 * PADDING:
                chosen_lines = lines; chosen_fs = fs; break
        next_fs = max(fs_min, int(fs * 0.88))
        if next_fs == fs:
            chosen_lines = _wrap(draw, text, _font(font_key, fs), max_w)
            chosen_fs    = fs; break
        fs = next_fs

    font    = _font(font_key, chosen_fs)
    line_h  = int(chosen_fs * 1.45)
    total_h = len(chosen_lines) * line_h
    y       = (H - total_h) // 2

    for line in chosen_lines:
        if not line.strip():
            y += line_h; continue
        lw = _text_w(draw, line, font)
        x  = (W - lw) // 2
        draw.text((x, y), line, font=font, fill=fg, direction="rtl")
        y += line_h

    del draw
    return img


def _build_entries(verses_list: list, start_aya: int, verse_durations: list,
                   sura: int = 0, font_key: str = "uthmani") -> list:
    """Build timed text entries for video frames.

    Basmala is always stripped — not shown in video.
    Font-conditional numbers: uthmani → Arabic-Indic (٣), others → western (3).
    """
    from .data import strip_basmala
    entries, t = [], 0.0
    for i, verse in enumerate(verses_list):
        dur        = verse_durations[i]
        aya_i      = start_aya + i
        num        = to_number(aya_i, font_key)
        stripped   = strip_basmala(verse, sura, aya_i) if sura else verse
        cleaned    = _clean_verse(stripped)
        frame_text = f"{cleaned} ({num})"
        entries.append({"text": frame_text, "start": t, "end": t + dur})
        t += dur
    return entries


# ── FFmpeg helpers ────────────────────────────────────────────────────────────

def _run(cmd: list) -> None:
    full = [FFMPEG_BIN, "-y", "-threads", "2"] + [str(x) for x in cmd]
    logger.debug("ffmpeg: %s", " ".join(full))
    r = subprocess.run(full, capture_output=True, start_new_session=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))

def _probe_audio_duration(path: Path):
    try:
        r = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
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

def _out_filename(voice, sura, range_start, range_end, ratio, bg_key, font_key) -> str:
    ratio_bit = 0 if ratio == "landscape" else 1
    range_id  = f"{sura:03d}{range_start:03d}{range_end:03d}"
    return f"{voice}_{range_id}_{ratio_bit}_{bg_key[:3]}_{font_key[:3]}.mp4"


# ── Main pipeline ─────────────────────────────────────────────────────────────

def gen_video(
    verses_list: list,
    start_aya: int,
    title: str,
    sura: int,
    voice: str            = "",
    audio_path            = None,
    output_dir: Path      = None,
    ratio: str            = VIDEO_DEFAULT_RATIO,
    bg_key: str           = VIDEO_DEFAULT_BG,
    font_key: str         = VIDEO_DEFAULT_FONT,
    verse_durations: list = None,
    progress_cb           = None,
) -> Path:
    """
    Generate a video for the given verses.
    Always: black background, white text, no border.
    Ratio controls output dimensions (landscape/portrait).
    Returns the path to the output .mp4 (cached if already exists).
    """
    range_start = start_aya
    range_end   = start_aya + len(verses_list) - 1

    def _progress(pct, msg=""):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    size   = VIDEO_SIZES.get(ratio, VIDEO_SIZES[VIDEO_DEFAULT_RATIO])
    vw, vh = size

    entries    = _build_entries(verses_list, start_aya, verse_durations, sura=sura, font_key=font_key)
    text_total = entries[-1]["end"] if entries else 10.0

    audio_dur = None
    if audio_path and Path(audio_path).exists():
        audio_dur = _probe_audio_duration(Path(audio_path))
    total_dur = audio_dur if audio_dur and audio_dur > 0 else text_total

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    out_name = _out_filename(voice, sura, range_start, range_end, ratio, bg_key, font_key)
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
            img = _render_frame(text=entry["text"], size=size, font_key=font_key, bg_key=bg_key)
            p   = tmp / f"verse_{idx:04d}.png"
            img.save(str(p))
            img.close()          # free PIL memory immediately
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

        # Background via lavfi color source (user-configurable)
        bg_hex = VIDEO_BACKGROUNDS.get(bg_key, VIDEO_BACKGROUNDS[VIDEO_DEFAULT_BG])
        filters = [
            f"color=c={bg_hex}:size={vw}x{vh}:rate={VIDEO_FPS}:duration={total_dur:.4f}[bg]",
            (f"[0:v]"
             f"setpts=PTS+{sync}/TB,"
             f"trim=start=0:end={total_dur:.4f},"
             f"setpts=PTS-STARTPTS,"
             f"scale={vw}:{vh},setsar=1,"
             f"colorkey=black:0.05:0.1[txt]"),
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
